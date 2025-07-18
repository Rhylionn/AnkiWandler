# card_processor.py - Card Data Processing
from typing import List, Dict, Tuple
from aqt import mw
from .utils import clean_html, color_german_word

class CardProcessor:
    """Handles card extraction and creation operations"""
    
    def __init__(self):
        pass
    
    def extract_cards_from_deck(self, deck_name: str) -> List[Dict]:
        """Extract cards from specified Anki deck"""
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
                    
                    # Get card ID, skip if empty or duplicate
                    card_id_val = fields.get('ID', '').strip()
                    if not card_id_val or card_id_val in unique_cards:
                        continue
                    
                    # Extract and clean card data
                    unique_cards[card_id_val] = {
                        "card_id": card_id_val,
                        "tl_word": clean_html(fields.get('TL Word', '')),
                        "tl_sentence": clean_html(fields.get('TL Sentence', '')),
                        "nl_word": clean_html(fields.get('NL Word', '')),
                        "nl_sentence": clean_html(fields.get('NL Sentence', ''))
                    }
                except Exception as e:
                    print(f"Error processing card {card_id}: {e}")
                    continue
            
            return list(unique_cards.values())
            
        except Exception as e:
            print(f"Error extracting cards from deck '{deck_name}': {e}")
            return []
    
    def get_next_available_id(self) -> int:
        """Get next available card ID"""
        if not mw.col:
            return 1
        
        try:
            # Search for notes with ID field
            note_ids = mw.col.find_notes('"ID:*"')
            if not note_ids:
                note_ids = mw.col.find_notes('ID:*')
            
            max_id = 0
            
            for note_id in note_ids:
                try:
                    note = mw.col.get_note(note_id)
                    
                    # Try to get ID field value
                    id_value = ""
                    if hasattr(note, '__getitem__') and 'ID' in note:
                        id_value = note['ID']
                    else:
                        # Alternative method
                        fields_dict = dict(zip(note.keys(), note.values()))
                        id_value = fields_dict.get('ID', '')
                    
                    id_value = id_value.strip()
                    if id_value and id_value.isdigit():
                        max_id = max(max_id, int(id_value))
                        
                except Exception as e:
                    continue
            
            return max_id + 1
            
        except Exception as e:
            print(f"Error getting next ID: {e}")
            return 1
    
    def create_cards_from_words(self, words: List[Dict], deck_name: str) -> Tuple[int, int]:
        """Create Anki cards from word data"""
        if not words or not mw.col:
            return 0, len(words) if words else 0
        
        try:
            deck_id = mw.col.decks.id(deck_name)
            
            # Find note type with ID field
            note_type = self._find_compatible_note_type()
            if not note_type:
                print("No compatible note type found with ID field")
                return 0, len(words)
            
            # Get starting ID
            starting_id = self.get_next_available_id()
            created_count = 0
            
            for i, word in enumerate(words):
                try:
                    note = mw.col.new_note(note_type)
                    new_id = starting_id + i
                    
                    # Set card fields
                    field_mapping = {
                        'ID': str(new_id),
                        'TL Word': color_german_word(word.get('original_word', '')),
                        'TL Sentence': word.get('tl_sentence', ''),
                        'NL Word': word.get('nl_word', ''),
                        'NL Sentence': word.get('nl_sentence', ''),
                        'TL Plural': word.get('tl_plural', '') or '',
                        'Add Reverse': 'y'
                    }
                    
                    # Set fields with error handling
                    for field_name, value in field_mapping.items():
                        try:
                            if field_name in note:
                                note[field_name] = value
                        except Exception as e:
                            print(f"Error setting field {field_name}: {e}")
                            continue
                    
                    # Add note to collection
                    mw.col.add_note(note, deck_id)
                    created_count += 1
                    
                except Exception as e:
                    print(f"Error creating card for word '{word.get('original_word', 'unknown')}': {e}")
                    continue
            
            # Save changes
            if created_count > 0:
                mw.col.save()
                mw.reset()
            
            return created_count, len(words) - created_count
            
        except Exception as e:
            print(f"Error creating cards: {e}")
            return 0, len(words)
    
    def _find_compatible_note_type(self):
        """Find note type with ID field"""
        try:
            models = mw.col.models.all()
            for model in models:
                field_names = [field['name'] for field in model['flds']]
                if 'ID' in field_names:
                    return model
            return None
        except Exception as e:
            print(f"Error finding note type: {e}")
            return None