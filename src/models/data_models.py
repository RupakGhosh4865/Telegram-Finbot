"""
Data models for the trading bot system.

This module contains all the data structures used throughout the application,
including market data, arbitrage opportunities, and configuration models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal


@dataclass
class OrderBookLevel:
    """Represents a single level in an order book."""
    
    price: float
    size: float
    
    def __post_init__(self):
        """Validate order book level data."""
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.size <= 0:
            raise ValueError("Size must be positive")


@dataclass
class MarketData:
    """Market data for a specific symbol and exchange."""
    
    symbol: str
    exchange: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    last_price: float
    timestamp: datetime
    
    def __post_init__(self):
        """Validate market data."""
        if self.bid_price <= 0 or self.ask_price <= 0:
            raise ValueError("Prices must be positive")
        if self.bid_size <= 0 or self.ask_size <= 0:
            raise ValueError("Sizes must be positive")
        if self.bid_price >= self.ask_price:
            raise ValueError("Bid price must be less than ask price")
    
    @property
    def spread_absolute(self) -> float:
        """Calculate absolute spread between bid and ask."""
        return self.ask_price - self.bid_price
    
    @property
    def spread_percentage(self) -> float:
        """Calculate percentage spread."""
        return (self.spread_absolute / self.bid_price) * 100
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        return (self.bid_price + self.ask_price) / 2
    
    def is_fresh(self, max_age_seconds: int = 30) -> bool:
        """Check if market data is fresh (within max_age_seconds)."""
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age <= max_age_seconds


@dataclass
class OrderBook:
    """Complete order book for a symbol on an exchange."""
    
    symbol: str
    exchange: str
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: datetime
    
    def __post_init__(self):
        """Validate order book data."""
        if not self.bids or not self.asks:
            raise ValueError("Order book must have both bids and asks")
        
        # Validate bid/ask ordering
        for i in range(len(self.bids) - 1):
            if self.bids[i].price < self.bids[i + 1].price:
                raise ValueError("Bids must be in descending order")
        
        for i in range(len(self.asks) - 1):
            if self.asks[i].price > self.asks[i + 1].price:
                raise ValueError("Asks must be in ascending order")
    
    @property
    def best_bid(self) -> OrderBookLevel:
        """Get the best bid (highest price)."""
        return self.bids[0]
    
    @property
    def best_ask(self) -> OrderBookLevel:
        """Get the best ask (lowest price)."""
        return self.asks[0]
    
    @property
    def market_data(self) -> MarketData:
        """Convert order book to market data format."""
        return MarketData(
            symbol=self.symbol,
            exchange=self.exchange,
            bid_price=self.best_bid.price,
            bid_size=self.best_bid.size,
            ask_price=self.best_ask.price,
            ask_size=self.best_ask.size,
            last_price=(self.best_bid.price + self.best_ask.price) / 2,
            timestamp=self.timestamp
        )


@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity between exchanges."""
    
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percentage: float
    spread_absolute: float
    timestamp: datetime
    estimated_profit: Optional[float] = None
    trade_size: Optional[float] = None
    
    def __post_init__(self):
        """Validate arbitrage opportunity data."""
        if self.buy_price <= 0 or self.sell_price <= 0:
            raise ValueError("Prices must be positive")
        if self.spread_percentage <= 0:
            raise ValueError("Spread percentage must be positive")
    
    def format_telegram_message(self) -> str:
        """Format arbitrage opportunity as Telegram message."""
        profit_info = ""
        if self.estimated_profit and self.trade_size:
            profit_info = f"\n💰 Est. Profit: ${self.estimated_profit:.2f} (Size: {self.trade_size})"
        
        return (
            f"🚨 **ARBITRAGE ALERT** 🚨\n\n"
            f"📊 **Symbol:** {self.symbol}\n"
            f"📈 **Buy:** {self.buy_exchange.upper()} @ ${self.buy_price:.4f}\n"
            f"📉 **Sell:** {self.sell_exchange.upper()} @ ${self.sell_price:.4f}\n"
            f"📊 **Spread:** {self.spread_percentage:.2f}% (${self.spread_absolute:.4f})\n"
            f"⏰ **Time:** {self.timestamp.strftime('%H:%M:%S UTC')}"
            f"{profit_info}"
        )
    
    def is_still_valid(self, current_data: Dict[str, MarketData], threshold: float) -> bool:
        """Check if arbitrage opportunity is still valid with current market data."""
        if self.buy_exchange not in current_data or self.sell_exchange not in current_data:
            return False
        
        buy_data = current_data[self.buy_exchange]
        sell_data = current_data[self.sell_exchange]
        
        current_spread = ((sell_data.ask_price - buy_data.bid_price) / buy_data.bid_price) * 100
        
        return current_spread >= threshold


