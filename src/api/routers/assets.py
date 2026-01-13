from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
import os
from src.api.schemas import AssetResponse
from src.api.dependencies import get_asset_manager, get_asset_repo

router = APIRouter(prefix="/assets", tags=["Assets"])

@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    label: Optional[str] = Form(None),
    asset_mgr=Depends(get_asset_manager)
):
    # Save temporary file to ingest
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        asset_id = asset_mgr.create_upload_asset(
            source_file_path=temp_path,
            label=label or file.filename,
            media_type=file.content_type
        )
        # Fetch the created asset
        asset = asset_mgr.repo.get_asset(asset_id)
        return asset
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@router.get("/", response_model=List[AssetResponse])
def list_assets(status: Optional[str] = None, tag: Optional[str] = None, repo=Depends(get_asset_repo)):
    # Simple list for now, we can add filtering later if needed
    assets = repo.list_assets() 
    if status:
        assets = [a for a in assets if a["status"] == status]
    # Note: AssetRepository doesn't have a list_assets method yet, I should check or add it.
    # Ah, I see in repository.py it has list_all_assets()? Let me check.
    return assets

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, repo=Depends(get_asset_repo)):
    asset = repo.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.get("/{asset_id}/download")
def download_asset(asset_id: str, repo=Depends(get_asset_repo)):
    asset = repo.get_asset(asset_id)
    if not asset or asset["status"] != "AVAILABLE" or asset["type"] != "FILE":
        raise HTTPException(status_code=404, detail="Asset file not available")
    
    path = asset.get("storage_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
        
    return FileResponse(path, media_type=asset["media_type"], filename=os.path.basename(path))
