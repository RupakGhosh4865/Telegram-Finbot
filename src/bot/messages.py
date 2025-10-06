"""
Message templates for the Telegram bot.

This module contains all message templates used throughout the bot
for user communication and notifications.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.models.data_models import ArbitrageOpportunity, ConsolidatedBBO, MonitoringConfig


class BotMessages:
    """Class containing all message templates for the Telegram bot."""
    
    # Welcome and help messages
    WELCOME_MESSAGE = """
🚀 **Welcome to GoQuant Trading Bot!**

I'm your cryptocurrency trading assistant that helps you:

📊 **Monitor Arbitrage Opportunities**
• Detect price differences across exchanges
• Real-time alerts for profitable opportunities
• Customizable thresholds and filters

📈 **Consolidated Market View**
• Best bid/offer across all exchanges
• Real-time market data streaming
• Venue comparison and analysis

🔍 **Quick Market Queries**
• Instant CBBO (Consolidated Best Bid/Offer) lookups
• Symbol discovery and listing
• Market statistics and trends

**Supported Exchanges:** OKX, Deribit, Bybit, Binance

Use the menu below to get started or type `/help` for detailed commands.
"""

    HELP_MESSAGE = """
📖 **GoQuant Trading Bot - Commands Guide**

**🎯 Main Commands:**
• `/start` - Initialize bot and show main menu
• `/help` - Show this help message
• `/status` - Show active monitoring sessions

**📊 Arbitrage Monitoring:**
• `/monitor_arb` - Start arbitrage monitoring wizard
• `/stop_arb` - Stop all arbitrage monitoring
• Configure exchanges, symbols, and thresholds
• Real-time alerts when opportunities are found

**📈 Market View:**
• `/view_market <symbol>` - Start consolidated market view
• `/stop_market` - Stop market view updates
• `/get_cbbo <symbol>` - Get instant CBBO for symbol
• Live updates showing best venues across exchanges

**📋 Symbol Discovery:**
• `/list_symbols <exchange>` - List available symbols
• Browse symbols by exchange and market type
• Search and filter functionality

**⚙️ Settings:**
• Configure default exchanges and symbols
• Set default thresholds and update intervals
• Manage notification preferences

**💡 Tips:**
• Use inline keyboards for easy navigation
• Set up monitoring for your favorite trading pairs
• Monitor multiple symbols simultaneously
• Use custom thresholds for your risk tolerance

Need more help? Use the menu buttons or contact support.
"""

    # Arbitrage monitoring messages
    @staticmethod
    def arbitrage_monitoring_start() -> str:
        return """
📊 **Arbitrage Monitoring Setup**

Let's configure your arbitrage monitoring session:

1️⃣ **Select Exchanges** - Choose which exchanges to monitor
2️⃣ **Select Symbols** - Pick trading pairs to watch
3️⃣ **Set Threshold** - Minimum spread percentage to alert on
4️⃣ **Start Monitoring** - Begin real-time monitoring

Use the buttons below to get started!
"""

    @staticmethod
    def arbitrage_monitoring_config(config: MonitoringConfig) -> str:
        return f"""
📊 **Current Monitoring Configuration**

**Exchanges:** {', '.join(config.exchanges).upper()}
**Symbols:** {', '.join(config.symbols)}
**Threshold:** {config.threshold_percentage}%
**Update Interval:** {config.update_interval}s
**Status:** {'🟢 Active' if config.is_active else '🔴 Inactive'}

Use the buttons below to modify or start monitoring.
"""

    @staticmethod
    def arbitrage_opportunity_alert(opportunity: ArbitrageOpportunity) -> str:
        """Format arbitrage opportunity as alert message."""
        return opportunity.format_telegram_message()
    
    @staticmethod
    def arbitrage_opportunity_update(opportunity: ArbitrageOpportunity, change_type: str = "updated") -> str:
        """Format arbitrage opportunity update message."""
        base_message = opportunity.format_telegram_message()
        return f"🔄 **{change_type.upper()}**\n\n{base_message}"
    
    @staticmethod
    def arbitrage_monitoring_started(config: MonitoringConfig) -> str:
        return f"""
✅ **Arbitrage Monitoring Started!**

**Configuration:**
• Exchanges: {', '.join(config.exchanges).upper()}
• Symbols: {', '.join(config.symbols)}
• Threshold: {config.threshold_percentage}%
• Update Interval: {config.update_interval}s

I'll send you real-time alerts when arbitrage opportunities are detected!

Use the buttons below to manage your monitoring session.
"""

    @staticmethod
    def arbitrage_monitoring_stopped() -> str:
        return """
⏹️ **Arbitrage Monitoring Stopped**

All monitoring sessions have been stopped. You can restart monitoring anytime using the main menu.

Use the buttons below to configure and start a new session.
"""

    # Market view messages
    @staticmethod
    def market_view_start(symbol: str, exchanges: List[str]) -> str:
        return f"""
📈 **Market View Setup - {symbol}**

**Selected Exchanges:** {', '.join(exchanges).upper()}

