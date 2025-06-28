from fastapi import APIRouter, HTTPException, Depends, status
from app.auth.api_key import verify_api_key
from app.schemas.word import AIRequest, LegacyAIResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/create_word", response_model=LegacyAIResponse)
async def create_word(ai_request: AIRequest, api_key: str = Depends(verify_api_key)):
    """Create a request to local AI for word processing (legacy endpoint)"""
    try:
        return AIService.create_ai_request(ai_request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating AI request: {str(e)}"
        )