# app/api/endpoints/words.py
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from app.auth.api_key import verify_api_key
from app.schemas.word import (
    WordCreate, WordListCreate, WordListResponse, 
    PendingWordResponse, ProcessedWordResponse
)
from app.services.word_service import WordService
from app.services.queue_service import queue_worker
import os

router = APIRouter(prefix="/words", tags=["words"])

@router.post("/add", response_model=dict)
async def add_word(word_data: WordCreate, api_key: str = Depends(verify_api_key)):
    """Add a single word to the enhanced processing queue"""
    try:
        return WordService.add_word(word_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding word: {str(e)}"
        )

@router.post("/add_list", response_model=WordListResponse)
async def add_word_list(word_list_data: WordListCreate, api_key: str = Depends(verify_api_key)):
    """Add multiple words to the enhanced processing queue"""
    try:
        result = WordService.add_word_list(word_list_data)
        return WordListResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding word list: {str(e)}"
        )

@router.get("/pending", response_model=List[PendingWordResponse])
async def get_pending_words(
    limit: Optional[int] = 100,
    api_key: str = Depends(verify_api_key)
):
    """Get all pending words (waiting for enhanced AI + dictionary processing)"""
    try:
        return WordService.get_pending_words(limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pending words: {str(e)}"
        )

@router.get("/processed", response_model=List[ProcessedWordResponse])
async def get_processed_words(
    limit: Optional[int] = 100,
    api_key: str = Depends(verify_api_key)
):
    """Get all processed words (completed enhanced AI + dictionary processing)"""
    try:
        return WordService.get_processed_words(limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving processed words: {str(e)}"
        )

@router.get("/queue/status")
async def get_queue_status(api_key: str = Depends(verify_api_key)):
    """Get current enhanced queue processing status"""
    try:
        return queue_worker.get_queue_status()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue status: {str(e)}"
        )

@router.get("/workflow/status")
async def get_workflow_status(api_key: str = Depends(verify_api_key)):
    """Get enhanced workflow and dictionary status"""
    try:
        # Check dictionary file availability
        morphology_exists = os.path.exists("data/DE_morph_dict.txt")
        kaikki_exists = os.path.exists("data/kaikki.org-dictionary-German.jsonl")
        
        # Get queue status
        queue_status = queue_worker.get_queue_status()
        
        return {
            "workflow_version": "3.0.0",
            "enhanced_workflow_active": True,
            "dictionary_integration": {
                "morphology_dict_available": morphology_exists,
                "morphology_dict_path": "data/DE_morph_dict.txt",
                "kaikki_dict_available": kaikki_exists,
                "kaikki_dict_path": "data/kaikki.org-dictionary-German.jsonl",
                "cache_rebuilds_on_restart": True
            },
            "processing_workflow": {
                "step_1": "Check if word has article",
                "step_2a_noun_with_article": "Get plural from Kaikki → AI fallback → Generate sentence → Translate",
                "step_2b_noun_without_article": "Determine type → Get article from dict/AI → Follow noun path",
                "step_2c_non_noun": "Generate sentence → Translate",
                "dictionary_first": True,
                "ai_fallback": True
            },
            "queue_status": queue_status
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting workflow status: {str(e)}"
        )

@router.post("/queue/retry")
async def retry_queue(api_key: str = Depends(verify_api_key)):
    """Retry failed words in the enhanced queue"""
    try:
        return queue_worker.retry_failed_words()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrying queue: {str(e)}"
        )

@router.delete("/pending/{word_id}")
async def delete_pending_word(word_id: int, api_key: str = Depends(verify_api_key)):
    """Delete a pending word from the database"""
    try:
        result = WordService.delete_pending_word(word_id)
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting pending word: {str(e)}"
        )

@router.delete("/processed/clear_all")
async def clear_all_processed_words(api_key: str = Depends(verify_api_key)):
    """Delete all processed words from the database"""
    try:
        result = WordService.clear_all_processed_words()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing all processed words: {str(e)}"
        )

@router.delete("/processed/{word_id}")
async def delete_processed_word(word_id: int, api_key: str = Depends(verify_api_key)):
    """Delete a processed word from the database"""
    try:
        result = WordService.delete_processed_word(word_id)
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting processed word: {str(e)}"
        )