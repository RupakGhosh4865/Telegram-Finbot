"""
Tests for data models and structures.

This module contains unit tests for all data models used in the trading system.
"""

import pytest
from datetime import datetime
from src.models.data_models import (
    MarketData, OrderBook, OrderBookLevel, ArbitrageOpportunity,
    ConsolidatedBBO, MonitoringConfig, find_arbitrage_opportunities,
    consolidate_bbo, calculate_spread_percentage
)


class TestOrderBookLevel:
    """Test OrderBookLevel data model."""
    
    def test_valid_order_book_level(self):
        """Test creating a valid order book level."""
        level = OrderBookLevel(price=100.0, size=1.5)
        assert level.price == 100.0
        assert level.size == 1.5
    
    def test_invalid_price(self):
        """Test creating order book level with invalid price."""
        with pytest.raises(ValueError, match="Price must be positive"):
            OrderBookLevel(price=0.0, size=1.5)
        
        with pytest.raises(ValueError, match="Price must be positive"):
            OrderBookLevel(price=-10.0, size=1.5)
    
    def test_invalid_size(self):
        """Test creating order book level with invalid size."""
        with pytest.raises(ValueError, match="Size must be positive"):
            OrderBookLevel(price=100.0, size=0.0)
        
        with pytest.raises(ValueError, match="Size must be positive"):
            OrderBookLevel(price=100.0, size=-1.0)


class TestMarketData:
    """Test MarketData data model."""
    
    def test_valid_market_data(self):
        """Test creating valid market data."""
        timestamp = datetime.utcnow()
        market_data = MarketData(
            symbol="BTC/USDT",
            exchange="binance",
            bid_price=50000.0,
            bid_size=1.0,
            ask_price=50001.0,
            ask_size=1.0,
            last_price=50000.5,
            timestamp=timestamp
        )
        
        assert market_data.symbol == "BTC/USDT"
        assert market_data.exchange == "binance"
        assert market_data.bid_price == 50000.0
        assert market_data.ask_price == 50001.0
        assert market_data.spread_absolute == 1.0
        assert market_data.mid_price == 50000.5
    
    def test_spread_calculations(self):
        """Test spread calculation methods."""
        market_data = MarketData(
            symbol="ETH/USDT",
            exchange="okx",
            bid_price=3000.0,
            bid_size=2.0,
            ask_price=3002.0,
            ask_size=1.5,
            last_price=3001.0,
            timestamp=datetime.utcnow()
        )
        
        assert market_data.spread_absolute == 2.0
        assert market_data.spread_percentage == (2.0 / 3000.0) * 100
        assert market_data.mid_price == 3001.0
    
    def test_data_freshness(self):
        """Test data freshness checking."""
        # Fresh data
        fresh_data = MarketData(
            symbol="BTC/USDT",
            exchange="binance",
            bid_price=50000.0,
            bid_size=1.0,
            ask_price=50001.0,
            ask_size=1.0,
            last_price=50000.5,
            timestamp=datetime.utcnow()
        )
        assert fresh_data.is_fresh(max_age_seconds=30)
        
        # Stale data
        from datetime import timedelta
        stale_timestamp = datetime.utcnow() - timedelta(seconds=60)
        stale_data = MarketData(
            symbol="BTC/USDT",
            exchange="binance",
            bid_price=50000.0,
            bid_size=1.0,
            ask_price=50001.0,
            ask_size=1.0,
            last_price=50000.5,
            timestamp=stale_timestamp
        )
        assert not stale_data.is_fresh(max_age_seconds=30)
    
    def test_invalid_market_data(self):
        """Test validation of market data."""
        # Invalid prices
        with pytest.raises(ValueError):
            MarketData(
                symbol="BTC/USDT",
                exchange="binance",
                bid_price=0.0,
                bid_size=1.0,
                ask_price=50001.0,
                ask_size=1.0,
                last_price=50000.5,
                timestamp=datetime.utcnow()
            )
        
        # Bid >= Ask
        with pytest.raises(ValueError):
            MarketData(
                symbol="BTC/USDT",
                exchange="binance",
                bid_price=50001.0,
                bid_size=1.0,
                ask_price=50000.0,
                ask_size=1.0,
                last_price=50000.5,
                timestamp=datetime.utcnow()
            )


