"""
Nela AI & RAG (Retrieval Augmented Generation) API Router

Provides endpoints for:
- Document upload and indexing (background task)
- Query Nela AI with RAG using user's documents
- Document management and deletion
- Document status tracking
- Multi-tenant document isolation
"""

import os
import uuid
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any

from Config.DB.db import get_db_session
from App.models.Document_model import Document, DocumentStatus
from App.schema.Document_schema import QueryRequest, QueryResponse
from App.controllers.AI_controller import AIService
from App.controllers.User_controller import UserController, oauth2_scheme
from Config.Security.ai_rate_limits import check_rate_limit
from App.utils.file_manager import get_file_manager

router = APIRouter(tags=["AI & Document Management"])
ai_service = AIService()
file_manager = get_file_manager()


# --- BACKGROUND TASK: Process Document Asynchronously ---
async def process_document_background(
    doc_id: str,
    file_bytes: bytes,
    user_id: str,
    filename: str,
) -> None:
    """
    Background task to chunk and index document in ChromaDB.
    
    The file has ALREADY been saved to disk in the main handler.
    This background task only handles:
    1. Mark document as "processing" in database
    2. Call AIService.add_document() to chunk and index
    3. Update document with chroma_id and mark as "completed"
    4. On error: Mark as "failed" with error message
    """
    from Config.DB.db import AsyncSessionLocal
    
    log_file = "/tmp/background_task_debug.log"
    
    def log(msg):
        print(msg, flush=True)
        try:
            with open(log_file, 'a') as f:
                f.write(msg + "\n")
                f.flush()
        except Exception as e:
            print(f"Failed to write to log: {e}", flush=True)
    
    log(f"\n🔄 [BACKGROUND TASK] Starting indexing: {doc_id}")
    log(f"   User: {user_id}, File: {filename}, Size: {len(file_bytes)} bytes\n")
    
    try:
        # Create a new async session for this background task
        log(f"💾 [STEP 1] Updating database status to PROCESSING...")
        async with AsyncSessionLocal() as db:
            # Mark as processing
            doc = await db.get(Document, uuid.UUID(doc_id))
            if doc:
                doc.status = DocumentStatus.PROCESSING
                await db.commit()
                log(f"✅ [STEP 1] Document marked as PROCESSING\n")
            else:
                log(f"⚠️  [STEP 1] Document not found in database!\n")
            
            # Index document in ChromaDB (chunks and embeds)
            log(f"🤖 [STEP 2] Indexing in ChromaDB...")
            index_result = await ai_service.add_document(
                file_bytes=file_bytes,
                user_id=user_id,
                filename=filename
            )
            log(f"✅ [STEP 2] Indexed with chroma_id: {index_result.get('chroma_id')}\n")
            
            # Update document with chroma_id and mark as completed
            log(f"💾 [STEP 3] Marking document as COMPLETED...")
            doc = await db.get(Document, uuid.UUID(doc_id))
            if doc:
                doc.chroma_id = index_result.get("chroma_id")
                doc.status = DocumentStatus.COMPLETED
                doc.error_message = None
                await db.commit()
                log(f"✅ [STEP 3] Document marked as COMPLETED\n")
            
        log(f"✅ [BACKGROUND TASK] Finished indexing: {doc_id}\n")
                
    except Exception as e:
        log(f"\n❌ [ERROR] Background task failed: {str(e)}\n")
        import traceback
        log(traceback.format_exc())
        
        # On error, mark document as failed
        try:
            async with AsyncSessionLocal() as db:
                doc = await db.get(Document, uuid.UUID(doc_id))
                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(e)[:500]  # Truncate to 500 chars
                    await db.commit()
                    log(f"💾 [ERROR] Document marked as FAILED\n")
        except Exception as db_error:
            log(f"⚠️  [ERROR] Could not update DB with error: {str(db_error)}\n")


