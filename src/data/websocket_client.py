"""
WebSocket client for real-time market data streaming.

This module provides WebSocket connectivity for real-time market data updates.
If WebSocket is not available, it falls back to polling mechanism.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import asdict

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.models.data_models import MarketData, OrderBook
from src.data.gomarket_client import GoMarketClient, GoMarketAPIError
from src.utils.logger import LoggerMixin
from src.utils.config import config


class DataStreamError(Exception):
    """Exception for data streaming errors."""
    pass


class WebSocketClient(LoggerMixin):
    """
    WebSocket client for real-time market data streaming.
    
    Provides real-time data streaming from GoMarket WebSocket endpoints.
    Falls back to polling if WebSocket is not available.
    """
    
    def __init__(
        self,
        gomarket_client: GoMarketClient,
        reconnect_delay: int = None,
        max_reconnect_attempts: int = None
    ):
        """
        Initialize WebSocket client.
        
        Args:
            gomarket_client: GoMarket API client instance
            reconnect_delay: Delay between reconnection attempts
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.gomarket_client = gomarket_client
        self.reconnect_delay = reconnect_delay or config.websocket_reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts or config.websocket_max_reconnect_attempts
        
        # WebSocket connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_count = 0
        
        # Subscription management
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.callback_queue: asyncio.Queue = asyncio.Queue()
        
        # Polling fallback
        self.use_polling = False
        self.polling_interval = 1.0  # seconds
        self.polling_tasks: Dict[str, asyncio.Task] = {}
        
        # WebSocket URL (to be determined based on API documentation)
        self.websocket_url = self._get_websocket_url()
        
        self.logger.info(
            "WebSocket client initialized",
            websocket_url=self.websocket_url,
            reconnect_delay=self.reconnect_delay,
            max_reconnect_attempts=self.max_reconnect_attempts
        )
    
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL for GoMarket API."""
        # This would need to be updated based on actual GoMarket WebSocket documentation
        base_url = config.gomarket_base_url.replace('https://', 'wss://').replace('http://', 'ws://')
        return f"{base_url}/ws"
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Attempting WebSocket connection", url=self.websocket_url)
            
            # Try WebSocket connection first
            try:
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                )
                
                self.is_connected = True
                self.reconnect_count = 0
                self.use_polling = False
                
                self.logger.info("WebSocket connection established")
                return True
                
            except Exception as e:
                self.logger.warning(
                    "WebSocket connection failed, falling back to polling",
                    error=str(e)
                )
                self.use_polling = True
                return True  # Polling is considered a valid connection
                
        except Exception as e:
            self.logger.error("Failed to establish connection", error=str(e))
            return False
    
    async def disconnect(self):
        """Close WebSocket connection and stop all tasks."""
        self.is_running = False
        
        # Stop polling tasks
        for task in self.polling_tasks.values():
            task.cancel()
        
        # Close WebSocket
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        self.is_connected = False
        self.logger.info("WebSocket client disconnected")
    
    async def subscribe(
        self,
        exchange: str,
        symbol: str,
        callback: Callable[[MarketData], None]
    ):
        """
        Subscribe to market data updates for a symbol.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            callback: Function to call with market data updates
        """
        subscription_key = f"{exchange}:{symbol}"
        
        if subscription_key not in self.subscriptions:
            self.subscriptions[subscription_key] = []
        
        self.subscriptions[subscription_key].append(callback)
        
        self.logger.info(
            "Subscribed to market data",
            exchange=exchange,
            symbol=symbol,
            callback_count=len(self.subscriptions[subscription_key])
        )
        
        # Start data stream for this subscription
        if self.use_polling:
            await self._start_polling(exchange, symbol)
        else:
            await self._send_subscription_message(exchange, symbol)
    
    async def unsubscribe(self, exchange: str, symbol: str):
        """
        Unsubscribe from market data updates for a symbol.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
        """
        subscription_key = f"{exchange}:{symbol}"
        
        if subscription_key in self.subscriptions:
            del self.subscriptions[subscription_key]
            
            # Stop polling task if exists
            if subscription_key in self.polling_tasks:
                self.polling_tasks[subscription_key].cancel()
                del self.polling_tasks[subscription_key]
            
            self.logger.info(
                "Unsubscribed from market data",
                exchange=exchange,
                symbol=symbol
            )
    
    async def _send_subscription_message(self, exchange: str, symbol: str):
        """Send subscription message via WebSocket."""
        if not self.websocket or self.websocket.closed:
            return
        
        try:
            message = {
                "action": "subscribe",
                "exchange": exchange,
                "symbol": symbol,
                "type": "ticker"
            }
            
            await self.websocket.send(json.dumps(message))
            self.logger.debug(
                "Sent subscription message",
                exchange=exchange,
                symbol=symbol
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to send subscription message",
                exchange=exchange,
                symbol=symbol,
                error=str(e)
            )
    
    async def _start_polling(self, exchange: str, symbol: str):
        """Start polling for market data updates."""
        subscription_key = f"{exchange}:{symbol}"
        
        if subscription_key in self.polling_tasks:
            return  # Already polling
        
        async def poll_worker():
            """Worker function for polling market data."""
            while self.is_running and subscription_key in self.subscriptions:
                try:
                    # Fetch market data
                    market_data = await self.gomarket_client.get_ticker(exchange, symbol)
                    
                    # Notify callbacks
                    await self._notify_callbacks(subscription_key, market_data)
                    
                    # Wait before next poll
                    await asyncio.sleep(self.polling_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(
                        "Error in polling worker",
                        exchange=exchange,
                        symbol=symbol,
                        error=str(e)
                    )
                    await asyncio.sleep(self.polling_interval)
        
        task = asyncio.create_task(poll_worker())
        self.polling_tasks[subscription_key] = task
        
        self.logger.info(
            "Started polling for market data",
            exchange=exchange,
            symbol=symbol,
            interval=self.polling_interval
        )
    
    async def _notify_callbacks(self, subscription_key: str, market_data: MarketData):
        """Notify all callbacks for a subscription."""
        if subscription_key not in self.subscriptions:
            return
        
        callbacks = self.subscriptions[subscription_key]
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(market_data)
                else:
                    callback(market_data)
            except Exception as e:
                self.logger.error(
                    "Error in callback",
                    subscription_key=subscription_key,
                    error=str(e)
                )
    
    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Parse market data from message
            market_data = self._parse_websocket_data(data)
            
            if market_data:
                subscription_key = f"{market_data.exchange}:{market_data.symbol}"
                await self._notify_callbacks(subscription_key, market_data)
            
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse WebSocket message", error=str(e))
        except Exception as e:
            self.logger.error("Error handling WebSocket message", error=str(e))
    
    def _parse_websocket_data(self, data: Dict[str, Any]) -> Optional[MarketData]:
        """Parse market data from WebSocket message."""
        try:
            # Extract market data fields from WebSocket message
            # This would need to be adapted based on actual GoMarket WebSocket format
            
            symbol = data.get('symbol', '')
            exchange = data.get('exchange', '')
            
            if not symbol or not exchange:
                return None
            
            # Parse price data
            bid_price = float(data.get('bid', data.get('bestBid', 0)))
            ask_price = float(data.get('ask', data.get('bestAsk', 0)))
            bid_size = float(data.get('bidSize', data.get('bestBidSize', 0)))
            ask_size = float(data.get('askSize', data.get('bestAskSize', 0)))
            last_price = float(data.get('last', data.get('lastPrice', (bid_price + ask_price) / 2)))
            
            # Parse timestamp
            timestamp = datetime.utcnow()
            if 'timestamp' in data:
                try:
                    ts_value = data['timestamp']
                    if isinstance(ts_value, (int, float)):
                        timestamp = datetime.fromtimestamp(ts_value / 1000)
                except Exception:
                    pass
            
            return MarketData(
                symbol=symbol,
                exchange=exchange,
                bid_price=bid_price,
                bid_size=bid_size,
                ask_price=ask_price,
                ask_size=ask_size,
                last_price=last_price,
                timestamp=timestamp
            )
            
        except Exception as e:
            self.logger.error("Failed to parse WebSocket data", error=str(e))
            return None
    
    async def start(self):
        """Start the WebSocket client."""
        self.is_running = True
        
        if self.use_polling:
            self.logger.info("Starting in polling mode")
            # Polling tasks are started when subscriptions are made
            return
        
        # Start WebSocket message handling
        try:
            while self.is_running and self.is_connected:
                try:
                    message = await self.websocket.recv()
                    await self._handle_websocket_message(message)
                    
                except ConnectionClosed:
                    self.logger.warning("WebSocket connection closed")
                    await self._reconnect()
                    break
                    
                except WebSocketException as e:
                    self.logger.error("WebSocket error", error=str(e))
                    await self._reconnect()
                    break
                    
        except Exception as e:
            self.logger.error("Error in WebSocket client", error=str(e))
            self.is_running = False
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if self.reconnect_count >= self.max_reconnect_attempts:
            self.logger.error("Max reconnection attempts reached, switching to polling")
            self.use_polling = True
            self.is_running = True
            return
        
        self.reconnect_count += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_count - 1))
        
        self.logger.info(
            "Attempting reconnection",
            attempt=self.reconnect_count,
            delay=delay
        )
        
        await asyncio.sleep(delay)
        
        if await self.connect():
            # Resubscribe to all active subscriptions
            for subscription_key in self.subscriptions.keys():
                exchange, symbol = subscription_key.split(':')
                await self._send_subscription_message(exchange, symbol)
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and statistics."""
        return {
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "use_polling": self.use_polling,
            "reconnect_count": self.reconnect_count,
            "subscriptions_count": len(self.subscriptions),
            "polling_tasks_count": len(self.polling_tasks),
            "websocket_url": self.websocket_url,
            "polling_interval": self.polling_interval if self.use_polling else None
        }


