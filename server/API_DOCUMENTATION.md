"""
API DOCUMENTATION - Nela Multi-Tenant AI Agent

This document outlines the clean, well-organized API structure.
Base URL: http://localhost:8001/api/v1

============================================================================
AUTHENTICATION & USER MANAGEMENT
============================================================================

POST /users/login
  Summary: User Login
  Description: Authenticate user with email and password to receive JWT token
  Request:
    {
      "email": "user@example.com",
      "password": "secure_password_min_8_chars"
    }
  Response (200):
    {
      "access_token": "eyJhbGc...",
      "token_type": "bearer"
    }


GET /users/me
  Summary: Get Current User Profile
  Description: Retrieve authenticated user's profile (requires JWT)
  Headers: Authorization: Bearer {token}
  Response (200):
    {
      "id": "uuid",
      "username": "analyst_01",
      "email": "user@example.com",
      "full_name": "John Analyst",
      "is_active": true,
      "is_superuser": false,
      "tier": "free",
      "created_at": "2025-12-26T10:00:00",
      "updated_at": "2025-12-26T10:00:00"
    }


POST /users/
  Summary: Create New User
  Description: Register a new user account
  Request:
    {
      "username": "analyst_01",
      "email": "user@example.com",
      "password": "secure_password_min_8_chars",
      "full_name": "John Analyst"
    }
  Response (201): UserResponse (same as /me)


GET /users/
  Summary: List Users
  Description: Get paginated list of users (requires authentication)
  Headers: Authorization: Bearer {token}
  Query Parameters:
    - limit: int (default: 10) - Max users to return
  Response (200): List[UserResponse]


GET /users/{user_id}
  Summary: Get User by ID
  Description: Retrieve a specific user's profile (requires authentication)
  Headers: Authorization: Bearer {token}
  Path Parameters:
    - user_id: UUID
  Response (200): UserResponse
  Response (404): {"detail": "User not found"}


PATCH /users/{user_id}
  Summary: Update User Profile
  Description: Partial update of user profile (requires authentication)
  Headers: Authorization: Bearer {token}
  Path Parameters:
    - user_id: UUID
  Request (all fields optional):
    {
      "username": "new_username",
      "email": "newemail@example.com",
      "full_name": "New Name",
      "is_active": true,
      "tier": "paid"
    }
  Response (200): UserResponse
  Response (404): {"detail": "User not found"}


DELETE /users/{user_id}
  Summary: Delete User Account
  Description: Permanently delete a user and all associated data (requires auth)
  Headers: Authorization: Bearer {token}
  Path Parameters:
    - user_id: UUID
  Response (204): No Content
  Response (404): {"detail": "User not found"}


============================================================================
PASSWORD MANAGEMENT
============================================================================

POST /users/reset-password
  Summary: Reset User Password
  Description: Reset password directly via user_id (requires authentication)
  Headers: Authorization: Bearer {token}
  Request:
    {
      "user_id": "uuid",
      "new_password": "new_secure_password_min_8_chars"
    }
  Response (200): {"message": "Password updated successfully"}
  Response (400): {"detail": "Password reset failed."}


POST /users/forgot-password
  Summary: Initiate Password Reset
  Description: Send password reset token to user email
  Request:
    {
      "email": "user@example.com"
    }
  Response (200): {"message": "If email is registered, reset link has been sent."}
  Note: Always returns 200 OK to prevent email enumeration


POST /users/confirm-password-reset
  Summary: Confirm Password Reset
  Description: Verify reset token and update password
  Request:
    {
      "token": "reset_token_from_email",
      "new_password": "new_secure_password_min_8_chars"
    }
  Response (200): {"message": "Password has been successfully reset."}
  Response (400): {"detail": "Invalid or expired reset token"}


============================================================================
LOCAL AI & RAG
============================================================================

POST /ai/upload
  Summary: Upload & Index Document
  Description: Upload a document to be indexed for AI queries
  Headers: Authorization: Bearer {token}
  Request: multipart/form-data
    - file: Binary file (.txt, .pdf, .md)
  Response (201):
    {
      "message": "File indexed and ready for AI queries",
      "doc_id": "uuid",
      "filename": "document.txt"
    }
  Response (400): {"detail": "Unsupported file format. Supported: .txt, .pdf, .md"}
  Response (500): {"detail": "Upload failed: ..."}


POST /ai/prompt
  Summary: Ask Local AI
  Description: Query Llama 3.2 using RAG over user's documents
  Headers: Authorization: Bearer {token}
  Request:
    {
      "prompt": "What is the key finding in the documents?"
    }
  Response (200):
    {
      "answer": "Based on the documents, the key finding is...",
      "sources": ["document1.txt", "document2.pdf"]
    }
  Response (429): {"detail": "Rate limit reached: Free accounts limited to 3 prompts/min"}
  Note: Free tier: 3 prompts per minute | Paid tier: unlimited


DELETE /ai/documents/{doc_id}
  Summary: Delete Document
  Description: Remove a document from vector store and database
  Headers: Authorization: Bearer {token}
  Path Parameters:
    - doc_id: UUID
  Response (200): {"message": "Document and vectors deleted successfully"}
  Response (404): {"detail": "Document not found"}
  Response (500): {"detail": "Deletion failed: ..."}


============================================================================
HEALTH CHECK
============================================================================

GET /
  Summary: Health Check
  Description: Check if API is running
  Response (200):
    {
      "status": "online",
      "agent": "Nela",
      "version": "1.0.0",
      "api_docs": "/docs",
      "redoc": "/redoc"
    }


============================================================================
ERROR RESPONSES
============================================================================

All error responses follow this format:
{
  "detail": "Error message describing what went wrong"
}

Common HTTP Status Codes:
- 200: OK - Request successful
- 201: Created - Resource created successfully
- 204: No Content - Successful deletion
- 400: Bad Request - Invalid input data
- 401: Unauthorized - Missing or invalid JWT token
- 404: Not Found - Resource doesn't exist
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error - Server error


============================================================================
AUTHENTICATION
============================================================================

All protected endpoints require a JWT Bearer token:

1. Login: POST /users/login
   - Returns: {"access_token": "...", "token_type": "bearer"}

2. Use token in subsequent requests:
   - Header: Authorization: Bearer {access_token}

3. Token expiration: Check JWT_EXPIRATION in environment variables


============================================================================
DATA MODELS
============================================================================

UserResponse:
  - id: UUID
  - username: str (3-50 chars)
  - email: EmailStr
  - full_name: Optional[str]
  - is_active: bool
  - is_superuser: bool
  - tier: UserTier (FREE | PAID)
  - created_at: datetime
  - updated_at: datetime

QueryResponse:
  - answer: str
  - sources: List[str] (filenames used)

UserTier:
  - FREE: Limited to 3 prompts per minute
  - PAID: Unlimited prompts


============================================================================
RATE LIMITING
============================================================================

Free Tier:
  - /ai/prompt: 3 requests per minute
  - Other endpoints: No limit

Paid Tier:
  - All endpoints: No limit

Rate Limit Response (429):
{
  "detail": "Rate limit reached: Free accounts are limited to 3 prompts per minute."
}


============================================================================
BEST PRACTICES
============================================================================

1. Security:
   - Always use HTTPS in production
   - Store JWT tokens securely (secure cookies)
   - Don't expose SECRET_KEY
   - Validate all user inputs

2. Error Handling:
   - Check HTTP status codes
   - Log errors for debugging
   - Provide meaningful error messages

3. Performance:
   - Use pagination for list endpoints
   - Cache frequently accessed data
   - Implement request timeouts

4. Versioning:
   - Current API version: v1
   - Future versions at /api/v2

============================================================================
"""
