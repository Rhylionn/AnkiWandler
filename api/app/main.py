from fastapi import FastAPI
from app.api.router import api_router
from app.database.connection import init_database
from app.services.queue_service import queue_worker

def create_application() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Word Management API with AI Processing",
        version="2.1.0",
        description="A structured API for managing words with AI processing and translation pipeline"
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/")
    async def root():
        return {"message": "Word Management API with AI Processing is running", "version": "2.1.0"}
    
    # Initialize database and start queue worker on startup
    @app.on_event("startup")
    async def startup_event():
        init_database()
        queue_worker.start()
    
    # Stop queue worker on shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        queue_worker.stop()
    
    return app

app = create_application()