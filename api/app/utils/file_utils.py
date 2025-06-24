import os
import uuid
from typing import Optional
from fastapi import UploadFile
from loguru import logger

def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Validate if file extension is allowed"""
    if not filename:
        return False
    
    file_extension = os.path.splitext(filename.lower())[1]
    return file_extension in allowed_extensions

def validate_file_size(file_content: bytes, max_size: int) -> bool:
    """Validate if file size is within limits"""
    return len(file_content) <= max_size

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename"""
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"

def save_uploaded_file(file_content: bytes, filename: str, upload_dir: str) -> str:
    """Save uploaded file to disk"""
    try:
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"File saved: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise

def cleanup_file(file_path: str) -> bool:
    """Delete file from disk"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False
