"""
Configuration management for the trading bot system.

This module handles loading and validating environment variables and configuration settings.
"""

import os
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration class containing all application settings."""
    
    # Telegram Bot Configuration
    telegram_bot_token: str
    
    # GoMarket API Configuration
    gomarket_api_key: Optional[str] = None
    gomarket_base_url: str = "https://gomarket-api.goquant.io"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/trading_bot.log"
    
    # Supported Exchanges
    supported_exchanges: List[str] = None
    
    # Monitoring Configuration
    default_threshold_percentage: float = 0.5
    default_update_interval: int = 5
    max_monitoring_sessions: int = 10
    
    # Database Configuration
    database_url: str = "sqlite:///trading_bot.db"
    
    # Rate Limiting
    api_rate_limit: int = 100
    telegram_rate_limit: int = 30
    
    # WebSocket Configuration
    websocket_reconnect_delay: int = 5
    websocket_max_reconnect_attempts: int = 10
    
    # Development
    debug: bool = False
    test_mode: bool = False
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.supported_exchanges is None:
            self.supported_exchanges = ["okx", "deribit", "bybit", "binance"]
        
        # Validate required settings
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        # Convert string lists to actual lists
        if isinstance(self.supported_exchanges, str):
            self.supported_exchanges = [
                exchange.strip() 
                for exchange in self.supported_exchanges.split(",")
            ]
        
        # Ensure log directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)


def load_config() -> Config:
    """
    Load configuration from environment variables.
    
    Returns:
        Config: Configuration object with all settings
        
    Raises:
        ValueError: If required configuration is missing
    """
    try:
        config = Config(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            gomarket_api_key=os.getenv("GOMARKET_API_KEY"),
            gomarket_base_url=os.getenv("GOMARKET_BASE_URL", "https://gomarket-api.goquant.io"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/trading_bot.log"),
            supported_exchanges=os.getenv("SUPPORTED_EXCHANGES", "okx,deribit,bybit,binance"),
            default_threshold_percentage=float(os.getenv("DEFAULT_THRESHOLD_PERCENTAGE", "0.5")),
            default_update_interval=int(os.getenv("DEFAULT_UPDATE_INTERVAL", "5")),
            max_monitoring_sessions=int(os.getenv("MAX_MONITORING_SESSIONS", "10")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///trading_bot.db"),
            api_rate_limit=int(os.getenv("API_RATE_LIMIT", "100")),
            telegram_rate_limit=int(os.getenv("TELEGRAM_RATE_LIMIT", "30")),
            websocket_reconnect_delay=int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5")),
            websocket_max_reconnect_attempts=int(os.getenv("WEBSOCKET_MAX_RECONNECT_ATTEMPTS", "10")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            test_mode=os.getenv("TEST_MODE", "false").lower() == "true"
        )
        
        return config
        
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")


# Global configuration instance
config = load_config()
