import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from Config.DB.db import Base

if TYPE_CHECKING:
    from .User_model import User

class DocumentStatus:
    """Status enum for document processing"""
    PENDING = "pending"         # Waiting to be processed
    PROCESSING = "processing"   # Currently being chunked and indexed
    COMPLETED = "completed"     # Successfully indexed in ChromaDB
    FAILED = "failed"          # Processing failed

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4, 
        server_default=text("gen_random_uuid()")
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=True)  # Path to uploaded file: server/upload/{user_id}/{filename}
    chroma_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)  # Can be NULL until processing completes
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    error_message: Mapped[str] = mapped_column(String(500), nullable=True)  # Error details if status=failed

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
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

    # Use string "User" here
    owner: Mapped["User"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(title={self.title!r}, status={self.status}, user_id={self.user_id})>"
