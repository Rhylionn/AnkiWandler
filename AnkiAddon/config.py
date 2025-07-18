# config.py - Rewritten Configuration Management
from aqt import mw

class ConfigManager:
    """Simple configuration manager using Anki's built-in system"""
    
    DEFAULT_CONFIG = {
        "server_url": "http://localhost:8000",
        "api_key": "",
        "deck_name": "Default",
        "auto_upload_on_startup": True,
        "auto_import_on_startup": True,
        "collect_cards": True,
        "collect_reviews": False,
        "collect_decks": False,
        "collect_patterns": False,
    }
    
    def __init__(self):
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        """Ensure configuration exists with defaults"""
        current = mw.addonManager.getConfig(__name__)
        if not current:
            mw.addonManager.writeConfig(__name__, self.DEFAULT_CONFIG.copy())
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        config = mw.addonManager.getConfig(__name__) or {}
        if key in config:
            return config[key]
        return self.DEFAULT_CONFIG.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
        config = mw.addonManager.getConfig(__name__) or {}
        config[key] = value
        mw.addonManager.writeConfig(__name__, config)
    
    def get_all(self):
        """Get all configuration values"""
        config = mw.addonManager.getConfig(__name__) or {}
        result = self.DEFAULT_CONFIG.copy()
        result.update(config)
        return result
    
    def update(self, updates: dict):
        """Update multiple configuration values"""
        config = mw.addonManager.getConfig(__name__) or {}
        config.update(updates)
        mw.addonManager.writeConfig(__name__, config)
    
    def save(self):
        """Save is handled automatically by set/update methods"""
        pass
    
    def is_server_configured(self):
        """Check if server is properly configured"""
        return bool(self.get('server_url') and self.get('api_key'))
    
    def reload(self):
        """Reload configuration (no-op since we read fresh each time)"""
        pass