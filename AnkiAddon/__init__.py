# Word Management Extension for Anki - Final Optimized Version
# Save this as: addons21/word_management/__init__.py

import json
import requests
import re
import html
from typing import List, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QGroupBox, QFormLayout, QProgressBar
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal

from aqt import mw, gui_hooks
from aqt.utils import showInfo, showCritical, tooltip


class Config:
    """Configuration management"""
    
    @staticmethod
    def load() -> Dict[str, Any]:
        return mw.addonManager.getConfig(__name__) or {
            "server_url": "http://localhost:8000",
            "api_key": "",
            "deck_name": "Default",
            "auto_upload_on_startup": True,
            "auto_pull_on_startup": True
        }
    
    @staticmethod
    def save(config: Dict[str, Any]) -> None:
        mw.addonManager.writeConfig(__name__, config)


class API:
    """Server communication"""
    
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    
    def _request(self, method: str, endpoint: str, data: Dict = None) -> Tuple[bool, Any]:
        try:
            response = requests.request(method, f"{self.url}{endpoint}", 
                                      headers=self.headers, json=data, timeout=30)
            return response.status_code == 200, (response.json() if response.status_code == 200 else response.text)
        except Exception as e:
            return False, str(e)
    
    def test_connection(self) -> Tuple[bool, str]:
        success, result = self._request("GET", "/")
        return success, "Connected" if success else "Connection failed"
    
    def clear_cards(self) -> bool:
        success, _ = self._request("DELETE", "/api/v1/anki/cards/clear_all")
        return success
    
    def send_cards(self, cards: List[Dict]) -> Tuple[bool, int]:
        success, _ = self._request("POST", "/api/v1/anki/cards", {"cards": cards})
        return success, len(cards) if success else 0
    
    def get_words(self) -> Tuple[bool, List[Dict]]:
        success, result = self._request("GET", "/api/v1/words/processed?limit=100")
        return success, (result if success else [])
    
    def clear_words(self) -> bool:
        success, _ = self._request("DELETE", "/api/v1/words/processed/clear_all")
        return success


