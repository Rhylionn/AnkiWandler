# __init__.py - Word Management Extension for Anki
"""
Simple, extensible Word Management extension for Anki
Handles card upload, word import, and flexible data collection
"""

from aqt import mw, gui_hooks
from aqt.utils import showInfo
from aqt.qt import QTimer

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
        self.startup_timer = None
        
        self._setup_data_collectors()
        self._setup_menus()
        self._setup_hooks()

    def closeEvent(self, event):
        """Ensure proper cleanup on close"""
        super().closeEvent(event)
    
    def _setup_data_collectors(self):
        """Register all available data collectors"""
        card_collector = CardDataCollector(self.card_processor)
        self.data_collector.register_collector(card_collector)
    
    def _setup_menus(self):
        """Setup menu items"""
        mw.form.menuTools.addSeparator()
        
        settings_action = mw.form.menuTools.addAction("Word Management Settings")
        settings_action.triggered.connect(self.show_settings)
        
        upload_action = mw.form.menuTools.addAction("📤 Upload Cards")
        upload_action.triggered.connect(self.manual_upload)
        
        import_action = mw.form.menuTools.addAction("📥 Import Words")
        import_action.triggered.connect(self.manual_import)
    
    def _setup_hooks(self):
        """Setup Anki hooks"""
        gui_hooks.main_window_did_init.append(self.on_startup)
        
        # Timer cleanup to prevent macOS crash
        try:
            gui_hooks.profile_will_close.append(self._cleanup_timer)
        except AttributeError:
            gui_hooks.main_window_will_close.append(self._cleanup_timer)
    
    def _cleanup_timer(self):
        """Clean up timer to prevent crash on quit"""
        if self.startup_timer:
            self.startup_timer.stop()
            self.startup_timer = None
    
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
        self.startup_timer = QTimer()
        self.startup_timer.setSingleShot(True)
        self.startup_timer.timeout.connect(self.perform_startup_operations)
        self.startup_timer.start(2000)
    
    def perform_startup_operations(self):
        """Perform auto-operations on startup"""
        self.startup_timer = None
        
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
            card_collector = self.data_collector.get_collector('cards')
            if card_collector:
                deck_name = self.config.get('deck_name', 'Default')
                card_collector.set_deck_name(deck_name)
                
                card_data = card_collector.collect()
                cards = card_data.get('cards', [])
                
                if cards:
                    self.api.clear_cards()
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
            
            success, words = self.api.get_words()
            
            if not success:
                showInfo("Failed to get words from server")
                return
            
            if not words:
                showInfo("No processed words available on server")
                return
            
            dialog = ImportDialog(words, self.config, self.card_processor, self.api)
            dialog.exec()
        
        except Exception as e:
            self.notifications.error(e, "Import Error")

# Initialize the extension
extension = AnkiExtension()

# Export version for addon manager
__version__ = "2.0.0"