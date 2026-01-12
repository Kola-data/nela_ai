from fastapi import Request, HTTPException, Depends
from datetime import datetime, timedelta
from typing import Any, Callable
from App.models.User_model import User
from App.enums import UserTier

# Memory store (In 2025 production, swap this for Redis)
usage_history = {}

async def check_rate_limit(user: Any = None):
    """Check rate limit - accepts user as Any type to avoid Pydantic validation."""
    if user is None:
        # If user not provided, skip rate limiting
        return
    
    # Superusers and Paid users bypass the limit
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return
    if hasattr(user, 'tier') and user.tier == UserTier.PAID:
        return

    now = datetime.now()
    user_id = str(user.id) if hasattr(user, 'id') else None
    
    if not user_id:
        return
    
    # Get last 60 seconds of history
    history = usage_history.get(user_id, [])
    history = [t for t in history if t > now - timedelta(minutes=1)]
    
    if len(history) >= 3:
        raise HTTPException(
            status_code=429, 
            detail="Rate limit reached: Free accounts are limited to 3 prompts per minute."
        )
    
    # Update history
    history.append(now)
    usage_history[user_id] = history
