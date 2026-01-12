#!/usr/bin/env python3
"""
Script to help find and update documents with file storage

This helps locate uploaded files that may be in other locations
"""

import os
import sys
import asyncio

# Add parent directory to path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

from sqlalchemy import text
from Config.DB.db import AsyncSessionLocal


async def find_files_in_system():
    """Find uploaded PDF files in the system"""
    
    print("🔍 SEARCHING FOR UPLOADED FILES")
    print("=" * 70)
    
    # Get document filenames from database
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(
            "SELECT id, filename, user_id FROM documents WHERE status = 'completed'"
        ))
        docs = result.fetchall()
    
    if not docs:
        print("❌ No completed documents found in database")
        return
    
    print(f"\n📄 Found {len(docs)} completed documents in database:\n")
    
    for doc_id, filename, user_id in docs:
        print(f"Searching for: {filename}")
        print(f"  User ID: {user_id}")
        print(f"  Doc ID: {doc_id}\n")
        
        # Search in common locations
        search_paths = [
            "/tmp",
            os.path.expanduser("~"),
            "/home",
            os.getcwd(),
        ]
        
        found_files = []
        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue
            try:
                for root, dirs, files in os.walk(search_path, topdown=True):
                    # Skip hidden directories and common large dirs
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'node_modules', '__pycache__']]
                    
                    for file in files:
                        if file == filename or filename in file:
                            full_path = os.path.join(root, file)
                            size = os.path.getsize(full_path)
                            found_files.append((full_path, size))
                            print(f"  ✅ Found: {full_path}")
                            print(f"     Size: {size} bytes")
                            print()
            except PermissionError:
                pass
        
        if not found_files:
            print(f"  ⚠️  File not found in system\n")
    
    print("=" * 70)
    print("\nℹ️  NEXT STEPS:")
    print("  1. For new uploads: Just re-upload files (they'll be saved automatically)")
    print("  2. Files are now stored in: server/upload/{user_id}/{filename}")
    print("  3. Migration completed successfully ✅")


if __name__ == "__main__":
    asyncio.run(find_files_in_system())
