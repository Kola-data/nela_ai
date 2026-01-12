#!/usr/bin/env python3
"""
Test script for FileManager
Tests file storage, retrieval, and user isolation
"""

import os
import sys
import tempfile
from pathlib import Path

# Add server to path
server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, server_dir)

from App.utils.file_manager import FileManager


def test_file_manager():
    """Test FileManager functionality"""
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Testing FileManager with temp dir: {temp_dir}")
        print("=" * 60)
        
        # Initialize FileManager
        fm = FileManager(base_upload_dir=temp_dir)
        print("✅ FileManager initialized")
        
        # Test 1: Create user directory
        print("\n🧪 Test 1: Create user directory")
        user_id_1 = "user_001"
        user_dir = fm.get_user_upload_dir(user_id_1)
        assert os.path.exists(user_dir), "User directory not created"
        print(f"✅ User directory created: {user_dir}")
        
        # Test 2: Save file
        print("\n🧪 Test 2: Save file")
        file_content = b"This is test content for document 1"
        file_path = fm.save_file(user_id_1, "test_document.txt", file_content)
        assert os.path.exists(file_path), "File not saved"
        print(f"✅ File saved: {file_path}")
        
        # Test 3: Retrieve file
        print("\n🧪 Test 3: Retrieve file")
        retrieved_content = fm.get_file(user_id_1, "test_document.txt")
        assert retrieved_content == file_content, "Retrieved content doesn't match"
        print(f"✅ File retrieved successfully")
        
        # Test 4: List files
        print("\n🧪 Test 4: List files")
        files = fm.list_user_files(user_id_1)
        assert "test_document.txt" in files, "File not in list"
        print(f"✅ Files listed: {files}")
        
        # Test 5: Save multiple files
        print("\n🧪 Test 5: Save multiple files")
        fm.save_file(user_id_1, "document2.pdf", b"PDF content here")
        fm.save_file(user_id_1, "report.md", b"# Report\nContent")
        files = fm.list_user_files(user_id_1)
        assert len(files) == 3, f"Expected 3 files, got {len(files)}"
        print(f"✅ Multiple files saved: {files}")
        
        # Test 6: User isolation
        print("\n🧪 Test 6: User isolation")
        user_id_2 = "user_002"
        fm.save_file(user_id_2, "secret.txt", b"User 2 secret")
        
        # User 1 should not see User 2's files
        user1_files = fm.list_user_files(user_id_1)
        user2_files = fm.list_user_files(user_id_2)
        assert "secret.txt" not in user1_files, "User isolation failed!"
        assert "secret.txt" in user2_files, "User 2 file not found"
        print(f"✅ User isolation verified")
        print(f"   User 1 files: {user1_files}")
        print(f"   User 2 files: {user2_files}")
        
        # Test 7: Storage info
        print("\n🧪 Test 7: Storage information")
        storage_info = fm.get_user_storage_info(user_id_1)
        assert storage_info["file_count"] == 3, "Wrong file count"
        assert storage_info["total_size_bytes"] > 0, "Wrong size calculation"
        print(f"✅ Storage info:")
        print(f"   Files: {storage_info['file_count']}")
        print(f"   Size: {storage_info['total_size_mb']} MB")
        print(f"   Total bytes: {storage_info['total_size_bytes']}")
        
        # Test 8: File size
        print("\n🧪 Test 8: Get file size")
        size = fm.get_file_size(user_id_1, "test_document.txt")
        assert size == len(file_content), "File size mismatch"
        print(f"✅ File size: {size} bytes")
        
        # Test 9: Delete file
        print("\n🧪 Test 9: Delete file")
        deleted = fm.delete_file(user_id_1, "test_document.txt")
        assert deleted, "Delete returned False"
        files_after = fm.list_user_files(user_id_1)
        assert "test_document.txt" not in files_after, "File still exists after deletion"
        print(f"✅ File deleted successfully")
        print(f"   Remaining files: {files_after}")
        
        # Test 10: Delete user directory
        print("\n🧪 Test 10: Delete user directory")
        user2_dir = os.path.join(temp_dir, user_id_2)
        deleted = fm.delete_user_directory(user_id_2)
        assert deleted, "Delete returned False"
        assert not os.path.exists(user2_dir), "Directory still exists after deletion"
        print(f"✅ User directory deleted successfully")
        
        # Test 11: Security - path traversal prevention
        print("\n🧪 Test 11: Security - path traversal prevention")
        dangerous_filename = "../../../etc/passwd"
        safe_path = fm.save_file(user_id_1, dangerous_filename, b"malicious")
        assert "etc" not in safe_path, "Path traversal not prevented!"
        print(f"✅ Path traversal prevented")
        print(f"   Dangerous name: {dangerous_filename}")
        print(f"   Safe path: {safe_path}")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        return True


if __name__ == "__main__":
    try:
        success = test_file_manager()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
