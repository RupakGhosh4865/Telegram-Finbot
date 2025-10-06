"""
Main application entry point for the GoQuant Trading Bot.

This module initializes all components, sets up the Telegram bot,
and coordinates between all services for the trading information system.
"""

import asyncio
import signal
import sys
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from src.bot.handlers import BotHandlers
from src.bot.keyboards import ConversationStates
from src.data.gomarket_client import GoMarketClient
from src.data.websocket_client import DataStreamManager
from src.services.arbitrage_service import ArbitrageService
from src.services.market_view_service import MarketViewService
from src.utils.config import config
from src.utils.logger import setup_logging, get_logger


class TradingBotApplication:
    """Main application class for the trading bot."""
    
    def __init__(self):
        """Initialize the trading bot application."""
        self.logger = get_logger(__name__)
        
        # Core components
        self.application: Optional[Application] = None
        self.bot_handlers: Optional[BotHandlers] = None
        self.gomarket_client: Optional[GoMarketClient] = None
        self.data_stream_manager: Optional[DataStreamManager] = None
        self.arbitrage_service: Optional[ArbitrageService] = None
        self.market_view_service: Optional[MarketViewService] = None
        
        # Application state
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        
        self.logger.info("Trading bot application initialized")
    
    async def initialize(self):
        """Initialize all application components."""
        try:
            self.logger.info("Initializing trading bot application")
            
            # Initialize Telegram application
            await self._initialize_telegram_app()
            
            # Initialize data clients
            await self._initialize_data_clients()
            
            # Initialize services
            await self._initialize_services()
            
            # Initialize bot handlers
            await self._initialize_bot_handlers()
            
            # Set up handlers
            await self._setup_handlers()
            
            # Set up notification callbacks
            await self._setup_notification_callbacks()
            
            # Run startup checks
            await self._run_startup_checks()
            
            self.logger.info("Trading bot application initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize application", error=str(e))
            raise
    
    async def _initialize_telegram_app(self):
        """Initialize Telegram bot application."""
        try:
            self.application = Application.builder().token(config.telegram_bot_token).build()
            
            # Configure application settings
            self.application.bot_data["config"] = config
            
            self.logger.info("Telegram application initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize Telegram application", error=str(e))
            raise
    
    async def _initialize_data_clients(self):
        """Initialize data clients."""
        try:
            # Initialize GoMarket client
            self.gomarket_client = GoMarketClient()
            
            # Initialize data stream manager
            self.data_stream_manager = DataStreamManager(self.gomarket_client)
            
            self.logger.info("Data clients initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize data clients", error=str(e))
            raise
    
    async def _initialize_services(self):
        """Initialize business logic services."""
        try:
            # Initialize arbitrage service
            self.arbitrage_service = ArbitrageService(
                self.gomarket_client,
                self.data_stream_manager
            )
            
            # Initialize market view service
            self.market_view_service = MarketViewService(
                self.gomarket_client,
                self.data_stream_manager
            )
            
            self.logger.info("Services initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize services", error=str(e))
            raise
    
    async def _initialize_bot_handlers(self):
        """Initialize bot handlers."""
        try:
            self.bot_handlers = BotHandlers()
            await self.bot_handlers.initialize_services()
            
            # Set service references
            self.bot_handlers.gomarket_client = self.gomarket_client
            self.bot_handlers.data_stream_manager = self.data_stream_manager
            self.bot_handlers.arbitrage_service = self.arbitrage_service
            self.bot_handlers.market_view_service = self.market_view_service
            
            self.logger.info("Bot handlers initialized")
            
        except Exception as e:
            self.logger.error("Failed to initialize bot handlers", error=str(e))
            raise
    
    async def _setup_handlers(self):
        """Set up all bot handlers."""
        try:
            # Command handlers
            self.application.add_handler(CommandHandler("start", self.bot_handlers.start_command))
            self.application.add_handler(CommandHandler("help", self.bot_handlers.help_command))
            self.application.add_handler(CommandHandler("status", self.bot_handlers.status_command))
            self.application.add_handler(CommandHandler("list_symbols", self.bot_handlers.list_symbols_command))
            self.application.add_handler(CommandHandler("monitor_arb", self.bot_handlers.monitor_arb_command))
            self.application.add_handler(CommandHandler("stop_arb", self.bot_handlers.stop_arb_command))
            self.application.add_handler(CommandHandler("view_market", self.bot_handlers.view_market_command))
            self.application.add_handler(CommandHandler("get_cbbo", self.bot_handlers.get_cbbo_command))
            
            # Callback query handlers
            self.application.add_handler(CallbackQueryHandler(self.bot_handlers.handle_callback_query))
            
            # Message handlers
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.bot_handlers.handle_text_message)
            )
            
            # Error handler
            self.application.add_error_handler(self.bot_handlers.error_handler)
            
            self.logger.info("Bot handlers set up successfully")
            
        except Exception as e:
            self.logger.error("Failed to set up handlers", error=str(e))
            raise
    
    async def _setup_notification_callbacks(self):
        """Set up notification callbacks between services and bot."""
        try:
            # Set up arbitrage opportunity notifications
            async def arbitrage_notification_callback(chat_id: int, opportunity):
                """Callback for arbitrage opportunity notifications."""
                try:
                    # Send notification via Telegram
                    message = opportunity.format_telegram_message()
                    
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Error sending arbitrage notification",
                        chat_id=chat_id,
                        error=str(e)
                    )
            
            # Set up market view notifications
            async def market_view_notification_callback(chat_id: int, cbbo, is_refresh: bool = False):
                """Callback for market view notifications."""
                try:
                    # Send notification via Telegram
                    message = cbbo.format_telegram_message("update" if not is_refresh else "refresh")
                    
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Error sending market view notification",
                        chat_id=chat_id,
                        error=str(e)
                    )
            
            # Register callbacks
            await self.arbitrage_service.add_notification_callback(arbitrage_notification_callback)
            await self.market_view_service.add_notification_callback(market_view_notification_callback)
            
            self.logger.info("Notification callbacks set up successfully")
            
        except Exception as e:
            self.logger.error("Failed to set up notification callbacks", error=str(e))
            raise
    
    async def _run_startup_checks(self):
        """Run startup health checks."""
        try:
            self.logger.info("Running startup checks")
            
            # Check Telegram bot connectivity
            bot_info = await self.application.bot.get_me()
            self.logger.info(
                "Telegram bot connected",
                username=bot_info.username,
                first_name=bot_info.first_name
            )
            
            # Check GoMarket API connectivity
            if self.gomarket_client:
                health_status = await self.gomarket_client.health_check()
                self.logger.info(
                    "GoMarket API health check",
                    status=health_status.get("status"),
                    exchanges=health_status.get("exchanges", {}).keys()
                )
            
            # Check supported exchanges
            self.logger.info(
                "Supported exchanges",
                exchanges=config.supported_exchanges
            )
            
            self.logger.info("Startup checks completed successfully")
            
        except Exception as e:
            self.logger.error("Startup checks failed", error=str(e))
            raise
    
    async def start(self):
        """Start the trading bot application."""
        try:
            self.logger.info("Starting trading bot application")
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Start data stream manager
            if self.data_stream_manager:
                await self.data_stream_manager.start()
            
            # Start Telegram bot
            await self.application.initialize()
            await self.application.start()
            
            # Start bot polling
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            self.is_running = True
            self.logger.info("Trading bot application started successfully")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            self.logger.error("Failed to start application", error=str(e))
            raise
    
    async def stop(self):
        """Stop the trading bot application."""
        try:
            self.logger.info("Stopping trading bot application")
            
            # Set shutdown event
            self.shutdown_event.set()
            
            # Stop services
            if self.arbitrage_service:
                await self.arbitrage_service.shutdown()
            
            if self.market_view_service:
                await self.market_view_service.shutdown()
            
            # Stop data stream manager
            if self.data_stream_manager:
                await self.data_stream_manager.stop()
            
            # Stop Telegram bot
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            # Close data clients
            if self.gomarket_client:
                await self.gomarket_client.close()
            
            # Cleanup bot handlers
            if self.bot_handlers:
                await self.bot_handlers.cleanup_services()
            
            self.is_running = False
            self.logger.info("Trading bot application stopped successfully")
            
        except Exception as e:
            self.logger.error("Error during application shutdown", error=str(e))
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.stop())
        
        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def get_application_status(self) -> dict:
        """Get comprehensive application status."""
        try:
            status = {
                "application": {
                    "is_running": self.is_running,
                    "uptime": "N/A",  # TODO: Implement uptime tracking
                },
                "telegram_bot": {
                    "connected": self.application is not None,
                },
                "gomarket_client": {
                    "initialized": self.gomarket_client is not None,
                },
                "arbitrage_service": {
                    "initialized": self.arbitrage_service is not None,
                },
                "market_view_service": {
                    "initialized": self.market_view_service is not None,
                }
            }
            
            # Get service statistics
            if self.arbitrage_service:
                status["arbitrage_service"]["statistics"] = await self.arbitrage_service.get_service_statistics()
            
            if self.market_view_service:
                status["market_view_service"]["statistics"] = await self.market_view_service.get_service_statistics()
            
            return status
            
        except Exception as e:
            self.logger.error("Error getting application status", error=str(e))
            return {"error": str(e)}


async def main():
    """Main entry point for the application."""
    # Set up logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting GoQuant Trading Bot")
    
    # Create and initialize application
    app = TradingBotApplication()
    
    try:
        # Initialize application
        await app.initialize()
        
        # Start application
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Application error", error=str(e))
        sys.exit(1)
    finally:
        # Cleanup
        await app.stop()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
