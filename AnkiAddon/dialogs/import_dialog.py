# dialogs/import_dialog.py - Word Import Dialog
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox,
    QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from aqt import mw
from typing import List, Dict

class ImportDialog(QDialog):
    """Simple dialog for importing processed words"""
    
    def __init__(self, words: List[Dict], config_manager, card_processor, api_client):
        super().__init__(mw)
        self.words = words
        self.config = config_manager
        self.card_processor = card_processor
        self.api = api_client
        self.selected_words = []
        
        self.setWindowTitle("Import Processed Words")
        self.setMinimumSize(800, 500)
        self.setModal(True)
        
        self.setup_ui()
        self.populate_table()

    def closeEvent(self, event):
        """Ensure proper cleanup on close"""
        super().closeEvent(event)
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        deck_name = self.config.get('deck_name', 'Default')
        header_text = f"Import {len(self.words)} processed words to deck: {deck_name}"
        header_label = QLabel(header_text)
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        layout.addWidget(header_label)
        
        # Selection controls
        select_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self.select_all(True))
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self.select_all(False))
        select_layout.addWidget(select_none_btn)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        # Words table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "✓", "German Word", "Native Lang. Word", "German Sentence", "Native Lang. Sentence", "Plural"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # German Word
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Native Lang. Word
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # German Sentence
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Native Lang. Sentence
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Plural
        
        self.table.setColumnWidth(0, 40)
        
        layout.addWidget(self.table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Clear server button
        clear_btn = QPushButton("Clear Server")
        clear_btn.clicked.connect(self.clear_server_words)
        clear_btn.setToolTip("Clear all processed words from server without importing")
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        import_btn = QPushButton("Import Selected")
        import_btn.clicked.connect(self.import_selected_words)
        import_btn.setDefault(True)
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
    
    def populate_table(self):
        """Populate table with word data and highlight flagged entries"""
        self.table.setRowCount(len(self.words))
        
        flagged_color = QColor(168, 50, 60)  # Dark red background
        
        for row, word in enumerate(self.words):
            # Check if word has review flags with length > 0
            has_flags = isinstance(word, dict) and word.get('review_flags') and len(word.get('review_flags', [])) > 0
            
            # Checkbox (column 0)
            checkbox_item = QTableWidgetItem("")
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if has_flags:
                checkbox_item.setBackground(flagged_color)
            self.table.setItem(row, 0, checkbox_item)
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)  # Select all by default
            self.table.setCellWidget(row, 0, checkbox)
            
            # Word data (columns 1-5)
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
                if has_flags:
                    item.setBackground(flagged_color)
                self.table.setItem(row, col, item)
        
        # Adjust row heights
        self.table.resizeRowsToContents()
    
    def select_all(self, checked: bool):
        """Select or deselect all words"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)
    
    def get_selected_words(self) -> List[Dict]:
        """Get list of selected words with any edits"""
        selected = []
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # Get edited values from table
                word_data = {
                    'original_word': self.table.item(row, 1).text(),
                    'nl_word': self.table.item(row, 2).text(),
                    'tl_sentence': self.table.item(row, 3).text(),
                    'nl_sentence': self.table.item(row, 4).text(),
                    'tl_plural': self.table.item(row, 5).text(),
                    'id': self.words[row].get('id', '')  # Keep original ID
                }
                selected.append(word_data)
        
        return selected
    
    def import_selected_words(self):
        """Import selected words as Anki cards"""
        selected_words = self.get_selected_words()
        
        if not selected_words:
            # No words selected - ask if user wants to clear server
            reply = QMessageBox.question(
                self, 
                "No Words Selected", 
                "No words selected for import.\n\nWould you like to clear all processed words from the server?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.clear_server_words()
            return
        
        # Confirm import
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import {len(selected_words)} words as Anki cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Create cards
            deck_name = self.config.get('deck_name', 'Default')
            created, failed = self.card_processor.create_cards_from_words(selected_words, deck_name)
            
            if created > 0:
                # Clear processed words from server after successful import
                success, _ = self.api.clear_words()
                
                # Show results
                message = f"✅ Successfully imported {created} cards"
                if failed > 0:
                    message += f"\n⚠️ {failed} cards failed to import"
                if not success:
                    message += "\n⚠️ Could not clear words from server"
                
                QMessageBox.information(self, "Import Complete", message)
                self.accept()
            else:
                QMessageBox.critical(self, "Import Failed", "Failed to create any cards. Check your note type configuration.")
        
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Error during import:\n{str(e)}")
    
    def clear_server_words(self):
        """Clear all processed words from server without importing"""
        reply = QMessageBox.question(
            self,
            "Clear Server Words",
            "This will permanently delete all processed words from the server.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success, result = self.api.clear_words()
                
                if success:
                    QMessageBox.information(self, "Success", "✅ All processed words cleared from server")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to clear words from server:\n{result}")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error clearing server words:\n{str(e)}")