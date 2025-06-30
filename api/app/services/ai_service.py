import asyncio
import httpx
import json
from typing import List, Optional
from app.schemas.word import WordCreate, AIResponse, SimpleAIResponse, WordClassification
from app.database.connection import get_db_connection
from app.config.settings import settings
from app.services.translation_service import TranslationService

class AIService:
    """Centralized AI service with unified API calls and prompt management"""
    
    # Prompt templates
    PROMPTS = {
        "classification": """Determine if the German word is a noun.

Input:
- target_word = {word}{context_info}

Output (JSON only, no markdown):
{{
  "is_noun": true/false
}}

Instructions:
- Answer true if the word is a German noun
- Answer false if it's a verb, adjective, adverb, or other word type
- Use context if provided to help determine word type
- Output only valid JSON""",

        "noun": """You are a German-language assistant specializing in noun articles and A1-level sentence construction.

Input:
- target_word = {word}{context_info}
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
- Output only valid JSON""",

        "simple": """You are a German-language assistant specializing in A1-level sentence construction.

Input:
- target_word = {word}{context_info}

Task:
Generate one A1-level German sentence using the target_word.

Output (JSON only, no markdown):
{{
  "tl_sentence": "<German A1 sentence>"
}}

Requirements:
- Sentence must be A1-level German, grammatically correct
- Use target_word appropriately in the sentence (verb, adjective, adverb, etc.)
- If context is provided, ensure the word usage matches the context
- Output only valid JSON"""
    }
    
    @staticmethod
    async def _make_ai_request(prompt: str, response_model: type):
        """Unified AI API call method"""
        async with httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT) as client:
            payload = {
                "model": "qwen2.5-optimized", 
                "prompt": prompt,
                "stream": False
            }
            
            try:
                response = await client.post(settings.AI_API_URL, json=payload)
                response.raise_for_status()
                
                # Parse response
                full_response = response.json()
                response_content = full_response["response"]
                ai_data = json.loads(response_content)
                
                return response_model(**ai_data)
                
            except httpx.TimeoutException:
                raise Exception(f"AI API timeout")
            except httpx.HTTPStatusError as e:
                raise Exception(f"AI API error {e.response.status_code}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in AI response: {str(e)}")
            except KeyError:
                raise Exception(f"Missing 'response' field in AI API response")
            except Exception as e:
                raise Exception(f"AI API call failed: {str(e)}")
    
    @staticmethod
    def _format_prompt(template_key: str, word: str, context_sentence: Optional[str] = None, 
                      needs_article: Optional[bool] = None) -> str:
        """Format prompt template with provided parameters"""
        template = AIService.PROMPTS[template_key]
        
        # Prepare context info for consistent formatting
        context_info = f"\n- context_sentence = {context_sentence}" if context_sentence else ""
        
        # Prepare format parameters
        format_params = {
            "word": word,
            "context_info": context_info
        }
        
        # Add needs_article only for noun template
        if template_key == "noun" and needs_article is not None:
            format_params["needs_article"] = needs_article
        
        return template.format(**format_params)
    
    @staticmethod
    async def classify_word_type(word: str, context_sentence: Optional[str] = None) -> WordClassification:
        prompt = AIService._format_prompt("classification", word, context_sentence)
        return await AIService._make_ai_request(prompt, WordClassification)
    
    @staticmethod
    async def process_noun(word: str, context_sentence: Optional[str] = None, needs_article: bool = False) -> AIResponse:
        prompt = AIService._format_prompt("noun", word, context_sentence, needs_article=needs_article)
        return await AIService._make_ai_request(prompt, AIResponse)
    
    @staticmethod
    async def process_simple_word(word: str, context_sentence: Optional[str] = None) -> SimpleAIResponse:
        prompt = AIService._format_prompt("simple", word, context_sentence)
        return await AIService._make_ai_request(prompt, SimpleAIResponse)
    
    @staticmethod
    async def _update_word_status(word_id: int, status: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pending_words 
                SET processing_status = ? 
                WHERE id = ?
            """, (status, word_id))
            conn.commit()
    
    @staticmethod
    async def _save_processed_word(word_id: int, word_data: WordCreate, tl_word: str, tl_sentence: str, 
                                 nl_word: str, nl_sentence: str, tl_plural: Optional[str] = None):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Insert into processed_words
            cursor.execute("""
                INSERT INTO processed_words 
                (original_word, date, tl_word, nl_word, tl_sentence, nl_sentence, tl_plural)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                word_data.word, word_data.date, tl_word, nl_word, 
                tl_sentence, nl_sentence, tl_plural
            ))
            
            # Remove from pending_words
            cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
            
            conn.commit()
    
    @staticmethod
    async def process_word_async(word_id: int, word_data: WordCreate, request_id: str):
        """Process a single word through the complete AI + translation pipeline"""
        try:
            # Update status to processing
            await AIService._update_word_status(word_id, 'processing')
            
            # Step 1: Classify word type
            classification = await AIService.classify_word_type(
                word_data.word, word_data.context_sentence
            )
            
            # Step 2: Process based on word type
            if classification.is_noun:
                # Full noun processing
                ai_response = await AIService.process_noun(
                    word_data.word, word_data.context_sentence, word_data.needs_article
                )
                tl_word = ai_response.tl_word
                tl_sentence = ai_response.tl_sentence
                tl_plural = ai_response.tl_plural
                word_type = "noun"
            else:
                # Simple processing for non-nouns
                simple_response = await AIService.process_simple_word(
                    word_data.word, word_data.context_sentence
                )
                tl_word = word_data.word
                tl_sentence = simple_response.tl_sentence
                tl_plural = None
                word_type = "non-noun"
            
            # Step 3: Translate to English
            nl_sentence, nl_word = await asyncio.gather(
                TranslationService.translate_text(tl_sentence),
                TranslationService.translate_text(word_data.word)
            )
            
            # Step 4: Save processed word to database
            await AIService._save_processed_word(
                word_id, word_data, tl_word, tl_sentence, nl_word, nl_sentence, tl_plural
            )
            
            # Log success
            context_info = " (with context)" if word_data.context_sentence else ""
            print(f"✅ Processed {word_type}: {word_data.word}{context_info} (Request: {request_id})")
            
        except Exception as e:
            # Update status to failed
            await AIService._update_word_status(word_id, 'failed')
            
            # Log failure
            context_info = " (with context)" if word_data.context_sentence else ""
            print(f"❌ Failed to process: {word_data.word}{context_info} - {str(e)} (Request: {request_id})")
    
    @staticmethod
    async def process_word_list_async(word_ids: List[int], word_list: List[WordCreate], request_id: str):
        """Process multiple words concurrently with controlled concurrency"""
        # Limit concurrent processing
        semaphore = asyncio.Semaphore(3)
        
        async def process_with_semaphore(word_id: int, word_data: WordCreate):
            async with semaphore:
                await AIService.process_word_async(word_id, word_data, request_id)
        
        # Process all words concurrently
        tasks = [
            process_with_semaphore(word_id, word_data)
            for word_id, word_data in zip(word_ids, word_list)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"🎉 Batch processing completed for request: {request_id}")