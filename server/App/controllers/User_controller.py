# In server/App/controllers/User_controller.py
import uuid
import os # Added for direct env access
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from jose import JWTError, jwt

# Absolute imports
from App.models.User_model import User
from App.schema.User_schema import UserCreate, UserUpdate
from Config.Security.password_hash import hash_password, verify_password
from Config.Security.tokens import create_access_token
from dotenv import load_dotenv

load_dotenv()
# Token scheme for Swagger UI
# Points to the OAuth2-compatible /token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

class UserController:
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate):
        """Create user with bcrypt hashed password"""
        hashed_pw = hash_password(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_pw,
            full_name=user_data.full_name
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @staticmethod
    async def get_user(db: AsyncSession, user_id: UUID):
        """Read a user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_users(db: AsyncSession, limit: int = 100):
        """Fetch a list of users"""
        query = select(User).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: UUID, update_data: UserUpdate):
        """Update user data dynamically"""
        data = update_data.model_dump(exclude_unset=True)
        if not data:
            return await UserController.get_user(db, user_id)

        query = (
            update(User)
            .where(User.id == user_id)
            .values(**data)
            .returning(User)
        )
        result = await db.execute(query)
        await db.commit()
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
        """Delete user from DB"""
        query = delete(User).where(User.id == user_id)
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str):
        """Verify user credentials for login"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user and verify_password(password, user.hashed_password):
            return user
        return None

    @staticmethod
    async def login_user(db: AsyncSession, email: str, password: str):
        """Handles authentication and returns JWT tokens"""
        user = await UserController.authenticate_user(db, email, password)
        if not user:
            return None
        
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    @staticmethod
    async def reset_password(db: AsyncSession, user_id: UUID, new_password: str) -> bool:
        """Applies the new hashed password to the database"""
        hashed_pw = hash_password(new_password)
        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=hashed_pw, 
                updated_at=datetime.now(timezone.utc)
            )
        )
        await db.execute(query)
        await db.commit()
        return True

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str):
        """
        Validates JWT using environment variables directly and fetches user.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        # Directly grab from environment variables
        SECRET_KEY = os.getenv("SECRET_KEY")
        ALGORITHM = os.getenv("ALGORITHM", "HS256")
        
        if not SECRET_KEY:
            raise HTTPException(status_code=500, detail="SECRET_KEY not set in environment")
        
        try:
            # Decode the JWT
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM]
            )
            user_id_str: str = payload.get("sub")
            
            if user_id_str is None:
                raise credentials_exception
                
            user_id = uuid.UUID(user_id_str)
        except (JWTError, ValueError):
            raise credentials_exception

        # Fetch user from database
        user = await UserController.get_user(db, user_id=user_id)
        
        if user is None:
            raise credentials_exception
            
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
            
        return user

    @staticmethod
    async def initiate_password_reset(db: AsyncSession, email: str) -> Optional[str]:
        """
        Initiate password reset flow.
        
        TODO: Generate reset token and store in database with expiration.
        TODO: Send email with reset link.
        
        Returns reset token if email found, None otherwise.
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # For security: Don't reveal whether email exists
            return None
        
        # TODO: Generate unique reset token
        # TODO: Store in reset_tokens table with expiration (e.g., 24 hours)
        reset_token = f"reset_{user.id}_{datetime.now(timezone.utc).timestamp()}"
        
        return reset_token

    @staticmethod
    async def verify_and_reset_password(
        db: AsyncSession, token: str, new_password: str
    ) -> bool:
        """
        Verify reset token and update password.
        
        TODO: Validate token against database.
        TODO: Check token expiration.
        
        Returns True if successful, False otherwise.
        """
        # TODO: Query reset_tokens table to validate token
        # TODO: Check if token is expired
        # TODO: Extract user_id from token
        
        # Placeholder implementation
        return False
