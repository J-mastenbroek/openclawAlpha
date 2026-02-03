"""
PolyWhale - Polymarket Whale Tracker & Trading Terminal

Core modules:
- whale_tracker: Monitor large wallet movements
- orderbook_analyzer: Detect irregular orderbook behavior
- trading_terminal: CLI trading interface with market intelligence
"""

from .whale_tracker import WhaleTracker
from .orderbook_analyzer import OrderbookAnalyzer
from .trading_terminal import TradingTerminal

__version__ = "0.1.0"
__all__ = ["WhaleTracker", "OrderbookAnalyzer", "TradingTerminal"]
