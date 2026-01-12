# In server/App/schema/User_schema.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from App.enums import UserTier

# --- AUTHENTICATION & TOKEN SCHEMAS ---

class UserLogin(BaseModel):
    """Schema for login requests"""
    email: EmailStr = Field(..., description="User email address", examples=["user@example.com"])
    password: str = Field(..., min_length=8, description="Plain text password")

class Token(BaseModel):
    """Schema for returning JWT tokens"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

class PasswordReset(BaseModel):
    """Schema for updating password via user_id"""
    user_id: UUID = Field(..., description="Target user ID")
    new_password: str = Field(..., min_length=8, description="New plain text password")

class PasswordResetRequest(BaseModel):
    """Schema for initiating password reset by email"""
    email: EmailStr = Field(..., description="Email address to initiate reset", examples=["user@example.com"])

class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset with token"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New plain text password")

# --- USER PROFILE SCHEMAS ---

class UserBase(BaseModel):
    """Base properties shared by all User schemas"""
    username: str = Field(..., min_length=3, max_length=50, examples=["analyst_01"])
    email: EmailStr = Field(..., examples=["user@example.com"])
    full_name: Optional[str] = Field(None, max_length=100)
    tier: UserTier = Field(default=UserTier.FREE) # Track if user is FREE or PAID

class UserCreate(UserBase):
    """Schema for Creating a User (Incoming Data)"""
    password: str = Field(..., min_length=8, description="Plain text password to be hashed")

class UserUpdate(BaseModel):
    """Schema for Updating a User (Incoming Data - All Optional)"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    tier: Optional[UserTier] = None # Allow updating to PAID tier

class UserResponse(UserBase):
    """Schema for Returning a User (Outgoing Data)"""
    id: UUID
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    # Modern Pydantic v2 configuration to allow reading SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)

class UserInDB(UserResponse):
    """Schema for internal usage (includes the hash)"""
    hashed_password: str
