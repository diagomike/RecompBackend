import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from src.services.asset_service.repository import AssetRepository

class AssetManager:
    """
    Manages the lifecycle of Assets (Files and Values).
    """

    def __init__(self, storage_root: str = "storage"):
        self.repo = AssetRepository()
        self.storage_root = Path(storage_root).absolute()
        self.uploads_dir = self.storage_root / "uploads"
        self.generated_dir = self.storage_root / "generated"
        
        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def create_upload_asset(self, source_file_path: str, label: str, media_type: str) -> str:
        """
        Ingests an existing file into the storage and registers it as AVAILABLE.
        """
        source_path = Path(source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file {source_file_path} does not exist.")

        # Create a unique storage path: uploads/YYYY-MM-DD/{asset_id}_{filename}
        date_str = datetime.now().strftime("%Y-%m-%d")
        dest_dir = self.uploads_dir / date_str
        dest_dir.mkdir(parents=True, exist_ok=True)

        asset_id = str(uuid.uuid4())
        dest_path = dest_dir / f"{asset_id}_{source_path.name}"
        
        # Copy file to storage
        shutil.copy2(source_path, dest_path)

        asset_data = {
            "_id": asset_id,
            "label": label,
            "status": "AVAILABLE",
            "type": "FILE",
            "media_type": media_type,
            "storage_path": str(dest_path),
            "tags": ["upload"]
        }
        
        return self.repo.create_asset(asset_data)

    def create_pending_asset(self, task_id: str, label: str, media_type: str) -> str:
        """
        Creates a PENDING asset promised by a specific task.
        """
        asset_data = {
            "label": label,
            "status": "PENDING",
            "type": "FILE",
            "media_type": media_type,
            "created_by_task": task_id,
            "storage_path": None,
            "tags": ["task-output"]
        }
        return self.repo.create_asset(asset_data)

    def fulfill_asset(self, asset_id: str, actual_file_path: str) -> bool:
        """
        Moves a produced file into the generated/task_id folder and marks asset as AVAILABLE.
        """
        asset = self.repo.get_asset(asset_id)
        if not asset:
            return False
        
        task_id = asset.get("created_by_task", "unknown")
        dest_dir = self.generated_dir / task_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(actual_file_path)
        dest_path = dest_dir / source_path.name

        # Atomically move file
        shutil.move(str(source_path), str(dest_path))

        self.repo.update_asset(asset_id, {
            "status": "AVAILABLE",
            "storage_path": str(dest_path)
        })
        return True

    def create_value_asset(self, label: str, value: Any, media_type: str = "application/json") -> str:
        """
        Creates a VALUE type asset (stored in DB).
        """
        asset_data = {
            "label": label,
            "status": "AVAILABLE",
            "type": "VALUE",
            "media_type": media_type,
            "value_content": value,
            "storage_path": None
        }
        return self.repo.create_asset(asset_data)

    def resolve_to_path(self, asset_id: str, temp_dir: Optional[str] = None) -> Optional[str]:
        """
        Resolves an asset to a physical file path.
        If it's a VALUE, it writes it to a temporary file.
        """
        asset = self.repo.get_asset(asset_id)
        if not asset or asset["status"] != "AVAILABLE":
            return None

        if asset["type"] == "FILE":
            return asset["storage_path"]
        
        if asset["type"] == "VALUE":
            # Write value to temp file
            import tempfile
            from pathlib import Path
            
            content = asset["value_content"]
            suffix = ".json" if asset["media_type"] == "application/json" else ".txt"
            
            # Use provided temp_dir or system default
            fd, path = tempfile.mkstemp(suffix=suffix, dir=temp_dir, prefix=f"asset_{asset_id}_")
            with os.fdopen(fd, 'w') as f:
                if isinstance(content, (dict, list)):
                    import json
                    json.dump(content, f)
                else:
                    f.write(str(content))
            return path
        
        return None