class DataStreamManager(LoggerMixin):
    """
    Manager for multiple data streams.
    
    Coordinates between WebSocket client and GoMarket client to provide
    unified data streaming interface.
    """
    
    def __init__(self, gomarket_client: GoMarketClient):
        """Initialize data stream manager."""
        self.gomarket_client = gomarket_client
        self.websocket_client = WebSocketClient(gomarket_client)
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start the data stream manager."""
        await self.websocket_client.connect()
        await self.websocket_client.start()
    
    async def stop(self):
        """Stop the data stream manager."""
        await self.websocket_client.disconnect()
    
    async def subscribe_to_market_data(
        self,
        exchange: str,
        symbol: str,
        callback: Callable[[MarketData], None]
    ):
        """Subscribe to market data for a symbol."""
        stream_key = f"{exchange}:{symbol}"
        
        await self.websocket_client.subscribe(exchange, symbol, callback)
        
        self.active_streams[stream_key] = {
            "exchange": exchange,
            "symbol": symbol,
            "callback": callback,
            "started_at": datetime.utcnow()
        }
        
        self.logger.info(
            "Subscribed to market data stream",
            exchange=exchange,
            symbol=symbol
        )
    
    async def unsubscribe_from_market_data(self, exchange: str, symbol: str):
        """Unsubscribe from market data for a symbol."""
        stream_key = f"{exchange}:{symbol}"
        
        await self.websocket_client.unsubscribe(exchange, symbol)
        
        if stream_key in self.active_streams:
            del self.active_streams[stream_key]
        
        self.logger.info(
            "Unsubscribed from market data stream",
            exchange=exchange,
            symbol=symbol
        )
    
    async def get_stream_status(self) -> Dict[str, Any]:
        """Get status of all active streams."""
        return {
            "active_streams": len(self.active_streams),
            "streams": list(self.active_streams.keys()),
            "websocket_status": await self.websocket_client.get_connection_status()
        }
