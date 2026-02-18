"""
Download Routes

This module provides routes for file and model downloads.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import os
from pathlib import Path
import uuid
import aiohttp
import asyncio

router = APIRouter(prefix="/api/download")

# Store download tasks
download_tasks = {}

class DownloadRequest(BaseModel):
    url: str
    filename: str

@router.post("/file")
async def download_file(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start a file download in the background"""
    task_id = str(uuid.uuid4())
    
    download_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "filename": request.filename,
        "url": request.url
    }
    
    # Start background task
    background_tasks.add_task(
        download_file_worker,
        task_id,
        request.url,
        request.filename
    )
    
    return {"task_id": task_id, "status": "started"}

@router.get("/task/{task_id}")
async def get_download_status(task_id: str):
    """Get download task status"""
    if task_id not in download_tasks:
        raise HTTPException(404, "Task not found")
    
    return download_tasks[task_id]

@router.get("/files")
async def list_downloaded_files():
    """List downloaded files in the files directory"""
    files_dir = Path("app/files")
    files_dir.mkdir(exist_ok=True)
    
    files = []
    for file_path in files_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "name": file_path.name,
                "size": stat.st_size,
                "size_human": _format_size(stat.st_size),
                "modified": stat.st_mtime
            })
    
    return {"files": files}

@router.delete("/file/{filename}")
async def delete_downloaded_file(filename: str):
    """Delete a downloaded file"""
    files_dir = Path("app/files")
    file_path = files_dir / filename
    
    # Security check
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File not found")
    
    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    
    try:
        file_path.unlink()
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(500, f"Failed to delete file: {str(e)}")

async def download_file_worker(task_id: str, url: str, filename: str):
    """Background worker for file downloads"""
    try:
        download_tasks[task_id]["status"] = "downloading"
        
        # Ensure files directory exists
        files_dir = Path("app/files")
        files_dir.mkdir(exist_ok=True)
        
        file_path = files_dir / filename
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(400, f"Failed to download: {response.status}")
                
                total_size = int(response.headers.get('content-length', 0))
                download_tasks[task_id]["total_bytes"] = total_size
                
                downloaded = 0
                with open(file_path, 'wb') as file:
                    async for chunk in response.content.iter_chunked(8192):
                        file.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                        download_tasks[task_id].update({
                            "progress": round(progress, 2),
                            "downloaded_bytes": downloaded
                        })
        
        download_tasks[task_id]["status"] = "completed"
        download_tasks[task_id]["file_path"] = str(file_path)
        
    except Exception as e:
        download_tasks[task_id]["status"] = "failed"
        download_tasks[task_id]["error"] = str(e)

def _format_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f}{size_names[i]}"
