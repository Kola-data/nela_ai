#!/usr/bin/env python3
"""
Setup script to create a test user
"""

import asyncio
import sys
sys.path.insert(0, '.')

# Import all models first
from App.models.User_model import User
from App.models.Document_model import Document
from App.models.Conversation_model import Conversation, ConversationSession

from Config.DB.db import AsyncSessionLocal
from Config.Security.password_hash import hash_password
import uuid

async def create_test_user():
    """Create a test user for testing"""
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "test_user@example.com")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Test user already exists: {existing_user.email}")
            return existing_user
        
        # Create new test user
        test_user = User(
            id=uuid.uuid4(),
            username="test_user",
            email="test_user@example.com",
            hashed_password=hash_password("test_password_123"),
            full_name="Test User",
            is_active=True
        )
        
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)
        
        print(f"✅ Test user created successfully!")
        print(f"   Email: test_user@example.com")
        print(f"   Password: test_password_123")
        print(f"   User ID: {test_user.id}")
        
        return test_user

if __name__ == "__main__":
    asyncio.run(create_test_user())
