import asyncio
import httpx
import uuid
from datetime import datetime
from typing import List
from app.schemas.word import AIRequest, LegacyAIResponse, WordCreate, AIResponse
from app.database.connection import get_db_connection
from app.config.settings import settings
from app.services.translation_service import TranslationService

class AIService:
    @staticmethod
    def create_prompt(word: str) -> str:
        """Create AI prompt with the word (dummy implementation)"""
        return f"""
        Please analyze the German word "{word}" and provide:
        1. A natural German sentence using this word
        2. The plural form of this word (if applicable)
        
        Respond only in JSON format with the exact structure:
        {{
            "tl_sentence": "<German sentence>",
            "tl_plural": "<plural form of the word>"
        }}
        
        Word to analyze: {word}
        """
    
    @staticmethod
    async def call_ai_api(word: str) -> AIResponse:
        """Call external AI API to process a word"""
        async with httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT) as client:
            prompt = AIService.create_prompt(word)
            payload = {
                "model": "mistral-nemo",
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
    
    @staticmethod
    async def process_word_async(word_id: int, word_data: WordCreate, request_id: str):
        """Process a single word through AI + translation pipeline"""
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
            
            # Step 1: Call AI API to get German sentence and plural
            ai_response = await AIService.call_ai_api(word_data.word)
            
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
                    word_data.word,  # tl_word (German word)
                    nl_word,         # nl_word (English word)
                    ai_response.tl_sentence,  # tl_sentence (German sentence)
                    nl_sentence,     # nl_sentence (English sentence)
                    ai_response.tl_plural     # tl_plural (German plural)
                ))
                
                # Delete from pending_words
                cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
                conn.commit()
                
            print(f"Successfully processed word: {word_data.word} (Request: {request_id})")
            
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
            
            print(f"Failed to process word: {word_data.word} - {str(e)} (Request: {request_id})")
    
    @staticmethod
    async def process_word_list_async(word_ids: List[int], word_list: List[WordCreate], request_id: str):
        """Process multiple words asynchronously with concurrency control"""
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
    
    @staticmethod
    def create_ai_request(ai_request: AIRequest) -> LegacyAIResponse:
        """Create a request to local AI for word processing (legacy endpoint)"""
        request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return LegacyAIResponse(
            message="AI request created successfully",
            request_id=request_id,
            word=ai_request.word,
            context=ai_request.context,
            target_language=ai_request.target_language,
            status="pending",
            ai_endpoint=settings.AI_API_URL
        )