class DataHandler:
    """Data processing"""
    
    @staticmethod
    def clean_html(text: str) -> str:
        """Remove HTML and decode entities"""
        return html.unescape(re.sub(r'<[^>]+>', '', text or "")).strip()
    
    @staticmethod
    def extract_cards(deck_name: str) -> List[Dict]:
        """Extract cards from deck"""
        if not mw.col:
            return []
        
        try:
            deck_id = mw.col.decks.id(deck_name)
            card_ids = mw.col.decks.cids(deck_id)
            unique_cards = {}
            
            for card_id in card_ids:
                try:
                    note = mw.col.getCard(card_id).note()
                    fields = dict(zip(note.keys(), note.values()))
                    
                    card_id_val = fields.get('ID', '').strip()
                    if not card_id_val or card_id_val in unique_cards:
                        continue
                    
                    unique_cards[card_id_val] = {
                        "card_id": card_id_val,
                        "tl_word": DataHandler.clean_html(fields.get('TL Word', '')),
                        "tl_sentence": DataHandler.clean_html(fields.get('TL Sentence', '')),
                        "nl_word": DataHandler.clean_html(fields.get('NL Word', '')),
                        "nl_sentence": DataHandler.clean_html(fields.get('NL Sentence', ''))
                    }
                except:
                    continue
            
            return list(unique_cards.values())
        except:
            return []
    
    @staticmethod
    def get_next_id() -> int:
        """Get next available ID"""
        if not mw.col:
            return 1
        
        try:
            # Try multiple search patterns
            note_ids = mw.col.find_notes('"ID:*"')
            if not note_ids:
                note_ids = mw.col.find_notes('ID:*')
            
            max_id = 0
            
            for note_id in note_ids:
                try:
                    note = mw.col.get_note(note_id)
                    # Try multiple ways to access ID field
                    id_val = ""
                    
                    # Method 1: Direct access
                    if hasattr(note, '__getitem__'):
                        try:
                            id_val = note['ID'] if 'ID' in note else ""
                        except:
                            pass
                    
                    # Method 2: Through fields dict
                    if not id_val:
                        try:
                            fields_dict = dict(zip(note.keys(), note.values()))
                            id_val = fields_dict.get('ID', '')
                        except:
                            pass
                    
                    id_val = id_val.strip()
                    if id_val and id_val.isdigit():
                        max_id = max(max_id, int(id_val))
                        
                except:
                    continue
            
            return max_id + 1
        except:
            return 1
    
    @staticmethod
    def color_word(word: str) -> str:
        """Color German articles"""
        if not word:
            return word
        
        colors = {"der": "#5555ff", "das": "#00aa00", "die": "#ff55ff"}
        parts = word.split()
        if len(parts) >= 2 and parts[0].lower() in colors:
            return f'<span style="color: {colors[parts[0].lower()]};">{word}</span>'
        return word
    
    @staticmethod
    def create_cards(words: List[Dict], deck_name: str) -> Tuple[int, int]:
        """Create cards from word data"""
        if not words:
            return 0, 0
        
        try:
            deck_id = mw.col.decks.id(deck_name)
            
            # Find note type with ID field - more robust detection
            note_type = None
            models = mw.col.models.all()
            for model in models:
                field_names = [field['name'] for field in model['flds']]
                if 'ID' in field_names:
                    note_type = model
                    break
            
            if not note_type:
                return 0, len(words)
            
            # Get starting ID once before creating any cards
            starting_id = DataHandler.get_next_id()
            created = 0
            
            for i, word in enumerate(words):
                try:
                    note = mw.col.new_note(note_type)
                    new_id = starting_id + i
                    
                    # Set ID field using multiple methods for reliability
                    try:
                        note['ID'] = str(new_id)
                    except:
                        # Alternative method if direct assignment fails
                        try:
                            if hasattr(note, '_fmap') and 'ID' in note._fmap:
                                note.fields[note._fmap['ID'][0]] = str(new_id)
                        except:
                            pass
                    
                    # Set other fields with fallback methods
                    field_mapping = {
                        'TL Word': DataHandler.color_word(word.get('original_word', '')),
                        'TL Sentence': word.get('tl_sentence', ''),
                        'NL Word': word.get('nl_word', ''),
                        'NL Sentence': word.get('nl_sentence', ''),
                        'TL Plural': word.get('tl_plural', ''),
                        'Add Reverse': 'y'
                    }
                    
                    for field_name, value in field_mapping.items():
                        try:
                            if field_name in note:
                                note[field_name] = value
                        except:
                            try:
                                if hasattr(note, '_fmap') and field_name in note._fmap:
                                    note.fields[note._fmap[field_name][0]] = value
                            except:
                                continue
                    
                    mw.col.add_note(note, deck_id)
                    created += 1
                except:
                    continue
            
            # Force immediate save
            mw.col.save()
            mw.reset()
            return created, len(words) - created
        except:
            return 0, len(words)


class StartupLoader(QDialog):
    """Startup progress window"""
    
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Word Management")
        self.setFixedSize(280, 80)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        self.label = QLabel("Starting...")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        
        layout.addWidget(self.label)
        layout.addWidget(self.progress)
    
    def update_status(self, text: str):
        self.label.setText(text)


class StartupWorker(QThread):
    """Background startup worker"""
    
    status = pyqtSignal(str)
    words_ready = pyqtSignal(list)
    complete = pyqtSignal(bool, str)
    
    def __init__(self, api, config):
        super().__init__()
        self.api = api
        self.config = config
    
    def run(self):
        try:
            # Check for words first
            if self.config.get('auto_pull_on_startup'):
                self.status.emit("Checking for words...")
                success, words = self.api.get_words()
                if success and words:
                    self.words_ready.emit(words)
                    return
            
            # Upload cards
            self.upload_cards()
        except Exception as e:
            self.complete.emit(False, "Startup failed")
    
    def upload_cards(self):
        """Upload cards to server"""
        if self.config.get('auto_upload_on_startup'):
            self.status.emit("Uploading to server...")
            self.api.clear_cards()
            cards = DataHandler.extract_cards(self.config['deck_name'])
            if cards:
                success, count = self.api.send_cards(cards)
                self.complete.emit(success, f"Synced {count} cards" if success else "Upload failed")
            else:
                self.complete.emit(False, "No cards found")
        else:
            self.complete.emit(True, "Ready")


