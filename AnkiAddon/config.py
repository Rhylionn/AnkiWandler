# config.py - Configuration Management
from typing import Dict, Any
from aqt import mw

class ConfigManager:
    """Simple configuration manager for settings storage and validation"""
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "server_url": "http://localhost:8000",
        "api_key": "",
        "deck_name": "Default",
        "auto_upload_on_startup": True,
        "auto_import_on_startup": True,
        
        # Data collection settings
        "collect_cards": True,
        "collect_reviews": False,
        "collect_decks": False,
        "collect_patterns": False,
        
        # Future extension point
        "data_sync_frequency": "startup"
    }
    
    def __init__(self):
        self._config = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from Anki addon manager"""
        addon_config = mw.addonManager.getConfig(__name__) or {}
        
        # Merge with defaults to ensure all keys exist
        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(addon_config)
    
    def get(self, key: str, default=None) -> Any:
        """Get configuration value"""
        if self._config is None:
            self._load_config()
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        if self._config is None:
            self._load_config()
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        if self._config is None:
            self._load_config()
        return self._config.copy()
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values"""
        if self._config is None:
            self._load_config()
        self._config.update(updates)
    
    def save(self) -> None:
        """Save configuration to Anki addon manager"""
        if self._config is not None:
            mw.addonManager.writeConfig(__name__, self._config)
    
    def is_server_configured(self) -> bool:
        """Check if server is properly configured"""
        return bool(self.get('server_url') and self.get('api_key'))
    
    def get_enabled_collectors(self) -> list:
        """Get list of enabled data collectors"""
        enabled = []
        for key, value in self._config.items():
            if key.startswith('collect_') and value:
                collector_name = key.replace('collect_', '')
                enabled.append(collector_name)
        return enabled
    
    def reload(self) -> None:
        """Reload configuration from storage"""
        self._load_config()