I'll provide real-time consolidated market data showing:
• Best bid/offer across all exchanges
• Venue comparison and analysis
• Live price updates and spreads

Use the buttons below to configure and start monitoring.
"""

    @staticmethod
    def market_view_update(cbbo: ConsolidatedBBO, is_update: bool = True) -> str:
        """Format market view update message."""
        return cbbo.format_telegram_message("update" if is_update else "initial")
    
    @staticmethod
    def market_view_started(symbol: str, exchanges: List[str], interval: int) -> str:
        return f"""
✅ **Market View Started!**

**Symbol:** {symbol}
**Exchanges:** {', '.join(exchanges).upper()}
**Update Interval:** {interval}s

I'll send you real-time consolidated market data updates!

Use the buttons below to manage your market view session.
"""

    @staticmethod
    def market_view_stopped() -> str:
        return """
⏹️ **Market View Stopped**

Market view monitoring has been stopped. You can start a new session anytime using the main menu.

Use the buttons below to configure and start a new session.
"""

    # CBBO messages
    @staticmethod
    def cbbo_result(cbbo: ConsolidatedBBO) -> str:
        """Format CBBO query result."""
        return cbbo.format_telegram_message("query")
    
    @staticmethod
    def cbbo_error(symbol: str, error: str) -> str:
        return f"""
❌ **CBBO Query Failed**

**Symbol:** {symbol}
**Error:** {error}

Please check the symbol format and try again, or use `/list_symbols` to see available symbols.
"""

    # Symbol listing messages
    @staticmethod
    def symbol_list_header(exchange: str, market_type: str = "spot") -> str:
        return f"""
📋 **Available Symbols**

**Exchange:** {exchange.upper()}
**Market Type:** {market_type.upper()}

Select symbols to monitor or use the search function.
"""

    @staticmethod
    def symbol_list_page(symbols: List[str], page: int, total_pages: int) -> str:
        start_idx = page * 10 + 1
        end_idx = min((page + 1) * 10, len(symbols))
        
        symbol_list = "\n".join([f"• {symbol}" for symbol in symbols[start_idx-1:end_idx]])
        
        return f"""
**Symbols {start_idx}-{end_idx} of {len(symbols)}**

{symbol_list}

**Page {page + 1} of {total_pages}**

Use the buttons below to navigate or select symbols.
"""

    @staticmethod
    def symbol_search_prompt() -> str:
        return """
🔍 **Symbol Search**

Enter the symbol you want to search for (e.g., BTC/USDT, ETH/USDT).

You can also select from common symbols below or type a custom symbol.
"""

    # Status messages
    @staticmethod
    def status_overview(
        active_monitoring: int,
        active_market_views: int,
        total_opportunities: int,
        last_opportunity_time: Optional[datetime] = None
    ) -> str:
        last_opp_text = ""
        if last_opportunity_time:
            last_opp_text = f"\n**Last Opportunity:** {last_opportunity_time.strftime('%H:%M:%S UTC')}"
        
        return f"""
📊 **Bot Status Overview**

**Active Sessions:**
• Arbitrage Monitoring: {active_monitoring}
• Market Views: {active_market_views}

**Statistics:**
• Total Opportunities Detected: {total_opportunities}{last_opp_text}

**System Status:** 🟢 Online
**Last Update:** {datetime.utcnow().strftime('%H:%M:%S UTC')}

Use the buttons below to manage your sessions or view detailed statistics.
"""

    @staticmethod
    def monitoring_session_status(config: MonitoringConfig) -> str:
        status_emoji = "🟢" if config.is_active else "🔴"
        last_update = config.last_update.strftime('%H:%M:%S UTC') if config.last_update else "Never"
        
        return f"""
📊 **Monitoring Session Status**

**Exchanges:** {', '.join(config.exchanges).upper()}
**Symbols:** {', '.join(config.symbols)}
**Threshold:** {config.threshold_percentage}%
**Status:** {status_emoji} {'Active' if config.is_active else 'Inactive'}
**Last Update:** {last_update}
**Created:** {config.created_at.strftime('%Y-%m-%d %H:%M UTC')}

Use the buttons below to manage this session.
"""

    # Error messages
    @staticmethod
    def error_generic(error: str) -> str:
        return f"""
❌ **Error**

{error}

Please try again or contact support if the problem persists.
"""

    @staticmethod
    def error_invalid_symbol(symbol: str) -> str:
        return f"""
❌ **Invalid Symbol**

The symbol "{symbol}" is not valid or not supported.

Please check the symbol format and try again. Use `/list_symbols` to see available symbols.
"""

    @staticmethod
    def error_exchange_not_supported(exchange: str) -> str:
        return f"""
❌ **Unsupported Exchange**

The exchange "{exchange}" is not supported.

Supported exchanges: OKX, Deribit, Bybit, Binance
"""

    @staticmethod
    def error_api_unavailable() -> str:
        return """
❌ **API Unavailable**

The market data API is currently unavailable. Please try again later.

I'll continue monitoring and will resume when the API is back online.
"""

    @staticmethod
    def error_no_data_available(symbol: str, exchange: str) -> str:
        return f"""
