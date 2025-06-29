import asyncio
import httpx
import uuid
from datetime import datetime
from typing import List, Optional
from app.schemas.word import WordCreate, AIResponse
from app.database.connection import get_db_connection
from app.config.settings import settings
from app.services.translation_service import TranslationService

class AIService:
    @staticmethod
    def create_prompt(word: str, context_sentence: Optional[str] = None, needs_article: bool = False) -> str:
        """Create AI prompt with adaptive context support and article detection"""
        
        return f"""You are a German-language assistant specializing in noun articles and A1-level sentence construction.

Input:
- target_word = {word}
- context_sentence = {context_sentence}
- needs_article = {needs_article}

Tasks:
1. If needs_article is true, use the context_sentence to determine the correct definite article (der/die/das) and add it to target_word. If needs_article is false, use target_word as-is for tl_word.
2. Generate one A1-level German sentence using target_word.
3. Determine the standard plural form of the base noun.

Output (JSON only, no markdown):
{{
  "tl_word": "<word with article>",
  "tl_sentence": "<German A1 sentence>",
  "tl_plural": "<plural form>"
}}

Requirements:
- When needs_article is true, use context to determine correct definite article in nominative case
- Sentence must be A1-level German, grammatically correct
- Plural must be accurate German plural form
- Output only valid JSON"""
    
    @staticmethod
    async def call_ai_api(word: str, context_sentence: Optional[str] = None, needs_article: bool = False) -> AIResponse:
        """Call external AI API to process a word with optional context and article detection"""
        async with httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT) as client:
            prompt = AIService.create_prompt(word, context_sentence, needs_article)
            payload = {
                "model": "qwen2.5-optimized",
                "prompt": prompt,
                "stream": False
            }
            
            try:
                response = await client.post(settings.AI_API_URL, json=payload)
                response.raise_for_status()
                
                # Get the full response as JSON
                full_response = response.json()
                
                # Extract the JSON string from the "response" field
                response_content = full_response["response"]
                
                # Parse the JSON string to get the actual data
                import json
                ai_data = json.loads(response_content)
                
                # Create and return the AIResponse object
                return AIResponse(**ai_data)
                
            except httpx.TimeoutException:
                raise Exception(f"AI API timeout for word: {word}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"AI API error {e.response.status_code} for word: {word}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in AI response for word: {word} - {str(e)}")
            except KeyError as e:
                raise Exception(f"Missing 'response' field in AI API response for word: {word}")
            except Exception as e:
                raise Exception(f"AI API call failed for word: {word} - {str(e)}")
            
        # Add this after getting the response but before parsing
        print(f"=== DEBUG: Raw AI Response ===")
        print(f"Status: {response.status_code}")
        print(f"Full response: {response.text}")
        print(f"=== END DEBUG ===")

        full_response = response.json()
        response_content = full_response["response"]

        print(f"=== DEBUG: Response Content ===")
        print(f"Response content: '{response_content}'")
        print(f"Content type: {type(response_content)}")
        print(f"Content length: {len(response_content) if response_content else 'None'}")
        print(f"=== END DEBUG ===")
    
    @staticmethod
    async def process_word_async(word_id: int, word_data: WordCreate, request_id: str):
        """Process a single word through AI + translation pipeline with context support"""
        try:
            # Update status to processing
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pending_words 
                    SET processing_status = 'processing' 
                    WHERE id = ?
                """, (word_id,))
                conn.commit()
            
            # Step 1: Call AI API to get German sentence and plural (with context and article detection)
            ai_response = await AIService.call_ai_api(
                word_data.word, 
                word_data.context_sentence,
                word_data.needs_article
            )
            
            # Step 2: Translate German sentence to English
            nl_sentence = await TranslationService.translate_text(
                ai_response.tl_sentence, "en"
            )
            
            # Step 3: Translate the word itself to English
            nl_word = await TranslationService.translate_text(
                word_data.word, "en"
            )
            
            # Step 4: Move to processed_words table
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert into processed_words
                cursor.execute("""
                    INSERT INTO processed_words 
                    (original_word, date, tl_word, nl_word, tl_sentence, nl_sentence, tl_plural)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    word_data.word, word_data.date,
                    ai_response.tl_word,  # tl_word (German word with/without article)
                    nl_word,              # nl_word (English word)
                    ai_response.tl_sentence,  # tl_sentence (German sentence)
                    nl_sentence,          # nl_sentence (English sentence)
                    ai_response.tl_plural # tl_plural (German plural)
                ))
                
                # Delete from pending_words
                cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
                conn.commit()
                
            context_info = f" (with context)" if word_data.context_sentence else ""
            print(f"Successfully processed word: {word_data.word}{context_info} (Request: {request_id})")
            
        except Exception as e:
            # Update status to failed
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE pending_words 
                    SET processing_status = 'failed' 
                    WHERE id = ?
                """, (word_id,))
                conn.commit()
            
            context_info = f" (with context)" if word_data.context_sentence else ""
            print(f"Failed to process word: {word_data.word}{context_info} - {str(e)} (Request: {request_id})")
    
    @staticmethod
    async def process_word_list_async(word_ids: List[int], word_list: List[WordCreate], request_id: str):
        """Process multiple words asynchronously with concurrency control and context support"""
        # Limit concurrent processing to prevent overwhelming the AI/translation services
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent processes
        
        async def process_single_word_with_semaphore(word_id: int, word_data: WordCreate):
            async with semaphore:
                await AIService.process_word_async(word_id, word_data, request_id)
        
        # Create tasks for all words
        tasks = [
            process_single_word_with_semaphore(word_id, word_data)
            for word_id, word_data in zip(word_ids, word_list)
        ]
        
        # Process all words concurrently (but limited by semaphore)
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"Batch processing completed for request: {request_id}")