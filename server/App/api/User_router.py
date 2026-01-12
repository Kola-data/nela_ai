"""
User Management & Authentication API Router

Provides endpoints for:
- User registration and login
- Password management and reset
- User profile management (CRUD)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated, Any
from uuid import UUID

from Config.DB.db import get_db_session
from App.schema.User_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    PasswordReset,
    PasswordResetRequest,
    PasswordResetConfirm,
    Token,
)
from App.controllers.User_controller import UserController, oauth2_scheme

router = APIRouter(tags=["Users & Auth"])

# --- DEPENDENCY: Get Current Authenticated User ---
async def get_current_active_user(
    db: AsyncSession = Depends(get_db_session),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """
    Dependency to inject the authenticated user.
    Uses Any type to avoid Pydantic validation errors with SQLAlchemy models.
    """
    return await UserController.get_current_user(db, token)


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user and receive JWT access token",
)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db_session),
) -> Token:
    """
    Authenticate user with email and password.
    
    Returns JWT access token for authenticated requests.
    
    **Request Format (JSON):**
    ```json
    {
      "email": "user@example.com",
      "password": "yourpassword"
    }
    ```
    """
    token_data = await UserController.login_user(db, login_data.email, login_data.password)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return token_data


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Compatible Token Endpoint",
    description="Get JWT token using OAuth2 password flow (username/password form data)",
    tags=["Users & Auth"],
)
async def login_for_access_token(
    username: str = Form(..., description="User email address"),
    password: str = Form(..., description="User password"),
    db: AsyncSession = Depends(get_db_session),
) -> Token:
    """
    OAuth2 compatible token endpoint.
    
    **This endpoint is for OAuth2 Password Flow authentication.**
    
    Use this when:
    - Swagger UI needs to authenticate
    - Your client expects OAuth2 form data format
    - You're using standard OAuth2 libraries
    
    **Form Data:**
    - `username`: User email address (e.g., user@example.com)
    - `password`: User password
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/users/token \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=user@example.com&password=yourpassword"
    ```
    
    **Response:**
    ```json
    {
      "access_token": "eyJhbGc...",
      "token_type": "bearer"
    }
    ```
    """
    # Use the email as both username and email for login
    token_data = await UserController.login_user(db, username, password)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset User Password",
    description="Reset password directly via user_id (protected)",
)
async def reset_password(
    reset_data: PasswordReset,
    current_user: Annotated[Any, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Reset a user's password.
    
    **Protected**: Requires authentication. Admin or self.
    """
    # TODO: Add authorization check - only admin or the user themselves can reset
    success = await UserController.reset_password(
        db,
        user_id=reset_data.user_id,
        new_password=reset_data.new_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed.",
        )
    return {"message": "Password updated successfully"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Initiate Password Reset",
    description="Send password reset token to user email",
)
async def forgot_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Initiate password reset flow.
    
    Always returns 200 OK to prevent email enumeration.
    Sends reset token to user email (if registered).
    """
    # TODO: Implement token generation and email sending
    reset_token = await UserController.initiate_password_reset(db, request.email)
    
    if reset_token:
        # TODO: Send email with reset link
        print(f"DEBUG: Reset Token for {request.email}: {reset_token}")
    
    return {"message": "If email is registered, reset link has been sent."}


@router.post(
    "/confirm-password-reset",
    status_code=status.HTTP_200_OK,
    summary="Confirm Password Reset",
    description="Verify reset token and update password",
)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Complete password reset with token verification.
    
    Validates the reset token and updates user password.
    """
    # TODO: Implement token verification
    success = await UserController.verify_and_reset_password(
        db, data.token, data.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"message": "Password has been successfully reset."}


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Retrieve authenticated user's profile",
)
async def read_user_me(
    user: Annotated[Any, Depends(get_current_active_user)],
) -> UserResponse:
    """
    Get the current authenticated user's profile.
    
    **Protected**: Requires valid JWT token.
    """
    return user


# ============================================================================
# USER CRUD ENDPOINTS
# ============================================================================


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New User",
    description="Register a new user account",
)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Register a new user.
    
    - Password is automatically hashed
    - User is active by default
    - Default tier is FREE
    """
    return await UserController.create_user(db, user_in)


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List Users",
    description="Retrieve all users (paginated)",
)
async def read_users(
    current_user: Annotated[Any, Depends(get_current_active_user)],
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
) -> List[UserResponse]:
    """
    Get list of users.
    
    **Protected**: Requires authentication.
    
    Query Parameters:
    - limit: Maximum number of users to return (default: 10)
    """
    # TODO: Add pagination with offset parameter
    return await UserController.get_all_users(db, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID",
    description="Retrieve a specific user's profile",
)
async def read_user(
    user_id: UUID,
    current_user: Annotated[Any, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Get a user's profile by UUID.
    
    **Protected**: Requires authentication.
    """
    user = await UserController.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update User Profile",
    description="Partial update of user profile",
)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: Annotated[Any, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """
    Update user profile fields.
    
    **Protected**: Requires authentication.
    
    Only provided fields are updated.
    """
    # TODO: Add authorization check - only admin or user themselves
    user = await UserController.update_user(db, user_id, user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User Account",
    description="Permanently delete a user and all associated data",
)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[Any, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Delete a user account.
    
    **Protected**: Requires authentication.
    **Warning**: This action is permanent and cannot be undone.
    """
    # TODO: Add authorization check - only admin or user themselves
    deleted = await UserController.delete_user(db, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return None

