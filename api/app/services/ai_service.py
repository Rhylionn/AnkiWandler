# app/services/ai_service.py
import httpx
import json
from typing import Optional
from pydantic import BaseModel
from app.config.settings import settings

class ArticleResponse(BaseModel):
    article: str

class PluralResponse(BaseModel):
    plural: str

class SentenceResponse(BaseModel):
    sentence: str

class AIService:
    """AI service with enhanced accuracy-focused prompts"""
    
    ARTICLE_PROMPT = """You are a German language expert. Your task is to determine the correct German definite article for a noun.

Input:
- target_word = {word}{context_info}

Rules:
- Masculine nouns = der
- Feminine nouns = die
- Neuter nouns = das

Task:
Generate the correct definite article for the given German noun based on its grammatical gender.

If context_sentence is provided, analyze how the noun is used in that sentence to determine its grammatical gender and select the appropriate article.

Examples:
- Hund → der
- Katze → die
- Haus → das
- Auto → das
- Frau → die
- Mann → der

Output (JSON only):
{{
  "article": "der" | "die" | "das"
}}"""

    PLURAL_PROMPT = """You are a German language expert. Your task is to generate the correct German plural form.

Input:
- target_word = {word}{context_info}

Task:
Generate the complete plural form (definite article + plural noun) for the given German word with article.

If context_sentence is provided, analyze how the noun is used in that sentence to understand its meaning and ensure you generate the correct plural form for that specific usage.

Examples:
- der Hund → die Hunde
- das Haus → die Häuser
- die Katze → die Katzen
- das Auto → die Autos
- der Lehrer → die Lehrer

Output (JSON only):
{{
  "plural": "<complete plural form>"
}}"""

    SENTENCE_PROMPT = """You are a German language expert. Your task is to create a grammatically correct German sentence.

Input:
- target_word = {word}

Task:
Create one simple, grammatically correct German sentence that uses the target word appropriately.

CRITICAL: If the target word includes an article (der/die/das + noun), you must use the word with the meaning that matches that specific article. Do not mix articles with wrong meanings.

Requirements:
- Use beginner-level German (A1/A2)
- Ensure perfect grammar
- Keep the sentence simple and natural
- Match the word meaning to its article correctly
- Use the word naturally in context

Output (JSON only):
{{
  "sentence": "<German sentence>"
}}"""
    
    @staticmethod
    async def initialize_model():
        """Initialize AI model on startup"""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                settings.AI_API_URL, 
                json={"model": "qwen2.5-optimized"}
            )
            response.raise_for_status()
            print("✅ AI model loaded")
    
    @staticmethod
    async def _make_request(prompt: str, response_model: type) -> BaseModel:
        """Make AI API request and parse response"""
        async with httpx.AsyncClient(timeout=settings.AI_API_TIMEOUT) as client:
            payload = {
                "model": "qwen2.5-optimized",
                "prompt": prompt,
                "stream": False
            }
            
            try:
                response = await client.post(settings.AI_API_URL, json=payload)
                response.raise_for_status()
                
                full_response = response.json()
                response_content = full_response["response"]
                ai_data = json.loads(response_content)
                
                return response_model(**ai_data)
                
            except httpx.TimeoutException:
                raise Exception(f"AI API timeout after {settings.AI_API_TIMEOUT}s")
            except httpx.HTTPStatusError as e:
                raise Exception(f"AI API HTTP error {e.response.status_code}")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in AI response: {str(e)}")
            except KeyError:
                raise Exception(f"Missing 'response' field in AI API response")
            except Exception as e:
                raise Exception(f"AI API call failed: {str(e)}")
    
    @staticmethod
    async def generate_article(word: str, context_sentence: Optional[str] = None) -> str:
        """Generate German article for noun"""
        context_info = f"\n- context_sentence = {context_sentence}" if context_sentence else ""
        prompt = AIService.ARTICLE_PROMPT.format(word=word, context_info=context_info)
        
        print(f"      🤖 AI ARTICLE: '{word}' | Context: {bool(context_sentence)}")
        
        response = await AIService._make_request(prompt, ArticleResponse)
        
        print(f"         ✅ Result: '{response.article}'")
        return response.article
    
    @staticmethod
    async def generate_plural(word_with_article: str, context_sentence: Optional[str] = None) -> str:
        """Generate German plural form"""
        context_info = f"\n- context_sentence = {context_sentence}" if context_sentence else ""
        prompt = AIService.PLURAL_PROMPT.format(word=word_with_article, context_info=context_info)
        
        print(f"      🤖 AI PLURAL: '{word_with_article}' | Context: {bool(context_sentence)}")
        
        response = await AIService._make_request(prompt, PluralResponse)
        
        print(f"         ✅ Result: '{response.plural}'")
        return response.plural
    
    @staticmethod
    async def generate_sentence(word: str) -> str:
        """Generate German sentence using word"""
        prompt = AIService.SENTENCE_PROMPT.format(word=word)
        
        print(f"      🤖 AI SENTENCE: '{word}'")
        
        response = await AIService._make_request(prompt, SentenceResponse)
        
        print(f"         ✅ Result: '{response.sentence}'")
        return response.sentence