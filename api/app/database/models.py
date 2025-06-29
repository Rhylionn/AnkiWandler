from typing import Optional
from datetime import datetime

class PendingWordModel:
    def __init__(self, id: int, word: str, date: str, 
                 created_at: str, processing_status: str,
                 context_sentence: Optional[str] = None, 
                 needs_article: bool = False):
        self.id = id
        self.word = word
        self.date = date
        self.created_at = created_at
        self.processing_status = processing_status
        self.context_sentence = context_sentence
        self.needs_article = needs_article

class ProcessedWordModel:
    def __init__(self, id: int, original_word: str, date: str,
                 tl_word: str, nl_word: str, tl_sentence: str, 
                 nl_sentence: str, tl_plural: Optional[str], processed_at: str):
        self.id = id
        self.original_word = original_word
        self.date = date
        self.tl_word = tl_word
        self.nl_word = nl_word
        self.tl_sentence = tl_sentence
        self.nl_sentence = nl_sentence
        self.tl_plural = tl_plural
        self.processed_at = processed_at

class AnkiDataModel:
    def __init__(self, id: int, deck_name: str, cards_data: str, 
                 metadata: Optional[str], created_at: str):
        self.id = id
        self.deck_name = deck_name
        self.cards_data = cards_data
        self.metadata = metadata
        self.created_at = created_at