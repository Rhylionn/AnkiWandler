from fastapi import APIRouter
from app.api.endpoints import words, anki

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(words.router)
api_router.include_router(anki.router)