@dataclass
class ConsolidatedBBO:
    """Consolidated Best Bid/Offer across multiple exchanges."""
    
    symbol: str
    best_bid_price: float
    best_bid_exchange: str
    best_ask_price: float
    best_ask_exchange: str
    mid_price: float
    timestamp: datetime
    spread_absolute: float = field(init=False)
    spread_percentage: float = field(init=False)
    all_exchanges: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields."""
        self.spread_absolute = self.best_ask_price - self.best_bid_price
        self.spread_percentage = (self.spread_absolute / self.best_bid_price) * 100
    
    def format_telegram_message(self, update_type: str = "update") -> str:
        """Format consolidated BBO as Telegram message."""
        emoji = "📊" if update_type == "update" else "🔍"
        
        return (
            f"{emoji} **CBBO - {self.symbol}**\n\n"
            f"📈 **Best Bid:** {self.best_bid_exchange.upper()} @ ${self.best_bid_price:.4f}\n"
            f"📉 **Best Ask:** {self.best_ask_exchange.upper()} @ ${self.best_ask_price:.4f}\n"
            f"📊 **Mid Price:** ${self.mid_price:.4f}\n"
            f"📏 **Spread:** {self.spread_percentage:.2f}% (${self.spread_absolute:.4f})\n"
            f"🏢 **Exchanges:** {', '.join(self.all_exchanges).upper()}\n"
            f"⏰ **Updated:** {self.timestamp.strftime('%H:%M:%S UTC')}"
        )
    
    def has_venue_changed(self, previous: 'ConsolidatedBBO') -> bool:
        """Check if best venue has changed since last update."""
        return (
            self.best_bid_exchange != previous.best_bid_exchange or
            self.best_ask_exchange != previous.best_ask_exchange
        )


@dataclass
class MonitoringConfig:
    """Configuration for monitoring sessions."""
    
    chat_id: int
    symbols: List[str]
    exchanges: List[str]
    threshold_percentage: float
    is_active: bool = True
    update_interval: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_update: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate monitoring configuration."""
        if not self.symbols:
            raise ValueError("At least one symbol must be specified")
        if not self.exchanges:
            raise ValueError("At least one exchange must be specified")
        if self.threshold_percentage <= 0:
            raise ValueError("Threshold percentage must be positive")
        if self.update_interval <= 0:
            raise ValueError("Update interval must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'chat_id': self.chat_id,
            'symbols': self.symbols,
            'exchanges': self.exchanges,
            'threshold_percentage': self.threshold_percentage,
            'is_active': self.is_active,
            'update_interval': self.update_interval,
            'created_at': self.created_at.isoformat(),
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoringConfig':
        """Create from dictionary."""
        return cls(
            chat_id=data['chat_id'],
            symbols=data['symbols'],
            exchanges=data['exchanges'],
            threshold_percentage=data['threshold_percentage'],
            is_active=data['is_active'],
            update_interval=data['update_interval'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_update=datetime.fromisoformat(data['last_update']) if data['last_update'] else None
        )


@dataclass
class ExchangeInfo:
    """Information about a supported exchange."""
    
    name: str
    display_name: str
    base_url: str
    is_active: bool = True
    rate_limit: int = 100
    supported_markets: List[str] = field(default_factory=lambda: ["spot"])
    
    def __post_init__(self):
        """Validate exchange information."""
        if not self.name or not self.display_name:
            raise ValueError("Exchange name and display name are required")


@dataclass
class SymbolInfo:
    """Information about a trading symbol."""
    
    symbol: str
    base_asset: str
    quote_asset: str
    exchanges: List[str]
    is_active: bool = True
    min_trade_size: Optional[float] = None
    price_precision: int = 4
    size_precision: int = 4
    
    def __post_init__(self):
        """Validate symbol information."""
        if not self.symbol or not self.base_asset or not self.quote_asset:
            raise ValueError("Symbol, base asset, and quote asset are required")
        if not self.exchanges:
            raise ValueError("At least one exchange must be specified")


# Helper functions for data validation and manipulation

def calculate_spread_percentage(bid_price: float, ask_price: float) -> float:
    """Calculate percentage spread between bid and ask prices."""
    if bid_price <= 0:
        raise ValueError("Bid price must be positive")
    return ((ask_price - bid_price) / bid_price) * 100


def find_arbitrage_opportunities(
    market_data: Dict[str, MarketData],
    threshold_percentage: float
) -> List[ArbitrageOpportunity]:
    """
    Find arbitrage opportunities from market data across exchanges.
    
    Args:
        market_data: Dictionary mapping exchange names to market data
        threshold_percentage: Minimum spread percentage to consider
        
    Returns:
        List of arbitrage opportunities
    """
    opportunities = []
    exchanges = list(market_data.keys())
    
    for i, buy_exchange in enumerate(exchanges):
        for sell_exchange in exchanges[i+1:]:
            buy_data = market_data[buy_exchange]
            sell_data = market_data[sell_exchange]
            
            # Check for arbitrage: buy on exchange with lower ask, sell on exchange with higher bid
            if sell_data.ask_price < buy_data.bid_price:
                spread_absolute = buy_data.bid_price - sell_data.ask_price
                spread_percentage = (spread_absolute / sell_data.ask_price) * 100
                
                if spread_percentage >= threshold_percentage:
                    opportunity = ArbitrageOpportunity(
                        symbol=buy_data.symbol,
                        buy_exchange=sell_exchange,  # Buy where ask is lower
                        sell_exchange=buy_exchange,  # Sell where bid is higher
                        buy_price=sell_data.ask_price,
                        sell_price=buy_data.bid_price,
                        spread_percentage=spread_percentage,
                        spread_absolute=spread_absolute,
                        timestamp=datetime.utcnow()
                    )
                    opportunities.append(opportunity)
    
    return opportunities


def consolidate_bbo(symbol: str, market_data: Dict[str, MarketData]) -> ConsolidatedBBO:
    """
    Calculate consolidated best bid/offer across exchanges.
    
    Args:
        symbol: Trading symbol
        market_data: Dictionary mapping exchange names to market data
        
    Returns:
        ConsolidatedBBO object
    """
    if not market_data:
        raise ValueError("Market data cannot be empty")
    
    # Find best bid (highest) and best ask (lowest)
    best_bid_price = 0
    best_bid_exchange = ""
    best_ask_price = float('inf')
    best_ask_exchange = ""
    
    all_exchanges = []
    
    for exchange, data in market_data.items():
        all_exchanges.append(exchange)
        
        if data.bid_price > best_bid_price:
            best_bid_price = data.bid_price
            best_bid_exchange = exchange
        
        if data.ask_price < best_ask_price:
            best_ask_price = data.ask_price
            best_ask_exchange = exchange
    
    mid_price = (best_bid_price + best_ask_price) / 2
    
    return ConsolidatedBBO(
        symbol=symbol,
        best_bid_price=best_bid_price,
        best_bid_exchange=best_bid_exchange,
        best_ask_price=best_ask_price,
        best_ask_exchange=best_ask_exchange,
        mid_price=mid_price,
        timestamp=datetime.utcnow(),
        all_exchanges=all_exchanges
    )
