import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING # Added TYPE_CHECKING

from sqlalchemy import String, DateTime, text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from Config.DB.db import Base
from App.enums import UserTier

# This prevents Pylance/MyPy from seeing a circular import at runtime
if TYPE_CHECKING:
    from .Document_model import Document
    from .Conversation_model import Conversation, ConversationSession

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    tier: Mapped[UserTier] = mapped_column(Enum(UserTier), default=UserTier.FREE)

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

    # Use string "Document" here to avoid undefined variable error
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )

    # Conversation history - using string references to avoid circular imports
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", 
        foreign_keys="Conversation.user_id",
        back_populates="owner", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    conversation_sessions: Mapped[List["ConversationSession"]] = relationship(
        "ConversationSession",
        foreign_keys="ConversationSession.user_id",
        back_populates="owner", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username!r}, email={self.email!r})>"
