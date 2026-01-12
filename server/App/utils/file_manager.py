"""
File Manager - Handles document storage with user-based directory structure

Stores uploaded files in: server/upload/{user_id}/{filename}
Provides utilities for saving, retrieving, and managing user documents.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages file storage with user-based directory isolation."""
    
    def __init__(self, base_upload_dir: str = None):
        """
        Initialize FileManager.
        
        Args:
            base_upload_dir: Base directory for uploads. 
                           If None, uses 'server/upload' relative to this file.
        """
        if base_upload_dir is None:
            # Default: server/upload/ directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_upload_dir = os.path.normpath(os.path.join(current_dir, "../../upload"))
        
        self.base_upload_dir = base_upload_dir
        self._ensure_base_dir()
    
    def _ensure_base_dir(self):
        """Ensure base upload directory exists."""
        os.makedirs(self.base_upload_dir, exist_ok=True)
    
    def get_user_upload_dir(self, user_id: str) -> str:
        """
        Get the upload directory for a specific user.
        Creates the directory if it doesn't exist.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            Absolute path to the user's upload directory
        """
        user_dir = os.path.join(self.base_upload_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def save_file(self, user_id: str, filename: str, file_bytes: bytes) -> str:
        """
        Save a file to the user's upload directory.
        
        Args:
            user_id: The user's unique identifier
            filename: Original filename
            file_bytes: File content as bytes
            
        Returns:
            Absolute path to the saved file
            
        Raises:
            ValueError: If filename is invalid
            IOError: If file write fails
        """
        # Validate filename
        if not filename or len(filename) == 0:
            raise ValueError("Filename cannot be empty")
        
        # Security: Remove path traversal attempts
        filename = os.path.basename(filename)
        
        # Get user directory
        user_dir = self.get_user_upload_dir(user_id)
        
        # Build file path
        file_path = os.path.join(user_dir, filename)
        
        # Write file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            print(f"✅ File saved: {file_path}")
            return file_path
        except Exception as e:
            raise IOError(f"Failed to save file {filename}: {str(e)}")
    
    def get_file(self, user_id: str, filename: str) -> Optional[bytes]:
        """
        Retrieve a file from the user's upload directory.
        
        Args:
            user_id: The user's unique identifier
            filename: The filename to retrieve
            
        Returns:
            File content as bytes, or None if file doesn't exist
        """
        user_dir = self.get_user_upload_dir(user_id)
        file_path = os.path.join(user_dir, filename)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Failed to read file {filename}: {str(e)}")
            return None
    
    def list_user_files(self, user_id: str) -> list:
        """
        List all files in a user's upload directory.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            List of filenames
        """
        user_dir = self.get_user_upload_dir(user_id)
        
        try:
            files = os.listdir(user_dir)
            return [f for f in files if os.path.isfile(os.path.join(user_dir, f))]
        except Exception as e:
            print(f"⚠️  Failed to list files for user {user_id}: {str(e)}")
            return []
    
    def delete_file(self, user_id: str, filename: str) -> bool:
        """
        Delete a file from the user's upload directory.
        
        Args:
            user_id: The user's unique identifier
            filename: The filename to delete
            
        Returns:
            True if successful, False otherwise
        """
        user_dir = self.get_user_upload_dir(user_id)
        file_path = os.path.join(user_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            return False
        
        try:
            os.remove(file_path)
            print(f"✅ File deleted: {file_path}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to delete file {filename}: {str(e)}")
            return False
    
    def delete_user_directory(self, user_id: str) -> bool:
        """
        Delete entire user's upload directory (for user account deletion).
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        user_dir = self.get_user_upload_dir(user_id)
        
        if not os.path.exists(user_dir):
            return True  # Already gone
        
        try:
            shutil.rmtree(user_dir)
            print(f"✅ User directory deleted: {user_dir}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to delete user directory: {str(e)}")
            return False
    
    def get_file_size(self, user_id: str, filename: str) -> int:
        """
        Get the size of a file in bytes.
        
        Args:
            user_id: The user's unique identifier
            filename: The filename
            
        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        user_dir = self.get_user_upload_dir(user_id)
        file_path = os.path.join(user_dir, filename)
        
        if not os.path.exists(file_path):
            return 0
        
        return os.path.getsize(file_path)
    
    def get_user_storage_info(self, user_id: str) -> dict:
        """
        Get storage information for a user.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            Dictionary with file count and total size
        """
        user_dir = self.get_user_upload_dir(user_id)
        
        try:
            files = self.list_user_files(user_id)
            total_size = sum(
                os.path.getsize(os.path.join(user_dir, f)) 
                for f in files
            )
            
            return {
                "user_id": str(user_id),
                "file_count": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files": files
            }
        except Exception as e:
            print(f"⚠️  Failed to get storage info: {str(e)}")
            return {
                "user_id": str(user_id),
                "file_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "files": []
            }


# Global instance
_file_manager = None

def get_file_manager(base_upload_dir: str = None) -> FileManager:
    """Get the global FileManager instance."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager(base_upload_dir)
    return _file_manager
