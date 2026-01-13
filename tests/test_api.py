import os
import sys
import json
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.main import app
from src.api.dependencies import get_task_repo, get_asset_repo, get_registry_repo

client = TestClient(app)

def test_api_flow():
    print("\n--- 1. Resetting Data ---")
    import pymongo
    conn = pymongo.MongoClient("mongodb://localhost:27017/")
    db = conn["task_runner_db"]
    db["tasks"].delete_many({})
    db["assets"].delete_many({})

    print("\n--- 2. Scanning Modules ---")
    response = client.post("/modules/scan")
    assert response.status_code == 200
    
    # Wait for scan to complete in DB
    time.sleep(2) # Modules take some time to install venvs

    print("\n--- 3. Listing Modules ---")
    response = client.get("/modules/")
    assert response.status_code == 200
    modules = response.json()
    assert len(modules) > 0
    test_module = modules[0]
    print(f"Found module: {test_module['id']}")

    print("\n--- 4. Uploading Asset ---")
    dummy_file = Path("api_test_input.txt")
    dummy_file.write_text("Hello API")
    try:
        with open(dummy_file, "rb") as f:
            response = client.post(
                "/assets/upload",
                files={"file": ("api_test_input.txt", f, "text/plain")},
                data={"label": "API Test Asset"}
            )
        assert response.status_code == 200
        asset = response.json()
        asset_id = asset["_id"]
        print(f"Uploaded Asset ID: {asset_id}")

        print("\n--- 5. Submitting Task ---")
        # For test-module-v1, we need 'msg'
        response = client.post(
            "/tasks/",
            json={
                "module_id": "test-module-v1",
                "input_mapping": {"msg": asset_id},
                "config": {}
            }
        )
        assert response.status_code == 200
        task = response.json()
        task_id = task["_id"]
        print(f"Created Task ID: {task_id}")

        print("\n--- 6. Verifying Task Status ---")
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] in ["QUEUED", "COMPLETED", "RUNNING"] # Depends if engine is running

    finally:
        if dummy_file.exists():
            dummy_file.unlink()

if __name__ == "__main__":
    import time
    test_api_flow()
