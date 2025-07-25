# app/services/translation_service.py
import httpx
from app.config.settings import settings

class TranslationService:
    @staticmethod
    async def translate_text(text: str) -> str:
        """Translate German text to configured target language using DeepL API"""
        # Get target language from settings
        target_lang = settings.TRANSLATION_TARGET_LANGUAGE
        
        async with httpx.AsyncClient(timeout=settings.TRANSLATION_API_TIMEOUT) as client:
            payload = {
                "text": [text],
                "source_lang": "DE", 
                "target_lang": target_lang
            }
            
            headers = {}
            if settings.TRANSLATION_API_KEY:
                headers["Authorization"] = f"DeepL-Auth-Key {settings.TRANSLATION_API_KEY}"
            
            try:
                response = await client.post(
                    settings.TRANSLATION_API_URL, 
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                return data["translations"][0]["text"]
                
            except httpx.TimeoutException:
                raise Exception(f"Translation timeout for text: {text}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"Translation API error {e.response.status_code} for text: {text}")
            except Exception as e:
                raise Exception(f"Translation failed for text: {text} - {str(e)}")