❌ **No Data Available**

No market data is currently available for {symbol} on {exchange.upper()}.

This could be due to:
• Market hours restrictions
• Symbol not actively traded
• Temporary API issues

Please try a different symbol or exchange.
"""

    # Configuration messages
    @staticmethod
    def configuration_saved(config_type: str) -> str:
        return f"""
✅ **Configuration Saved**

Your {config_type} settings have been saved successfully.

You can modify these settings anytime using the settings menu.
"""

    @staticmethod
    def threshold_set(threshold: float) -> str:
        return f"""
✅ **Threshold Set**

Minimum spread threshold set to {threshold}%

I'll only alert you when arbitrage opportunities exceed this threshold.
"""

    @staticmethod
    def update_interval_set(interval: int) -> str:
        return f"""
✅ **Update Interval Set**

Market data update interval set to {interval} seconds.

This affects how frequently you receive updates for market views.
"""

    # Notification messages
    @staticmethod
    def daily_summary(
        opportunities_detected: int,
        best_spread: float,
        most_active_exchange: str,
        most_traded_symbol: str
    ) -> str:
        return f"""
📊 **Daily Trading Summary**

**Today's Activity:**
• Opportunities Detected: {opportunities_detected}
• Best Spread: {best_spread:.2f}%
• Most Active Exchange: {most_active_exchange.upper()}
• Most Traded Symbol: {most_traded_symbol}

Keep monitoring for more opportunities! 🚀
"""

    @staticmethod
    def system_maintenance_notice() -> str:
        return """
🔧 **System Maintenance Notice**

The trading bot will be undergoing maintenance in the next few minutes.

During this time:
• Monitoring sessions will be paused
• New sessions cannot be started
• You'll receive updates when service resumes

Expected downtime: 5-10 minutes
"""

    # Quick action messages
    @staticmethod
    def quick_arbitrage_check(symbols: List[str], exchanges: List[str]) -> str:
        return f"""
🚨 **Quick Arbitrage Check**

Scanning {', '.join(symbols)} across {', '.join(exchanges).upper()}...

This may take a few seconds to gather data from all exchanges.
"""

    @staticmethod
    def quick_arbitrage_results(opportunities: List[ArbitrageOpportunity]) -> str:
        if not opportunities:
            return """
✅ **Quick Arbitrage Check Complete**

No arbitrage opportunities found at the moment.

The market appears to be efficient across the monitored exchanges.
"""
        
        results = "🚨 **Quick Arbitrage Check Results**\n\n"
        for i, opp in enumerate(opportunities[:5], 1):  # Show top 5
            results += f"**{i}.** {opp.symbol}\n"
            results += f"   Buy: {opp.buy_exchange.upper()} @ ${opp.buy_price:.4f}\n"
            results += f"   Sell: {opp.sell_exchange.upper()} @ ${opp.sell_price:.4f}\n"
            results += f"   Spread: {opp.spread_percentage:.2f}%\n\n"
        
        if len(opportunities) > 5:
            results += f"... and {len(opportunities) - 5} more opportunities\n"
        
        return results

    # Confirmation messages
    @staticmethod
    def confirm_monitoring_start(config: MonitoringConfig) -> str:
        return f"""
🤔 **Confirm Monitoring Start**

**Configuration Summary:**
• Exchanges: {', '.join(config.exchanges).upper()}
• Symbols: {', '.join(config.symbols)}
• Threshold: {config.threshold_percentage}%
• Update Interval: {config.update_interval}s

Are you sure you want to start monitoring with these settings?
"""

    @staticmethod
    def confirm_monitoring_stop() -> str:
        return """
🤔 **Confirm Monitoring Stop**

Are you sure you want to stop all arbitrage monitoring sessions?

This action cannot be undone. You'll need to reconfigure and restart monitoring.
"""

    @staticmethod
    def confirm_market_view_start(symbol: str, exchanges: List[str], interval: int) -> str:
        return f"""
🤔 **Confirm Market View Start**

**Configuration Summary:**
• Symbol: {symbol}
• Exchanges: {', '.join(exchanges).upper()}
• Update Interval: {interval}s

Are you sure you want to start market view monitoring with these settings?
"""

    # Information messages
    @staticmethod
    def exchange_info(exchange: str) -> str:
        exchange_info_map = {
            "okx": "OKX - Leading cryptocurrency exchange with advanced trading features",
            "deribit": "Deribit - Professional crypto derivatives exchange",
            "bybit": "Bybit - Global cryptocurrency derivatives exchange",
            "binance": "Binance - World's largest cryptocurrency exchange by volume"
        }
        
        info = exchange_info_map.get(exchange.lower(), "Unknown exchange")
        return f"""
ℹ️ **Exchange Information**

**{exchange.upper()}**
{info}

This exchange is supported for arbitrage monitoring and market data.
"""

    @staticmethod
    def feature_coming_soon(feature: str) -> str:
        return f"""
🚧 **Feature Coming Soon**

{feature} is currently under development and will be available in a future update.

Stay tuned for new features and improvements!
"""
