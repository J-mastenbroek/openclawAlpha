# PolyWhale - Polymarket Whale Tracker & Trading Terminal

Real-time whale tracking, orderbook analysis, and trading terminal for Polymarket prediction markets.

## Features

- **Whale Tracker**: Monitor large wallet movements and positions
- **Orderbook Monitor**: Detect irregular orderbook behavior and anomalies
- **Market Overview**: View all active Polymarket markets with real-time pricing
- **Trading Terminal**: Execute trades directly with market intelligence
- **Web Dashboard**: GitHub Pages site with live market data and whale activity

## Architecture

```
polywhale/
├── tracker/           # Whale detection & tracking
├── orderbook/         # Orderbook analysis & anomalies
├── terminal/          # CLI trading interface
├── api/              # REST API for market data
├── web/              # GitHub Pages dashboard (docs/)
└── scripts/          # Data collection & monitoring
```

## Live Dashboard

🔗 [PolyWhale Dashboard](https://j-mastenbroek.github.io/openclawAlpha)

## Getting Started

```bash
pip install -r requirements.txt
python -m polywhale tracker      # Start whale tracking
python -m polywhale terminal     # Open trading terminal
```

---

Building real-time market intelligence for Polymarket traders.
