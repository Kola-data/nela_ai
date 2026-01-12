"""
CODE STYLE GUIDE - Nela Multi-Tenant AI Agent

This document outlines the clean code practices and standards used throughout
the Nela codebase.

============================================================================
PROJECT STRUCTURE
============================================================================

server/
├── main.py                 # FastAPI application entry point
├── App/
│   ├── __init__.py
│   ├── enums.py           # Shared enumerations (UserTier)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── User_router.py   # User & Auth endpoints
│   │   └── AI_router.py     # AI & RAG endpoints
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── User_controller.py   # User business logic
│   │   └── AI_controller.py     # AI business logic
│   ├── models/
│   │   ├── __init__.py
│   │   ├── User_model.py        # SQLAlchemy User ORM
│   │   └── Document_model.py    # SQLAlchemy Document ORM
│   └── schema/
│       ├── __init__.py
│       ├── User_schema.py       # Pydantic User schemas
│       └── Document_schema.py   # Pydantic Document schemas
├── Config/
│   ├── __init__.py
│   ├── DB/
│   │   ├── __init__.py
│   │   ├── db.py            # Database session management
│   │   └── init_db.py       # Database initialization
│   ├── Security/
│   │   ├── __init__.py
│   │   ├── password_hash.py # Password hashing utilities
│   │   ├── tokens.py        # JWT token management
│   │   └── ai_rate_limits.py # Rate limiting logic
│   └── Redis/
│       └── __init__.py
├── Test/
│   └── db_conn_test.py
├── API_DOCUMENTATION.md     # Complete API reference
└── requirements.txt         # Python dependencies


============================================================================
NAMING CONVENTIONS
============================================================================

Files:
  - Use snake_case for module files (user_router.py, password_hash.py)
  - Use PascalCase for model files (User_model.py, Document_model.py)
  - Use snake_case for test files (db_conn_test.py)

Classes:
  - Use PascalCase (User, Document, UserController, AIService)
  - Use descriptive names (UserController, not UC)

Functions/Methods:
  - Use snake_case (get_user, create_document, hash_password)
  - Async functions: prefix with "async def", use consistent naming
  - Private methods: prefix with underscore (_internal_method)

Variables:
  - Use snake_case (user_id, document_name, api_key)
  - Constants: use UPPERCASE (SECRET_KEY, MAX_FILE_SIZE)
  - Don't use single letters except in loops (for i in range(...))

Database/ORM:
  - Table names: lowercase, plural (users, documents)
  - Column names: snake_case (hashed_password, created_at)
  - Primary keys: always named "id"
  - Foreign keys: {table}_id format (user_id, document_id)

API Routes:
  - Use lowercase with hyphens for multi-word paths (/reset-password)
  - Resource names: plural (/users, /documents)
  - Specific resources: /users/{user_id}


============================================================================
CODE ORGANIZATION
============================================================================

Router (API Layer):
  1. Module docstring
  2. Imports
  3. Router initialization
  4. Dependencies (helper functions)
  5. Endpoint groups with section comments (# ===== SECTION ===== #)
  6. Related endpoints together

Controller (Business Logic Layer):
  1. Module docstring
  2. Imports
  3. Class definition
  4. Static methods grouped by functionality
  5. Helper methods at the end

Models (Data Layer):
  1. Module docstring
  2. Imports
  3. Enums and constants
  4. SQLAlchemy model class
  5. Relationships and methods

Schemas (Validation Layer):
  1. Module docstring
  2. Imports
  3. Request schemas (Input)
  4. Response schemas (Output)
  5. Related schemas together


============================================================================
DOCUMENTATION STANDARDS
============================================================================

Module Docstring:
  """
  Brief description of module purpose
  
  Additional details if needed, such as:
  - Main classes/functions
  - Key responsibilities
  - External dependencies
  """

Function Docstring:
  """
  One-line summary.
  
  Longer description if needed.
  
  Args:
    param1: Description
    param2: Description
  
  Returns:
    Description of return value
  
  Raises:
    ExceptionType: When this exception occurs
  """

Class Docstring:
  """
  Brief class description.
  
  Key methods and their purposes.
  
  Example:
    usage example if helpful
  """

Comments:
  - Use for "why", not "what" (code should explain what)
  - Keep comments up-to-date with code
  - Use TODO: for incomplete features
  - Use FIXME: for known issues


============================================================================
FASTAPI ENDPOINT DOCUMENTATION
============================================================================

Every endpoint should have:

1. Path decorator with metadata:
   @router.get(
       "/path",
       response_model=ResponseSchema,
       status_code=200,
       summary="Action Description",
       description="Longer description of what endpoint does"
   )

2. Function with clear parameters:
   async def endpoint_name(
       path_param: Type,
       query_param: Type = Default,
       db: AsyncSession = Depends(get_db_session),
       current_user: Annotated[Any, Depends(get_current_user)]
   ) -> ResponseType:

3. Comprehensive docstring:
   """
   Clear description of what the endpoint does.
   
   **Protected**: If authentication required
   **Paginated**: If returns list
   
   Returns:
     - field1: Description
     - field2: Description
   """


============================================================================
TYPE HINTS
============================================================================

Always use type hints:
  ✓ def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
  ✗ def get_user(db, user_id):

Common types:
  - str, int, float, bool for primitives
  - UUID for IDs
  - Optional[Type] for nullable values
  - List[Type] for lists
  - Dict[str, Type] for dictionaries
  - Any for SQLAlchemy models in FastAPI deps (avoid Pydantic validation)
  - Callable for functions
  - Union[Type1, Type2] for multiple types
  - Annotated[Type, metadata] for FastAPI dependencies


============================================================================
ERROR HANDLING
============================================================================

HTTP Status Codes:
  - 200: OK (GET, PATCH, POST returning data)
  - 201: Created (POST creating resource)
  - 204: No Content (DELETE)
  - 400: Bad Request (validation errors)
  - 401: Unauthorized (missing/invalid JWT)
  - 403: Forbidden (permission denied)
  - 404: Not Found (resource doesn't exist)
  - 429: Too Many Requests (rate limited)
  - 500: Internal Server Error (unexpected error)

Exception Pattern:
  if not valid:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Clear error message"
      )

Validation Pattern:
  from pydantic import BaseModel, Field, validator
  
  class UserCreate(BaseModel):
      email: EmailStr
      password: str = Field(..., min_length=8)
      
      @validator('password')
      def validate_password(cls, v):
          if v.isdigit():
              raise ValueError('Password cannot be all numbers')
          return v


============================================================================
TESTING
============================================================================

Test file naming:
  - test_{module}.py
  - {feature}_test.py

Test function naming:
  - test_{function_being_tested}_{condition}_{expected_result}
  - Example: test_login_with_invalid_email_returns_401

Test structure:
  def test_feature():
      # Arrange - Setup test data
      user = create_test_user()
      
      # Act - Execute the code
      result = authenticate_user(user.email, password)
      
      # Assert - Verify results
      assert result.is_success == True


============================================================================
SECURITY BEST PRACTICES
============================================================================

Authentication:
  - Use JWT tokens for API authentication
  - Implement rate limiting for auth endpoints
  - Hash passwords with bcrypt (not plain text)
  - Use oauth2_scheme for token extraction

Authorization:
  - Always verify user owns the resource
  - Check permissions on protected endpoints
  - Use dependency injection for auth checks

Data Security:
  - Never log sensitive data (passwords, tokens)
  - Use environment variables for secrets
  - Validate all input data
  - Sanitize error messages


============================================================================
ASYNC/AWAIT PATTERNS
============================================================================

Database operations:
  async def get_user(db: AsyncSession, user_id: UUID):
      result = await db.execute(select(User).where(User.id == user_id))
      return result.scalar_one_or_none()

Always commit after mutations:
  await db.execute(...)
  await db.commit()

Rollback on errors:
  try:
      # database operations
      await db.commit()
  except Exception as e:
      await db.rollback()
      raise HTTPException(...)


============================================================================
DEPENDENCIES (SQLAlchemy / Pydantic / FastAPI)
============================================================================

SQLAlchemy Models (app/models/):
  - Use declarative base
  - Use Mapped and mapped_column for type hints
  - Use relationships with back_populates
  - Include timestamps (created_at, updated_at)

Pydantic Schemas (app/schema/):
  - Base schemas for shared fields
  - Create, Read, Update schemas
  - Always use ConfigDict(from_attributes=True) for ORM compatibility

FastAPI Dependencies:
  - Use Depends() for injection
  - Use Annotated for type clarity
  - Create reusable dependency functions
  - Document dependency requirements


============================================================================
PERFORMANCE CONSIDERATIONS
============================================================================

Database:
  - Use select() for queries (SQLAlchemy 2.0+)
  - Index frequently queried columns
  - Paginate large result sets
  - Use .limit() and .offset()

Caching:
  - Cache frequently accessed data
  - Implement Redis for distributed caching
  - Use cache invalidation strategies

API Response:
  - Return only necessary fields
  - Limit default pagination (10-100 items)
  - Use compression middleware

"""
