"""
Telegram bot handlers for command processing and user interactions.

This module contains all command handlers, callback handlers, and conversation
handlers for the trading bot system.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    MessageHandler, 
    CommandHandler, 
    CallbackQueryHandler,
    filters
)

from src.bot.keyboards import BotKeyboards, ConversationStates
from src.bot.messages import BotMessages
from src.data.gomarket_client import GoMarketClient, GoMarketAPIError
from src.data.websocket_client import DataStreamManager
from src.services.arbitrage_service import ArbitrageService
from src.services.market_view_service import MarketViewService
from src.utils.logger import LoggerMixin
from src.utils.config import config


class BotHandlers(LoggerMixin):
    """Main class containing all bot handlers."""
    
    def __init__(self):
        """Initialize bot handlers with required services."""
        self.gomarket_client: Optional[GoMarketClient] = None
        self.data_stream_manager: Optional[DataStreamManager] = None
        self.arbitrage_service: Optional[ArbitrageService] = None
        self.market_view_service: Optional[MarketViewService] = None
        
        # User session data
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        self.logger.info("Bot handlers initialized")
    
    async def initialize_services(self):
        """Initialize all required services."""
        try:
            self.gomarket_client = GoMarketClient()
            self.data_stream_manager = DataStreamManager(self.gomarket_client)
            self.arbitrage_service = ArbitrageService(
                self.gomarket_client, 
                self.data_stream_manager
            )
            self.market_view_service = MarketViewService(
                self.gomarket_client,
                self.data_stream_manager
            )
            
            self.logger.info("All services initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize services", error=str(e))
            raise
    
    async def cleanup_services(self):
        """Cleanup all services."""
        try:
            if self.data_stream_manager:
                await self.data_stream_manager.stop()
            if self.gomarket_client:
                await self.gomarket_client.close()
            
            self.logger.info("All services cleaned up successfully")
            
        except Exception as e:
            self.logger.error("Error during service cleanup", error=str(e))
    
    def _get_user_session(self, user_id: int) -> Dict[str, Any]:
        """Get or create user session."""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'selected_exchanges': [],
                'selected_symbols': [],
                'threshold': config.default_threshold_percentage,
                'update_interval': config.default_update_interval,
                'current_conversation': None
            }
        return self.user_sessions[user_id]
    
    # Command handlers
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        self.logger.info("Start command received", user_id=user.id, username=user.username)
        
        # Initialize user session
        self._get_user_session(user.id)
        
        keyboard = BotKeyboards.get_main_menu()
        await update.message.reply_text(
            BotMessages.WELCOME_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return ConversationStates.END
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user = update.effective_user
        
        self.logger.info("Help command received", user_id=user.id)
        
        keyboard = BotKeyboards.get_help_menu()
        await update.message.reply_text(
            BotMessages.HELP_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        self.logger.info("Status command received", user_id=user.id)
        
        try:
            # Get status from services
            active_monitoring = await self.arbitrage_service.get_active_sessions_count(chat_id) if self.arbitrage_service else 0
            active_market_views = await self.market_view_service.get_active_sessions_count(chat_id) if self.market_view_service else 0
            
            status_message = BotMessages.status_overview(
                active_monitoring=active_monitoring,
                active_market_views=active_market_views,
                total_opportunities=0,  # TODO: Get from statistics service
                last_opportunity_time=None
            )
            
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error("Error getting status", error=str(e))
            await update.message.reply_text(
                BotMessages.error_generic("Failed to retrieve status information")
            )
    
    async def list_symbols_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_symbols command."""
        user = update.effective_user
        
        self.logger.info("List symbols command received", user_id=user.id)
        
        # Check if exchange is provided
        if context.args:
            exchange = context.args[0].lower()
            if exchange not in config.supported_exchanges:
                await update.message.reply_text(
                    BotMessages.error_exchange_not_supported(exchange)
                )
                return
            
            await self._show_symbols_for_exchange(update, exchange)
        else:
            # Show exchange selection
            keyboard = self._get_exchange_selection_keyboard()
            await update.message.reply_text(
                "Select an exchange to view available symbols:",
                reply_markup=keyboard
            )
    
    async def monitor_arb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor_arb command."""
        user = update.effective_user
        
        self.logger.info("Monitor arbitrage command received", user_id=user.id)
        
        # Start arbitrage monitoring conversation
        keyboard = BotKeyboards.get_exchange_selection()
        await update.message.reply_text(
            BotMessages.arbitrage_monitoring_start(),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return ConversationStates.SELECTING_EXCHANGES
    
    async def stop_arb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop_arb command."""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        self.logger.info("Stop arbitrage command received", user_id=user.id)
        
        try:
            if self.arbitrage_service:
                await self.arbitrage_service.stop_monitoring(chat_id)
            
            keyboard = BotKeyboards.get_monitoring_controls(is_active=False)
            await update.message.reply_text(
                BotMessages.arbitrage_monitoring_stopped(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error("Error stopping arbitrage monitoring", error=str(e))
            await update.message.reply_text(
                BotMessages.error_generic("Failed to stop monitoring")
            )
    
    async def view_market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_market command."""
        user = update.effective_user
        
        self.logger.info("View market command received", user_id=user.id)
        
        if context.args:
            symbol = context.args[0].upper()
            # Start market view for specific symbol
            await self._start_market_view_for_symbol(update, symbol)
        else:
            # Show symbol input prompt
            keyboard = BotKeyboards.get_symbol_search_keyboard()
            await update.message.reply_text(
                BotMessages.symbol_search_prompt(),
                reply_markup=keyboard
            )
    
    async def get_cbbo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /get_cbbo command."""
        user = update.effective_user
        
        self.logger.info("Get CBBO command received", user_id=user.id)
        
        if not context.args:
            await update.message.reply_text(
                "Please provide a symbol. Example: /get_cbbo BTC/USDT"
            )
            return
        
        symbol = context.args[0].upper()
        
        try:
            if self.market_view_service:
                cbbo = await self.market_view_service.get_current_cbbo(
                    symbol, 
                    config.supported_exchanges
                )
                
                await update.message.reply_text(
                    BotMessages.cbbo_result(cbbo),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    BotMessages.error_generic("Market view service not available")
                )
                
        except Exception as e:
            self.logger.error("Error getting CBBO", symbol=symbol, error=str(e))
            await update.message.reply_text(
                BotMessages.cbbo_error(symbol, str(e))
            )
    
    # Callback query handlers
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        data = query.data
        
        self.logger.info(
            "Callback query received",
            user_id=user_id,
            chat_id=chat_id,
            callback_data=data
        )
        
        try:
            # Route callback to appropriate handler
            if data == "main_menu":
                await self._handle_main_menu(query)
            elif data == "monitor_arb":
                await self._handle_monitor_arb_callback(query)
            elif data == "view_market":
                await self._handle_view_market_callback(query)
            elif data.startswith("select_exchange:"):
                await self._handle_exchange_selection(query)
            elif data == "confirm_exchanges":
                await self._handle_confirm_exchanges(query)
            elif data.startswith("select_symbol:"):
                await self._handle_symbol_selection(query)
            elif data.startswith("select_threshold:"):
                await self._handle_threshold_selection(query)
            elif data == "start_monitoring":
                await self._handle_start_monitoring(query)
            elif data == "stop_monitoring":
                await self._handle_stop_monitoring(query)
            elif data == "help":
                await self._handle_help_callback(query)
            elif data == "status":
                await self._handle_status_callback(query)
            else:
                await self._handle_unknown_callback(query)
                
        except Exception as e:
            self.logger.error("Error handling callback query", error=str(e))
            await query.edit_message_text(
                BotMessages.error_generic("An error occurred processing your request")
            )
    
    # Conversation handlers
    async def select_exchanges_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle exchange selection conversation."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        session = self._get_user_session(user_id)
        
        if query.data.startswith("select_exchange:"):
            exchange = query.data.split(":", 1)[1]
            
            if exchange in session['selected_exchanges']:
                session['selected_exchanges'].remove(exchange)
            else:
                session['selected_exchanges'].append(exchange)
            
            # Update keyboard with new selection
            keyboard = BotKeyboards.get_exchange_selection(
                selected=session['selected_exchanges']
            )
            await query.edit_message_reply_markup(reply_markup=keyboard)
        
        elif query.data == "confirm_exchanges":
            if not session['selected_exchanges']:
                await query.edit_message_text(
                    "Please select at least one exchange to continue."
                )
                return ConversationStates.SELECTING_EXCHANGES
            
            # Move to symbol selection
            await self._show_symbol_selection(query, session['selected_exchanges'][0])
            return ConversationStates.SELECTING_SYMBOLS
        
        elif query.data == "cancel_exchange_selection":
            await query.edit_message_text(
                "Exchange selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )
            return ConversationStates.END
        
        return ConversationStates.SELECTING_EXCHANGES
    
    async def select_symbols_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle symbol selection conversation."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        session = self._get_user_session(user_id)
        
        if query.data.startswith("select_symbol:"):
            symbol = query.data.split(":", 1)[1]
            
            if symbol in session['selected_symbols']:
                session['selected_symbols'].remove(symbol)
            else:
                session['selected_symbols'].append(symbol)
            
            # Update keyboard with new selection
            # TODO: Implement symbol pagination
            keyboard = BotKeyboards.get_symbol_selection(
                symbols=[],  # TODO: Get from API
                selected=session['selected_symbols']
            )
            await query.edit_message_reply_markup(reply_markup=keyboard)
        
        elif query.data == "confirm_symbols":
            if not session['selected_symbols']:
                await query.edit_message_text(
                    "Please select at least one symbol to continue."
                )
                return ConversationStates.SELECTING_SYMBOLS
            
            # Move to threshold selection
            await self._show_threshold_selection(query)
            return ConversationStates.SETTING_THRESHOLD
        
        elif query.data == "cancel_symbol_selection":
            await query.edit_message_text(
                "Symbol selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )
            return ConversationStates.END
        
        return ConversationStates.SELECTING_SYMBOLS
    
    async def set_threshold_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle threshold setting conversation."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        session = self._get_user_session(user_id)
        
        if query.data.startswith("select_threshold:"):
            threshold = float(query.data.split(":", 1)[1])
            session['threshold'] = threshold
            
            await query.edit_message_text(
                BotMessages.threshold_set(threshold),
                reply_markup=BotKeyboards.get_main_menu()
            )
            
            # Move to confirmation
            return await self._show_monitoring_confirmation(query, session)
        
        elif query.data == "cancel_threshold":
            await query.edit_message_text(
                "Threshold selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )
            return ConversationStates.END
        
        return ConversationStates.SETTING_THRESHOLD
    
    # Helper methods
    async def _show_symbols_for_exchange(self, update: Update, exchange: str):
        """Show symbols for a specific exchange."""
        try:
            if not self.gomarket_client:
                await update.message.reply_text(
                    BotMessages.error_generic("Market data service not available")
                )
                return
            
            symbols = await self.gomarket_client.get_symbols(exchange)
            
            if not symbols:
                await update.message.reply_text(
                    f"No symbols found for {exchange.upper()}"
                )
                return
            
            # Show first page of symbols
            keyboard = BotKeyboards.get_symbol_selection(symbols[:10])
            
            message = BotMessages.symbol_list_header(exchange)
            await update.message.reply_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except GoMarketAPIError as e:
            self.logger.error("API error getting symbols", exchange=exchange, error=str(e))
            await update.message.reply_text(
                BotMessages.error_generic(f"Failed to get symbols: {e}")
            )
        except Exception as e:
            self.logger.error("Error showing symbols", exchange=exchange, error=str(e))
            await update.message.reply_text(
                BotMessages.error_generic("Failed to retrieve symbols")
            )
    
    async def _show_symbol_selection(self, query, exchange: str):
        """Show symbol selection interface."""
        try:
            if not self.gomarket_client:
                await query.edit_message_text(
                    BotMessages.error_generic("Market data service not available")
                )
                return
            
            symbols = await self.gomarket_client.get_symbols(exchange)
            
            if not symbols:
                await query.edit_message_text(
                    f"No symbols found for {exchange.upper()}"
                )
                return
            
            keyboard = BotKeyboards.get_symbol_selection(symbols[:10])
            message = BotMessages.symbol_list_header(exchange)
            
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error("Error showing symbol selection", error=str(e))
            await query.edit_message_text(
                BotMessages.error_generic("Failed to load symbols")
            )
    
    async def _show_threshold_selection(self, query):
        """Show threshold selection interface."""
        keyboard = BotKeyboards.get_threshold_selection()
        message = "Select the minimum spread percentage threshold for arbitrage alerts:"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard
        )
    
    async def _show_monitoring_confirmation(self, query, session):
        """Show monitoring configuration confirmation."""
        config = MonitoringConfig(
            chat_id=query.message.chat_id,
            symbols=session['selected_symbols'],
            exchanges=session['selected_exchanges'],
            threshold_percentage=session['threshold']
        )
        
        keyboard = BotKeyboards.get_confirmation_dialog("start_monitoring")
        message = BotMessages.confirm_monitoring_start(config)
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return ConversationStates.CONFIRMING_MONITORING
    
    async def _handle_main_menu(self, query):
        """Handle main menu callback."""
        await query.edit_message_text(
            BotMessages.WELCOME_MESSAGE,
            reply_markup=BotKeyboards.get_main_menu(),
            parse_mode='Markdown'
        )
    
    async def _handle_monitor_arb_callback(self, query):
        """Handle monitor arbitrage callback."""
        keyboard = BotKeyboards.get_exchange_selection()
        await query.edit_message_text(
            BotMessages.arbitrage_monitoring_start(),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    async def _handle_view_market_callback(self, query):
        """Handle view market callback."""
        # For symbol search we use a ReplyKeyboardMarkup (reply keyboard).
        # Editing an existing message after a callback expects an InlineKeyboardMarkup,
        # so send a new message with the reply keyboard instead to avoid Telegram 400 errors.
        keyboard = BotKeyboards.get_symbol_search_keyboard()

        # Acknowledge the callback and send a fresh message with the reply keyboard
        await query.answer()
        await query.message.reply_text(
            BotMessages.symbol_search_prompt(),
            reply_markup=keyboard
        )

    async def _handle_exchange_selection(self, query):
        """Handle exchange selection callbacks coming from inline buttons."""
        await query.answer()

        user_id = query.from_user.id
        session = self._get_user_session(user_id)

        # Toggle selection
        if query.data.startswith("select_exchange:"):
            exchange = query.data.split(":", 1)[1]
            if exchange in session["selected_exchanges"]:
                session["selected_exchanges"].remove(exchange)
            else:
                session["selected_exchanges"].append(exchange)

            keyboard = BotKeyboards.get_exchange_selection(selected=session["selected_exchanges"])
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif query.data == "confirm_exchanges":
            if not session["selected_exchanges"]:
                await query.edit_message_text("Please select at least one exchange to continue.")
                return

            # Proceed to symbol selection for the first selected exchange
            await self._show_symbol_selection(query, session["selected_exchanges"][0])

        elif query.data == "cancel_exchange_selection":
            await query.edit_message_text(
                "Exchange selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )

    async def _handle_confirm_exchanges(self, query):
        """Alias handler in case callbacks route directly to confirm action."""
        await query.answer()
        user_id = query.from_user.id
        session = self._get_user_session(user_id)

        if not session["selected_exchanges"]:
            await query.edit_message_text("Please select at least one exchange to continue.")
            return

        await self._show_symbol_selection(query, session["selected_exchanges"][0])
    
    async def _handle_help_callback(self, query):
        """Handle help callback."""
        keyboard = BotKeyboards.get_help_menu()
        await query.edit_message_text(
            BotMessages.HELP_MESSAGE,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def _handle_symbol_selection(self, query):
        """Handle symbol selection callbacks from inline buttons."""
        await query.answer()

        user_id = query.from_user.id
        session = self._get_user_session(user_id)

        if query.data.startswith("select_symbol:"):
            symbol = query.data.split(":", 1)[1]

            if symbol in session["selected_symbols"]:
                session["selected_symbols"].remove(symbol)
            else:
                session["selected_symbols"].append(symbol)

            # Update keyboard (symbols list may be empty when called from other places)
            keyboard = BotKeyboards.get_symbol_selection(symbols=[], selected=session["selected_symbols"])
            await query.edit_message_reply_markup(reply_markup=keyboard)

        elif query.data == "confirm_symbols":
            if not session["selected_symbols"]:
                await query.edit_message_text("Please select at least one symbol to continue.")
                return

            await self._show_threshold_selection(query)

        elif query.data == "cancel_symbol_selection":
            await query.edit_message_text(
                "Symbol selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )
    
    async def _handle_status_callback(self, query):
        """Handle status callback."""
        chat_id = query.message.chat_id
        
        try:
            active_monitoring = await self.arbitrage_service.get_active_sessions_count(chat_id) if self.arbitrage_service else 0
            active_market_views = await self.market_view_service.get_active_sessions_count(chat_id) if self.market_view_service else 0
            
            status_message = BotMessages.status_overview(
                active_monitoring=active_monitoring,
                active_market_views=active_market_views,
                total_opportunities=0,
                last_opportunity_time=None
            )
            
            keyboard = BotKeyboards.get_main_menu()
            await query.edit_message_text(
                status_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error("Error getting status", error=str(e))
            await query.edit_message_text(
                BotMessages.error_generic("Failed to retrieve status information")
            )
    
    async def _handle_start_monitoring(self, query):
        """Handle start monitoring callback."""
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        session = self._get_user_session(user_id)
        
        try:
            if self.arbitrage_service:
                config = MonitoringConfig(
                    chat_id=chat_id,
                    symbols=session['selected_symbols'],
                    exchanges=session['selected_exchanges'],
                    threshold_percentage=session['threshold']
                )
                
                await self.arbitrage_service.start_monitoring(config)
                
                keyboard = BotKeyboards.get_monitoring_controls(is_active=True)
                await query.edit_message_text(
                    BotMessages.arbitrage_monitoring_started(config),
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    BotMessages.error_generic("Arbitrage service not available")
                )
                
        except Exception as e:
            self.logger.error("Error starting monitoring", error=str(e))
            await query.edit_message_text(
                BotMessages.error_generic("Failed to start monitoring")
            )

    async def _handle_threshold_selection(self, query):
        """Handle threshold selection callbacks."""
        await query.answer()

        user_id = query.from_user.id
        session = self._get_user_session(user_id)

        if query.data.startswith("select_threshold:"):
            try:
                threshold = float(query.data.split(":", 1)[1])
            except Exception:
                threshold = config.default_threshold_percentage

            session["threshold"] = threshold

            await query.edit_message_text(
                BotMessages.threshold_set(threshold),
                reply_markup=BotKeyboards.get_main_menu()
            )

            # Move to confirmation
            await self._show_monitoring_confirmation(query, session)

        elif query.data == "cancel_threshold":
            await query.edit_message_text(
                "Threshold selection cancelled.",
                reply_markup=BotKeyboards.get_main_menu()
            )
    
    async def _handle_stop_monitoring(self, query):
        """Handle stop monitoring callback."""
        chat_id = query.message.chat_id
        
        try:
            if self.arbitrage_service:
                await self.arbitrage_service.stop_monitoring(chat_id)
            
            keyboard = BotKeyboards.get_monitoring_controls(is_active=False)
            await query.edit_message_text(
                BotMessages.arbitrage_monitoring_stopped(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error("Error stopping monitoring", error=str(e))
            await query.edit_message_text(
                BotMessages.error_generic("Failed to stop monitoring")
            )
    
    async def _handle_unknown_callback(self, query):
        """Handle unknown callback queries."""
        await query.edit_message_text(
            "Unknown command. Please use the main menu.",
            reply_markup=BotKeyboards.get_main_menu()
        )
    
    def _get_exchange_selection_keyboard(self):
        """Get exchange selection keyboard for symbol listing."""
        keyboard = []
        for exchange in config.supported_exchanges:
            keyboard.append([
                InlineKeyboardButton(
                    exchange.upper(),
                    callback_data=f"list_symbols_{exchange}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _start_market_view_for_symbol(self, update: Update, symbol: str):
        """Start market view for a specific symbol."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            if self.market_view_service:
                cbbo = await self.market_view_service.get_current_cbbo(
                    symbol,
                    config.supported_exchanges
                )
                
                keyboard = BotKeyboards.get_market_view_controls()
                await update.message.reply_text(
                    BotMessages.cbbo_result(cbbo),
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    BotMessages.error_generic("Market view service not available")
                )
                
        except Exception as e:
            self.logger.error("Error starting market view", symbol=symbol, error=str(e))
            await update.message.reply_text(
                BotMessages.cbbo_error(symbol, str(e))
            )
    
    # Error handlers
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors in bot operations."""
        error = context.error
        
        self.logger.error("Bot error occurred", error=str(error))
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                BotMessages.error_generic("An unexpected error occurred. Please try again.")
            )
    
    # Message handlers
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for custom symbol input, etc.)."""
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check if this is a symbol search
        if message_text.upper().endswith('/USDT') or message_text.upper().endswith('/BTC'):
            symbol = message_text.upper()
            await self._start_market_view_for_symbol(update, symbol)
        else:
            await update.message.reply_text(
                "I don't understand that message. Please use the menu buttons or commands.",
                reply_markup=BotKeyboards.get_main_menu()
            )
    
    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        await update.message.reply_text(
            "Unknown command. Please use /help to see available commands.",
            reply_markup=BotKeyboards.get_main_menu()
        )