class TestOrderBook:
    """Test OrderBook data model."""
    
    def test_valid_order_book(self):
        """Test creating a valid order book."""
        timestamp = datetime.utcnow()
        
        bids = [
            OrderBookLevel(price=50000.0, size=1.0),
            OrderBookLevel(price=49999.0, size=2.0),
            OrderBookLevel(price=49998.0, size=1.5)
        ]
        
        asks = [
            OrderBookLevel(price=50001.0, size=1.0),
            OrderBookLevel(price=50002.0, size=2.0),
            OrderBookLevel(price=50003.0, size=1.5)
        ]
        
        order_book = OrderBook(
            symbol="BTC/USDT",
            exchange="binance",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        assert order_book.symbol == "BTC/USDT"
        assert order_book.exchange == "binance"
        assert len(order_book.bids) == 3
        assert len(order_book.asks) == 3
        assert order_book.best_bid.price == 50000.0
        assert order_book.best_ask.price == 50001.0
    
    def test_market_data_conversion(self):
        """Test converting order book to market data."""
        timestamp = datetime.utcnow()
        
        bids = [OrderBookLevel(price=50000.0, size=1.0)]
        asks = [OrderBookLevel(price=50001.0, size=1.0)]
        
        order_book = OrderBook(
            symbol="BTC/USDT",
            exchange="binance",
            bids=bids,
            asks=asks,
            timestamp=timestamp
        )
        
        market_data = order_book.market_data
        assert market_data.symbol == "BTC/USDT"
        assert market_data.exchange == "binance"
        assert market_data.bid_price == 50000.0
        assert market_data.ask_price == 50001.0
        assert market_data.last_price == 50000.5


class TestArbitrageOpportunity:
    """Test ArbitrageOpportunity data model."""
    
    def test_valid_arbitrage_opportunity(self):
        """Test creating a valid arbitrage opportunity."""
        timestamp = datetime.utcnow()
        opportunity = ArbitrageOpportunity(
            symbol="BTC/USDT",
            buy_exchange="binance",
            sell_exchange="okx",
            buy_price=50000.0,
            sell_price=50050.0,
            spread_percentage=0.1,
            spread_absolute=50.0,
            timestamp=timestamp
        )
        
        assert opportunity.symbol == "BTC/USDT"
        assert opportunity.buy_exchange == "binance"
        assert opportunity.sell_exchange == "okx"
        assert opportunity.spread_percentage == 0.1
        assert opportunity.spread_absolute == 50.0
    
    def test_telegram_message_format(self):
        """Test Telegram message formatting."""
        timestamp = datetime.utcnow()
        opportunity = ArbitrageOpportunity(
            symbol="BTC/USDT",
            buy_exchange="binance",
            sell_exchange="okx",
            buy_price=50000.0,
            sell_price=50050.0,
            spread_percentage=0.1,
            spread_absolute=50.0,
            timestamp=timestamp
        )
        
        message = opportunity.format_telegram_message()
        assert "ARBITRAGE ALERT" in message
        assert "BTC/USDT" in message
        assert "BINANCE" in message
        assert "OKX" in message
        assert "0.10%" in message


class TestConsolidatedBBO:
    """Test ConsolidatedBBO data model."""
    
    def test_valid_consolidated_bbo(self):
        """Test creating a valid consolidated BBO."""
        timestamp = datetime.utcnow()
        cbbo = ConsolidatedBBO(
            symbol="BTC/USDT",
            best_bid_price=50000.0,
            best_bid_exchange="binance",
            best_ask_price=50001.0,
            best_ask_exchange="okx",
            mid_price=50000.5,
            timestamp=timestamp,
            all_exchanges=["binance", "okx"]
        )
        
        assert cbbo.symbol == "BTC/USDT"
        assert cbbo.best_bid_price == 50000.0
        assert cbbo.best_ask_price == 50001.0
        assert cbbo.spread_absolute == 1.0
        assert cbbo.spread_percentage == (1.0 / 50000.0) * 100
    
    def test_telegram_message_format(self):
        """Test Telegram message formatting."""
        timestamp = datetime.utcnow()
        cbbo = ConsolidatedBBO(
            symbol="BTC/USDT",
            best_bid_price=50000.0,
            best_bid_exchange="binance",
            best_ask_price=50001.0,
            best_ask_exchange="okx",
            mid_price=50000.5,
            timestamp=timestamp,
            all_exchanges=["binance", "okx"]
        )
        
        message = cbbo.format_telegram_message()
        assert "CBBO" in message
        assert "BTC/USDT" in message
        assert "BINANCE" in message
        assert "OKX" in message


class TestMonitoringConfig:
    """Test MonitoringConfig data model."""
    
    def test_valid_monitoring_config(self):
        """Test creating a valid monitoring configuration."""
        config = MonitoringConfig(
            chat_id=12345,
            symbols=["BTC/USDT", "ETH/USDT"],
            exchanges=["binance", "okx"],
            threshold_percentage=0.5
        )
        
        assert config.chat_id == 12345
        assert config.symbols == ["BTC/USDT", "ETH/USDT"]
        assert config.exchanges == ["binance", "okx"]
        assert config.threshold_percentage == 0.5
        assert config.is_active is True
    
    def test_dict_conversion(self):
        """Test converting monitoring config to/from dictionary."""
        config = MonitoringConfig(
            chat_id=12345,
            symbols=["BTC/USDT"],
            exchanges=["binance"],
            threshold_percentage=1.0
        )
        
        config_dict = config.to_dict()
        assert config_dict["chat_id"] == 12345
        assert config_dict["symbols"] == ["BTC/USDT"]
        
        restored_config = MonitoringConfig.from_dict(config_dict)
        assert restored_config.chat_id == config.chat_id
        assert restored_config.symbols == config.symbols


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_spread_percentage_calculation(self):
        """Test spread percentage calculation."""
        spread = calculate_spread_percentage(100.0, 102.0)
        assert spread == 2.0  # 2% spread
    
    def test_find_arbitrage_opportunities(self):
        """Test finding arbitrage opportunities."""
        # Create mock market data
        market_data = {
            "binance": MarketData(
                symbol="BTC/USDT",
                exchange="binance",
                bid_price=50000.0,
                bid_size=1.0,
                ask_price=50001.0,
                ask_size=1.0,
                last_price=50000.5,
                timestamp=datetime.utcnow()
            ),
            "okx": MarketData(
                symbol="BTC/USDT",
                exchange="okx",
                bid_price=50050.0,  # Higher bid on OKX
                bid_size=1.0,
                ask_price=50051.0,
                ask_size=1.0,
                last_price=50050.5,
                timestamp=datetime.utcnow()
            )
        }
        
        opportunities = find_arbitrage_opportunities(market_data, threshold_percentage=0.05)
        
        # Should find opportunity: buy on binance (ask=50001), sell on okx (bid=50050)
        assert len(opportunities) == 1
        opportunity = opportunities[0]
        assert opportunity.symbol == "BTC/USDT"
        assert opportunity.buy_exchange == "binance"
        assert opportunity.sell_exchange == "okx"
    
    def test_consolidate_bbo(self):
        """Test consolidated BBO calculation."""
        market_data = {
            "binance": MarketData(
                symbol="BTC/USDT",
                exchange="binance",
                bid_price=50000.0,
                bid_size=1.0,
                ask_price=50001.0,
                ask_size=1.0,
                last_price=50000.5,
                timestamp=datetime.utcnow()
            ),
            "okx": MarketData(
                symbol="BTC/USDT",
                exchange="okx",
                bid_price=49999.0,  # Lower bid
                bid_size=1.0,
                ask_price=50000.5,  # Lower ask
                ask_size=1.0,
                last_price=49999.75,
                timestamp=datetime.utcnow()
            )
        }
        
        cbbo = consolidate_bbo("BTC/USDT", market_data)
        
        assert cbbo.symbol == "BTC/USDT"
        assert cbbo.best_bid_price == 50000.0  # Highest bid (binance)
        assert cbbo.best_bid_exchange == "binance"
        assert cbbo.best_ask_price == 50000.5  # Lowest ask (okx)
        assert cbbo.best_ask_exchange == "okx"
        assert "binance" in cbbo.all_exchanges
        assert "okx" in cbbo.all_exchanges


if __name__ == "__main__":
    pytest.main([__file__])
