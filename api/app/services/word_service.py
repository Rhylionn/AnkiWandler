# app/services/word_service.py
from typing import List
from app.database.connection import get_db_connection
from app.schemas.word import WordCreate, WordListCreate, PendingWordResponse, ProcessedWordResponse
import json

class WordService:
    @staticmethod
    def add_word(word_data: WordCreate) -> dict:
        """Add a single word to the enhanced processing queue"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pending_words (word, date, context_sentence, needs_article)
                VALUES (?, ?, ?, ?)
            """, (
                word_data.word, 
                word_data.date,
                word_data.context_sentence,
                word_data.needs_article
            ))
            
            word_id = cursor.lastrowid
            conn.commit()
            
        # Signal enhanced queue worker that new work is available
        from app.services.queue_service import queue_worker
        queue_worker.signal_work_available()
        
        context_info = " (with context)" if word_data.context_sentence else ""
        
        return {
            "message": "Word added to enhanced processing queue",
            "word_id": word_id,
            "word": word_data.word,
            "queued": True,
            "context_provided": bool(word_data.context_sentence),
            "needs_article": word_data.needs_article,
            "enhanced_workflow": True
        }
    
    @staticmethod
    def add_word_list(word_list_data: WordListCreate) -> dict:
        """Add multiple words to the enhanced processing queue"""
        word_ids = []
        context_count = 0
        direct_count = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for word_data in word_list_data.words:
                try:
                    cursor.execute("""
                        INSERT INTO pending_words (word, date, context_sentence, needs_article)
                        VALUES (?, ?, ?, ?)
                    """, (
                        word_data.word, 
                        word_data.date,
                        word_data.context_sentence,
                        word_data.needs_article
                    ))
                    
                    word_ids.append(cursor.lastrowid)
                    
                    # Track collection types
                    if word_data.needs_article:
                        context_count += 1
                    else:
                        direct_count += 1
                    
                except Exception as e:
                    print(f"Failed to insert word '{word_data.word}': {str(e)}")
            
            conn.commit()
        
        # Signal enhanced queue worker that new work is available
        from app.services.queue_service import queue_worker
        queue_worker.signal_work_available()
        
        return {
            "message": f"Words added to enhanced processing queue",
            "total_words": len(word_list_data.words),
            "context_words": context_count,
            "direct_words": direct_count,
            "queued": True,
            "enhanced_workflow": True
        }
    
    @staticmethod
    def get_pending_words(limit: int = 100) -> List[PendingWordResponse]:
        """Get pending words from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, word, date, created_at, processing_status, 
                       context_sentence, needs_article, retry_count
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
                    processing_status=row[4],
                    context_sentence=row[5],
                    needs_article=bool(row[6]) if row[6] is not None else False
                ) for row in rows
            ]
    
    @staticmethod
    def get_processed_words(limit: int = 100) -> List[ProcessedWordResponse]:
        """Get processed words from database - NOW WITH REVIEW FLAGS"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT id, original_word, date, tl_word, nl_word, 
                       tl_sentence, nl_sentence, tl_plural, processed_at, review_flags
                FROM processed_words 
                ORDER BY processed_at DESC LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                # Parse review_flags JSON if it exists
                review_flags = []
                if row[9]:  # review_flags column
                    try:
                        review_flags = json.loads(row[9])
                    except json.JSONDecodeError:
                        review_flags = []
                
                processed_word = ProcessedWordResponse(
                    id=row[0],
                    original_word=row[1],
                    date=row[2],
                    tl_word=row[3],
                    nl_word=row[4],
                    tl_sentence=row[5],
                    nl_sentence=row[6],
                    tl_plural=row[7],
                    processed_at=row[8]
                )
                
                # Add review_flags as additional attribute
                processed_word.review_flags = review_flags
                
                result.append(processed_word)
            
            return result
    
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
                "message": f"All processed words cleared successfully (enhanced workflow v2)",
                "deleted_count": count,
                "enhanced_workflow": True
            }