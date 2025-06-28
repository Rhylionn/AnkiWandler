from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WordBase(BaseModel):
    word: str
    date: str

class WordCreate(WordBase):
    pass

class WordListCreate(BaseModel):
    words: List[WordBase]

class WordListResponse(BaseModel):
    message: str
    total_words: int
    processing_started: bool
    request_id: str

class PendingWordResponse(BaseModel):
    id: int
    word: str
    date: str
    created_at: str
    processing_status: str

class ProcessedWordResponse(BaseModel):
    id: int
    original_word: str
    date: str
    tl_word: str
    nl_word: str
    tl_sentence: str
    nl_sentence: str
    tl_plural: Optional[str]
    processed_at: str

class AIResponse(BaseModel):
    tl_sentence: str
    tl_plural: Optional[str] = None

class TranslationRequest(BaseModel):
    text: str
    target_language: str = "en"

class TranslationResponse(BaseModel):
    translated_text: str

class AIRequest(BaseModel):
    word: str
    context: Optional[str] = None
    target_language: Optional[str] = "en"

class LegacyAIResponse(BaseModel):
    message: str
    request_id: str
    word: str
    context: Optional[str]
    target_language: str
    status: str
    ai_endpoint: str

class RetryResponse(BaseModel):
    message: str
    count: int
    request_id: str
    processing_started: bool