class SettingsDialog(QDialog):
    """Settings configuration"""
    
    def __init__(self):
        super().__init__(mw)
        self.config = Config.load()
        self.setWindowTitle("Word Management Settings")
        self.setFixedSize(400, 280)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Server
        server_group = QGroupBox("Server")
        server_layout = QFormLayout(server_group)
        
        self.url_edit = QLineEdit(self.config.get('server_url', ''))
        self.key_edit = QLineEdit(self.config.get('api_key', ''))
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        server_layout.addRow("URL:", self.url_edit)
        server_layout.addRow("API Key:", self.key_edit)
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_connection)
        server_layout.addRow(test_btn)
        
        layout.addWidget(server_group)
        
        # Anki
        anki_group = QGroupBox("Settings")
        anki_layout = QFormLayout(anki_group)
        
        self.deck_combo = QComboBox()
        self.deck_combo.setEditable(True)
        self.deck_combo.addItems([deck['name'] for deck in mw.col.decks.all()])
        self.deck_combo.setCurrentText(self.config.get('deck_name', 'Default'))
        
        self.upload_check = QCheckBox()
        self.upload_check.setChecked(self.config.get('auto_upload_on_startup', True))
        
        self.pull_check = QCheckBox()
        self.pull_check.setChecked(self.config.get('auto_pull_on_startup', True))
        
        anki_layout.addRow("Deck:", self.deck_combo)
        anki_layout.addRow("Auto-upload:", self.upload_check)
        anki_layout.addRow("Auto-import:", self.pull_check)
        
        layout.addWidget(anki_group)
        
        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)
    
    def test_connection(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        
        if not url or not key:
            QMessageBox.warning(self, "Error", "Enter URL and API key")
            return
        
        api = API(url, key)
        success, msg = api.test_connection()
        QMessageBox.information(self, "Result", "✅ Connected" if success else "❌ Failed")
    
    def save(self):
        Config.save({
            'server_url': self.url_edit.text().strip(),
            'api_key': self.key_edit.text().strip(),
            'deck_name': self.deck_combo.currentText().strip(),
            'auto_upload_on_startup': self.upload_check.isChecked(),
            'auto_pull_on_startup': self.pull_check.isChecked()
        })
        self.accept()


class ImportDialog(QDialog):
    """Word import interface"""
    
    def __init__(self, words: List[Dict], deck: str):
        super().__init__(mw)
        self.words = words
        self.selected = []
        
        self.setWindowTitle("Import Words")
        self.setMinimumSize(650, 400)
        self.setup_ui(deck)
    
    def setup_ui(self, deck: str):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Import to: {deck} ({len(self.words)} words)"))
        
        # Controls
        controls = QHBoxLayout()
        all_btn = QPushButton("All")
        none_btn = QPushButton("None")
        all_btn.clicked.connect(lambda: self.select_all(True))
        none_btn.clicked.connect(lambda: self.select_all(False))
        controls.addWidget(all_btn)
        controls.addWidget(none_btn)
        controls.addStretch()
        layout.addLayout(controls)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["✓", "TL Word", "NL Word", "TL Sentence", "NL Sentence", "Plural"])
        self.populate_table()
        layout.addWidget(self.table)
        
        # Buttons
        buttons = QHBoxLayout()
        import_btn = QPushButton("Import Selected")
        cancel_btn = QPushButton("Cancel")
        import_btn.clicked.connect(self.import_words)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(import_btn)
        layout.addLayout(buttons)
    
    def populate_table(self):
        self.table.setRowCount(len(self.words))
        
        for row, word in enumerate(self.words):
            checkbox = QCheckBox()
            self.table.setCellWidget(row, 0, checkbox)
            
            data = [
                word.get('original_word', ''),
                word.get('nl_word', ''),
                word.get('tl_sentence', ''),
                word.get('nl_sentence', ''),
                word.get('tl_plural', '')
            ]
            
            for col, text in enumerate(data, 1):
                item = QTableWidgetItem(str(text))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        
        self.table.resizeColumnsToContents()
    
    def select_all(self, checked: bool):
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, 0).setChecked(checked)
    
    def import_words(self):
        selected = []
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 0).isChecked():
                selected.append({
                    'original_word': self.table.item(row, 1).text(),
                    'nl_word': self.table.item(row, 2).text(),
                    'tl_sentence': self.table.item(row, 3).text(),
                    'nl_sentence': self.table.item(row, 4).text(),
                    'tl_plural': self.table.item(row, 5).text(),
                    'id': self.words[row].get('id', '')
                })
        
        if not selected:
            # Ask user if they want to clear words from server when none selected
            reply = QMessageBox.question(
                self, "Clear Words", 
                "No words selected for import.\nClear all processed words from server?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.selected = []  # Empty list signals to clear server
                self.accept()
            return
        
        if QMessageBox.question(self, "Confirm", f"Import {len(selected)} words?") == QMessageBox.StandardButton.Yes:
            self.selected = selected
            self.accept()


class WordManagement:
    """Main extension controller"""
    
    def __init__(self):
        self.api = None
        self.startup_done = False
        self.init()
    
    def init(self):
        # Menu
        mw.form.menuTools.addAction("Word Management Settings").triggered.connect(self.settings)
        mw.form.menuTools.addAction("📤 Upload Cards").triggered.connect(self.upload)
        mw.form.menuTools.addAction("📥 Import Words").triggered.connect(self.import_words)
        
        # Hook
        gui_hooks.main_window_did_init.append(self.startup)
    
    def startup(self):
        if self.startup_done:
            return
        
        tooltip("Word Management loaded", period=1500)
        QTimer.singleShot(2000, self.startup_tasks)
    
    def startup_tasks(self):
        if self.startup_done:
            return
        
        config = Config.load()
        if not config.get('server_url') or not config.get('api_key'):
            self.startup_done = True
            return
        
        self.api = API(config['server_url'], config['api_key'])
        
        # Show loader
        self.loader = StartupLoader()
        self.worker = StartupWorker(self.api, config)
        
        self.worker.status.connect(self.loader.update_status)
        self.worker.words_ready.connect(self.handle_words)
        self.worker.complete.connect(self.startup_complete)
        
        self.loader.show()
        self.worker.start()
    
    def handle_words(self, words):
        """Handle imported words"""
        self.loader.close()
        
        config = Config.load()
        dialog = ImportDialog(words, config['deck_name'])
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected:
                # Import selected words
                created, failed = DataHandler.create_cards(dialog.selected, config['deck_name'])
                
                if created > 0:
                    self.api.clear_words()
                    tooltip(f"✅ Imported {created} cards", period=2500)
                else:
                    tooltip("❌ Import failed", period=2500)
            else:
                # Empty list means user chose to clear server without importing
                self.api.clear_words()
                tooltip("✅ Server words cleared", period=2500)
        
        # Continue with upload
        QTimer.singleShot(500, self.continue_startup)
    
    def continue_startup(self):
        """Continue startup after import"""
        self.loader = StartupLoader()
        self.loader.update_status("Uploading...")
        self.loader.show()
        QTimer.singleShot(500, self.worker.upload_cards)
    
    def startup_complete(self, success: bool, message: str):
        """Handle startup completion"""
        if hasattr(self, 'loader'):
            self.loader.close()
        
        self.startup_done = True
        tooltip(f"✅ {message}" if success else f"❌ {message}", period=2000)
    
    def settings(self):
        """Show settings"""
        dialog = SettingsDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = Config.load()
            if config.get('server_url') and config.get('api_key'):
                self.api = API(config['server_url'], config['api_key'])
            tooltip("Settings saved", period=1500)
    
    def upload(self):
        """Manual upload"""
        if not self.api:
            showCritical("Configure settings first")
            return
        
        config = Config.load()
        self.api.clear_cards()
        cards = DataHandler.extract_cards(config['deck_name'])
        
        if cards:
            success, count = self.api.send_cards(cards)
            tooltip(f"✅ Uploaded {count} cards" if success else "❌ Upload failed", period=2000)
        else:
            showCritical("No cards found")
    
    def import_words(self):
        """Manual import"""
        if not self.api:
            showCritical("Configure settings first")
            return
        
        success, words = self.api.get_words()
        if not success:
            showCritical("Failed to get words")
            return
        
        if not words:
            showInfo("No words available")
            return
        
        config = Config.load()
        dialog = ImportDialog(words, config['deck_name'])
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected:
                # Import selected words
                created, failed = DataHandler.create_cards(dialog.selected, config['deck_name'])
                
                if created > 0:
                    self.api.clear_words()
                    msg = f"✅ Created {created} cards"
                    if failed > 0:
                        msg += f" ({failed} failed)"
                    showInfo(msg)
                else:
                    showCritical("Failed to create cards")
            else:
                # Empty list means user chose to clear server without importing
                self.api.clear_words()
                showInfo("✅ Server words cleared")


# Initialize
word_management = WordManagement()

__version__ = "3.0.0"