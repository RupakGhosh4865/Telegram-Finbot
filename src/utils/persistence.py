"""
Persistence utilities for user configurations and session data.

This module provides functionality to save and load user configurations,
session data, and preferences to/from persistent storage.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from src.models.data_models import MonitoringConfig
from src.utils.logger import LoggerMixin
from src.utils.config import config


class PersistenceManager(LoggerMixin):
    """
    Manager for persisting user configurations and session data.
    
    Provides functionality to save and load user preferences,
    monitoring configurations, and session state.
    """
    
    def __init__(self, data_dir: str = "user_configs"):
        """
        Initialize persistence manager.
        
        Args:
            data_dir: Directory to store user configuration files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.logger.info(
            "Persistence manager initialized",
            data_dir=str(self.data_dir)
        )
    
    def save_user_config(self, chat_id: int, config_data: Dict[str, Any]) -> bool:
        """
        Save user configuration to file.
        
        Args:
            chat_id: Chat ID of the user
            config_data: Configuration data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_file = self.data_dir / f"user_{chat_id}.json"
            
            # Add metadata
            config_with_metadata = {
                "chat_id": chat_id,
                "config": config_data,
                "last_updated": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_with_metadata, f, indent=2)
            
            self.logger.info(
                "User configuration saved",
                chat_id=chat_id,
                config_file=str(config_file)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to save user configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def load_user_config(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Load user configuration from file.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Configuration data if found, None otherwise
        """
        try:
            config_file = self.data_dir / f"user_{chat_id}.json"
            
            if not config_file.exists():
                self.logger.debug(
                    "User configuration file not found",
                    chat_id=chat_id
                )
                return None
            
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            self.logger.info(
                "User configuration loaded",
                chat_id=chat_id,
                config_file=str(config_file)
            )
            
            return data.get("config", {})
            
        except Exception as e:
            self.logger.error(
                "Failed to load user configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return None
    
    def save_monitoring_config(self, chat_id: int, monitoring_config: MonitoringConfig) -> bool:
        """
        Save monitoring configuration for a user.
        
        Args:
            chat_id: Chat ID of the user
            monitoring_config: Monitoring configuration to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_data = {
                "monitoring_config": monitoring_config.to_dict(),
                "is_active": monitoring_config.is_active
            }
            
            return self.save_user_config(chat_id, config_data)
            
        except Exception as e:
            self.logger.error(
                "Failed to save monitoring configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def load_monitoring_config(self, chat_id: int) -> Optional[MonitoringConfig]:
        """
        Load monitoring configuration for a user.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Monitoring configuration if found, None otherwise
        """
        try:
            user_config = self.load_user_config(chat_id)
            
            if not user_config or "monitoring_config" not in user_config:
                return None
            
            config_dict = user_config["monitoring_config"]
            return MonitoringConfig.from_dict(config_dict)
            
        except Exception as e:
            self.logger.error(
                "Failed to load monitoring configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return None
    
    def save_user_preferences(self, chat_id: int, preferences: Dict[str, Any]) -> bool:
        """
        Save user preferences.
        
        Args:
            chat_id: Chat ID of the user
            preferences: User preferences to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing config
            user_config = self.load_user_config(chat_id) or {}
            
            # Update preferences
            user_config["preferences"] = preferences
            
            return self.save_user_config(chat_id, user_config)
            
        except Exception as e:
            self.logger.error(
                "Failed to save user preferences",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def load_user_preferences(self, chat_id: int) -> Dict[str, Any]:
        """
        Load user preferences.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            User preferences dictionary
        """
        try:
            user_config = self.load_user_config(chat_id)
            
            if not user_config:
                return self._get_default_preferences()
            
            return user_config.get("preferences", self._get_default_preferences())
            
        except Exception as e:
            self.logger.error(
                "Failed to load user preferences",
                chat_id=chat_id,
                error=str(e)
            )
            return self._get_default_preferences()
    
    def save_session_data(self, chat_id: int, session_data: Dict[str, Any]) -> bool:
        """
        Save user session data.
        
        Args:
            chat_id: Chat ID of the user
            session_data: Session data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Load existing config
            user_config = self.load_user_config(chat_id) or {}
            
            # Update session data
            user_config["session_data"] = session_data
            
            return self.save_user_config(chat_id, user_config)
            
        except Exception as e:
            self.logger.error(
                "Failed to save session data",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def load_session_data(self, chat_id: int) -> Dict[str, Any]:
        """
        Load user session data.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Session data dictionary
        """
        try:
            user_config = self.load_user_config(chat_id)
            
            if not user_config:
                return {}
            
            return user_config.get("session_data", {})
            
        except Exception as e:
            self.logger.error(
                "Failed to load session data",
                chat_id=chat_id,
                error=str(e)
            )
            return {}
    
    def delete_user_config(self, chat_id: int) -> bool:
        """
        Delete user configuration file.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            config_file = self.data_dir / f"user_{chat_id}.json"
            
            if config_file.exists():
                config_file.unlink()
                
                self.logger.info(
                    "User configuration deleted",
                    chat_id=chat_id
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete user configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return False
    
    def list_user_configs(self) -> list:
        """
        List all user configuration files.
        
        Returns:
            List of chat IDs with configurations
        """
        try:
            config_files = list(self.data_dir.glob("user_*.json"))
            
            chat_ids = []
            for config_file in config_files:
                try:
                    # Extract chat ID from filename
                    filename = config_file.stem
                    chat_id = int(filename.replace("user_", ""))
                    chat_ids.append(chat_id)
                except ValueError:
                    continue
            
            self.logger.info(
                "User configurations listed",
                count=len(chat_ids)
            )
            
            return chat_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to list user configurations",
                error=str(e)
            )
            return []
    
    def get_config_stats(self) -> Dict[str, Any]:
        """
        Get configuration statistics.
        
        Returns:
            Dictionary with configuration statistics
        """
        try:
            config_files = list(self.data_dir.glob("user_*.json"))
            
            total_size = sum(f.stat().st_size for f in config_files)
            
            # Analyze file ages
            now = datetime.utcnow()
            recent_files = 0
            old_files = 0
            
            for config_file in config_files:
                file_age = now - datetime.fromtimestamp(config_file.stat().st_mtime)
                if file_age.days < 7:
                    recent_files += 1
                elif file_age.days > 30:
                    old_files += 1
            
            return {
                "total_configs": len(config_files),
                "total_size_bytes": total_size,
                "recent_configs": recent_files,
                "old_configs": old_files,
                "data_directory": str(self.data_dir)
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get configuration statistics",
                error=str(e)
            )
            return {}
    
    def cleanup_old_configs(self, days: int = 90) -> int:
        """
        Clean up old configuration files.
        
        Args:
            days: Number of days after which to delete configs
            
        Returns:
            Number of files deleted
        """
        try:
            cutoff_time = datetime.utcnow().timestamp() - (days * 24 * 3600)
            
            deleted_count = 0
            config_files = list(self.data_dir.glob("user_*.json"))
            
            for config_file in config_files:
                if config_file.stat().st_mtime < cutoff_time:
                    try:
                        config_file.unlink()
                        deleted_count += 1
                        
                        # Extract chat ID for logging
                        filename = config_file.stem
                        chat_id = int(filename.replace("user_", ""))
                        
                        self.logger.info(
                            "Old user configuration deleted",
                            chat_id=chat_id,
                            age_days=days
                        )
                        
                    except Exception as e:
                        self.logger.error(
                            "Failed to delete old config file",
                            file=str(config_file),
                            error=str(e)
                        )
            
            self.logger.info(
                "Configuration cleanup completed",
                deleted_count=deleted_count,
                cutoff_days=days
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(
                "Failed to cleanup old configurations",
                error=str(e)
            )
            return 0
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        Get default user preferences.
        
        Returns:
            Dictionary with default preferences
        """
        return {
            "default_exchanges": config.supported_exchanges,
            "default_threshold": config.default_threshold_percentage,
            "default_update_interval": config.default_update_interval,
            "notifications_enabled": True,
            "notification_frequency": "immediate",
            "preferred_market_type": "spot",
            "language": "en",
            "timezone": "UTC"
        }
    
    def export_user_config(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Export user configuration for backup.
        
        Args:
            chat_id: Chat ID of the user
            
        Returns:
            Complete configuration data if found, None otherwise
        """
        try:
            config_file = self.data_dir / f"user_{chat_id}.json"
            
            if not config_file.exists():
                return None
            
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            self.logger.error(
                "Failed to export user configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return None
    
    def import_user_config(self, chat_id: int, config_data: Dict[str, Any]) -> bool:
        """
        Import user configuration from backup.
        
        Args:
            chat_id: Chat ID of the user
            config_data: Configuration data to import
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            config_file = self.data_dir / f"user_{chat_id}.json"
            
            # Add metadata
            config_with_metadata = {
                "chat_id": chat_id,
                "config": config_data.get("config", config_data),
                "last_updated": datetime.utcnow().isoformat(),
                "version": "1.0",
                "imported": True
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_with_metadata, f, indent=2)
            
            self.logger.info(
                "User configuration imported",
                chat_id=chat_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to import user configuration",
                chat_id=chat_id,
                error=str(e)
            )
            return False
