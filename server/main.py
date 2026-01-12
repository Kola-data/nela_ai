"""
Nela AI - Multi-Tenant AI Agent API Server

Created in 2026 by Bytelink Technologies to help their clients get responses from their documents.

An AI agent that helps users chat with their documents.

A FastAPI-based backend providing:
- Multi-tenant user management and authentication (JWT-based)
- RAG-powered AI queries with local LLM (Llama 3.2)
- Document creation, management, and indexing
- AI-powered document chat and analysis
- Rate limiting and access control
"""

import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables at the very top
load_dotenv()

# Import models first (ensures all relationships are registered)
from App.models.User_model import User
from App.models.Document_model import Document
from App.models.Conversation_model import Conversation, ConversationSession

# Import route handlers
from App.api.User_router import router as user_router
from App.api.AI_router import router as ai_router

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Nela AI - Multi-Tenant AI Agent API",
    description="An AI agent that helps users chat with their documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route Inclusion ---
# API v1 endpoints are prefixed with /api/v1 for versioning

app.include_router(user_router, prefix="/api/v1/users")

app.include_router(ai_router, prefix="/api/v1/ai")


# ============================================================================
# HEALTH CHECK
# ============================================================================


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Used for monitoring and load balancer checks.
    """
    return {
        "status": "online",
        "agent": "Nela",
        "version": "1.0.0",
        "created": "2026",
        "by": "Bytelink Technologies",
        "purpose": "Help clients get responses from their documents",
        "api_docs": "/docs",
        "redoc": "/redoc",
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    server_port = int(os.getenv("SERVER_PORT", 8001))
    
    # ✅ OPTIMIZATION: Production settings for better performance
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=server_port,
        reload=False,  # ✅ CRITICAL: Disable reload in production (huge slowdown)
        workers=4,     # ✅ Multiple workers for concurrent requests
        loop="uvloop", # ✅ Use uvloop for better async performance
        access_log=False,  # ✅ Disable access logging (reduces I/O)
    )

