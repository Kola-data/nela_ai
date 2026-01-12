#!/usr/bin/env python3
"""
Diagnostic tool to check file storage issues and fix them
"""

import os
import sys
import asyncio

# Add parent directory to path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

from sqlalchemy import text
from Config.DB.db import AsyncSessionLocal
from App.utils.file_manager import get_file_manager


async def diagnose():
    """Run diagnostic checks"""
    
    print("🔍 FILE STORAGE DIAGNOSTIC")
    print("=" * 70)
    
    # 1. Check upload directory
    print("\n1️⃣  Upload Directory Check:")
    fm = get_file_manager()
    upload_dir = fm.base_upload_dir
    print(f"   Upload dir: {upload_dir}")
    print(f"   Exists: {os.path.exists(upload_dir)}")
    print(f"   Permissions: {oct(os.stat(upload_dir).st_mode)[-3:]}")
    
    # 2. Check database
    print("\n2️⃣  Database Check:")
    async with AsyncSessionLocal() as session:
        # Check if file_path column exists
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' 
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result.fetchall()]
        print(f"   Columns in documents table: {', '.join(columns)}")
        print(f"   file_path exists: {'file_path' in columns}")
        
        # Check documents
        result = await session.execute(text(
            "SELECT COUNT(*) FROM documents"
        ))
        count = result.scalar()
        print(f"   Total documents: {count}")
        
        if count > 0:
            result = await session.execute(text("""
                SELECT id, filename, file_path, status, created_at 
                FROM documents 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            rows = result.fetchall()
            print("\n   Recent documents:")
            for row in rows:
                print(f"     • {row[1]}")
                print(f"       ID: {row[0]}")
                print(f"       File Path: {row[2]}")
                print(f"       Status: {row[3]}")
                print(f"       Created: {row[4]}")
                print()
    
    # 3. Check for orphaned files
    print("3️⃣  Files in Upload Directory:")
    file_count = 0
    for root, dirs, files in os.walk(upload_dir):
        for file in files:
            file_count += 1
            full_path = os.path.join(root, file)
            size = os.path.getsize(full_path)
            print(f"   Found: {full_path} ({size} bytes)")
    
    if file_count == 0:
        print("   ⚠️  No files found in upload directory")
    else:
        print(f"   ✅ Found {file_count} file(s)")
    
    print("\n" + "=" * 70)
    print("\n📋 SUMMARY:")
    if file_count == 0 and count > 0:
        print("""
   ❌ ISSUE DETECTED:
      • Documents are in database but NO files in server/upload/
      • Reason: Files were uploaded BEFORE file storage system was implemented
      
   ✅ SOLUTION:
      Option 1: Test upload a new file (it will be saved correctly)
      Option 2: Re-upload existing documents
      Option 3: Check if files are in a different location
        """)
    elif file_count == 0 and count == 0:
        print("""
   ℹ️  No documents uploaded yet
      • Test by uploading a new file
      • File should appear in server/upload/{user_id}/
        """)
    else:
        print("""
   ✅ System working correctly!
      • Files are being saved to server/upload/
        """)

if __name__ == "__main__":
    asyncio.run(diagnose())
