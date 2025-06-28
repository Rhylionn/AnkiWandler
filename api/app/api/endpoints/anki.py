from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.auth.api_key import verify_api_key
from app.schemas.anki import (
    AnkiCard, AnkiCardList, 
    AnkiCardResponse, AnkiCardData
)
from app.services.anki_service import AnkiService

router = APIRouter(prefix="/anki", tags=["anki"])

@router.post("/cards", response_model=AnkiCardResponse)
async def push_anki_cards(card_list: AnkiCardList, api_key: str = Depends(verify_api_key)):
    """Push Anki cards at startup - stores individual card data with upsert functionality"""
    try:
        return AnkiService.store_anki_cards(card_list)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error storing Anki cards: {str(e)}"
        )

@router.get("/cards", response_model=List[AnkiCardData])
async def get_anki_cards(
    limit: Optional[int] = 1000,
    api_key: str = Depends(verify_api_key)
):
    """Get all stored Anki cards"""
    try:
        return AnkiService.get_all_anki_cards(limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving Anki cards: {str(e)}"
        )

@router.delete("/cards/clear_all")
async def clear_all_anki_cards(api_key: str = Depends(verify_api_key)):
    """Delete all Anki cards from the database"""
    try:
        result = AnkiService.clear_all_anki_cards()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing all Anki cards: {str(e)}"
        )