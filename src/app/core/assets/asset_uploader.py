import os
import uuid
import logging
from fastapi import UploadFile
from urllib.parse import urljoin
from src.app.config.settings import settings

class LocalAssetUploader:
    """
    Handles file uploads to local storage.
    
    🎓 FASTAPI MIGRATION NOTE:
    In Flask, we used 'werkzeug.datastructures.FileStorage'.
    In FastAPI, we use 'fastapi.UploadFile' which is more efficient 
    and supports async file operations.
    """
    
    def __init__(self, base_upload_dir: str = None, base_url: str = None):
        self.base_upload_dir = base_upload_dir or settings.general.BASE_UPLOAD_DIR
        self.base_url = base_url or settings.general.BASE_URL
        
        # Ensure upload directory exists
        if not os.path.exists(self.base_upload_dir):
            os.makedirs(self.base_upload_dir, exist_ok=True)
            logging.info(f"📁 Created upload directory: {self.base_upload_dir}")

    async def upload(self, file: UploadFile) -> str:
        """
        Uploads an image file asynchronously and returns its access URL.
        """
        if not file:
            raise ValueError("No file provided for upload")
            
        # Generate unique filename
        filename = file.filename if file.filename else "upload.jpg"
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(self.base_upload_dir, unique_filename)
        
        try:
            # Async read and write
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            logging.info(f"✅ File uploaded: {unique_filename} ({len(content)} bytes)")
        except Exception as e:
            logging.error(f"❌ Failed to save file: {str(e)}")
            raise OSError(f"Failed to save file: {str(e)}")
        finally:
            await file.close()
            
        # Generate and return the file URL
        # Ensure base_url ends with / or urljoin handles it
        base_url = self.base_url if self.base_url.endswith('/') else self.base_url + '/'
        file_url = urljoin(base_url, unique_filename)
        
        return file_url

    async def upload_bytes(self, content: bytes, filename: str = "upload.jpg") -> str:
        """
        Uploads raw image bytes asynchronously and returns its access URL.
        """
        if not content:
            raise ValueError("No content provided for upload")
            
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(self.base_upload_dir, unique_filename)
        
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            
            logging.info(f"✅ Bytes uploaded: {unique_filename} ({len(content)} bytes)")
        except Exception as e:
            logging.error(f"❌ Failed to save file from bytes: {str(e)}")
            raise OSError(f"Failed to save file: {str(e)}")
            
        base_url = self.base_url if self.base_url.endswith('/') else self.base_url + '/'
        file_url = urljoin(base_url, unique_filename)
        
        return file_url
