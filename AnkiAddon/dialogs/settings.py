# dialogs/settings.py - Settings Configuration Dialog
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from aqt import mw

class SettingsDialog(QDialog):
    """Simple settings configuration dialog"""
    
    def __init__(self, config_manager, api_client):
        super().__init__(mw)
        self.config = config_manager
        self.api = api_client
        
        self.setWindowTitle("Word Management Settings")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Server tab
        server_tab = self.create_server_tab()
        tabs.addTab(server_tab, "Server")
        
        # Sync tab
        sync_tab = self.create_sync_tab()
        tabs.addTab(sync_tab, "Sync")
        
        # Data Collection tab
        data_tab = self.create_data_collection_tab()
        tabs.addTab(data_tab, "Data Collection")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self.test_connection)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def create_server_tab(self) -> QWidget:
        """Create server configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Server group
        server_group = QGroupBox("Server Configuration")
        server_layout = QFormLayout(server_group)
        
        self.server_url_edit = QLineEdit()
        self.server_url_edit.setPlaceholderText("http://localhost:8000")
        server_layout.addRow("Server URL:", self.server_url_edit)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter your API key")
        server_layout.addRow("API Key:", self.api_key_edit)
        
        layout.addWidget(server_group)
        layout.addStretch()
        
        return widget
    
    def create_sync_tab(self) -> QWidget:
        """Create sync configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Anki group
        anki_group = QGroupBox("Anki Configuration")
        anki_layout = QFormLayout(anki_group)
        
        self.deck_combo = QComboBox()
        self.deck_combo.setEditable(True)
        # Populate with available decks
        if mw.col:
            deck_names = [deck['name'] for deck in mw.col.decks.all()]
            self.deck_combo.addItems(deck_names)
        anki_layout.addRow("Target Deck:", self.deck_combo)
        
        layout.addWidget(anki_group)
        
        # Auto-operations group
        auto_group = QGroupBox("Automatic Operations")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_upload_check = QCheckBox("Auto-upload cards on startup")
        self.auto_upload_check.setToolTip("Automatically upload existing cards to server when Anki starts")
        auto_layout.addWidget(self.auto_upload_check)
        
        self.auto_import_check = QCheckBox("Auto-import words on startup")
        self.auto_import_check.setToolTip("Automatically check for and import processed words when Anki starts")
        auto_layout.addWidget(self.auto_import_check)
        
        layout.addWidget(auto_group)
        layout.addStretch()
        
        return widget
    
    def create_data_collection_tab(self) -> QWidget:
        """Create data collection configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Data collection group
        data_group = QGroupBox("Data Collection Settings")
        data_layout = QVBoxLayout(data_group)
        
        # Cards collection (always enabled, this is core functionality)
        self.collect_cards_check = QCheckBox("Cards (Required)")
        self.collect_cards_check.setChecked(True)
        self.collect_cards_check.setEnabled(False)
        self.collect_cards_check.setToolTip("Card data collection is required for core functionality")
        data_layout.addWidget(self.collect_cards_check)
        
        # Future data collections
        self.collect_reviews_check = QCheckBox("Review Statistics (Future)")
        self.collect_reviews_check.setEnabled(False)
        self.collect_reviews_check.setToolTip("Review data collection - not yet implemented")
        data_layout.addWidget(self.collect_reviews_check)
        
        self.collect_decks_check = QCheckBox("Deck Metadata (Future)")
        self.collect_decks_check.setEnabled(False)
        self.collect_decks_check.setToolTip("Deck metadata collection - not yet implemented")
        data_layout.addWidget(self.collect_decks_check)
        
        self.collect_patterns_check = QCheckBox("Study Patterns (Future)")
        self.collect_patterns_check.setEnabled(False)
        self.collect_patterns_check.setToolTip("Study pattern analysis - not yet implemented")
        data_layout.addWidget(self.collect_patterns_check)
        
        layout.addWidget(data_group)
        
        # Info section
        info_label = QLabel(
            "Data collection settings control what information is sent to your server. "
            "Future options will be enabled as they become available."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 10px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        return widget
    
    def load_settings(self):
        """Load current settings into the form"""
        self.server_url_edit.setText(self.config.get('server_url', ''))
        self.api_key_edit.setText(self.config.get('api_key', ''))
        self.deck_combo.setCurrentText(self.config.get('deck_name', 'Default'))
        self.auto_upload_check.setChecked(self.config.get('auto_upload_on_startup', True))
        self.auto_import_check.setChecked(self.config.get('auto_import_on_startup', True))
        
        # Data collection settings (future use)
        self.collect_reviews_check.setChecked(self.config.get('collect_reviews', False))
        self.collect_decks_check.setChecked(self.config.get('collect_decks', False))
        self.collect_patterns_check.setChecked(self.config.get('collect_patterns', False))
    
    def save_settings(self):
        """Save settings and close dialog"""
        # Validate required fields
        if not self.server_url_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Server URL is required")
            return
        
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "API Key is required")
            return
        
        # Update configuration
        self.config.update({
            'server_url': self.server_url_edit.text().strip(),
            'api_key': self.api_key_edit.text().strip(),
            'deck_name': self.deck_combo.currentText().strip(),
            'auto_upload_on_startup': self.auto_upload_check.isChecked(),
            'auto_import_on_startup': self.auto_import_check.isChecked(),
            'collect_cards': True,  # Always enabled
            'collect_reviews': self.collect_reviews_check.isChecked(),
            'collect_decks': self.collect_decks_check.isChecked(),
            'collect_patterns': self.collect_patterns_check.isChecked()
        })
        
        # Save to storage
        self.config.save()
        
        QMessageBox.information(self, "Success", "Settings saved successfully")
        self.accept()
    
    def test_connection(self):
        """Test connection to server"""
        # Temporarily update API client with current form values
        original_url = self.config.get('server_url')
        original_key = self.config.get('api_key')
        
        self.config.set('server_url', self.server_url_edit.text().strip())
        self.config.set('api_key', self.api_key_edit.text().strip())
        
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Testing...")
        
        try:
            success, message = self.api.test_connection()
            
            if success:
                QMessageBox.information(self, "Connection Test", "✅ Connection successful!")
            else:
                QMessageBox.warning(self, "Connection Test", f"❌ Connection failed:\n{message}")
        
        except Exception as e:
            QMessageBox.critical(self, "Connection Test", f"❌ Test failed:\n{str(e)}")
        
        finally:
            # Restore original values
            self.config.set('server_url', original_url)
            self.config.set('api_key', original_key)
            
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Connection")