from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.router import api_router
from app.database.connection import init_database
from app.services.queue_service import queue_worker
from app.services.ai_service import AIService
from app.config.settings import settings

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
    """Create FastAPI application with enhanced word processing"""
    app = FastAPI(
        title="Enhanced Word Management API with Dictionary Integration",
        version="3.0.0",
        description="Enhanced API with German morphological dictionaries and Kaikki data integration"
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
        return {
            "message": "Enhanced Word Management API with Dictionary Integration", 
            "version": "3.0.0",
            "features": [
                "German morphological dictionary integration",
                "Kaikki plural data lookup",
                "Enhanced workflow processing",
                "Dictionary-first with AI fallback"
            ]
        }
    
    # Initialize everything on startup
    @app.on_event("startup")
    async def startup_event():
        print("🚀 Starting Enhanced Word Management API...")
        print("=" * 60)
        
        # Initialize database
        print("📊 Initializing database...")
        init_database()
        print("✅ Database ready")
        
        # Load AI model
        print("🤖 Loading AI model...")
        try:
            await AIService.initialize_model()
        except Exception as e:
            print(f"❌ AI model failed: {e}")
            print("⚠️ Continuing without AI model - some features may not work")
        
        # Start enhanced queue worker (which will initialize dictionaries)
        print("⚙️ Starting enhanced queue worker...")
        queue_worker.start()
        
        print("=" * 60)
        print("🎉 Enhanced Word Management API is ready!")
        print("📚 Dictionary Files Status:")
        morphology_exists = os.path.exists(settings.MORPHOLOGY_DICT_PATH)
        kaikki_exists = os.path.exists(settings.KAIKKI_DICT_PATH)
        print(f"   📖 Morphology: {'✅ Available' if morphology_exists else '❌ Missing'} ({settings.MORPHOLOGY_DICT_PATH})")
        print(f"   📚 Kaikki: {'✅ Available' if kaikki_exists else '❌ Missing'} ({settings.KAIKKI_DICT_PATH})")
        
        if not morphology_exists or not kaikki_exists:
            print("⚠️  Some dictionary files are missing!")
            print("💡 Place files in data/ directory for full functionality")
        
        print("=" * 60)
    
    # Stop services on shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        print("🛑 Shutting down Enhanced Word Management API...")
        queue_worker.stop()
        print("✅ Shutdown complete")
        print("=" * 60)
    
    return app

app = create_application()