import httpx
from app.schemas.word import TranslationRequest, TranslationResponse
from app.config.settings import settings

class TranslationService:
    @staticmethod
    async def translate_text(text: str, target_language: str = "en") -> str:
        """Translate text using external translation API"""
        async with httpx.AsyncClient(timeout=settings.TRANSLATION_API_TIMEOUT) as client:
            payload = {
              "text": [ text ],
              "source_lang": "DE",
              "target_lang": "FR"
            }
            
            # Add API key to headers if available
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
                
                import json
                data = json.loads(response.text)
                return data["translations"][0]["text"]
                
            except httpx.TimeoutException:
                raise Exception(f"Translation API timeout for text: {text}")
            except httpx.HTTPStatusError as e:
                raise Exception(f"Translation API error {e.response.status_code} for text: {text}")
            except Exception as e:
                raise Exception(f"Translation API call failed for text: {text} - {str(e)}")