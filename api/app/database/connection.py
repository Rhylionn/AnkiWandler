# app/database/connection.py
import sqlite3
from contextlib import contextmanager
from app.config.settings import settings

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Pending words table (for words waiting to be processed)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            date TEXT NOT NULL,
            context_sentence TEXT,
            needs_article BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_status TEXT DEFAULT 'pending'
        )
    """)
    
    # Processed words table (AI + translation processed words)
    # Updated to explicitly allow NULL for tl_plural
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_word TEXT NOT NULL,
            date TEXT NOT NULL,
            tl_word TEXT NOT NULL,
            nl_word TEXT NOT NULL,
            tl_sentence TEXT NOT NULL,
            nl_sentence TEXT NOT NULL,
            tl_plural TEXT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Anki cards table (individual card storage)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anki_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT UNIQUE NOT NULL,
            tl_word TEXT NOT NULL,
            tl_sentence TEXT NOT NULL,
            nl_word TEXT NOT NULL,
            nl_sentence TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index on card_id for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_anki_cards_card_id ON anki_cards(card_id)
    """)
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    try:
        yield conn
    finally:
        conn.close()