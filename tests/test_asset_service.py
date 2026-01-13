import os
import sys
from pathlib import Path

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.asset_service.manager import AssetManager

def test_asset_flow():
    manager = AssetManager()
    
    print("--- Testing Asset Ingestion ---")
    sample_file = Path("tests/assets/sample_input.txt")
    if not sample_file.exists():
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text("Hello Asset World")

    asset_id = manager.create_upload_asset(
        str(sample_file), 
        label="Sample Text", 
        media_type="text/plain"
    )
    print(f"Created Asset ID: {asset_id}")
    
    asset = manager.repo.get_asset(asset_id)
    print(f"Asset Status: {asset['status']}")
    print(f"Storage Path: {asset['storage_path']}")

    print("\n--- Testing Pending/Fulfill Flow ---")
    task_id = "test-task-999"
    pending_id = manager.create_pending_asset(
        task_id=task_id,
        label="Task Output",
        media_type="video/mp4"
    )
    print(f"Created Pending Asset ID: {pending_id}")
    
    # Simulate a file being produced by a module
    dummy_output = Path(f"temp_output_{task_id}.mp4")
    dummy_output.write_text("DUMMY VIDEO DATA")
    
    print(f"Fulfilling asset {pending_id} with {dummy_output}...")
    manager.fulfill_asset(pending_id, str(dummy_output))
    
    updated_asset = manager.repo.get_asset(pending_id)
    print(f"Updated Status: {updated_asset['status']}")
    print(f"Updated Storage Path: {updated_asset['storage_path']}")

    print("\n--- Testing Value Asset & Resolution ---")
    value_id = manager.create_value_asset(
        label="Config String",
        value={"threshold": 0.8, "mode": "fast"},
        media_type="application/json"
    )
    print(f"Created Value Asset ID: {value_id}")
    
    resolved_path = manager.resolve_to_path(value_id)
    print(f"Resolved VALUE to path: {resolved_path}")
    if resolved_path and os.path.exists(resolved_path):
        with open(resolved_path, 'r') as f:
            print(f"Content of resolved file: {f.read()}")
        os.remove(resolved_path) # Cleanup temp file

    print("\nASSET MANAGER TEST COMPLETE")

if __name__ == "__main__":
    test_asset_flow()
