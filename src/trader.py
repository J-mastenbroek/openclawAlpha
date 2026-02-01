"""Paper trader for signal validation."""

import json
from typing import Dict, List, Optional
from datetime import datetime

class PaperTrader:
    """Simulate trading on detected signals without real capital."""
    
    def __init__(self, initial_capital: float = 100.0):
        self.capital = initial_capital
        self.positions = []  # List of open trades
        self.closed_trades = []  # Historical trades
        self.trades_log = []
    
    def execute_signal(self, signal: Dict, size: float = 10.0) -> Dict:
        """
        Execute a hypothetical trade on a signal.
        
        Strategy: 
        - Price momentum at 0.75-0.85 = "overweight" the stronger side
        - Bet on reversion OR continuation based on type
        - Size: Fixed $10 per signal (conservative)
        """
        if self.capital < size:
            return {"status": "rejected", "reason": "insufficient_capital"}
        
        signal_type = signal.get("type")
        market_id = signal.get("market_id")
        score = signal.get("_score", 0.5)
        
        # For momentum signals: bet on the direction
        if signal_type == "price_momentum":
            price = signal.get("price", 0.5)
            outcome = signal.get("outcome")
            
            # At 80% price, the market expects 80% success
            # But prices can be inefficient. Assume mean reversion slightly
            expected_return = 0.15 if price > 0.7 else -0.10
            
            position = {
                "id": len(self.positions),
                "market_id": market_id,
                "type": signal_type,
                "size": size,
                "entry_price": price,
                "outcome": outcome,
                "entry_time": datetime.now().isoformat(),
                "score": score,
                "expected_return": expected_return,
                "status": "open"
            }
            
            self.capital -= size
            self.positions.append(position)
            self.trades_log.append({
                "action": "ENTRY",
                "position_id": position["id"],
                "timestamp": datetime.now().isoformat(),
                "size": size,
                "capital_remaining": self.capital
            })
            
            return {
                "status": "accepted",
                "position_id": position["id"],
                "size": size,
                "capital_remaining": self.capital
            }
        
        return {"status": "rejected", "reason": "unknown_signal_type"}
    
    def close_position(self, position_id: int, exit_price: float) -> Dict:
        """Close an open position."""
        position = None
        for i, p in enumerate(self.positions):
            if p["id"] == position_id:
                position = p
                break
        
        if not position:
            return {"status": "rejected", "reason": "position_not_found"}
        
        # Calculate PnL
        entry_price = position["entry_price"]
        size = position["size"]
        
        # Simple model: if outcome wins, you keep the size
        # If you were right about inefficiency, you profit on the spread
        pnl = size * (exit_price - entry_price) / entry_price * 10  # 10x leverage assumption
        
        self.capital += size + pnl
        
        closed_position = position.copy()
        closed_position["exit_price"] = exit_price
        closed_position["pnl"] = pnl
        closed_position["pnl_percent"] = pnl / size * 100 if size > 0 else 0
        closed_position["status"] = "closed"
        closed_position["exit_time"] = datetime.now().isoformat()
        
        self.closed_trades.append(closed_position)
        self.positions.remove(position)
        
        self.trades_log.append({
            "action": "EXIT",
            "position_id": position_id,
            "timestamp": datetime.now().isoformat(),
            "pnl": pnl,
            "capital": self.capital
        })
        
        return {
            "status": "closed",
            "pnl": pnl,
            "pnl_percent": closed_position["pnl_percent"],
            "capital": self.capital
        }
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        return self.capital
    
    def get_stats(self) -> Dict:
        """Get trading statistics."""
        if not self.closed_trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "total_pnl": 0,
                "capital": self.capital
            }
        
        wins = [t for t in self.closed_trades if t["pnl"] > 0]
        losses = [t for t in self.closed_trades if t["pnl"] < 0]
        
        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
        
        return {
            "total_trades": len(self.closed_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(self.closed_trades) if self.closed_trades else 0,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "total_pnl": sum(t["pnl"] for t in self.closed_trades),
            "capital": self.capital
        }
    
    def save_trades(self, filename: str = "trades.jsonl"):
        """Save trades log."""
        with open(filename, "w") as f:
            for trade in self.trades_log:
                f.write(json.dumps(trade) + "\n")
