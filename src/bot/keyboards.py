"""
Interactive inline keyboards for the Telegram bot.

This module provides all the inline keyboard layouts used throughout the bot
for user interactions and command navigation.
"""

from typing import List, Optional, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ConversationHandler

from src.utils.config import config


class BotKeyboards:
    """Class containing all keyboard layouts for the Telegram bot."""
    
    @staticmethod
    def get_main_menu() -> InlineKeyboardMarkup:
        """Get the main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Monitor Arbitrage", callback_data="monitor_arb"),
                InlineKeyboardButton("📈 Market View", callback_data="view_market")
            ],
            [
                InlineKeyboardButton("🔍 Get CBBO", callback_data="get_cbbo"),
                InlineKeyboardButton("📋 List Symbols", callback_data="list_symbols")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                InlineKeyboardButton("ℹ️ Help", callback_data="help")
            ],
            [
                InlineKeyboardButton("📊 Status", callback_data="status")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_exchange_selection(exchanges: List[str] = None, selected: List[str] = None) -> InlineKeyboardMarkup:
        """
        Get exchange selection keyboard with multi-select capability.
        
        Args:
            exchanges: List of available exchanges
            selected: List of currently selected exchanges
        """
        if exchanges is None:
            exchanges = config.supported_exchanges
        
        if selected is None:
            selected = []
        
        keyboard = []
        
        # Add exchange selection buttons
        for i in range(0, len(exchanges), 2):
            row = []
            for j in range(2):
                if i + j < len(exchanges):
                    exchange = exchanges[i + j]
                    display_name = exchange.upper()
                    prefix = "✅" if exchange in selected else "⬜"
                    
                    row.append(
                        InlineKeyboardButton(
                            f"{prefix} {display_name}",
                            callback_data=f"select_exchange:{exchange}"
                        )
                    )
            keyboard.append(row)
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton("✅ Confirm Selection", callback_data="confirm_exchanges"),
            InlineKeyboardButton("🔄 Select All", callback_data="select_all_exchanges")
        ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_exchange_selection")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_market_type_selection(selected: str = "spot") -> InlineKeyboardMarkup:
        """Get market type selection keyboard."""
        market_types = [
            ("spot", "💰 Spot"),
            ("futures", "📈 Futures"),
            ("options", "📊 Options")
        ]
        
        keyboard = []
        for market_type, display_name in market_types:
            prefix = "✅" if market_type == selected else "⬜"
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix} {display_name}",
                    callback_data=f"select_market_type:{market_type}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_market_type"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_market_type")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_symbol_selection(
        symbols: List[str],
        page: int = 0,
        symbols_per_page: int = 10,
        selected: List[str] = None
    ) -> InlineKeyboardMarkup:
        """
        Get paginated symbol selection keyboard.
        
        Args:
            symbols: List of available symbols
            page: Current page number
            symbols_per_page: Number of symbols per page
            selected: List of currently selected symbols
        """
        if selected is None:
            selected = []
        
        start_idx = page * symbols_per_page
        end_idx = start_idx + symbols_per_page
        page_symbols = symbols[start_idx:end_idx]
        
        keyboard = []
        
        # Add symbol buttons
        for symbol in page_symbols:
            prefix = "✅" if symbol in selected else "⬜"
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix} {symbol}",
                    callback_data=f"select_symbol:{symbol}"
                )
            ])
        
        # Add pagination buttons
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"symbol_page:{page-1}")
            )
        
        if end_idx < len(symbols):
            nav_row.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"symbol_page:{page+1}")
            )
        
        if nav_row:
            keyboard.append(nav_row)
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton("✅ Confirm Selection", callback_data="confirm_symbols"),
            InlineKeyboardButton("🔄 Select All", callback_data="select_all_symbols")
        ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_symbol_selection")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_threshold_selection() -> InlineKeyboardMarkup:
        """Get threshold percentage selection keyboard."""
        thresholds = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
        
        keyboard = []
        for i in range(0, len(thresholds), 2):
            row = []
            for j in range(2):
                if i + j < len(thresholds):
                    threshold = thresholds[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{threshold}%",
                            callback_data=f"select_threshold:{threshold}"
                        )
                    )
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("✏️ Custom", callback_data="custom_threshold")
        ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_threshold"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_threshold")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_monitoring_controls(is_active: bool = False) -> InlineKeyboardMarkup:
        """Get monitoring control buttons."""
        keyboard = []
        
        if is_active:
            keyboard.append([
                InlineKeyboardButton("⏹️ Stop Monitoring", callback_data="stop_monitoring")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("▶️ Start Monitoring", callback_data="start_monitoring")
            ])
        
        keyboard.append([
            InlineKeyboardButton("⚙️ Configure", callback_data="configure_monitoring"),
            InlineKeyboardButton("📊 Status", callback_data="monitoring_status")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_market_view_controls(is_active: bool = False) -> InlineKeyboardMarkup:
        """Get market view control buttons."""
        keyboard = []
        
        if is_active:
            keyboard.append([
                InlineKeyboardButton("⏹️ Stop Market View", callback_data="stop_market_view")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("▶️ Start Market View", callback_data="start_market_view")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_market_view"),
            InlineKeyboardButton("⚙️ Configure", callback_data="configure_market_view")
        ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_settings_menu() -> InlineKeyboardMarkup:
        """Get settings menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Default Threshold", callback_data="settings_threshold"),
                InlineKeyboardButton("⏱️ Update Interval", callback_data="settings_interval")
            ],
            [
                InlineKeyboardButton("🏢 Default Exchanges", callback_data="settings_exchanges"),
                InlineKeyboardButton("📈 Default Symbols", callback_data="settings_symbols")
            ],
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("📊 Statistics", callback_data="settings_stats")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_help_menu() -> InlineKeyboardMarkup:
        """Get help menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Arbitrage Monitoring", callback_data="help_arbitrage"),
                InlineKeyboardButton("📈 Market View", callback_data="help_market_view")
            ],
            [
                InlineKeyboardButton("🔍 CBBO Commands", callback_data="help_cbbo"),
                InlineKeyboardButton("📋 Symbol Commands", callback_data="help_symbols")
            ],
            [
                InlineKeyboardButton("⚙️ Settings Help", callback_data="help_settings"),
                InlineKeyboardButton("🚨 Troubleshooting", callback_data="help_troubleshooting")
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation_dialog(action: str, details: str = "") -> InlineKeyboardMarkup:
        """
        Get confirmation dialog keyboard.
        
        Args:
            action: The action to confirm
            details: Additional details to display
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"confirm:{action}"),
                InlineKeyboardButton("❌ No", callback_data=f"cancel:{action}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Get simple back button keyboard."""
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data=callback_data)]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_cancel_button(callback_data: str = "cancel") -> InlineKeyboardMarkup:
        """Get simple cancel button keyboard."""
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data=callback_data)]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_update_interval_selection() -> InlineKeyboardMarkup:
        """Get update interval selection keyboard."""
        intervals = [1, 2, 5, 10, 15, 30]  # seconds
        
        keyboard = []
        for i in range(0, len(intervals), 2):
            row = []
            for j in range(2):
                if i + j < len(intervals):
                    interval = intervals[i + j]
                    row.append(
                        InlineKeyboardButton(
                            f"{interval}s",
                            callback_data=f"select_interval:{interval}"
                        )
                    )
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data="confirm_interval"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_interval")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_symbol_search_keyboard() -> ReplyKeyboardMarkup:
        """Get symbol search keyboard with common symbols."""
        common_symbols = [
            ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
            ["ADA/USDT", "SOL/USDT", "DOT/USDT"],
            ["MATIC/USDT", "AVAX/USDT", "LINK/USDT"]
        ]
        
        keyboard = [
            [KeyboardButton(symbol) for symbol in row]
            for row in common_symbols
        ]
        
        keyboard.append([KeyboardButton("🔍 Custom Symbol")])
        keyboard.append([KeyboardButton("❌ Cancel")])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    @staticmethod
    def get_quick_actions() -> InlineKeyboardMarkup:
        """Get quick actions keyboard for power users."""
        keyboard = [
            [
                InlineKeyboardButton("🚨 Quick Arbitrage Check", callback_data="quick_arb_check"),
                InlineKeyboardButton("📊 Quick CBBO", callback_data="quick_cbbo")
            ],
            [
                InlineKeyboardButton("📈 Top Spreads", callback_data="top_spreads"),
                InlineKeyboardButton("📉 Market Summary", callback_data="market_summary")
            ],
            [
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


class ConversationStates:
    """Constants for conversation handler states."""
    
    # Arbitrage monitoring states
    SELECTING_EXCHANGES = "selecting_exchanges"
    SELECTING_SYMBOLS = "selecting_symbols"
    SETTING_THRESHOLD = "setting_threshold"
    CONFIRMING_MONITORING = "confirming_monitoring"
    
    # Market view states
    SELECTING_MARKET_EXCHANGES = "selecting_market_exchanges"
    SELECTING_MARKET_SYMBOL = "selecting_market_symbol"
    SETTING_MARKET_INTERVAL = "setting_market_interval"
    CONFIRMING_MARKET_VIEW = "confirming_market_view"
    
    # Symbol listing states
    SELECTING_LIST_EXCHANGE = "selecting_list_exchange"
    SELECTING_LIST_MARKET_TYPE = "selecting_list_market_type"
    BROWSING_SYMBOLS = "browsing_symbols"
    
    # Settings states
    SETTINGS_THRESHOLD = "settings_threshold"
    SETTINGS_INTERVAL = "settings_interval"
    SETTINGS_EXCHANGES = "settings_exchanges"
    SETTINGS_SYMBOLS = "settings_symbols"
    
    # Custom input states
    CUSTOM_THRESHOLD = "custom_threshold"
    CUSTOM_SYMBOL = "custom_symbol"
    
    # End conversation
    END = ConversationHandler.END
