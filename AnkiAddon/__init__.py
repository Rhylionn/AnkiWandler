# __init__.py - Word Management Extension for Anki
"""
Simple, extensible Word Management extension for Anki
Handles card upload, word import, and flexible data collection
"""

from aqt import mw, gui_hooks
from aqt.utils import showInfo

# Import all components
from .config import ConfigManager
from .api_client import APIClient
from .card_processor import CardProcessor
from .data_collector import DataCollector, CardDataCollector
from .notifications import NotificationManager
from .dialogs.settings import SettingsDialog
from .dialogs.import_dialog import ImportDialog

class AnkiExtension:
    """Main extension controller - simple and linear"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.api = APIClient(self.config)
        self.card_processor = CardProcessor()
        self.data_collector = DataCollector()
        self.notifications = NotificationManager()
        
        self.startup_completed = False
        self._setup_data_collectors()
        self._setup_menus()
        self._setup_hooks()
    
    def _setup_data_collectors(self):
        """Register all available data collectors"""
        # Register card collector (core functionality)
        card_collector = CardDataCollector(self.card_processor)
        self.data_collector.register_collector(card_collector)
        
        # Future collectors can be registered here
        # self.data_collector.register_collector(ReviewDataCollector())
        # self.data_collector.register_collector(DeckDataCollector())
    
    def _setup_menus(self):
        """Setup menu items"""
        # Add menu items to Tools menu
        mw.form.menuTools.addSeparator()
        
        settings_action = mw.form.menuTools.addAction("Word Management Settings")
        settings_action.triggered.connect(self.show_settings)
        
        upload_action = mw.form.menuTools.addAction("📤 Upload Cards")
        upload_action.triggered.connect(self.manual_upload)
        
        import_action = mw.form.menuTools.addAction("📥 Import Words")
        import_action.triggered.connect(self.manual_import)
    
    def _setup_hooks(self):
        """Setup Anki hooks"""
        # Hook into main window initialization
        gui_hooks.main_window_did_init.append(self.on_startup)
    
    def on_startup(self):
        """Handle extension startup - called when Anki main window is ready"""
        if self.startup_completed:
            return
        
        self.startup_completed = True
        
        # Show startup notification
        self.notifications.success("Word Management loaded", 1500)
        
        # Check if server is configured
        if not self.config.is_server_configured():
            self.notifications.info("Configure server settings in Tools > Word Management Settings")
            return
        
        # Perform startup operations after a short delay
        from aqt.qt import QTimer
        QTimer.singleShot(2000, self.perform_startup_operations)
    
    def perform_startup_operations(self):
        """Perform auto-operations on startup"""
        results = {
            'imported': 0,
            'uploaded': 0,
            'errors': 0
        }
        
        try:
            # Auto-import words if enabled
            if self.config.get('auto_import_on_startup', True):
                imported_count = self._auto_import_words()
                results['imported'] = imported_count
            
            # Auto-upload cards if enabled
            if self.config.get('auto_upload_on_startup', True):
                uploaded_count = self._auto_upload_cards()
                results['uploaded'] = uploaded_count
        
        except Exception as e:
            print(f"Startup operation error: {e}")
            results['errors'] = 1
        
        # Show completion notification
        self.notifications.startup_complete(results)
    
    def _auto_import_words(self) -> int:
        """Auto-import words on startup"""
        try:
            success, words = self.api.get_words()
            if success and words:
                # Show import dialog
                dialog = ImportDialog(words, self.config, self.card_processor, self.api)
                dialog.exec()
                return len(words)
            return 0
        except Exception as e:
            print(f"Auto-import error: {e}")
            return 0
    
    def _auto_upload_cards(self) -> int:
        """Auto-upload cards on startup"""
        try:
            # Get card collector and set deck name
            card_collector = self.data_collector.get_collector('cards')
            if card_collector:
                deck_name = self.config.get('deck_name', 'Default')
                card_collector.set_deck_name(deck_name)
                
                # Collect card data
                card_data = card_collector.collect()
                cards = card_data.get('cards', [])
                
                if cards:
                    # Clear server cards first
                    self.api.clear_cards()
                    
                    # Upload new cards
                    success, result = self.api.upload_cards(cards)
                    if success:
                        return len(cards)
            return 0
        except Exception as e:
            print(f"Auto-upload error: {e}")
            return 0
    
    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self.config, self.api)
            if dialog.exec():
                # Reload configuration after changes
                self.config.reload()
                self.notifications.success("Settings updated")
        except Exception as e:
            self.notifications.error(e, "Settings Error")
    
    def manual_upload(self):
        """Manual card upload"""
        try:
            if not self.config.is_server_configured():
                showInfo("Please configure server settings first")
                return
            
            # Get card data
            card_collector = self.data_collector.get_collector('cards')
            if not card_collector:
                showInfo("Card collector not available")
                return
            
            deck_name = self.config.get('deck_name', 'Default')
            card_collector.set_deck_name(deck_name)
            
            card_data = card_collector.collect()
            cards = card_data.get('cards', [])
            
            if not cards:
                showInfo("No cards found in the specified deck")
                return
            
            # Clear server and upload
            self.api.clear_cards()
            success, result = self.api.upload_cards(cards)
            
            if success:
                self.notifications.success(f"Uploaded {len(cards)} cards")
            else:
                self.notifications.error(f"Upload failed: {result}")
        
        except Exception as e:
            self.notifications.error(e, "Upload Error")
    
    def manual_import(self):
        """Manual word import"""
        try:
            if not self.config.is_server_configured():
                showInfo("Please configure server settings first")
                return
            
            # Get words from server
            success, words = self.api.get_words()
            
            if not success:
                showInfo("Failed to get words from server")
                return
            
            if not words:
                showInfo("No processed words available on server")
                return
            
            # Show import dialog
            dialog = ImportDialog(words, self.config, self.card_processor, self.api)
            dialog.exec()
        
        except Exception as e:
            self.notifications.error(e, "Import Error")

# Initialize the extension
extension = AnkiExtension()

# Export version for addon manager
__version__ = "2.0.0"