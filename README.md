# GoQuant Trading Information System

A comprehensive cryptocurrency trading information system with Telegram bot integration for monitoring arbitrage opportunities and providing consolidated market views across multiple exchanges.

## 🚀 Features

- **Multi-Exchange Support**: Monitor arbitrage opportunities across OKX, Deribit, Bybit, and Binance
- **Real-time Data**: WebSocket connections for live market data streaming
- **Arbitrage Detection**: Automated detection of price differences between exchanges
- **Consolidated Market View**: Best bid/offer (CBBO) calculations across venues
- **Telegram Integration**: Interactive bot with real-time alerts and controls
- **Historical Tracking**: Store and analyze arbitrage opportunities over time

## 📋 Prerequisites

- Python 3.9+
- Telegram Bot Token
- GoMarket API access (access code: 2194)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd GoQuant
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp env.example .env
# Edit .env with your actual values
```

## ⚙️ Configuration

Copy `env.example` to `.env` and configure the following variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `GOMARKET_API_KEY`: Your GoMarket API key (if required)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `SUPPORTED_EXCHANGES`: Comma-separated list of exchanges

## 🏃‍♂️ Running the Bot

```bash
python main.py
```

## 📱 Bot Commands

- `/start` - Initialize and welcome message
- `/help` - Display all available commands
- `/list_symbols <exchange>` - Show available trading symbols
- `/monitor_arb` - Start arbitrage monitoring
- `/stop_arb` - Stop arbitrage monitoring
- `/view_market <symbol>` - Start consolidated market view
- `/get_cbbo <symbol>` - Get current consolidated BBO
- `/status` - Show active monitoring sessions

## 🏗️ Architecture

```
src/
├── bot/           # Telegram bot handlers and keyboards
├── data/          # API clients and data sources
├── services/      # Business logic services
├── models/        # Data models and structures
└── utils/         # Configuration and utilities
```

## 📊 Data Models

- `MarketData`: Real-time market data from exchanges
- `ArbitrageOpportunity`: Detected arbitrage opportunities
- `ConsolidatedBBO`: Best bid/offer across all exchanges
- `OrderBook`: Complete order book data
- `MonitoringConfig`: User monitoring configurations

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
```

## 📝 License

This project is developed for GoQuant trading assignment.

## 🤝 Contributing

This is a private assignment project. Please contact the development team for any questions.
