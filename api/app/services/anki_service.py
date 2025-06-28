# app/services/anki_service.py
import sqlite3
import json
from datetime import datetime
from typing import List
from app.schemas.anki import AnkiData, AnkiResponse, AnkiCard, AnkiCardList, AnkiCardResponse, AnkiCardData
from app.database.connection import get_db_connection

class AnkiService:
    @staticmethod
    def store_anki_data(anki_data: AnkiData) -> AnkiResponse:
        """Store Anki data in database (legacy endpoint)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO anki_data (deck_name, cards_data, metadata)
                VALUES (?, ?, ?)
            """, (
                anki_data.deck_name,
                json.dumps(anki_data.cards),
                json.dumps(anki_data.metadata) if anki_data.metadata else None
            ))
            
            data_id = cursor.lastrowid
            conn.commit()
            
            return AnkiResponse(
                message="Anki data received successfully",
                data_id=data_id,
                deck_name=anki_data.deck_name,
                cards_count=len(anki_data.cards),
                timestamp=datetime.now().isoformat()
            )
    
    @staticmethod
    def store_anki_cards(card_list: AnkiCardList) -> AnkiCardResponse:
        """Store individual Anki cards with upsert functionality"""
        cards_inserted = 0
        cards_updated = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for card in card_list.cards:
                try:
                    # Try to insert new card
                    cursor.execute("""
                        INSERT INTO anki_cards (card_id, tl_word, tl_sentence, nl_word, nl_sentence)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        card.card_id,
                        card.tl_word,
                        card.tl_sentence,
                        card.nl_word,
                        card.nl_sentence
                    ))
                    cards_inserted += 1
                    
                except sqlite3.IntegrityError:
                    # Card already exists, update it
                    cursor.execute("""
                        UPDATE anki_cards 
                        SET tl_word = ?, tl_sentence = ?, nl_word = ?, nl_sentence = ?, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE card_id = ?
                    """, (
                        card.tl_word,
                        card.tl_sentence,
                        card.nl_word,
                        card.nl_sentence,
                        card.card_id
                    ))
                    cards_updated += 1
            
            conn.commit()
        
        return AnkiCardResponse(
            message="Anki cards processed successfully",
            cards_received=len(card_list.cards),
            cards_inserted=cards_inserted,
            cards_updated=cards_updated,
            timestamp=datetime.now().isoformat()
        )
    
    @staticmethod
    def get_all_anki_cards(limit: int = 1000) -> List[AnkiCardData]:
        """Get all stored Anki cards"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, card_id, tl_word, tl_sentence, nl_word, nl_sentence, 
                       created_at, updated_at
                FROM anki_cards 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            return [
                AnkiCardData(
                    id=row[0],
                    card_id=row[1],
                    tl_word=row[2],
                    tl_sentence=row[3],
                    nl_word=row[4],
                    nl_sentence=row[5],
                    created_at=row[6],
                    updated_at=row[7]
                ) for row in rows
            ]
    
    @staticmethod
    def clear_all_anki_cards() -> dict:
        """Delete all Anki cards from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count cards before deletion
            cursor.execute("SELECT COUNT(*) FROM anki_cards")
            count = cursor.fetchone()[0]
            
            if count == 0:
                return {
                    "message": "No Anki cards to delete",
                    "deleted_count": 0
                }
            
            # Delete all cards
            cursor.execute("DELETE FROM anki_cards")
            conn.commit()
            
            return {
                "message": f"All Anki cards cleared successfully",
                "deleted_count": count
            }