# app/services/ai_service.py
import asyncio
import httpx
import json
from typing import Optional
from app.config.settings import settings

class AIService:
    """AI service - called by dictionary service when generation is needed"""
    
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
        
        print(f"      🤖 AI ARTICLE GENERATION:")
        print(f"         📝 Word: '{word}'")
        print(f"         📝 Context: {context_sentence if context_sentence else 'None'}")
        
        prompt = AIService._format_prompt("article_generation", word, context_sentence)
        print(f"         📋 Prompt length: {len(prompt)} characters")
        
        response = await AIService._make_ai_request(prompt, ArticleResponse, timeout=settings.AI_API_TIMEOUT)
        
        print(f"         ✅ AI Response: '{response.article}'")
        return response.article
    
    @staticmethod
    async def generate_plural(word_with_article: str, context_sentence: Optional[str] = None) -> str:
        """Generate plural using AI"""
        from pydantic import BaseModel
        
        class PluralResponse(BaseModel):
            plural: str
        
        print(f"      🤖 AI PLURAL GENERATION:")
        print(f"         📝 Word with article: '{word_with_article}'")
        print(f"         📝 Context: {context_sentence if context_sentence else 'None'}")
        
        prompt = AIService._format_prompt("plural_generation", word_with_article, context_sentence)
        print(f"         📋 Prompt length: {len(prompt)} characters")
        
        response = await AIService._make_ai_request(prompt, PluralResponse, timeout=settings.AI_API_TIMEOUT)
        
        print(f"         ✅ AI Response: '{response.plural}'")
        return response.plural
    
    @staticmethod
    async def generate_sentence(word: str, word_type: str, context_sentence: Optional[str] = None) -> str:
        """Generate sentence using AI"""
        from pydantic import BaseModel
        
        class SentenceResponse(BaseModel):
            sentence: str
        
        print(f"      🤖 AI SENTENCE GENERATION:")
        print(f"         📝 Word: '{word}'")
        print(f"         📝 Word type: '{word_type}'")
        print(f"         📝 Context: {context_sentence if context_sentence else 'None'}")
        
        prompt = AIService._format_prompt("sentence_generation", word, context_sentence, word_type)
        print(f"         📋 Prompt length: {len(prompt)} characters")
        
        response = await AIService._make_ai_request(prompt, SentenceResponse, timeout=settings.AI_API_TIMEOUT)
        
        print(f"         ✅ AI Response: '{response.sentence}'")
        return response.sentence