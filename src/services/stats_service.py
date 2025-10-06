"""
Statistics service for tracking and analyzing arbitrage opportunities.

This service provides historical tracking, analytics, and reporting
capabilities for arbitrage opportunities and trading data.
"""

import sqlite3
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict

from src.models.data_models import ArbitrageOpportunity
from src.utils.logger import LoggerMixin
from src.utils.config import config


class StatsService(LoggerMixin):
    """
    Service for tracking and analyzing arbitrage statistics.
    
    Provides historical data storage, analytics, and reporting
    for arbitrage opportunities and market data.
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize statistics service.
        
        Args:
            database_url: SQLite database URL
        """
        self.database_url = database_url or config.database_url.replace("sqlite:///", "")
        self.connection_pool_size = 5
        self.connections = []
        
        self.logger.info(
            "Stats service initialized",
            database_url=self.database_url
        )
    
    async def initialize(self):
        """Initialize the statistics service and database."""
        try:
            # Create database and tables
            await self._create_database_schema()
            
            # Initialize connection pool
            await self._initialize_connection_pool()
            
            self.logger.info("Stats service initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize stats service", error=str(e))
            raise
    
    async def _create_database_schema(self):
        """Create database schema if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.database_url)
            cursor = conn.cursor()
            
            # Create arbitrage opportunities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    buy_exchange TEXT NOT NULL,
                    sell_exchange TEXT NOT NULL,
                    buy_price REAL NOT NULL,
                    sell_price REAL NOT NULL,
                    spread_percentage REAL NOT NULL,
                    spread_absolute REAL NOT NULL,
                    estimated_profit REAL,
                    trade_size REAL,
                    timestamp DATETIME NOT NULL,
                    chat_id INTEGER
                )
            """)
            
            # Create market data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    bid_price REAL NOT NULL,
                    ask_price REAL NOT NULL,
                    bid_size REAL NOT NULL,
                    ask_size REAL NOT NULL,
                    last_price REAL NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            
            # Create user sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL,
                    session_data TEXT,
                    created_at DATETIME NOT NULL,
                    last_activity DATETIME NOT NULL
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_arbitrage_timestamp 
                ON arbitrage_opportunities(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_arbitrage_symbol 
                ON arbitrage_opportunities(symbol)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_arbitrage_exchanges 
                ON arbitrage_opportunities(buy_exchange, sell_exchange)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_timestamp 
                ON market_data(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_data_symbol_exchange 
                ON market_data(symbol, exchange)
            """)
            
            conn.commit()
            conn.close()
            
            self.logger.info("Database schema created successfully")
            
        except Exception as e:
            self.logger.error("Failed to create database schema", error=str(e))
            raise
    
    async def _initialize_connection_pool(self):
        """Initialize connection pool for database operations."""
        try:
            for _ in range(self.connection_pool_size):
                conn = sqlite3.connect(self.database_url)
                conn.row_factory = sqlite3.Row  # Enable column access by name
                self.connections.append(conn)
            
            self.logger.info(
                "Connection pool initialized",
                pool_size=len(self.connections)
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize connection pool", error=str(e))
            raise
    
    async def log_arbitrage_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        chat_id: Optional[int] = None
    ):
        """
        Log an arbitrage opportunity to the database.
        
        Args:
            opportunity: Arbitrage opportunity to log
            chat_id: Chat ID of the user who received the alert
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO arbitrage_opportunities 
                (symbol, buy_exchange, sell_exchange, buy_price, sell_price, 
                 spread_percentage, spread_absolute, estimated_profit, trade_size, 
                 timestamp, chat_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opportunity.symbol,
                opportunity.buy_exchange,
                opportunity.sell_exchange,
                opportunity.buy_price,
                opportunity.sell_price,
                opportunity.spread_percentage,
                opportunity.spread_absolute,
                opportunity.estimated_profit,
                opportunity.trade_size,
                opportunity.timestamp.isoformat(),
                chat_id
            ))
            
            conn.commit()
            await self._release_connection(conn)
            
            self.logger.debug(
                "Arbitrage opportunity logged",
                symbol=opportunity.symbol,
                spread=opportunity.spread_percentage
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to log arbitrage opportunity",
                error=str(e)
            )
            await self._release_connection(conn)
    
    async def log_market_data(self, market_data):
        """
        Log market data to the database.
        
        Args:
            market_data: MarketData object to log
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO market_data 
                (symbol, exchange, bid_price, ask_price, bid_size, ask_size, 
                 last_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol,
                market_data.exchange,
                market_data.bid_price,
                market_data.ask_price,
                market_data.bid_size,
                market_data.ask_size,
                market_data.last_price,
                market_data.timestamp.isoformat()
            ))
            
            conn.commit()
            await self._release_connection(conn)
            
        except Exception as e:
            self.logger.error(
                "Failed to log market data",
                error=str(e)
            )
            await self._release_connection(conn)
    
    async def get_arbitrage_statistics(
        self,
        symbol: Optional[str] = None,
        exchange_pair: Optional[tuple] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get arbitrage statistics for a given period.
        
        Args:
            symbol: Filter by symbol (optional)
            exchange_pair: Filter by exchange pair (buy_exchange, sell_exchange)
            hours: Number of hours to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            # Build query
            query = """
                SELECT 
                    COUNT(*) as total_opportunities,
                    AVG(spread_percentage) as avg_spread,
                    MAX(spread_percentage) as max_spread,
                    MIN(spread_percentage) as min_spread,
                    AVG(spread_absolute) as avg_spread_absolute,
                    MAX(spread_absolute) as max_spread_absolute
                FROM arbitrage_opportunities 
                WHERE timestamp >= ?
            """
            
            params = [datetime.utcnow() - timedelta(hours=hours)]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if exchange_pair:
                query += " AND buy_exchange = ? AND sell_exchange = ?"
                params.extend(exchange_pair)
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            # Get top exchange pairs
            exchange_query = """
                SELECT buy_exchange, sell_exchange, COUNT(*) as count,
                       AVG(spread_percentage) as avg_spread
                FROM arbitrage_opportunities 
                WHERE timestamp >= ?
            """
            exchange_params = [datetime.utcnow() - timedelta(hours=hours)]
            
            if symbol:
                exchange_query += " AND symbol = ?"
                exchange_params.append(symbol)
            
            exchange_query += """
                GROUP BY buy_exchange, sell_exchange 
                ORDER BY count DESC 
                LIMIT 10
            """
            
            cursor.execute(exchange_query, exchange_params)
            top_pairs = cursor.fetchall()
            
            # Get symbol frequency
            symbol_query = """
                SELECT symbol, COUNT(*) as count,
                       AVG(spread_percentage) as avg_spread
                FROM arbitrage_opportunities 
                WHERE timestamp >= ?
            """
            symbol_params = [datetime.utcnow() - timedelta(hours=hours)]
            
            symbol_query += """
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 10
            """
            
            cursor.execute(symbol_query, symbol_params)
            top_symbols = cursor.fetchall()
            
            await self._release_connection(conn)
            
            return {
                "period_hours": hours,
                "total_opportunities": result["total_opportunities"] or 0,
                "average_spread_percentage": result["avg_spread"] or 0,
                "max_spread_percentage": result["max_spread"] or 0,
                "min_spread_percentage": result["min_spread"] or 0,
                "average_spread_absolute": result["avg_spread_absolute"] or 0,
                "max_spread_absolute": result["max_spread_absolute"] or 0,
                "top_exchange_pairs": [
                    {
                        "buy_exchange": pair["buy_exchange"],
                        "sell_exchange": pair["sell_exchange"],
                        "count": pair["count"],
                        "avg_spread": pair["avg_spread"]
                    }
                    for pair in top_pairs
                ],
                "top_symbols": [
                    {
                        "symbol": symbol["symbol"],
                        "count": symbol["count"],
                        "avg_spread": symbol["avg_spread"]
                    }
                    for symbol in top_symbols
                ]
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get arbitrage statistics",
                error=str(e)
            )
            await self._release_connection(conn)
            return {}
    
    async def get_best_opportunities(
        self,
        symbol: Optional[str] = None,
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the best arbitrage opportunities for a period.
        
        Args:
            symbol: Filter by symbol (optional)
            hours: Number of hours to look back
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity dictionaries
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM arbitrage_opportunities 
                WHERE timestamp >= ?
            """
            params = [datetime.utcnow() - timedelta(hours=hours)]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY spread_percentage DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            await self._release_connection(conn)
            
            return [
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "buy_exchange": row["buy_exchange"],
                    "sell_exchange": row["sell_exchange"],
                    "buy_price": row["buy_price"],
                    "sell_price": row["sell_price"],
                    "spread_percentage": row["spread_percentage"],
                    "spread_absolute": row["spread_absolute"],
                    "estimated_profit": row["estimated_profit"],
                    "trade_size": row["trade_size"],
                    "timestamp": datetime.fromisoformat(row["timestamp"])
                }
                for row in results
            ]
            
        except Exception as e:
            self.logger.error(
                "Failed to get best opportunities",
                error=str(e)
            )
            await self._release_connection(conn)
            return []
    
    async def get_hourly_statistics(
        self,
        symbol: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get hourly statistics for arbitrage opportunities.
        
        Args:
            symbol: Filter by symbol (optional)
            hours: Number of hours to look back
            
        Returns:
            List of hourly statistics
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    COUNT(*) as opportunities,
                    AVG(spread_percentage) as avg_spread,
                    MAX(spread_percentage) as max_spread
                FROM arbitrage_opportunities 
                WHERE timestamp >= ?
            """
            params = [datetime.utcnow() - timedelta(hours=hours)]
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += """
                GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                ORDER BY hour
            """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            await self._release_connection(conn)
            
            return [
                {
                    "hour": datetime.fromisoformat(row["hour"]),
                    "opportunities": row["opportunities"],
                    "avg_spread": row["avg_spread"],
                    "max_spread": row["max_spread"]
                }
                for row in results
            ]
            
        except Exception as e:
            self.logger.error(
                "Failed to get hourly statistics",
                error=str(e)
            )
            await self._release_connection(conn)
            return []
    
    async def save_user_session(self, chat_id: int, session_data: Dict[str, Any]):
        """
        Save user session data.
        
        Args:
            chat_id: Chat ID of the user
            session_data: Session data to save
        """
        try:
            import json
            
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_sessions 
                (chat_id, session_data, created_at, last_activity)
                VALUES (?, ?, ?, ?)
            """, (
                chat_id,
                json.dumps(session_data),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
            await self._release_connection(conn)
            
        except Exception as e:
            self.logger.error(
                "Failed to save user session",
                error=str(e)
            )
            await self._release_connection(conn)
    
    async def load_user_session(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Load user session data.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Session data if found, None otherwise
        """
        try:
            import json
            
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT session_data FROM user_sessions WHERE chat_id = ?",
                (chat_id,)
            )
            result = cursor.fetchone()
            
            await self._release_connection(conn)
            
            if result:
                return json.loads(result["session_data"])
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to load user session",
                error=str(e)
            )
            await self._release_connection(conn)
            return None
    
    async def cleanup_old_data(self, days: int = 30):
        """
        Clean up old data from the database.
        
        Args:
            days: Number of days to keep
        """
        try:
            conn = await self._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean up old arbitrage opportunities
            cursor.execute(
                "DELETE FROM arbitrage_opportunities WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            arb_deleted = cursor.rowcount
            
            # Clean up old market data
            cursor.execute(
                "DELETE FROM market_data WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            market_deleted = cursor.rowcount
            
            # Clean up old user sessions
            cursor.execute(
                "DELETE FROM user_sessions WHERE last_activity < ?",
                (cutoff_date.isoformat(),)
            )
            session_deleted = cursor.rowcount
            
            conn.commit()
            await self._release_connection(conn)
            
            self.logger.info(
                "Data cleanup completed",
                arbitrage_deleted=arb_deleted,
                market_deleted=market_deleted,
                sessions_deleted=session_deleted
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup old data",
                error=str(e)
            )
            await self._release_connection(conn)
    
    async def _get_connection(self):
        """Get a database connection from the pool."""
        if not self.connections:
            # Create new connection if pool is empty
            conn = sqlite3.connect(self.database_url)
            conn.row_factory = sqlite3.Row
            return conn
        
        return self.connections.pop()
    
    async def _release_connection(self, conn):
        """Release a database connection back to the pool."""
        if len(self.connections) < self.connection_pool_size:
            self.connections.append(conn)
        else:
            conn.close()
    
    async def shutdown(self):
        """Shutdown the statistics service."""
        try:
            # Close all connections
            for conn in self.connections:
                conn.close()
            
            self.connections.clear()
            
            self.logger.info("Stats service shutdown complete")
            
        except Exception as e:
            self.logger.error("Error during stats service shutdown", error=str(e))
