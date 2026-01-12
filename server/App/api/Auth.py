from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

# Local Imports
from Config.DB.db import get_db_session
from App.schema.User_schema import UserCreate, UserUpdate, UserResponse, UserLogin, PasswordResetRequest, PasswordResetConfirm
from App.controllers.User_controller import UserController

router = APIRouter(prefix="/users", tags=["Users/Auth"])

# --- Authentication Endpoints ---

@router.post("/login")
async def login(
    login_data: UserLogin, 
    db: AsyncSession = Depends(get_db_session)
):
    """Authenticate user and return a JWT access token"""
    token_data = await UserController.login_user(db, login_data.email, login_data.password)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password"
        )
    return token_data

# --- Password Reset Flow ---

@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Initiate password reset.
    Always returns 200 OK to prevent email enumeration.
    """
    reset_token = await UserController.initiate_password_reset(db, request.email)
    
    if reset_token:
        # Best Practice: Use BackgroundTasks to send the email without blocking the response
        # background_tasks.add_task(send_reset_email, request.email, reset_token)
        print(f"DEBUG: Reset Token for {request.email}: {reset_token}") # Replace with actual email logic
        
    return {"message": "If this email is registered, a reset link has been sent."}

@router.post("/reset-password-confirm")
async def reset_password_confirm(
    data: PasswordResetConfirm, 
    db: AsyncSession = Depends(get_db_session)
):
    """Verify reset token and update to the new password"""
    success = await UserController.verify_and_reset_password(db, data.token, data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid or expired reset token"
        )
    return {"message": "Password has been successfully reset."}

# --- Existing CRUD Endpoints ---

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db_session)):
    return await UserController.create_user(db, user_in)

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    user = await UserController.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
