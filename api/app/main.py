from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.router import api_router
from app.database.connection import init_database
from app.services.queue_service import queue_worker

def get_cors_origins():
    """Automatically determine allowed origins based on environment"""
    
    # Check if we're in development (DEBUG mode)
    debug_mode = os.getenv("DEBUG", "True").lower() == "true"
    
    if debug_mode:
        # Development: Allow localhost on common ports
        return [
            "http://localhost:9090"
        ]
    else:
        # Production: Only allow your production domain
        prod_domain = os.getenv("PROD_DOMAIN")
        return [prod_domain]

def create_application() -> FastAPI:
    """Create FastAPI application with auto CORS"""
    app = FastAPI(
        title="Word Management API with AI Processing",
        version="2.1.0",
        description="A structured API for managing words with AI processing and translation pipeline"
    )
    
    # Add CORS middleware with automatic origin detection
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
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