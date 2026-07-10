from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import verify_api_key

# Import routes (to be created)
from app.api.routes import job_posts, interviews, matching, analysis, rag

app = FastAPI(
    title="GigBridge AI Service",
    description="Stand-alone Microservice providing NLP and AI intelligence to GigBridge platform.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exceptions
register_exception_handlers(app)

# Include routers (protected by default at API router inclusion level, or inside routes)
app.include_router(
    job_posts.router,
    prefix="/api/ai",
    tags=["Job Posts"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    interviews.router,
    prefix="/api/ai",
    tags=["AI Interviews"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    matching.router,
    prefix="/api/ai",
    tags=["Talent Matching"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    analysis.router,
    prefix="/api/ai",
    tags=["AI Analysis"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    rag.router,
    prefix="/api/ai",
    tags=["RAG Knowledge Base"],
    dependencies=[Depends(verify_api_key)]
)

@app.get("/health", tags=["Health"])
async def health_check():
    """Service health status endpoint"""
    return {
        "success": True,
        "message": "GigBridge AI Microservice is running.",
        "data": {
            "status": "healthy",
            "active_llm_provider": settings.DEFAULT_LLM_PROVIDER
        },
        "errors": []
    }
