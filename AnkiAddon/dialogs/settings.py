# dialogs/settings.py - Rewritten Settings Dialog
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout,
    QMessageBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from aqt import mw

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config_manager, api_client):
        super().__init__(mw)
        self.config = config_manager
        self.api = api_client
        
        self.setWindowTitle("Word Management Settings")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_current_settings()
    
    def closeEvent(self, event):
        """Ensure proper cleanup on close"""
        super().closeEvent(event)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self.create_server_tab(), "Server")
        tabs.addTab(self.create_sync_tab(), "Sync")
        layout.addWidget(tabs)
        
        button_layout = QHBoxLayout()
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setDefault(True)
        
        button_layout.addWidget(test_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def create_server_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
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
    
    def create_sync_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        anki_group = QGroupBox("Anki Configuration")
        anki_layout = QFormLayout(anki_group)
        
        self.deck_combo = QComboBox()
        self.deck_combo.setEditable(True)
        if mw.col:
            deck_names = [deck['name'] for deck in mw.col.decks.all()]
            self.deck_combo.addItems(deck_names)
        anki_layout.addRow("Target Deck:", self.deck_combo)
        
        layout.addWidget(anki_group)
        
        auto_group = QGroupBox("Automatic Operations")
        auto_layout = QVBoxLayout(auto_group)
        
        self.auto_upload_check = QCheckBox("Auto-upload cards on startup")
        auto_layout.addWidget(self.auto_upload_check)
        
        self.auto_import_check = QCheckBox("Auto-import words on startup")
        auto_layout.addWidget(self.auto_import_check)
        
        layout.addWidget(auto_group)
        layout.addStretch()
        
        return widget
    
    def load_current_settings(self):
        """Load current settings from config"""
        self.server_url_edit.setText(self.config.get('server_url', ''))
        self.api_key_edit.setText(self.config.get('api_key', ''))
        self.deck_combo.setCurrentText(self.config.get('deck_name', 'Default'))
        self.auto_upload_check.setChecked(self.config.get('auto_upload_on_startup', True))
        self.auto_import_check.setChecked(self.config.get('auto_import_on_startup', True))
    
    def save_and_close(self):
        """Save all settings and close dialog"""
        server_url = self.server_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        
        if not server_url:
            QMessageBox.warning(self, "Error", "Server URL is required")
            return
        
        if not api_key:
            QMessageBox.warning(self, "Error", "API Key is required")
            return
        
        # Save each setting individually
        self.config.set('server_url', server_url)
        self.config.set('api_key', api_key)
        self.config.set('deck_name', self.deck_combo.currentText().strip())
        self.config.set('auto_upload_on_startup', self.auto_upload_check.isChecked())
        self.config.set('auto_import_on_startup', self.auto_import_check.isChecked())
        
        QMessageBox.information(self, "Success", "Settings saved successfully")
        self.accept()
    
    def test_connection(self):
        """Test connection with current form values"""
        server_url = self.server_url_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        
        if not server_url or not api_key:
            QMessageBox.warning(self, "Error", "Please enter both server URL and API key")
            return
        
        # Save current values temporarily
        original_url = self.config.get('server_url')
        original_key = self.config.get('api_key')
        
        # Set test values
        self.config.set('server_url', server_url)
        self.config.set('api_key', api_key)
        
        try:
            success, message = self.api.test_connection()
            
            if success:
                QMessageBox.information(self, "Test Result", "✅ Connection successful!")
            else:
                QMessageBox.warning(self, "Test Result", f"❌ Connection failed:\n{message}")
        
        except Exception as e:
            QMessageBox.critical(self, "Test Result", f"❌ Test error:\n{str(e)}")
        
        finally:
            # Restore original values
            self.config.set('server_url', original_url)
            self.config.set('api_key', original_key)