"""
Arbitrage detection service for monitoring price differences across exchanges.

This service monitors multiple symbols across multiple exchanges simultaneously,
detects arbitrage opportunities based on configurable thresholds, and sends
real-time alerts to users via Telegram.
"""

import asyncio
from typing import Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import asdict

from src.models.data_models import (
    MarketData, 
    ArbitrageOpportunity, 
    MonitoringConfig,
    find_arbitrage_opportunities,
    consolidate_bbo
)
from src.data.gomarket_client import GoMarketClient, GoMarketAPIError
from src.data.websocket_client import DataStreamManager
from src.utils.logger import LoggerMixin
from src.utils.config import config


class ArbitrageService(LoggerMixin):
    """
    Service for detecting and managing arbitrage opportunities.
    
    Monitors multiple symbols across exchanges, detects price differences,
    and sends alerts to users when opportunities exceed configured thresholds.
    """
    
    def __init__(
        self,
        gomarket_client: GoMarketClient,
        data_stream_manager: DataStreamManager
    ):
        """
        Initialize arbitrage service.
        
        Args:
            gomarket_client: GoMarket API client
            data_stream_manager: Data stream manager for real-time updates
        """
        self.gomarket_client = gomarket_client
        self.data_stream_manager = data_stream_manager
        
        # Monitoring sessions
        self.monitoring_sessions: Dict[int, MonitoringConfig] = {}
        self.active_monitoring_tasks: Dict[int, asyncio.Task] = {}
        
        # Data storage
        self.market_data_cache: Dict[str, Dict[str, MarketData]] = {}
        self.opportunity_history: List[ArbitrageOpportunity] = []
        
        # Alert management
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.alert_cooldown_minutes = 1  # Minimum time between alerts for same opportunity
        
        # Callbacks for notifications
        self.notification_callbacks: List[Callable] = []
        
        self.logger.info("Arbitrage service initialized")
    
    async def start_monitoring(self, monitoring_config: MonitoringConfig):
        """
        Start arbitrage monitoring for a user.
        
        Args:
            monitoring_config: Configuration for monitoring session
        """
        chat_id = monitoring_config.chat_id
        
        if chat_id in self.monitoring_sessions:
            self.logger.warning(
                "Monitoring session already exists",
                chat_id=chat_id
            )
            # Update existing session
            self.monitoring_sessions[chat_id] = monitoring_config
            return
        
        self.logger.info(
            "Starting arbitrage monitoring",
            chat_id=chat_id,
            symbols=monitoring_config.symbols,
            exchanges=monitoring_config.exchanges,
            threshold=monitoring_config.threshold_percentage
        )
        
        # Store monitoring configuration
        self.monitoring_sessions[chat_id] = monitoring_config
        
        # Start monitoring task
        task = asyncio.create_task(
            self._monitoring_loop(chat_id, monitoring_config)
        )
        self.active_monitoring_tasks[chat_id] = task
        
        # Subscribe to data streams
        await self._subscribe_to_symbols(monitoring_config)
        
        self.logger.info(
            "Arbitrage monitoring started successfully",
            chat_id=chat_id
        )
    
    async def stop_monitoring(self, chat_id: int):
        """
        Stop arbitrage monitoring for a user.
        
        Args:
            chat_id: Chat ID of the user
        """
        if chat_id not in self.monitoring_sessions:
            self.logger.warning(
                "No monitoring session found",
                chat_id=chat_id
            )
            return
        
        self.logger.info("Stopping arbitrage monitoring", chat_id=chat_id)
        
        # Cancel monitoring task
        if chat_id in self.active_monitoring_tasks:
            task = self.active_monitoring_tasks[chat_id]
            task.cancel()
            del self.active_monitoring_tasks[chat_id]
        
        # Unsubscribe from data streams
        monitoring_config = self.monitoring_sessions[chat_id]
        await self._unsubscribe_from_symbols(monitoring_config)
        
        # Remove session
        del self.monitoring_sessions[chat_id]
        
        self.logger.info("Arbitrage monitoring stopped", chat_id=chat_id)
    
    async def get_active_sessions_count(self, chat_id: int = None) -> int:
        """
        Get count of active monitoring sessions.
        
        Args:
            chat_id: Specific chat ID (optional)
            
        Returns:
            Number of active sessions
        """
        if chat_id is not None:
            return 1 if chat_id in self.monitoring_sessions else 0
        
        return len(self.monitoring_sessions)
    
    async def get_monitoring_status(self, chat_id: int) -> Optional[MonitoringConfig]:
        """
        Get monitoring status for a user.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Monitoring configuration if active, None otherwise
        """
        return self.monitoring_sessions.get(chat_id)
    
    async def update_monitoring_config(self, chat_id: int, config_updates: Dict):
        """
        Update monitoring configuration for a user.
        
        Args:
            chat_id: Chat ID of the user
            config_updates: Dictionary of configuration updates
        """
        if chat_id not in self.monitoring_sessions:
            self.logger.warning(
                "No monitoring session found for update",
                chat_id=chat_id
            )
            return
        
        current_config = self.monitoring_sessions[chat_id]
        
        # Update configuration
        for key, value in config_updates.items():
            if hasattr(current_config, key):
                setattr(current_config, key, value)
        
        self.monitoring_sessions[chat_id] = current_config
        
        self.logger.info(
            "Monitoring configuration updated",
            chat_id=chat_id,
            updates=config_updates
        )
    
    async def get_opportunity_history(
        self,
        chat_id: int = None,
        symbol: str = None,
        hours: int = 24
    ) -> List[ArbitrageOpportunity]:
        """
        Get historical arbitrage opportunities.
        
        Args:
            chat_id: Filter by chat ID (optional)
            symbol: Filter by symbol (optional)
            hours: Number of hours to look back
            
        Returns:
            List of arbitrage opportunities
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_opportunities = [
            opp for opp in self.opportunity_history
            if opp.timestamp >= cutoff_time
        ]
        
        if chat_id is not None:
            # TODO: Add chat_id to opportunity tracking
            pass
        
        if symbol is not None:
            filtered_opportunities = [
                opp for opp in filtered_opportunities
                if opp.symbol == symbol
            ]
        
        return filtered_opportunities
    
    async def _monitoring_loop(self, chat_id: int, monitoring_config: MonitoringConfig):
        """
        Main monitoring loop for a user session.
        
        Args:
            chat_id: Chat ID of the user
            monitoring_config: Monitoring configuration
        """
        self.logger.info(
            "Starting monitoring loop",
            chat_id=chat_id
        )
        
        try:
            while chat_id in self.monitoring_sessions:
                try:
                    # Check for arbitrage opportunities
                    opportunities = await self._check_arbitrage_opportunities(
                        monitoring_config
                    )
                    
                    # Process and send alerts
                    for opportunity in opportunities:
                        await self._process_opportunity(chat_id, opportunity)
                    
                    # Wait before next check
                    await asyncio.sleep(monitoring_config.update_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(
                        "Error in monitoring loop",
                        chat_id=chat_id,
                        error=str(e)
                    )
                    await asyncio.sleep(5)  # Wait before retrying
        
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled", chat_id=chat_id)
        except Exception as e:
            self.logger.error(
                "Fatal error in monitoring loop",
                chat_id=chat_id,
                error=str(e)
            )
        finally:
            self.logger.info("Monitoring loop ended", chat_id=chat_id)
    
    async def _subscribe_to_symbols(self, monitoring_config: MonitoringConfig):
        """Subscribe to data streams for all symbols and exchanges."""
        for symbol in monitoring_config.symbols:
            for exchange in monitoring_config.exchanges:
                try:
                    await self.data_stream_manager.subscribe_to_market_data(
                        exchange=exchange,
                        symbol=symbol,
                        callback=self._market_data_callback
                    )
                    
                    self.logger.debug(
                        "Subscribed to market data",
                        symbol=symbol,
                        exchange=exchange
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to subscribe to market data",
                        symbol=symbol,
                        exchange=exchange,
                        error=str(e)
                    )
    
    async def _unsubscribe_from_symbols(self, monitoring_config: MonitoringConfig):
        """Unsubscribe from data streams for all symbols and exchanges."""
        for symbol in monitoring_config.symbols:
            for exchange in monitoring_config.exchanges:
                try:
                    await self.data_stream_manager.unsubscribe_from_market_data(
                        exchange=exchange,
                        symbol=symbol
                    )
                    
                    self.logger.debug(
                        "Unsubscribed from market data",
                        symbol=symbol,
                        exchange=exchange
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to unsubscribe from market data",
                        symbol=symbol,
                        exchange=exchange,
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
            "Market data updated",
            symbol=market_data.symbol,
            exchange=market_data.exchange,
            bid=market_data.bid_price,
            ask=market_data.ask_price
        )
    
    async def _check_arbitrage_opportunities(
        self,
        monitoring_config: MonitoringConfig
    ) -> List[ArbitrageOpportunity]:
        """
        Check for arbitrage opportunities across monitored symbols.
        
        Args:
            monitoring_config: Monitoring configuration
            
        Returns:
            List of detected arbitrage opportunities
        """
        opportunities = []
        
        for symbol in monitoring_config.symbols:
            try:
                # Get market data for symbol across exchanges
                symbol_data = self.market_data_cache.get(symbol, {})
                
                # Filter to only include monitored exchanges
                filtered_data = {
                    exchange: data for exchange, data in symbol_data.items()
                    if exchange in monitoring_config.exchanges
                }
                
                # Skip if we don't have data from all exchanges
                if len(filtered_data) < 2:
                    continue
                
                # Check data freshness
                fresh_data = {}
                for exchange, data in filtered_data.items():
                    if data.is_fresh(max_age_seconds=60):  # 1 minute max age
                        fresh_data[exchange] = data
                
                if len(fresh_data) < 2:
                    self.logger.debug(
                        "Insufficient fresh data for arbitrage check",
                        symbol=symbol,
                        exchanges=list(fresh_data.keys())
                    )
                    continue
                
                # Find arbitrage opportunities
                symbol_opportunities = find_arbitrage_opportunities(
                    fresh_data,
                    monitoring_config.threshold_percentage
                )
                
                opportunities.extend(symbol_opportunities)
                
            except Exception as e:
                self.logger.error(
                    "Error checking arbitrage opportunities",
                    symbol=symbol,
                    error=str(e)
                )
        
        return opportunities
    
    async def _process_opportunity(
        self,
        chat_id: int,
        opportunity: ArbitrageOpportunity
    ):
        """
        Process a detected arbitrage opportunity.
        
        Args:
            chat_id: Chat ID of the user
            opportunity: Detected arbitrage opportunity
        """
        # Check alert cooldown
        opportunity_key = f"{opportunity.symbol}:{opportunity.buy_exchange}:{opportunity.sell_exchange}"
        
        if self._is_alert_cooldown_active(opportunity_key):
            self.logger.debug(
                "Alert cooldown active, skipping opportunity",
                opportunity_key=opportunity_key
            )
            return
        
        # Store opportunity in history
        self.opportunity_history.append(opportunity)
        
        # Set alert cooldown
        self.alert_cooldowns[opportunity_key] = datetime.utcnow()
        
        # Send notification
        await self._send_opportunity_alert(chat_id, opportunity)
        
        self.logger.info(
            "Arbitrage opportunity processed",
            chat_id=chat_id,
            symbol=opportunity.symbol,
            spread=opportunity.spread_percentage,
            buy_exchange=opportunity.buy_exchange,
            sell_exchange=opportunity.sell_exchange
        )
    
    def _is_alert_cooldown_active(self, opportunity_key: str) -> bool:
        """
        Check if alert cooldown is active for an opportunity.
        
        Args:
            opportunity_key: Unique key for the opportunity
            
        Returns:
            True if cooldown is active, False otherwise
        """
        if opportunity_key not in self.alert_cooldowns:
            return False
        
        last_alert_time = self.alert_cooldowns[opportunity_key]
        cooldown_end = last_alert_time + timedelta(minutes=self.alert_cooldown_minutes)
        
        return datetime.utcnow() < cooldown_end
    
    async def _send_opportunity_alert(
        self,
        chat_id: int,
        opportunity: ArbitrageOpportunity
    ):
        """
        Send arbitrage opportunity alert to user.
        
        Args:
            chat_id: Chat ID of the user
            opportunity: Arbitrage opportunity to alert about
        """
        try:
            # Call notification callbacks
            for callback in self.notification_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(chat_id, opportunity)
                    else:
                        callback(chat_id, opportunity)
                except Exception as e:
                    self.logger.error(
                        "Error in notification callback",
                        error=str(e)
                    )
            
            self.logger.info(
                "Opportunity alert sent",
                chat_id=chat_id,
                symbol=opportunity.symbol,
                spread=opportunity.spread_percentage
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send opportunity alert",
                chat_id=chat_id,
                symbol=opportunity.symbol,
                error=str(e)
            )
    
    async def add_notification_callback(self, callback: Callable):
        """
        Add a notification callback.
        
        Args:
            callback: Function to call when opportunities are detected
        """
        self.notification_callbacks.append(callback)
        self.logger.info("Notification callback added")
    
    async def remove_notification_callback(self, callback: Callable):
        """
        Remove a notification callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
            self.logger.info("Notification callback removed")
    
    async def get_service_statistics(self) -> Dict:
        """
        Get service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "active_sessions": len(self.monitoring_sessions),
            "total_opportunities_detected": len(self.opportunity_history),
            "market_data_cache_size": sum(
                len(symbol_data) for symbol_data in self.market_data_cache.values()
            ),
            "active_alert_cooldowns": len(self.alert_cooldowns),
            "notification_callbacks": len(self.notification_callbacks)
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired data from caches and history."""
        current_time = datetime.utcnow()
        
        # Clean up old opportunities (keep last 24 hours)
        cutoff_time = current_time - timedelta(hours=24)
        self.opportunity_history = [
            opp for opp in self.opportunity_history
            if opp.timestamp >= cutoff_time
        ]
        
        # Clean up expired alert cooldowns
        expired_cooldowns = []
        for key, alert_time in self.alert_cooldowns.items():
            if current_time - alert_time > timedelta(hours=1):
                expired_cooldowns.append(key)
        
        for key in expired_cooldowns:
            del self.alert_cooldowns[key]
        
        # Clean up stale market data
        for symbol, exchange_data in self.market_data_cache.items():
            stale_exchanges = []
            for exchange, market_data in exchange_data.items():
                if not market_data.is_fresh(max_age_seconds=300):  # 5 minutes
                    stale_exchanges.append(exchange)
            
            for exchange in stale_exchanges:
                del exchange_data[exchange]
        
        self.logger.info(
            "Data cleanup completed",
            opportunities_kept=len(self.opportunity_history),
            cooldowns_removed=len(expired_cooldowns)
        )
    
    async def shutdown(self):
        """Shutdown the arbitrage service."""
        self.logger.info("Shutting down arbitrage service")
        
        # Stop all monitoring sessions
        for chat_id in list(self.monitoring_sessions.keys()):
            await self.stop_monitoring(chat_id)
        
        # Cancel any remaining tasks
        for task in self.active_monitoring_tasks.values():
            task.cancel()
        
        self.logger.info("Arbitrage service shutdown complete")
