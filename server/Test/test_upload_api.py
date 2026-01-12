#!/usr/bin/env python3
"""
Test file upload with proper JWT token generation
"""

import os
import sys
import asyncio
import requests
import json
from datetime import datetime, timedelta, timezone

# Add server to path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

from Config.Security.tokens import create_access_token
from sqlalchemy import text
from Config.DB.db import AsyncSessionLocal

API_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{API_URL}/api/v1/ai/upload"
TEST_FILE = "/tmp/test_upload.txt"


async def get_or_create_user():
    """Get existing user or create test user"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user = result.fetchone()
        if user:
            return str(user[0])
        else:
            raise Exception("No users found in database")


async def main():
    print("=" * 80)
    print("🧪 FILE UPLOAD TEST WITH JWT TOKEN")
    print("=" * 80)
    
    try:
        # 1. Create test file
        print("\n1️⃣  Creating test file...")
        with open(TEST_FILE, "w") as f:
            f.write("This is a test document for upload testing.\n")
            f.write("File should be stored in: server/upload/{user_id}/\n")
            f.write("Testing file storage system.\n")
        print(f"   ✅ Test file created: {TEST_FILE}")
        print(f"   📊 File size: {os.path.getsize(TEST_FILE)} bytes")
        
        # 2. Get user and create JWT token
        print("\n2️⃣  Generating JWT token...")
        user_id = await get_or_create_user()
        print(f"   ✅ User ID: {user_id}")
        
        token = create_access_token({"sub": user_id})
        print(f"   ✅ JWT Token generated")
        
        # 3. Upload file
        print("\n3️⃣  Uploading file to API...")
        print(f"   📍 Endpoint: POST {UPLOAD_ENDPOINT}")
        
        with open(TEST_FILE, "rb") as f:
            files = {"file": ("test_upload.txt", f, "text/plain")}
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                headers=headers,
                timeout=30
            )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("   ✅ Upload accepted!")
            
            # Parse and display response
            try:
                resp_data = response.json()
                print("\n4️⃣  Server Response (Formatted):")
                print("   " + "-" * 70)
                
                for key, value in resp_data.items():
                    if key == "status":
                        print(f"   Status: {value}")
                    elif key == "filename":
                        print(f"   Filename: {value}")
                    elif key == "task_id":
                        print(f"   Task ID: {value}")
                    elif key == "file_location":
                        print(f"   File Location: {value}")
                    elif key == "storage_path":
                        print(f"   Storage Path: {value}")
                    elif key == "status_url":
                        print(f"   Status URL: {value}")
                    elif key == "message":
                        print(f"   Message: {value}")
                    else:
                        print(f"   {key}: {value}")
                
                print("   " + "-" * 70)
                    
            except Exception as e:
                print(f"   Response text: {response.text}")
        else:
            print(f"   ❌ Upload failed!")
            print(f"   Error: {response.text}")
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 4. Check file storage
    print("\n5️⃣  Checking file storage...")
    upload_dir = "/home/kwola/Documents/ai_projects/statistics_analyist_agent/server/upload"
    if os.path.exists(upload_dir):
        print(f"   ✅ Upload directory exists")
        
        file_count = 0
        for root, dirs, files in os.walk(upload_dir):
            level = root.replace(upload_dir, '').count(os.sep)
            indent = " " * 4 * (level + 1)
            
            # Show directory
            dirname = os.path.basename(root)
            if dirname:
                print(f"   {indent}📁 {dirname}/")
            
            # Show files
            for file in files:
                file_count += 1
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                print(f"   {indent}  📄 {file} ({size:,} bytes)")
        
        if file_count == 0:
            print("   ⚠️  No files found yet (may still be uploading)")
        else:
            print(f"   ✅ Found {file_count} file(s)")
    else:
        print(f"   ❌ Upload directory doesn't exist: {upload_dir}")
    
    # 5. Check database
    print("\n6️⃣  Checking database...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(
            "SELECT COUNT(*) FROM documents WHERE status = 'completed' OR status = 'pending' OR status = 'processing'"
        ))
        count = result.scalar()
        print(f"   Documents in DB: {count}")
        
        result = await session.execute(text(
            "SELECT filename, file_path, status FROM documents ORDER BY created_at DESC LIMIT 3"
        ))
        rows = result.fetchall()
        for filename, file_path, status in rows:
            print(f"   📋 {filename}: {status}")
            if file_path:
                print(f"      Path: {file_path}")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
