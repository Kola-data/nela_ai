#!/usr/bin/env python3
"""
Test file upload to verify the storage system works
"""

import os
import sys
import asyncio
import requests
import json

# Configuration
API_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{API_URL}/api/v1/upload"

# Test file path - create a simple PDF
TEST_FILE = "/tmp/test_upload.txt"


async def main():
    print("=" * 70)
    print("🧪 FILE UPLOAD TEST")
    print("=" * 70)
    
    # 1. Create test file
    print("\n1️⃣  Creating test file...")
    with open(TEST_FILE, "w") as f:
        f.write("This is a test document for upload testing.\n")
        f.write("It contains some test content.\n")
        f.write("File storage system should save this to server/upload/{user_id}/\n")
    print(f"   ✅ Test file created: {TEST_FILE}")
    
    # 2. Get auth token (you need to provide this)
    print("\n2️⃣  Authentication:")
    token = os.getenv("AUTH_TOKEN")
    if not token:
        print("   ⚠️  No AUTH_TOKEN environment variable set")
        print("   ℹ️  To test, set your authentication token:")
        print("      export AUTH_TOKEN='your_jwt_token'")
        print("\n   For testing without token, we'll continue anyway...")
        token = "test_token"
    else:
        print(f"   ✅ Token found")
    
    # 3. Upload file
    print("\n3️⃣  Uploading file...")
    
    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": (os.path.basename(TEST_FILE), f, "text/plain")}
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            print(f"   Uploading to: {UPLOAD_ENDPOINT}")
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                headers=headers,
                timeout=10
            )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("   ✅ Upload successful!")
            
            # Parse response
            try:
                resp_data = response.json()
                print("\n4️⃣  Response Details:")
                print(json.dumps(resp_data, indent=2))
                
                # Check for file location
                if "file_location" in resp_data:
                    print(f"\n   📁 File location: {resp_data['file_location']}")
                if "storage_path" in resp_data:
                    print(f"   📁 Storage path: {resp_data['storage_path']}")
                if "task_id" in resp_data:
                    print(f"   📋 Task ID: {resp_data['task_id']}")
                    
            except Exception as e:
                print(f"   Response text: {response.text}")
        else:
            print(f"   ❌ Upload failed!")
            print(f"   Error: {response.text}")
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # 4. Check if file was saved
    print("\n5️⃣  Checking file storage...")
    upload_dir = "/home/kwola/Documents/ai_projects/statistics_analyist_agent/server/upload"
    if os.path.exists(upload_dir):
        print(f"   ✅ Upload directory exists: {upload_dir}")
        
        # Count files
        file_count = 0
        for root, dirs, files in os.walk(upload_dir):
            for file in files:
                file_count += 1
                full_path = os.path.join(root, file)
                size = os.path.getsize(full_path)
                print(f"   📄 Found: {full_path} ({size} bytes)")
        
        if file_count == 0:
            print("   ⚠️  No files found in upload directory")
        else:
            print(f"   ✅ Found {file_count} file(s)")
    else:
        print(f"   ❌ Upload directory doesn't exist: {upload_dir}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
