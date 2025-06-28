# app/schemas/anki.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Legacy schemas (keep for backward compatibility)
class AnkiData(BaseModel):
    deck_name: str
    cards: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None

class AnkiResponse(BaseModel):
    message: str
    data_id: int
    deck_name: str
    cards_count: int
    timestamp: str

# New card-based schemas
class AnkiCard(BaseModel):
    card_id: str
    tl_word: str
    tl_sentence: str
    nl_word: str
    nl_sentence: str

class AnkiCardList(BaseModel):
    cards: List[AnkiCard]

class AnkiCardResponse(BaseModel):
    message: str
    cards_received: int
    cards_inserted: int
    cards_updated: int
    timestamp: str

class AnkiCardData(BaseModel):
    id: int
    card_id: str
    tl_word: str
    tl_sentence: str
    nl_word: str
    nl_sentence: str
    created_at: str
    updated_at: str