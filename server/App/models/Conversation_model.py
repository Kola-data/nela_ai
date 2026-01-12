"""
Conversation Model - Stores chat history for each user
Allows AI to remember previous conversations and context
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, text, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from Config.DB.db import Base

if TYPE_CHECKING:
    from .User_model import User


class Conversation(Base):
    """Stores individual messages in a conversation"""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True  # Index for faster lookups
    )
    
    # Message content
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)  # The actual message
    
    # For context awareness
    query_embedding_hash: Mapped[str] = mapped_column(String(64), nullable=True)  # Hash of query for caching
    context_sources: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string of source documents used
    relevance_score: Mapped[float] = mapped_column(Float, nullable=True)  # How relevant this message is
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()")
    )
    
    owner: Mapped["User"] = relationship("User", back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation(user_id={self.user_id}, role={self.role}, created_at={self.created_at})>"


class ConversationSession(Base):
    """Groups conversations into sessions for better organization"""
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=True)  # Optional session title
    description: Mapped[str] = mapped_column(Text, nullable=True)  # Optional description
    
    # Session tracking
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()")
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()")
    )
    
    ended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    owner: Mapped["User"] = relationship("User", back_populates="conversation_sessions")

    def __repr__(self) -> str:
        return f"<ConversationSession(user_id={self.user_id}, title={self.title})>"
