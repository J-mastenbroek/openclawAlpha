#!/usr/bin/env python3
"""
Polymarket Real-Time Data Capturer
Hans's production implementation for live market data collection.
WebSocket + Gamma API integration for authentic market intelligence.
"""

import asyncio
import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time
import requests
import websockets
from bisect import bisect_right
from collections import deque
import os

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
RTDS_WS_URL = "wss://ws-live-data.polymarket.com"
SCAN_INTERVAL_SEC = 600
SCHEDULER_TICK_SEC = 1
START_BUFFER_SEC = 10
STOP_BUFFER_SEC = 10
LEVELS = 5
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

class PriceCache:
    """Cache oracle prices with time-based lookup"""
    def __init__(self, max_age_sec: int = 60 * 30):
        self.max_age_ms = max_age_sec * 1000
        self._ts: Dict[tuple[str, str], List[int]] = {}
        self._px: Dict[tuple[str, str], List[float]] = {}

    def add(self, source: str, asset: str, ts_ms: int, price: float) -> None:
        key = (source, asset)
        if key not in self._ts:
            self._ts[key] = []
            self._px[key] = []
        
        ts_arr = self._ts[key]
        px_arr = self._px[key]
        
        if not ts_arr or ts_ms >= ts_arr[-1]:
            ts_arr.append(ts_ms)
            px_arr.append(price)
        else:
            i = bisect_right(ts_arr, ts_ms)
            ts_arr.insert(i, ts_ms)
            px_arr.insert(i, price)
        
        cutoff = ts_arr[-1] - self.max_age_ms
        j = bisect_right(ts_arr, cutoff - 1)
        if j > 0:
            del ts_arr[:j]
            del px_arr[:j]

    def asof(self, source: str, asset: str, ts_ms: int) -> Tuple[Optional[int], Optional[float]]:
        key = (source, asset)
        ts_arr = self._ts.get(key)
        if not ts_arr:
            return None, None
        
        i = bisect_right(ts_arr, ts_ms) - 1
        if i < 0:
            return None, None
        
        return ts_arr[i], self._px[key][i]

class OrderBook:
    """Maintain live bid/ask levels"""
    def __init__(self, asset_id: str):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.asset_id = str(asset_id)

    def book(self, bids: List[dict], asks: List[dict]) -> None:
        bids_sorted = sorted(
            ((float(b["price"]), float(b["size"])) for b in bids),
            key=lambda x: x[0],
            reverse=True
        )[:LEVELS]
        asks_sorted = sorted(
            ((float(a["price"]), float(a["size"])) for a in asks),
            key=lambda x: x[0]
        )[:LEVELS]
        
        self.bids = dict(bids_sorted)
        self.asks = dict(asks_sorted)

    def snapshot(self) -> dict:
        out = {}
        bid_items = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:LEVELS]
        ask_items = sorted(self.asks.items(), key=lambda x: x[0])[:LEVELS]
        
        for i, (p, s) in enumerate(bid_items, 1):
            out[f"bid_price_{i}"] = p
            out[f"bid_size_{i}"] = s
        
        for i, (p, s) in enumerate(ask_items, 1):
            out[f"ask_price_{i}"] = p
            out[f"ask_size_{i}"] = s
        
        return out

class GammaClient:
    """Gamma API for market discovery and metadata"""
    def __init__(self):
        self.base = GAMMA_URL.rstrip("/")
        self.s = requests.Session()

    def get(self, path: str, params: dict = None) -> Any:
        r = self.s.get(f"{self.base}/{path.lstrip('/')}", params=params, timeout=(5, 15))
        r.raise_for_status()
        return r.json()

    def scan_15m_events(self, horizon_sec: int = 2 * 3600) -> List[dict]:
        out, offset = [], 0
        now = utc_now()
        lo = now - timedelta(seconds=horizon_sec)
        hi = now + timedelta(seconds=horizon_sec)
        
        for _ in range(20):
            data = self.get("events", {
                "order": "id",
                "ascending": "false",
                "limit": 200,
                "offset": offset,
                "closed": "false",
            })
            
            if not data:
                break
            
            for e in data:
                if not any(s.get("recurrence") == "15m" for s in e.get("series", [])):
                    continue
                
                start = e.get("eventStartTime") or e.get("startTime")
                if not start:
                    continue
                
                try:
                    st = parse_iso(start)
                except Exception:
                    continue
                
                if lo <= st <= hi:
                    out.append(e)
            
            offset += 200
        
        return out

    @staticmethod
    def extract_asset(e: dict) -> str:
        slug = (e.get("slug") or "").lower()
        for a in ("btc", "eth", "sol", "xrp"):
            if slug.startswith(a + "-"):
                return a
        
        for t in e.get("tags", []):
            s = (t.get("slug") or "").lower()
            if s in {"btc", "eth", "sol", "xrp"}:
                return s
        
        return slug.split("-")[0] if slug else "unknown"

    @staticmethod
    def token_pair(m: dict) -> Tuple[str, str]:
        ids = json.loads(m["clobTokenIds"])
        return str(ids[0]), str(ids[1])