# --- DEPENDENCY: Get Current Authenticated User ---
async def get_authenticated_user(
    db: AsyncSession = Depends(get_db_session),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """
    Dependency to inject the authenticated user.
    Uses Any type to avoid Pydantic validation errors with SQLAlchemy models.
    """
    return await UserController.get_current_user(db, token)


# ============================================================================
# DOCUMENT MANAGEMENT ENDPOINTS
# ============================================================================


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload Document (Async)",
    description="Upload a document to be indexed asynchronously for AI queries",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.txt, .pdf, .md)"),
    user: Annotated[Any, Depends(get_authenticated_user)] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Upload and index a document asynchronously.
    
    **IMPORTANT**: This endpoint returns IMMEDIATELY (202 Accepted) with a task_id.
    The document is processed in the background.
    
    Supported formats: .txt, .pdf, .md
    
    **Protected**: Requires authentication.
    
    The document is:
    1. Stored in database with status="pending"
    2. Asynchronously chunked and indexed in ChromaDB
    3. Status updated to "completed" when ready
    4. Can be queried once status="completed"
    
    Use GET /api/v1/ai/documents/{doc_id}/status to check processing status.
    """
    # Validate file type
    if not file.filename.endswith((".txt", ".pdf", ".md")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Supported: .txt, .pdf, .md",
        )

    try:
        # Read file content as bytes
        file_bytes = await file.read()
        
        # Create document record with status="pending"
        new_doc = Document(
            title=file.filename,
            filename=file.filename,
            chroma_id=None,  # Will be set after processing
            status=DocumentStatus.PENDING,
            user_id=user.id,
        )
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)
        
        # SAVE FILE IMMEDIATELY (don't wait for background task)
        file_path = file_manager.save_file(str(user.id), file.filename, file_bytes)
        print(f"✅ File saved immediately: {file_path}")
        
        # Update document with file path
        new_doc.file_path = file_path
        await db.commit()
        
        # Add background task to process the document
        # This will chunk, embed, and store in ChromaDB asynchronously
        if background_tasks:
            background_tasks.add_task(
                process_document_background,
                doc_id=str(new_doc.id),
                file_bytes=file_bytes,
                user_id=str(user.id),
                filename=file.filename,
            )
        else:
            # Fallback: create asyncio task if BackgroundTasks not available
            asyncio.create_task(
                process_document_background(
                    doc_id=str(new_doc.id),
                    file_bytes=file_bytes,
                    user_id=str(user.id),
                    filename=file.filename,
                )
            )
        
        # Build file path for reference
        upload_dir = file_manager.get_user_upload_dir(str(user.id))
        
        return {
            "message": "File upload accepted. Processing in background.",
            "task_id": str(new_doc.id),
            "filename": file.filename,
            "status": DocumentStatus.PENDING,
            "file_location": f"upload/{user.id}/{file.filename}",
            "storage_path": os.path.join(upload_dir, file.filename),
            "status_url": f"/api/v1/ai/documents/{new_doc.id}/status",
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@router.get(
    "/documents/{doc_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Check Document Status",
    description="Check the processing status of an uploaded document",
)
async def get_document_status(
    doc_id: uuid.UUID,
    user: Annotated[Any, Depends(get_authenticated_user)],
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Check the processing status of a document.
    
    **Protected**: Only the document owner can check status.
    
    Status values:
    - "pending": Waiting to be processed
    - "processing": Currently being chunked and indexed
    - "completed": Ready to be queried
    - "failed": Processing failed, check error_message
    
    Once status is "completed", the document can be queried via /api/v1/ai/prompt
    """
    # Fetch document from database
    doc = await db.get(Document, doc_id)
    
    # Security check: Ensure document exists and belongs to the user
    if not doc or doc.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    
    return {
        "doc_id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
        "error_message": doc.error_message,
        "ready_for_query": doc.status == DocumentStatus.COMPLETED,
    }


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Remove a document from the vector store and database",
)
async def delete_document(
    doc_id: uuid.UUID,
    user: Annotated[Any, Depends(get_authenticated_user)],
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Delete a document from ChromaDB and PostgreSQL.
    
    **Protected**: Only the document owner can delete.
    **Warning**: This action is permanent.
    """
    # Fetch document from database
    doc = await db.get(Document, doc_id)

    # Security check: Ensure document exists and belongs to the user
    if not doc or doc.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        # 1. Delete from ChromaDB (Vector Store) only if it was indexed
        if doc.chroma_id:
            await ai_service.delete_user_docs(str(user.id), doc.filename)

        # 2. Delete from PostgreSQL
        await db.delete(doc)
        await db.commit()

        return {"message": "Document and vectors deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}",
        )


# ============================================================================
# AI QUERY ENDPOINTS
# ============================================================================


@router.post(
    "/prompt",
    response_model=QueryResponse,
    summary="Ask Nela",
    description="Query Nela AI using RAG over user's documents",
)
async def ask_local_ai(
    request: QueryRequest,
    user: Annotated[Any, Depends(get_authenticated_user)],
    db: AsyncSession = Depends(get_db_session),
) -> QueryResponse:
    """
    Chat with Nela - an AI agent that helps you chat with your documents.
    
    Uses Retrieval Augmented Generation (RAG) with memory to search your uploaded 
    documents and provide intelligent answers. Nela remembers previous conversations!
    
    **Protected**: Requires authentication.
    **Rate Limited**: Free tier limited to 3 prompts per minute.
    
    Returns:
    - answer: AI-generated response from Nela
    - sources: List of document filenames used for the answer
    """
    # Check rate limit for this user
    await check_rate_limit(user)

    # Use provided user_id if given (for testing), otherwise use authenticated user
    effective_user_id = request.user_id if request.user_id else str(user.id)
    
    # Get conversation context for memory
    from App.controllers.Conversation_controller import ConversationManager
    conv_manager = ConversationManager()
    conversation_context = await conv_manager.get_conversation_summary(db, user.id)
    
    # Query the AI service with RAG and memory
    result = await ai_service.query_ai(
        request.prompt, 
        effective_user_id,
        previous_context=conversation_context
    )
    
    # Save user's question to history
    try:
        await conv_manager.save_message(
            db, 
            user.id, 
            role="user", 
            content=request.prompt,
            sources=result.get("sources", [])
        )
        
        # Save AI's response to history
        await conv_manager.save_message(
            db,
            user.id,
            role="assistant",
            content=result.get("answer", ""),
            sources=result.get("sources", []),
            relevance_score=0.9  # Default score
        )
    except Exception as e:
        print(f"⚠️  Failed to save conversation history: {e}")
    
    return result


# ============================================================================
# FILE MANAGEMENT ENDPOINTS
# ============================================================================


@router.get(
    "/files",
    status_code=status.HTTP_200_OK,
    summary="List User's Uploaded Files",
    description="Get list of all files uploaded by the current user",
)
async def list_user_files(
    user: Annotated[Any, Depends(get_authenticated_user)],
) -> dict:
    """
    List all files uploaded by the current user.
    
    **Protected**: Only the user can list their own files.
    
    Returns:
    - file_count: Number of files uploaded
    - total_size_mb: Total storage used in MB
    - files: List of filenames
    - storage_location: Base directory where files are stored
    """
    storage_info = file_manager.get_user_storage_info(str(user.id))
    
    return {
        "file_count": storage_info["file_count"],
        "total_size_mb": storage_info["total_size_mb"],
        "files": storage_info["files"],
        "storage_location": f"upload/{user.id}/",
        "message": f"User has {storage_info['file_count']} files using {storage_info['total_size_mb']} MB"
    }


@router.get(
    "/storage/info",
    status_code=status.HTTP_200_OK,
    summary="Get Storage Information",
    description="Get detailed storage information for the current user",
)
async def get_storage_info(
    user: Annotated[Any, Depends(get_authenticated_user)],
) -> dict:
    """
    Get detailed storage information for the current user.
    
    **Protected**: Requires authentication.
    
    Returns detailed information about uploaded files:
    - user_id: The user's ID
    - file_count: Number of files
    - total_size_bytes: Total size in bytes
    - total_size_mb: Total size in megabytes
    - files: List of all filenames
    - upload_directory: Path to where files are stored
    """
    storage_info = file_manager.get_user_storage_info(str(user.id))
    
    return {
        **storage_info,
        "upload_directory": file_manager.get_user_upload_dir(str(user.id)),
    }


# ============================================================================
# CONVERSATION MEMORY ENDPOINTS
# ============================================================================


@router.get(
    "/conversation/history",
    status_code=status.HTTP_200_OK,
    summary="Get Conversation History",
    description="Retrieve the user's recent conversation history",
)
async def get_conversation_history(
    limit: int = 10,
    user: Annotated[Any, Depends(get_authenticated_user)] = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get the user's recent conversation history (remember me feature).
    
    **Protected**: Only the user can view their own conversation history.
    
    Returns:
    - message_count: Total number of messages in history
    - messages: List of recent messages with timestamps
    - conversation_context: Summary of recent conversations
    """
    from App.controllers.Conversation_controller import ConversationManager
    from sqlalchemy import select, desc
    from App.models.Conversation_model import Conversation
    
    conv_manager = ConversationManager()
    
    try:
        # Get recent messages
        query = select(Conversation).where(
            Conversation.user_id == user.id
        ).order_by(
            desc(Conversation.created_at)
        ).limit(limit)
        
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        # Format for response
        messages = []
        for conv in reversed(conversations):
            messages.append({
                "role": conv.role,
                "content": conv.content[:200] + "..." if len(conv.content) > 200 else conv.content,
                "timestamp": conv.created_at.isoformat(),
                "sources": json.loads(conv.context_sources) if conv.context_sources else []
            })
        
        # Get summary
        summary = await conv_manager.get_conversation_summary(db, user.id)
        
        return {
            "message_count": len(messages),
            "messages": messages,
            "conversation_context": summary,
            "message": f"Retrieved {len(messages)} recent messages"
        }
        
    except Exception as e:
        print(f"❌ Error retrieving conversation history: {e}")
        return {
            "message_count": 0,
            "messages": [],
            "conversation_context": "No conversation history",
            "error": str(e)
        }


@router.delete(
    "/conversation/clear",
    status_code=status.HTTP_200_OK,
    summary="Clear Conversation History",
    description="Clear all conversation history for the user",
)
async def clear_conversation_history(
    user: Annotated[Any, Depends(get_authenticated_user)] = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Clear all conversation history for the user.
    
    **Protected**: Only the user can clear their own history.
    
    This action cannot be undone.
    """
    from sqlalchemy import delete
    from App.models.Conversation_model import Conversation
    
    try:
        # Delete all conversations for this user
        stmt = delete(Conversation).where(Conversation.user_id == user.id)
        result = await db.execute(stmt)
        await db.commit()
        
        deleted_count = result.rowcount
        
        return {
            "message": f"Cleared {deleted_count} conversation messages",
            "deleted_count": deleted_count,
            "status": "success"
        }
        
    except Exception as e:
        await db.rollback()
        print(f"❌ Error clearing conversation history: {e}")
        return {
            "message": f"Error clearing history: {str(e)}",
            "status": "error"
        }
