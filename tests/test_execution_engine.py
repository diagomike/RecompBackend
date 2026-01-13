import os
import sys
import time

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.task_runner.task_orchestrator import TaskOrchestrator
from src.services.task_runner.execution_engine import ExecutionEngine
from src.services.task_runner.registry.orchestrator import RegistryOrchestrator

def test_full_pipeline():
    print("--- 1. Reset Metadata (Scan Modules) ---")
    reg_orch = RegistryOrchestrator(modules_root="modules")
    reg_orch.discover_and_register()

    # Clear stale test data
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["task_runner_db"]
    db["tasks"].delete_many({})
    db["assets"].delete_many({})

    task_orch = TaskOrchestrator()
    engine = ExecutionEngine()
    asset_mgr = task_orch.asset_manager

    print("\n--- 2. Create Input Asset ---")
    input_val = "Test Message for Engine"
    asset_id = asset_mgr.create_value_asset(
        label="Input Msg",
        value=input_val,
        media_type="text/plain"
    )
    print(f"Created Input Asset: {asset_id}")

    print("\n--- 3. Submit Task via Orchestrator ---")
    task_info = task_orch.validate_and_create_task(
        module_id="test-module-v1",
        input_map={"msg": asset_id}
    )
    task_id = task_info["task_id"]
    output_asset_id = task_info["outputs"]["response"]
    print(f"Task Created: {task_id}, Status: {task_info['status']}")
    print(f"Output Promise: {output_asset_id}")

    if task_info["status"] != "QUEUED":
        print("FAILED: Task should be QUEUED immediately")
        sys.exit(1)

    print("\n--- 4. Run Execution Engine ---")
    success = engine.run_once()
    if not success:
        print("FAILED: Engine did not find any task to run")
        sys.exit(1)

    print("\n--- 5. Verify Results ---")
    # Verify Task Final Status
    time.sleep(1) # Give it a moment to finish DB writes if async (though it's sync here)
    task = task_orch.task_repo.get_task(task_id)
    print(f"Final Task Status: {task['status']}")
    
    if task["status"] != "COMPLETED":
        print(f"FAILED: Task status is {task['status']}, expected COMPLETED")
        if "error_log" in task:
            print(f"Error: {task['error_log']}")
        sys.exit(1)

    # Verify Output Asset
    output_asset = asset_mgr.repo.get_asset(output_asset_id)
    print(f"Output Asset Status: {output_asset['status']}")
    print(f"Output Content: {output_asset.get('value_content')}")

    if output_asset["status"] == "AVAILABLE" and "Echo: " in output_asset.get("value_content", ""):
        print(f"Verified Echo content: {output_asset.get('value_content')}")
        print("\nSUCCESS: End-to-End Pipeline Verified!")
    else:
        print("FAILED: Output asset incorrect")
        sys.exit(1)

if __name__ == "__main__":
    test_full_pipeline()
