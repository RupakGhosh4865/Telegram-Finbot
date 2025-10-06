"""
Consolidated market view service for providing unified market data across exchanges.

This service aggregates BBO data from multiple exchanges for symbols,
calculates consolidated best bid/offer (CBBO), and provides real-time
market view updates to users.
"""

import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

from src.models.data_models import (
    MarketData, 
    ConsolidatedBBO,
    consolidate_bbo
)
from src.data.gomarket_client import GoMarketClient, GoMarketAPIError
from src.data.websocket_client import DataStreamManager
from src.utils.logger import LoggerMixin
from src.utils.config import config


class MarketViewSession:
    """Represents a single market view monitoring session."""
    
    def __init__(
        self,
        chat_id: int,
        symbol: str,
        exchanges: List[str],
        update_interval: int = 5
    ):
        self.chat_id = chat_id
        self.symbol = symbol
        self.exchanges = exchanges
        self.update_interval = update_interval
        self.is_active = True
        self.created_at = datetime.utcnow()
        self.last_update = None
        self.last_cbbo: Optional[ConsolidatedBBO] = None
        self.message_id: Optional[int] = None


class MarketViewService(LoggerMixin):
    """
    Service for consolidated market view across multiple exchanges.
    
    Provides real-time consolidated best bid/offer (CBBO) calculations,
    venue comparison, and market data aggregation across exchanges.
    """
    
    def __init__(
        self,
        gomarket_client: GoMarketClient,
        data_stream_manager: DataStreamManager
    ):
        """
        Initialize market view service.
        
        Args:
            gomarket_client: GoMarket API client
            data_stream_manager: Data stream manager for real-time updates
        """
        self.gomarket_client = gomarket_client
        self.data_stream_manager = data_stream_manager
        
        # Active market view sessions
        self.active_sessions: Dict[int, MarketViewSession] = {}
        self.active_tasks: Dict[int, asyncio.Task] = {}
        
        # Data storage
        self.market_data_cache: Dict[str, Dict[str, MarketData]] = {}
        
        # Callbacks for notifications
        self.notification_callbacks: List[Callable] = []
        
        # Update settings
        self.max_update_interval = 30  # Maximum update interval in seconds
        self.min_update_interval = 1   # Minimum update interval in seconds
        
        self.logger.info("Market view service initialized")
    
    async def start_market_view(
        self,
        chat_id: int,
        symbol: str,
        exchanges: List[str],
        update_interval: int = 5
    ):
        """
        Start market view monitoring for a user.
        
        Args:
            chat_id: Chat ID of the user
            symbol: Trading symbol to monitor
            exchanges: List of exchanges to monitor
            update_interval: Update interval in seconds
        """
        # Validate update interval
        update_interval = max(self.min_update_interval, min(update_interval, self.max_update_interval))
        
        if chat_id in self.active_sessions:
            self.logger.warning(
                "Market view session already exists",
                chat_id=chat_id
            )
            # Update existing session
            session = self.active_sessions[chat_id]
            session.symbol = symbol
            session.exchanges = exchanges
            session.update_interval = update_interval
            return
        
        self.logger.info(
            "Starting market view",
            chat_id=chat_id,
            symbol=symbol,
            exchanges=exchanges,
            update_interval=update_interval
        )
        
        # Create session
        session = MarketViewSession(
            chat_id=chat_id,
            symbol=symbol,
            exchanges=exchanges,
            update_interval=update_interval
        )
        
        self.active_sessions[chat_id] = session
        
        # Start monitoring task
        task = asyncio.create_task(
            self._market_view_loop(chat_id, session)
        )
        self.active_tasks[chat_id] = task
        
        # Subscribe to data streams
        await self._subscribe_to_symbol_data(session)
        
        self.logger.info(
            "Market view started successfully",
            chat_id=chat_id,
            symbol=symbol
        )
    
    async def stop_market_view(self, chat_id: int):
        """
        Stop market view monitoring for a user.
        
        Args:
            chat_id: Chat ID of the user
        """
        if chat_id not in self.active_sessions:
            self.logger.warning(
                "No market view session found",
                chat_id=chat_id
            )
            return
        
        self.logger.info("Stopping market view", chat_id=chat_id)
        
        # Cancel monitoring task
        if chat_id in self.active_tasks:
            task = self.active_tasks[chat_id]
            task.cancel()
            del self.active_tasks[chat_id]
        
        # Unsubscribe from data streams
        session = self.active_sessions[chat_id]
        await self._unsubscribe_from_symbol_data(session)
        
        # Remove session
        del self.active_sessions[chat_id]
        
        self.logger.info("Market view stopped", chat_id=chat_id)
    
    async def get_current_cbbo(
        self,
        symbol: str,
        exchanges: List[str]
    ) -> ConsolidatedBBO:
        """
        Get current consolidated best bid/offer for a symbol.
        
        Args:
            symbol: Trading symbol
            exchanges: List of exchanges to query
            
        Returns:
            ConsolidatedBBO object
            
        Raises:
            GoMarketAPIError: If unable to fetch market data
        """
        try:
            # Fetch current market data from all exchanges
            market_data = {}
            
            for exchange in exchanges:
                try:
                    ticker_data = await self.gomarket_client.get_ticker(exchange, symbol)
                    market_data[exchange] = ticker_data
                    
                except GoMarketAPIError as e:
                    self.logger.warning(
                        "Failed to get ticker data",
                        exchange=exchange,
                        symbol=symbol,
                        error=str(e)
                    )
                    continue
            
            if not market_data:
                raise GoMarketAPIError(f"No market data available for {symbol}")
            
            # Calculate consolidated BBO
            cbbo = consolidate_bbo(symbol, market_data)
            
            self.logger.debug(
                "CBBO calculated",
                symbol=symbol,
                exchanges=list(market_data.keys()),
                best_bid=cbbo.best_bid_price,
                best_ask=cbbo.best_ask_price,
                spread=cbbo.spread_percentage
            )
            
            return cbbo
            
        except Exception as e:
            self.logger.error(
                "Error calculating CBBO",
                symbol=symbol,
                exchanges=exchanges,
                error=str(e)
            )
            raise GoMarketAPIError(f"Failed to calculate CBBO: {e}")
    
    async def refresh_market_view(self, chat_id: int):
        """
        Manually refresh market view for a user.
        
        Args:
            chat_id: Chat ID of the user
        """
        if chat_id not in self.active_sessions:
            self.logger.warning(
                "No market view session found for refresh",
                chat_id=chat_id
            )
            return
        
        session = self.active_sessions[chat_id]
        
        try:
            # Get current CBBO
            cbbo = await self.get_current_cbbo(session.symbol, session.exchanges)
            
            # Update session
            session.last_cbbo = cbbo
            session.last_update = datetime.utcnow()
            
            # Send update notification
            await self._send_market_update(chat_id, cbbo, is_refresh=True)
            
            self.logger.info(
                "Market view refreshed",
                chat_id=chat_id,
                symbol=session.symbol
            )
            
        except Exception as e:
            self.logger.error(
                "Error refreshing market view",
                chat_id=chat_id,
                symbol=session.symbol,
                error=str(e)
            )
    
    async def get_active_sessions_count(self, chat_id: int = None) -> int:
        """
        Get count of active market view sessions.
        
        Args:
            chat_id: Specific chat ID (optional)
            
        Returns:
            Number of active sessions
        """
        if chat_id is not None:
            return 1 if chat_id in self.active_sessions else 0
        
        return len(self.active_sessions)
    
    async def get_session_info(self, chat_id: int) -> Optional[MarketViewSession]:
        """
        Get market view session information for a user.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Market view session if active, None otherwise
        """
        return self.active_sessions.get(chat_id)
    
    async def _market_view_loop(self, chat_id: int, session: MarketViewSession):
        """
        Main market view monitoring loop for a user session.
        
        Args:
            chat_id: Chat ID of the user
            session: Market view session
        """
        self.logger.info(
            "Starting market view loop",
            chat_id=chat_id,
            symbol=session.symbol
        )
        
        try:
            while chat_id in self.active_sessions and session.is_active:
                try:
                    # Get current market data
                    symbol_data = self.market_data_cache.get(session.symbol, {})
                    
                    # Filter to only include session exchanges
                    filtered_data = {
                        exchange: data for exchange, data in symbol_data.items()
                        if exchange in session.exchanges
                    }
                    
                    # Check if we have fresh data
                    fresh_data = {}
                    for exchange, data in filtered_data.items():
                        if data.is_fresh(max_age_seconds=session.update_interval * 2):
                            fresh_data[exchange] = data
                    
                    if len(fresh_data) >= 2:  # Need at least 2 exchanges for comparison
                        # Calculate consolidated BBO
                        cbbo = consolidate_bbo(session.symbol, fresh_data)
                        
                        # Check if there are significant changes
                        if self._should_send_update(session, cbbo):
                            session.last_cbbo = cbbo
                            session.last_update = datetime.utcnow()
                            
                            # Send update notification
                            await self._send_market_update(chat_id, cbbo)
                    
                    # Wait before next update
                    await asyncio.sleep(session.update_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(
                        "Error in market view loop",
                        chat_id=chat_id,
                        symbol=session.symbol,
                        error=str(e)
                    )
                    await asyncio.sleep(5)  # Wait before retrying
        
        except asyncio.CancelledError:
            self.logger.info("Market view loop cancelled", chat_id=chat_id)
        except Exception as e:
            self.logger.error(
                "Fatal error in market view loop",
                chat_id=chat_id,
                symbol=session.symbol,
                error=str(e)
            )
        finally:
            self.logger.info("Market view loop ended", chat_id=chat_id)
    
    async def _subscribe_to_symbol_data(self, session: MarketViewSession):
        """Subscribe to data streams for session symbol and exchanges."""
        for exchange in session.exchanges:
            try:
                await self.data_stream_manager.subscribe_to_market_data(
                    exchange=exchange,
                    symbol=session.symbol,
                    callback=self._market_data_callback
                )
                
                self.logger.debug(
                    "Subscribed to market data for market view",
                    symbol=session.symbol,
                    exchange=exchange,
                    chat_id=session.chat_id
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to subscribe to market data for market view",
                    symbol=session.symbol,
                    exchange=exchange,
                    chat_id=session.chat_id,
                    error=str(e)
                )
    
    async def _unsubscribe_from_symbol_data(self, session: MarketViewSession):
        """Unsubscribe from data streams for session symbol and exchanges."""
        for exchange in session.exchanges:
            try:
                await self.data_stream_manager.unsubscribe_from_market_data(
                    exchange=exchange,
                    symbol=session.symbol
                )
                
                self.logger.debug(
                    "Unsubscribed from market data for market view",
                    symbol=session.symbol,
                    exchange=exchange,
                    chat_id=session.chat_id
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to unsubscribe from market data for market view",
                    symbol=session.symbol,
                    exchange=exchange,
                    chat_id=session.chat_id,
                    error=str(e)
                )
    
    async def _market_data_callback(self, market_data: MarketData):
        """
        Callback for market data updates.
        
        Args:
            market_data: Updated market data
        """
        # Update cache
        if market_data.symbol not in self.market_data_cache:
            self.market_data_cache[market_data.symbol] = {}
        
        self.market_data_cache[market_data.symbol][market_data.exchange] = market_data
        
        self.logger.debug(
            "Market data updated for market view",
            symbol=market_data.symbol,
            exchange=market_data.exchange,
            bid=market_data.bid_price,
            ask=market_data.ask_price
        )
    
    def _should_send_update(self, session: MarketViewSession, cbbo: ConsolidatedBBO) -> bool:
        """
        Determine if a market update should be sent.
        
        Args:
            session: Market view session
            cbbo: Current consolidated BBO
            
        Returns:
            True if update should be sent, False otherwise
        """
        # Always send first update
        if session.last_cbbo is None:
            return True
        
        # Check if significant changes occurred
        last_cbbo = session.last_cbbo
        
        # Venue changes
        venue_changed = (
            cbbo.best_bid_exchange != last_cbbo.best_bid_exchange or
            cbbo.best_ask_exchange != last_cbbo.best_ask_exchange
        )
        
        # Price changes (more than 0.1% for significant pairs)
        price_change_threshold = 0.001  # 0.1%
        bid_change = abs(cbbo.best_bid_price - last_cbbo.best_bid_price) / last_cbbo.best_bid_price
        ask_change = abs(cbbo.best_ask_price - last_cbbo.best_ask_price) / last_cbbo.best_ask_price
        price_changed = bid_change > price_change_threshold or ask_change > price_change_threshold
        
        # Spread changes (more than 5% change in spread)
        spread_change_threshold = 0.05  # 5%
        spread_change = abs(cbbo.spread_percentage - last_cbbo.spread_percentage) / last_cbbo.spread_percentage
        spread_changed = spread_change > spread_change_threshold
        
        return venue_changed or price_changed or spread_changed
    
    async def _send_market_update(
        self,
        chat_id: int,
        cbbo: ConsolidatedBBO,
        is_refresh: bool = False
    ):
        """
        Send market update notification to user.
        
        Args:
            chat_id: Chat ID of the user
            cbbo: Consolidated BBO data
            is_refresh: Whether this is a manual refresh
        """
        try:
            # Call notification callbacks
            for callback in self.notification_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(chat_id, cbbo, is_refresh)
                    else:
                        callback(chat_id, cbbo, is_refresh)
                except Exception as e:
                    self.logger.error(
                        "Error in market update notification callback",
                        error=str(e)
                    )
            
            self.logger.info(
                "Market update sent",
                chat_id=chat_id,
                symbol=cbbo.symbol,
                is_refresh=is_refresh
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send market update",
                chat_id=chat_id,
                symbol=cbbo.symbol,
                error=str(e)
            )
    
    async def add_notification_callback(self, callback: Callable):
        """
        Add a notification callback.
        
        Args:
            callback: Function to call when market updates are available
        """
        self.notification_callbacks.append(callback)
        self.logger.info("Market view notification callback added")
    
    async def remove_notification_callback(self, callback: Callable):
        """
        Remove a notification callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
            self.logger.info("Market view notification callback removed")
    
    async def get_service_statistics(self) -> Dict:
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "active_sessions": len(self.active_sessions),
            "market_data_cache_size": sum(
                len(symbol_data) for symbol_data in self.market_data_cache.values()
            ),
            "notification_callbacks": len(self.notification_callbacks),
            "sessions_by_symbol": {
                symbol: sum(1 for session in self.active_sessions.values() if session.symbol == symbol)
                for symbol in set(session.symbol for session in self.active_sessions.values())
            }
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired data from caches."""
        current_time = datetime.utcnow()
        
        # Clean up stale market data (older than 5 minutes)
        for symbol, exchange_data in self.market_data_cache.items():
            stale_exchanges = []
            for exchange, market_data in exchange_data.items():
                if not market_data.is_fresh(max_age_seconds=300):
                    stale_exchanges.append(exchange)
            
            for exchange in stale_exchanges:
                del exchange_data[exchange]
        
        self.logger.info("Market view data cleanup completed")
    
    async def shutdown(self):
        """Shutdown the market view service."""
        self.logger.info("Shutting down market view service")
        
        # Stop all sessions
        for chat_id in list(self.active_sessions.keys()):
            await self.stop_market_view(chat_id)
        
        # Cancel any remaining tasks
        for task in self.active_tasks.values():
            task.cancel()
        
        self.logger.info("Market view service shutdown complete")
