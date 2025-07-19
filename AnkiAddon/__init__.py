# __init__.py - Word Management Extension for Anki
"""
Simple, extensible Word Management extension for Anki
Handles card upload, word import, and flexible data collection
"""

import json
from aqt import mw, gui_hooks
from aqt.utils import showInfo
from aqt.qt import QTimer, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout

# Import all components
from .config import ConfigManager
from .api_client import APIClient
from .card_processor import CardProcessor
from .review_processor import ReviewProcessor
from .data_collector import DataCollector, CardDataCollector, ReviewDataCollector
from .notifications import NotificationManager
from .dialogs.settings import SettingsDialog
from .dialogs.import_dialog import ImportDialog

class JSONViewerDialog(QDialog):
    """Simple dialog to display JSON data"""
    
    def __init__(self, json_data, title="JSON Data"):
        super().__init__(mw)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Text area for JSON
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(json.dumps(json_data, indent=2, ensure_ascii=False))
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(mw.app.font())
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def copy_to_clipboard(self):
        """Copy JSON text to clipboard"""
        mw.app.clipboard().setText(self.text_edit.toPlainText())
        showInfo("JSON copied to clipboard!")

class AnkiExtension:
    """Main extension controller - simple and linear"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.api = APIClient(self.config)
        self.card_processor = CardProcessor()
        self.review_processor = ReviewProcessor()
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
        
        review_collector = ReviewDataCollector(self.review_processor, self.config)
        self.data_collector.register_collector(review_collector)
    
    def _setup_menus(self):
        """Setup menu items"""
        mw.form.menuTools.addSeparator()
        
        settings_action = mw.form.menuTools.addAction("Word Management Settings")
        settings_action.triggered.connect(self.show_settings)
        
        upload_action = mw.form.menuTools.addAction("📤 Upload Cards")
        upload_action.triggered.connect(self.manual_upload)
        
        import_action = mw.form.menuTools.addAction("📥 Import Words")
        import_action.triggered.connect(self.manual_import)
        
        analytics_action = mw.form.menuTools.addAction("📊 View Analytics")
        analytics_action.triggered.connect(self.view_analytics)
        
        send_analytics_action = mw.form.menuTools.addAction("📊 Send Analytics")
        send_analytics_action.triggered.connect(self.send_analytics)
        
        # Debug menu for viewing raw JSON
        debug_action = mw.form.menuTools.addAction("🔍 Debug Analytics JSON")
        debug_action.triggered.connect(self.debug_analytics_json)
    
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
    
    def view_analytics(self):
        """View analytics data (simple display for now)"""
        try:
            # Collect review data
            review_collector = self.data_collector.get_collector('reviews')
            if not review_collector:
                showInfo("Review collector not available")
                return
            
            review_data = review_collector.collect()
            
            # Check if data collection was successful
            if review_data.get('status') == 'error':
                showInfo(f"Error collecting analytics data: {review_data.get('error', 'Unknown error')}")
                return
            
            # Get latest session and other data
            latest_session = review_data.get('latest_session')
            current_state = review_data.get('current_state', {})
            metrics = review_data.get('overall_metrics', {})
            
            # Format data for display
            info_lines = [
                "📊 Analytics Summary",
                "",
                "🔥 Latest Session:"
            ]
            
            if latest_session:
                info_lines.extend([
                    f"  • Date: {latest_session.get('date', 'Unknown')}",
                    f"  • Duration: {latest_session.get('duration_minutes', 0):.1f} minutes",
                    f"  • Cards Reviewed: {latest_session.get('cards_reviewed', 0)}",
                    f"  • Success Rate: {latest_session.get('success_rate', 0):.1%}",
                    f"  • New Cards Learned: {latest_session.get('new_cards_learned', 0)}"
                ])
                
                # Show if session was merged
                if latest_session.get('merged_sessions_count', 0) > 1:
                    info_lines.append(f"  • Merged {latest_session.get('merged_sessions_count')} sessions")
            else:
                info_lines.append("  • No session data available")
            
            info_lines.extend([
                "",
                f"📈 Current State ({current_state.get('deck_name', 'Unknown Deck')}):",
                f"  • Cards Due Today: {current_state.get('cards_due_today', 0)}",
                f"  • New Cards Available: {current_state.get('new_cards_available', 0)}",
                f"  • Cards Overdue: {current_state.get('cards_overdue', 0)}",
                f"  • Total Cards: {current_state.get('total_cards', 0)}",
                "",
                "📋 Overall Metrics (Last 30 Days):",
                f"  • Engagement Score: {metrics.get('engagement_score', 0):.2f}",
                f"  • Motivation Trend: {metrics.get('motivation_trend', 0):.2f}",
                f"  • Burnout Risk: {metrics.get('burnout_risk_score', 0):.2f}",
                f"  • Procrastination: {metrics.get('procrastination_indicator', 0):.2f}",
                "",
                "💡 Use 'Send Analytics' to upload this data to server"
            ])
            
            showInfo("\n".join(info_lines))
        
        except Exception as e:
            self.notifications.error(e, "Analytics Error")
    
    def debug_analytics_json(self):
        """Show raw analytics JSON data for debugging"""
        try:
            # Collect review data
            review_collector = self.data_collector.get_collector('reviews')
            if not review_collector:
                showInfo("Review collector not available")
                return
            
            review_data = review_collector.collect()
            
            # Show JSON viewer dialog
            dialog = JSONViewerDialog(review_data, "Analytics JSON Data")
            dialog.exec()
        
        except Exception as e:
            showInfo(f"Error collecting analytics data: {str(e)}")
    
    def send_analytics(self):
        """Send analytics data to server"""
        try:
            if not self.config.is_server_configured():
                showInfo("Please configure server settings first")
                return
            
            # Collect review data
            review_collector = self.data_collector.get_collector('reviews')
            if not review_collector:
                showInfo("Review collector not available")
                return
            
            review_data = review_collector.collect()
            
            # Check if data collection was successful
            if review_data.get('status') == 'error':
                showInfo(f"Error collecting analytics data: {review_data.get('error', 'Unknown error')}")
                return
            
            if not review_data.get('latest_session') and not review_data.get('current_state'):
                showInfo("No analytics data to send")
                return
            
            # Send to server
            success, result = self.api.send_analytics_data(review_data)
            
            if success:
                self.notifications.success("Analytics data sent successfully")
            else:
                self.notifications.error(f"Failed to send analytics: {result}")
        
        except Exception as e:
            self.notifications.error(e, "Analytics Send Error")

# Initialize the extension
extension = AnkiExtension()

# Export version for addon manager
__version__ = "2.0.0"