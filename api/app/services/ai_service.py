# app/services/ai_service.py
import asyncio
import httpx
import json
from typing import Optional, Dict
from app.schemas.word import WordCreate
from app.database.connection import get_db_connection
from app.config.settings import settings
from app.services.translation_service import TranslationService
from app.services.dictionary_service import GermanDictionaryService

class AIService:
    """Enhanced AI service with dictionary integration - the main word processing service"""
    
    # Enhanced prompt templates for new workflow
    PROMPTS = {
        "article_generation": """Generate the correct German definite article for the noun.

Input:
- target_word = {word}{context_info}

Output (JSON only, no markdown):
{{
  "article": "der/die/das"
}}

Instructions:
- Determine the correct definite article (der, die, das) for the German noun
- Use context if provided to help determine the correct article
- Output only valid JSON""",

        "plural_generation": """Generate the correct German plural form.

Input:
- target_word = {word}{context_info}

Output (JSON only, no markdown):
{{
  "plural": "<plural form>"
}}

Instructions:
- Generate the correct German plural form for the given word with article
- Use standard German pluralization rules
- Output only valid JSON""",

        "sentence_generation": """Generate a German sentence using the given word.

Input:
- target_word = {word}
- word_type = {word_type}{context_info}

Output (JSON only, no markdown):
{{
  "sentence": "<German sentence>"
}}

Instructions:
- Generate an A1-level German sentence using the target word
- Sentence must be grammatically correct
- Use word appropriately based on its type (noun, verb, adjective, etc.)
- Output only valid JSON"""
    }
    
    def __init__(self):
        self.dictionary = GermanDictionaryService()
        
    async def initialize(self):
        """Initialize dictionary services"""
        return await self.dictionary.initialize()
    
    @staticmethod
    async def initialize_model():
        """Load the AI model on startup"""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                payload = {"model": "qwen2.5-optimized"}
                
                response = await client.post(settings.AI_API_URL, json=payload)
                response.raise_for_status()
                
                print("✅ AI model loaded")
                return True
                
        except Exception as e:
            print(f"❌ AI model failed: {str(e)}")
            raise e
    
    @staticmethod
    async def _make_ai_request(prompt: str, response_model: type, timeout: int = None):
        """Unified AI API call method with configurable timeout"""
        if timeout is None:
            timeout = settings.AI_API_TIMEOUT
        
        async with httpx.AsyncClient(timeout=timeout) as client:
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
                raise Exception(f"AI API timeout after {timeout}s")
            except httpx.HTTPStatusError as e:
                raise Exception(f"AI API HTTP error {e.response.status_code}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in AI response: {str(e)}")
            except KeyError:
                raise Exception(f"Missing 'response' field in AI API response")
            except Exception as e:
                raise Exception(f"AI API call failed: {str(e)}")
    
    @staticmethod
    def _format_prompt(template_key: str, word: str, context_sentence: Optional[str] = None, 
                      word_type: Optional[str] = None) -> str:
        """Format prompt template with provided parameters"""
        template = AIService.PROMPTS[template_key]
        
        # Prepare context info for consistent formatting
        context_info = f"\n- context_sentence = {context_sentence}" if context_sentence else ""
        
        # Prepare format parameters
        format_params = {
            "word": word,
            "context_info": context_info
        }
        
        # Add word_type for sentence generation
        if template_key == "sentence_generation" and word_type:
            format_params["word_type"] = word_type
        
        return template.format(**format_params)
    
    @staticmethod
    async def generate_article(word: str, context_sentence: Optional[str] = None) -> str:
        """Generate article using AI"""
        from pydantic import BaseModel
        
        class ArticleResponse(BaseModel):
            article: str
        
        prompt = AIService._format_prompt("article_generation", word, context_sentence)
        response = await AIService._make_ai_request(prompt, ArticleResponse, timeout=settings.AI_API_TIMEOUT)
        return response.article
    
    @staticmethod
    async def generate_plural(word_with_article: str, context_sentence: Optional[str] = None) -> str:
        """Generate plural using AI"""
        from pydantic import BaseModel
        
        class PluralResponse(BaseModel):
            plural: str
        
        prompt = AIService._format_prompt("plural_generation", word_with_article, context_sentence)
        response = await AIService._make_ai_request(prompt, PluralResponse, timeout=settings.AI_API_TIMEOUT)
        return response.plural
    
    @staticmethod
    async def generate_sentence(word: str, word_type: str, context_sentence: Optional[str] = None) -> str:
        """Generate sentence using AI"""
        from pydantic import BaseModel
        
        class SentenceResponse(BaseModel):
            sentence: str
        
        prompt = AIService._format_prompt("sentence_generation", word, context_sentence, word_type)
        response = await AIService._make_ai_request(prompt, SentenceResponse, timeout=settings.AI_API_TIMEOUT)
        return response.sentence
    
    async def process_word_enhanced(self, word_id: int, word_data: WordCreate, request_id: str) -> Dict:
        """
        Enhanced word processing following the workflow diagram strictly
        """
        word = word_data.word
        context = word_data.context_sentence
        needs_article = word_data.needs_article
        
        processing_log = []
        processing_log.append(f"Processing: {word}")
        
        # Check if word has article already
        parts = word.strip().split()
        has_article = len(parts) == 2 and parts[0].lower() in ['der', 'die', 'das']
        
        if has_article:
            # Word already has article - extract it
            article, clean_word = parts
            processing_log.append(f"Has article: {article}")
            
            # Follow the noun path directly
            result = await self._process_noun_path(clean_word, article, context, processing_log)
            
        else:
            # Word without article - determine type first
            processing_log.append("No article - checking type")
            
            word_type = await self.dictionary.determine_word_type(word)
            
            if word_type == 'noun':
                # Check if word is already plural
                is_plural = await self.dictionary.is_word_plural(word)
                if is_plural:
                    processing_log.append("Type: noun (already plural)")
                    result = await self._process_plural_noun(word, context, processing_log)
                else:
                    processing_log.append("Type: noun (singular)")
                    result = await self._process_noun_without_article(word, context, needs_article, processing_log)
            else:
                processing_log.append(f"Type: {word_type or 'unknown'}")
                result = await self._process_non_noun_path(word, word_type, context, processing_log)
        
        # Save to database
        await self._save_processed_word_enhanced(word_id, word_data, result, processing_log, request_id)
        
        return result
    
    async def _process_noun_path(self, word: str, article: str, context: Optional[str], processing_log: list) -> Dict:
        """Process noun with known article"""
        
        # Get plural using enhanced strategy
        word_with_article = f"{article} {word}"
        plural = await self.dictionary.get_plural_advanced(word_with_article)
        
        if plural:
            processing_log.append(f"Found plural: {plural}")
        else:
            processing_log.append("No plural found, generating with AI")
            plural = await AIService.generate_plural(word_with_article, context)
            processing_log.append(f"AI generated: {plural}")
        
        # Generate sentence
        processing_log.append("Generating sentence")
        sentence = await AIService.generate_sentence(word_with_article, "noun", context)
        
        # Generate translation
        processing_log.append("Translating")
        translation = await TranslationService.translate_text(sentence)
        # Use complete word with article for better translation accuracy
        word_translation = await TranslationService.translate_text(word_with_article)
        
        return {
            'tl_word': word_with_article,
            'tl_sentence': sentence,
            'nl_word': word_translation,
            'nl_sentence': translation,
            'tl_plural': plural,
            'word_type': 'noun',
            'processing_path': 'noun_with_article'
        }
    
    async def _process_plural_noun(self, word: str, context: Optional[str], processing_log: list) -> Dict:
        """Process noun that is already plural - no need to find plural form"""
        
        processing_log.append("Word is already plural - skipping plural lookup")
        
        # Generate sentence
        processing_log.append("Generating sentence")
        sentence = await AIService.generate_sentence(word, "noun", context)
        
        # Generate translation
        processing_log.append("Translating")
        translation = await TranslationService.translate_text(sentence)
        word_translation = await TranslationService.translate_text(word)
        
        return {
            'tl_word': word,
            'tl_sentence': sentence,
            'nl_word': word_translation,
            'nl_sentence': translation,
            'tl_plural': None,  # Already plural, no need for plural form
            'word_type': 'noun',
            'processing_path': 'plural_noun'
        }
    
    async def _process_noun_without_article(self, word: str, context: Optional[str], needs_article: bool, processing_log: list) -> Dict:
        """Process noun without article - always try to get article for nouns"""
        
        # For nouns, ALWAYS try to get the article (regardless of needs_article flag)
        processing_log.append("Noun detected - finding article")
        
        # Try to get article from dictionary
        article = await self.dictionary.get_article_for_noun(word)
        
        if article:
            processing_log.append(f"Found article: {article}")
            # Continue with noun path with the found article
            return await self._process_noun_path(word, article, context, processing_log)
        else:
            processing_log.append("No article found, generating with AI")
            article = await AIService.generate_article(word, context)
            processing_log.append(f"AI generated: {article}")
            # Continue with noun path with the AI-generated article
            return await self._process_noun_path(word, article, context, processing_log)
    
    async def _process_non_noun_path(self, word: str, word_type: Optional[str], context: Optional[str], processing_log: list) -> Dict:
        """Process non-noun words - generate sentence directly"""
        
        # Generate sentence
        processing_log.append("Generating sentence")
        sentence = await AIService.generate_sentence(word, word_type or "unknown", context)
        
        # Generate translation
        processing_log.append("Translating")
        translation = await TranslationService.translate_text(sentence)
        word_translation = await TranslationService.translate_text(word)
        
        return {
            'tl_word': word,
            'tl_sentence': sentence,
            'nl_word': word_translation,
            'nl_sentence': translation,
            'tl_plural': None,
            'word_type': word_type or 'unknown',
            'processing_path': 'non_noun'
        }
    
    async def _save_processed_word_enhanced(self, word_id: int, word_data: WordCreate, result: Dict, processing_log: list, request_id: str):
        """Save processed word to database"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert into processed_words
                cursor.execute("""
                    INSERT INTO processed_words 
                    (original_word, date, tl_word, nl_word, tl_sentence, nl_sentence, tl_plural)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    word_data.word, 
                    word_data.date, 
                    result['tl_word'], 
                    result['nl_word'], 
                    result['tl_sentence'], 
                    result['nl_sentence'], 
                    result['tl_plural']
                ))
                
                # Remove from pending_words
                cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
                
                conn.commit()
            
            # Enhanced verbose logging for processed words
            path_summary = " → ".join(processing_log)
            print(f"✅ PROCESSED: {word_data.word}")
            print(f"   📍 Path: {result['processing_path']}")
            print(f"   🔄 Steps: {path_summary}")
            print(f"   📝 Result:")
            print(f"      German: {result['tl_word']}")
            print(f"      English: {result['nl_word']}")
            if result['tl_plural']:
                print(f"      Plural: {result['tl_plural']}")
            print(f"      Sentence (DE): {result['tl_sentence']}")
            print(f"      Sentence (EN): {result['nl_sentence']}")
            print(f"   ⏱️  Request: {request_id}")
            print("-" * 60)
            
        except Exception as e:
            print(f"❌ SAVE FAILED: {word_data.word}")
            print(f"   Error: {str(e)}")
            print("-" * 60)
            raise e