async def rtds_prices_listener(cache: PriceCache, stop_evt: asyncio.Event) -> None:
    """Listen to real-time price data from RTDS"""
    sub_msg = {
        "action": "subscribe",
        "subscriptions": [
            {"topic": "crypto_prices_chainlink", "type": "update", "filters": ""},
            {"topic": "crypto_prices", "type": "update", "filters": ""},
        ],
    }
    
    while not stop_evt.is_set():
        try:
            async with websockets.connect(
                RTDS_WS_URL,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                print("[RTDS] connected", flush=True)
                await ws.send(json.dumps(sub_msg))
                print("[RTDS] subscribed", flush=True)
                
                while not stop_evt.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    except asyncio.TimeoutError:
                        break
                    
                    if not raw or not raw.strip():
                        continue
                    
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    
                    topic = msg.get("topic") or msg.get("payload", {}).get("topic")
                    payload = msg.get("payload") or {}
                    
                    ts = payload.get("timestamp")
                    val = payload.get("value")
                    sym = payload.get("symbol")
                    
                    if ts is None or val is None:
                        continue
                    
                    if topic == "crypto_prices_chainlink":
                        asset = sym.split("/")[0].lower() if sym and "/" in sym else None
                        if asset and asset in {"btc", "eth", "sol", "xrp"}:
                            try:
                                cache.add("cl", asset, int(ts), float(val))
                            except Exception:
                                continue
                    
                    elif topic == "crypto_prices":
                        sym = (sym or "").lower()
                        if sym.endswith("usdt"):
                            asset = sym[:-4]
                            if asset in {"btc", "eth", "sol", "xrp"}:
                                try:
                                    cache.add("bn", asset, int(ts), float(val))
                                except Exception:
                                    continue
        
        except Exception:
            pass
        
        if not stop_evt.is_set():
            print("[RTDS] closed -> reconnect", flush=True)
            await asyncio.sleep(0.2)

async def orderbook_listener(market_id: str, token_id: str, callback, stop_evt: asyncio.Event) -> None:
    """Listen to orderbook updates via CLOB WebSocket"""
    print(f"[CLOB-CONNECT] market={market_id} token={token_id[:6]}...", flush=True)
    
    try:
        async with websockets.connect(CLOB_WS_URL, ping_interval=None) as ws:
            await ws.send(json.dumps({"type": "market", "assets_ids": [token_id]}))
            print(f"[CLOB-SUBSCRIBED] market={market_id} token={token_id[:6]}...", flush=True)
            
            async def pinger():
                while not stop_evt.is_set():
                    try:
                        await ws.send("PING")
                    except Exception:
                        return
                    await asyncio.sleep(10)
            
            ping_task = asyncio.create_task(pinger())
            
            try:
                async for raw in ws:
                    if stop_evt.is_set():
                        break
                    
                    try:
                        payload = json.loads(raw)
                        if isinstance(payload, dict):
                            events = [payload]
                        elif isinstance(payload, list):
                            events = payload
                        else:
                            continue
                    except Exception:
                        continue
                    
                    for msg in events:
                        await callback(msg)
            
            finally:
                ping_task.cancel()
    
    except Exception as e:
        print(f"[CLOB] error: {e}", flush=True)

# Export for use in live_feed_updater
__all__ = [
    "PriceCache",
    "OrderBook",
    "GammaClient",
    "rtds_prices_listener",
    "orderbook_listener",
    "utc_now",
    "parse_iso",
]
