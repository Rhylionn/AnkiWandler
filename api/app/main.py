from fastapi import FastAPI
from app.api.router import api_router
from app.database.connection import init_database

def create_application() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Word Management API with AI Processing",
        version="2.0.0",
        description="A structured API for managing words with AI processing and translation pipeline"
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/")
    async def root():
        return {"message": "Word Management API with AI Processing is running", "version": "2.0.0"}
    
    # Initialize database on startup
    @app.on_event("startup")
    async def startup_event():
        init_database()
    
    return app

app = create_application()