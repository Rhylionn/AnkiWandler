def signal_work_available(self):
        """Signal that new work is available (thread-safe)"""
        if self.loop and self.work_event and self.running:
            # Schedule the event to be set in the worker's event loop
            self.loop.call_soon_threadsafe(self.work_event.set)
            print("🔔 Signaled work available to queue worker")# app/services/queue_service.py
import asyncio
import threading
from typing import List, Optional
from app.database.connection import get_db_connection
from app.schemas.word import WordCreate
from app.services.ai_service import AIService

class QueueService:
    """Event-driven background queue worker for processing words with retry logic"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.loop = None
        self.work_event = None
        
    def start(self):
        """Start the background queue worker"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_worker, daemon=True)
        self.thread.start()
        print("🚀 Queue worker started")
    
    def stop(self):
        """Stop the background queue worker"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        print("🛑 Queue worker stopped")
    
    def _run_worker(self):
        """Main worker loop - runs in separate thread"""
        # Create new event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create event for this loop
        self.work_event = asyncio.Event()
        
        try:
            self.loop.run_until_complete(self._worker_loop())
        except Exception as e:
            print(f"❌ Queue worker error: {e}")
        finally:
            self.loop.close()
    
    async def _worker_loop(self):
        """Event-driven processing loop"""
        while self.running:
            try:
                # Get pending words
                pending_words = self._get_pending_words()
                
                if pending_words:
                    print(f"📝 Processing {len(pending_words)} pending words")
                    await self._process_words_batch(pending_words)
                    
                    # Check immediately for more work after batch completion
                    continue
                
                # No work found, wait for event signal or timeout
                print("💤 No pending words, waiting for work signal...")
                try:
                    await asyncio.wait_for(self.work_event.wait(), timeout=300)  # 5 minute fallback
                    self.work_event.clear()  # Reset event
                    print("🔔 Work signal received, checking for pending words...")
                except asyncio.TimeoutError:
                    print("⏰ Timeout reached, checking for pending words...")
                
            except Exception as e:
                print(f"❌ Worker loop error: {e}")
                await asyncio.sleep(60)  # Wait on error
    
    def _get_pending_words(self) -> List[dict]:
        """Get words that need processing"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get words that are pending or failed with less than 3 retry attempts
            cursor.execute("""
                SELECT id, word, date, context_sentence, needs_article, retry_count
                FROM pending_words 
                WHERE processing_status IN ('pending', 'failed') 
                AND (retry_count IS NULL OR retry_count < 3)
                ORDER BY created_at ASC
                LIMIT 20
            """)
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'word': row[1],
                    'date': row[2],
                    'context_sentence': row[3],
                    'needs_article': bool(row[4]) if row[4] is not None else False,
                    'retry_count': row[5] or 0
                }
                for row in rows
            ]
    
    async def _process_words_batch(self, words: List[dict]):
        """Process a batch of words with concurrency control"""
        # Limit concurrent processing
        semaphore = asyncio.Semaphore(2)  # Reduced from 3 to 2 for stability
        
        async def process_with_semaphore(word_data: dict):
            async with semaphore:
                await self._process_single_word(word_data)
        
        # Process all words concurrently
        tasks = [process_with_semaphore(word) for word in words]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_word(self, word_data: dict):
        """Process a single word with retry logic"""
        word_id = word_data['id']
        retry_count = word_data['retry_count']
        
        try:
            # Add retry delay (exponential backoff)
            if retry_count > 0:
                delay = min(2 ** retry_count, 60)  # 2s, 4s, 8s, max 60s
                print(f"⏳ Retrying word {word_data['word']} (attempt {retry_count + 1}) after {delay}s delay")
                await asyncio.sleep(delay)
            
            # Update status to processing
            self._update_word_status(word_id, 'processing', retry_count + 1)
            
            # Create WordCreate object
            word_create = WordCreate(
                word=word_data['word'],
                date=word_data['date'],
                context_sentence=word_data['context_sentence'],
                needs_article=word_data['needs_article']
            )
            
            # Process through AI service
            await AIService.process_word_async(word_id, word_create, f"queue-{word_id}")
            
            print(f"✅ Successfully processed: {word_data['word']}")
            
        except Exception as e:
            # Update retry count and set to failed
            new_retry_count = retry_count + 1
            
            if new_retry_count >= 3:
                self._update_word_status(word_id, 'failed', new_retry_count)
                print(f"❌ Permanently failed after {new_retry_count} attempts: {word_data['word']} - {str(e)}")
            else:
                self._update_word_status(word_id, 'failed', new_retry_count)
                print(f"⚠️ Failed attempt {new_retry_count}/3: {word_data['word']} - {str(e)}")
    
    def _update_word_status(self, word_id: int, status: str, retry_count: int):
        """Update word processing status and retry count"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_words 
                SET processing_status = ?, retry_count = ?
                WHERE id = ?
            """, (status, retry_count, word_id))
            conn.commit()
    
    def get_queue_status(self) -> dict:
        """Get current queue status"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count by status
            cursor.execute("""
                SELECT processing_status, COUNT(*) 
                FROM pending_words 
                GROUP BY processing_status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Count retryable failed words
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pending_words 
                WHERE processing_status = 'failed' 
                AND (retry_count IS NULL OR retry_count < 3)
            """)
            retryable_failed = cursor.fetchone()[0]
            
            return {
                'queue_running': self.running,
                'pending': status_counts.get('pending', 0),
                'processing': status_counts.get('processing', 0),
                'failed': status_counts.get('failed', 0),
                'retryable_failed': retryable_failed,
                'total_pending': status_counts.get('pending', 0) + retryable_failed
            }
    
    def retry_failed_words(self) -> dict:
        """Reset failed words for retry"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count words to retry
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pending_words 
                WHERE processing_status = 'failed' 
                AND (retry_count IS NULL OR retry_count < 3)
            """)
            retry_count = cursor.fetchone()[0]
            
            if retry_count > 0:
                # Reset status to pending
                cursor.execute("""
                    UPDATE pending_words 
                    SET processing_status = 'pending'
                    WHERE processing_status = 'failed' 
                    AND (retry_count IS NULL OR retry_count < 3)
                """)
                conn.commit()
            
            return {
                'message': f'Reset {retry_count} failed words for retry',
                'retry_count': retry_count
            }
    
    def signal_work_available(self):
        """Signal that new work is available (thread-safe)"""
        if self.loop and self.work_event and self.running:
            # Schedule the event to be set in the worker's event loop
            self.loop.call_soon_threadsafe(self.work_event.set)
            print("🔔 Signaled work available to queue worker")

# Global queue instance
queue_worker = QueueService()