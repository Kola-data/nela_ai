# In server/Config/Security/tokens.py
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from dotenv import load_dotenv
from fastapi import HTTPException, status

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
RESET_TOKEN_EXPIRE_MINUTES = 15  # Best practice: Reset tokens expire faster

def create_access_token(data: dict) -> str:
    """Encodes user data into a standard Access JWT."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_reset_token(data: dict) -> str:
    """Encodes user data into a short-lived Password Reset JWT."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    # Add a 'type' to prevent using a reset token as a login token
    to_encode.update({"exp": expire, "type": "password_reset"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, expected_type: str) -> Optional[dict]:
    """
    Decodes and validates a token. 
    Checks for expiration and ensures the token type matches.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Token is malformed
