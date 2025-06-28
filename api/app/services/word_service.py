# app/services/word_service.py
import asyncio
import uuid
from typing import List, Optional
from app.database.connection import get_db_connection
from app.schemas.word import WordCreate, WordListCreate, PendingWordResponse, ProcessedWordResponse, RetryResponse
from app.services.ai_service import AIService

class WordService:
    @staticmethod
    def add_word(word_data: WordCreate) -> dict:
        """Add a single word and start AI processing pipeline"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pending_words (word, date)
                VALUES (?, ?)
            """, (word_data.word, word_data.date))
            
            word_id = cursor.lastrowid
            conn.commit()
            
            # Start AI processing pipeline asynchronously
            request_id = str(uuid.uuid4())
            asyncio.create_task(AIService.process_word_async(word_id, word_data, request_id))
            
            return {
                "message": "Word added and processing started",
                "word_id": word_id,
                "word": word_data.word,
                "request_id": request_id,
                "processing_started": True
            }
    
    @staticmethod
    def add_word_list(word_list_data: WordListCreate) -> dict:
        """Add multiple words and start batch AI processing pipeline"""
        word_ids = []
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for word_data in word_list_data.words:
                try:
                    cursor.execute("""
                        INSERT INTO pending_words (word, date)
                        VALUES (?, ?)
                    """, (word_data.word, word_data.date))
                    
                    word_ids.append(cursor.lastrowid)
                    
                except Exception as e:
                    print(f"Failed to insert word '{word_data.word}': {str(e)}")
            
            conn.commit()
        
        # Start batch AI processing pipeline asynchronously
        request_id = str(uuid.uuid4())
        asyncio.create_task(AIService.process_word_list_async(word_ids, word_list_data.words, request_id))
        
        return {
            "message": f"Batch word insertion completed and processing started",
            "total_words": len(word_list_data.words),
            "processing_started": True,
            "request_id": request_id
        }
    
    @staticmethod
    def get_pending_words(limit: int = 100) -> List[PendingWordResponse]:
        """Get pending words from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, word, date, created_at, processing_status 
                FROM pending_words 
                ORDER BY created_at DESC LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            return [
                PendingWordResponse(
                    id=row[0],
                    word=row[1],
                    date=row[2],
                    created_at=row[3],
                    processing_status=row[4]
                ) for row in rows
            ]
    
    @staticmethod
    def get_processed_words(limit: int = 100) -> List[ProcessedWordResponse]:
        """Get processed words from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, original_word, date, tl_word, nl_word, 
                       tl_sentence, nl_sentence, tl_plural, processed_at
                FROM processed_words 
                ORDER BY processed_at DESC LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            return [
                ProcessedWordResponse(
                    id=row[0],
                    original_word=row[1],
                    date=row[2],
                    tl_word=row[3],
                    nl_word=row[4],
                    tl_sentence=row[5],
                    nl_sentence=row[6],
                    tl_plural=row[7],
                    processed_at=row[8]
                ) for row in rows
            ]
    
    @staticmethod
    def retry_failed_words() -> RetryResponse:
        """Retry processing all failed words"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all failed words
            cursor.execute("""
                SELECT id, word, date 
                FROM pending_words 
                WHERE processing_status = 'failed'
            """)
            failed_words = cursor.fetchall()
            
            if not failed_words:
                return RetryResponse(
                    message="No failed words to retry",
                    count=0,
                    request_id="",
                    processing_started=False
                )
            
            # Reset status to pending
            cursor.execute("""
                UPDATE pending_words 
                SET processing_status = 'pending' 
                WHERE processing_status = 'failed'
            """)
            conn.commit()
        
        # Create word objects and start processing
        word_ids = []
        words = []
        
        for row in failed_words:
            word_ids.append(row[0])
            words.append(WordCreate(
                word=row[1],
                date=row[2]
            ))
        
        # Start batch processing
        request_id = str(uuid.uuid4())
        asyncio.create_task(AIService.process_word_list_async(word_ids, words, request_id))
        
        return RetryResponse(
            message=f"Retry started for {len(failed_words)} failed words",
            count=len(failed_words),
            request_id=request_id,
            processing_started=True
        )
    
    @staticmethod
    def delete_pending_word(word_id: int) -> dict:
        """Delete a pending word from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
            
            if cursor.rowcount == 0:
                return {"error": "Word not found"}
            
            conn.commit()
            return {"message": f"Pending word {word_id} deleted successfully"}
    
    @staticmethod
    def delete_processed_word(word_id: int) -> dict:
        """Delete a processed word from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processed_words WHERE id = ?", (word_id,))
            
            if cursor.rowcount == 0:
                return {"error": "Word not found"}
            
            conn.commit()
            return {"message": f"Processed word {word_id} deleted successfully"}
    
    @staticmethod
    def clear_all_processed_words() -> dict:
        """Delete all processed words from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First count how many words will be deleted
            cursor.execute("SELECT COUNT(*) FROM processed_words")
            count = cursor.fetchone()[0]
            
            if count == 0:
                return {
                    "message": "No processed words to delete",
                    "deleted_count": 0
                }
            
            # Delete all processed words
            cursor.execute("DELETE FROM processed_words")
            conn.commit()
            
            return {
                "message": f"All processed words cleared successfully",
                "deleted_count": count
            }