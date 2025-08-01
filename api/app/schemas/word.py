from pydantic import BaseModel
from typing import Optional, List

class WordBase(BaseModel):
    word: str
    date: str
    context_sentence: Optional[str] = None
    needs_article: bool = False

class WordCreate(WordBase):
    pass

class WordListCreate(BaseModel):
    words: List[WordBase]

class WordListResponse(BaseModel):
    message: str
    total_words: int
    queued: bool

class PendingWordResponse(BaseModel):
    id: int
    word: str
    date: str
    created_at: str
    processing_status: str
    context_sentence: Optional[str] = None
    needs_article: bool

class ProcessedWordResponse(BaseModel):
    id: int
    original_word: str
    date: str
    tl_word: str
    nl_word: str
    tl_sentence: str
    nl_sentence: str
    tl_plural: Optional[str] = None
    processed_at: str

# Internal AI processing schemas (not exposed via API)
class WordClassification(BaseModel):
    is_noun: bool

class AIResponse(BaseModel):
    tl_word: str
    tl_sentence: str
    tl_plural: Optional[str] = None

class SimpleAIResponse(BaseModel):
    tl_sentence: str

class TranslationRequest(BaseModel):
    text: str
    target_language: str = "en"

class TranslationResponse(BaseModel):
    translated_text: str