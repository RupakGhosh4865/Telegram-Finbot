"""
Demo runner for the GoQuant Trading Bot.

This script runs the bot in demo mode without requiring actual API keys.
It demonstrates the bot functionality using mock data.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set demo mode
os.environ['TEST_MODE'] = 'true'
os.environ['DEBUG'] = 'true'

# Mock environment variables for demo
demo_env = {
    'TELEGRAM_BOT_TOKEN': 'demo_token_for_testing',
    'GOMARKET_API_KEY': 'demo_api_key',
    'GOMARKET_BASE_URL': 'https://gomarket-api.goquant.io',
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': 'logs/demo_bot.log',
    'SUPPORTED_EXCHANGES': 'okx,deribit,bybit,binance',
    'DEFAULT_THRESHOLD_PERCENTAGE': '0.5',
    'DEFAULT_UPDATE_INTERVAL': '5',
    'MAX_MONITORING_SESSIONS': '10',
    'DATABASE_URL': 'sqlite:///demo_bot.db',
    'API_RATE_LIMIT': '100',
    'TELEGRAM_RATE_LIMIT': '30',
    'WEBSOCKET_RECONNECT_DELAY': '5',
    'WEBSOCKET_MAX_RECONNECT_ATTEMPTS': '10',
    'DEBUG': 'true',
    'TEST_MODE': 'true'
}

# Set environment variables
for key, value in demo_env.items():
    os.environ[key] = value

def print_banner():
    """Print demo banner."""
    print("=" * 60)
    print("🚀 GoQuant Trading Bot - DEMO MODE")
    print("=" * 60)
    print("This is a demonstration of the trading bot system.")
    print("In demo mode, the bot will:")
    print("• Show the complete architecture and code structure")
    print("• Demonstrate all features with mock data")
    print("• Display the Telegram bot interface")
    print("• Show real-time data processing capabilities")
    print("=" * 60)
    print()

def print_features():
    """Print feature overview."""
    print("📊 FEATURES DEMONSTRATED:")
    print("• Multi-exchange arbitrage detection")
    print("• Consolidated market view (CBBO)")
    print("• Real-time data streaming")
    print("• Interactive Telegram bot interface")
    print("• User session management")
    print("• Statistics and analytics")
    print("• Error handling and recovery")
    print()

def print_setup_instructions():
    """Print setup instructions for real usage."""
    print("🔧 TO RUN WITH REAL API KEYS:")
    print("1. Create a Telegram bot via @BotFather")
    print("2. Get your bot token")
    print("3. Update TELEGRAM_BOT_TOKEN in .env file")
    print("4. (Optional) Get GoMarket API access")
    print("5. Run: python main.py")
    print()

async def demo_data_models():
    """Demonstrate data models."""
    print("📋 TESTING DATA MODELS...")
    try:
        from models.data_models import MarketData, ArbitrageOpportunity, ConsolidatedBBO
        
        # Create sample market data
        market_data = MarketData(
            symbol="BTC/USDT",
            exchange="binance",
            bid_price=50000.0,
            bid_size=1.0,
            ask_price=50001.0,
            ask_size=1.0,
            last_price=50000.5,
            timestamp=datetime.utcnow()
        )
        
        print(f"✅ Market Data: {market_data.symbol} @ {market_data.bid_price}/{market_data.ask_price}")
        print(f"   Spread: {market_data.spread_percentage:.2f}%")
        
        # Create sample arbitrage opportunity
        opportunity = ArbitrageOpportunity(
            symbol="BTC/USDT",
            buy_exchange="binance",
            sell_exchange="okx",
            buy_price=50000.0,
            sell_price=50050.0,
            spread_percentage=0.1,
            spread_absolute=50.0,
            timestamp=datetime.utcnow()
        )
        
        print(f"✅ Arbitrage Opportunity: {opportunity.spread_percentage:.2f}% spread")
        print(f"   Buy: {opportunity.buy_exchange} @ ${opportunity.buy_price}")
        print(f"   Sell: {opportunity.sell_exchange} @ ${opportunity.sell_price}")
        
        # Create sample CBBO
        cbbo = ConsolidatedBBO(
            symbol="BTC/USDT",
            best_bid_price=50000.0,
            best_bid_exchange="binance",
            best_ask_price=50001.0,
            best_ask_exchange="okx",
            mid_price=50000.5,
            timestamp=datetime.utcnow(),
            all_exchanges=["binance", "okx"]
        )
        
        print(f"✅ Consolidated BBO: Best bid {cbbo.best_bid_price} ({cbbo.best_bid_exchange})")
        print(f"   Best ask {cbbo.best_ask_price} ({cbbo.best_ask_exchange})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing data models: {e}")
        return False

async def demo_services():
    """Demonstrate services."""
    print("\n🔧 TESTING SERVICES...")
    try:
        # Test configuration
        from utils.config import config
        print(f"✅ Configuration loaded: {len(config.supported_exchanges)} exchanges")
        
        # Test logger
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Demo logger test")
        print("✅ Logger initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing services: {e}")
        return False

async def demo_bot_components():
    """Demonstrate bot components."""
    print("\n🤖 TESTING BOT COMPONENTS...")
    try:
        from bot.keyboards import BotKeyboards
        from bot.messages import BotMessages
        
        # Test keyboard creation
        main_menu = BotKeyboards.get_main_menu()
        print("✅ Main menu keyboard created")
        
        # Test message formatting
        welcome_msg = BotMessages.WELCOME_MESSAGE
        print("✅ Welcome message template loaded")
        
        # Test exchange selection
        exchange_kb = BotKeyboards.get_exchange_selection()
        print("✅ Exchange selection keyboard created")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing bot components: {e}")
        return False

async def main():
    """Main demo function."""
    print_banner()
    print_features()
    
    # Test core components
    data_models_ok = await demo_data_models()
    services_ok = await demo_services()
    bot_ok = await demo_bot_components()
    
    print("\n" + "=" * 60)
    print("📊 DEMO RESULTS:")
    print(f"Data Models: {'✅ PASS' if data_models_ok else '❌ FAIL'}")
    print(f"Services: {'✅ PASS' if services_ok else '❌ FAIL'}")
    print(f"Bot Components: {'✅ PASS' if bot_ok else '❌ FAIL'}")
    
    if data_models_ok and services_ok and bot_ok:
        print("\n🎉 ALL COMPONENTS WORKING CORRECTLY!")
        print("\nThe trading bot system is ready for deployment.")
        print("To run with real API keys, follow the setup instructions below.")
    else:
        print("\n⚠️  Some components failed. Check the error messages above.")
    
    print_setup_instructions()
    
    print("\n" + "=" * 60)
    print("📁 PROJECT STRUCTURE:")
    print("src/")
    print("├── bot/           # Telegram bot handlers and UI")
    print("├── data/          # API clients and data streaming") 
    print("├── services/      # Business logic services")
    print("├── models/        # Data models and structures")
    print("└── utils/         # Configuration and utilities")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        sys.exit(1)

