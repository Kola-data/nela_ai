"""
Conversation Manager - Handles chat history and memory
Allows AI to remember previous conversations and context
"""

import json
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from App.models.Conversation_model import Conversation, ConversationSession
import uuid


class ConversationManager:
    """Manages conversation history and session context"""
    
    def __init__(self):
        pass
    
    async def save_message(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        role: str,
        content: str,
        session_id: Optional[uuid.UUID] = None,
        sources: Optional[List[str]] = None,
        relevance_score: Optional[float] = None,
    ) -> Conversation:
        """Save a message to conversation history"""
        try:
            conversation = Conversation(
                user_id=user_id,
                role=role,
                content=content,
                context_sources=json.dumps(sources) if sources else None,
                relevance_score=relevance_score,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            return conversation
        except Exception as e:
            await db.rollback()
            print(f"❌ Error saving message: {e}")
            raise
    
    async def get_recent_context(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 5,
    ) -> List[Conversation]:
        """Get recent conversation messages for context"""
        try:
            query = select(Conversation).where(
                Conversation.user_id == user_id
            ).order_by(
                desc(Conversation.created_at)
            ).limit(limit)
            
            result = await db.execute(query)
            conversations = result.scalars().all()
            # Reverse to get chronological order
            return list(reversed(conversations))
        except Exception as e:
            print(f"❌ Error retrieving context: {e}")
            return []
    
    async def get_conversation_summary(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> str:
        """Get summary of recent conversations for prompt context"""
        conversations = await self.get_recent_context(db, user_id, limit=3)
        
        if not conversations:
            return "No previous conversation context."
        
        summary_parts = ["Recent conversation context:"]
        for conv in conversations:
            role_label = "You" if conv.role == "user" else "Assistant"
            # Truncate long messages
            content = conv.content[:100] + "..." if len(conv.content) > 100 else conv.content
            summary_parts.append(f"- {role_label}: {content}")
        
        return "\n".join(summary_parts)
    
    async def create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ConversationSession:
        """Create a new conversation session"""
        try:
            session = ConversationSession(
                user_id=user_id,
                title=title,
                description=description,
                message_count=0,
                is_active=True,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return session
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating session: {e}")
            raise
    
    async def get_active_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> Optional[ConversationSession]:
        """Get the user's active conversation session"""
        try:
            query = select(ConversationSession).where(
                (ConversationSession.user_id == user_id) &
                (ConversationSession.is_active == True)
            ).order_by(
                desc(ConversationSession.created_at)
            ).limit(1)
            
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"❌ Error getting active session: {e}")
            return None
