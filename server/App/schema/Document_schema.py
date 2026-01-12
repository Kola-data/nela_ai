from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from App.enums import UserTier

# --- 1. USER SCHEMAS (Required for UserController) ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    tier: UserTier = UserTier.FREE

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    # All fields optional for dynamic updates
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    tier: Optional[UserTier] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    
    # Pydantic V2 replacement for orm_mode = True
    model_config = ConfigDict(from_attributes=True)

# --- 2. DOCUMENT SCHEMAS ---
class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class DocumentCreate(DocumentBase):
    filename: str

class DocumentResponse(DocumentBase):
    id: UUID
    filename: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- 3. AI SCHEMAS ---
class QueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    user_id: Optional[str] = Field(None, description="Optional: Override user_id (for testing). If not provided, uses authenticated user.")

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = [] # Defaults to empty list if no sources found

    model_config = ConfigDict(from_attributes=True)
