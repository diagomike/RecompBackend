import os
import sys
import time
from pathlib import Path

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.task_runner.task_orchestrator import TaskOrchestrator
from src.services.task_runner.registry.orchestrator import RegistryOrchestrator

def test_orchestrator_flow():
    print("--- 1. Setup Support Systems ---")
    reg_orch = RegistryOrchestrator(modules_root="modules")
    reg_orch.discover_and_register()
    
    task_orch = TaskOrchestrator()
    asset_mgr = task_orch.asset_manager # Reuse the internal manager
    
    print("--- 2. Create Dependencies (Pending & Available) ---")
    # A. Create an AVAILABLE asset (e.g., config for 'msg')
    config_asset_id = asset_mgr.create_value_asset(
        label="Message Config",
        value="Hello from Orchestrator",
        media_type="text/plain"
    )
    print(f"Created Available Asset: {config_asset_id}")

    # B. Create a PENDING asset (e.g., a promise from a previous task)
    pending_asset_id = asset_mgr.create_pending_asset(
        task_id="upstream-task-001",
        label="Future Video",
        media_type="video/mp4"
    )
    print(f"Created Pending Asset: {pending_asset_id}")

    print("\n--- 3. Submit Task (Should be BLOCKED) ---")
    # For test-module-v1, inputs are {"msg": ...}
    # Let's verify module contract first
    module = task_orch.registry_repo.get_module("test-module-v1")
    print(f"Target Module Inputs: {module['config']['inputs']}")

    # Submit task using the PENDING asset as input
    # Note: test-module-v1 expects 'msg' type 'string'. 
    # But for this test, we want to force usage of our pending asset to test blocking logic.
    # The current test-module-v1 contract says: { "key": "msg", "contract_type": "VALUE", "type": "string" }
    # So if we pass a FILE/PENDING asset, it might fail validation if we implemented strict type check?
    
    # In task_orchestrator.py: 
    # if contract_type == "ASSET": check media_type
    # It does NOT strictly forbid passing an asset of type FILE to a contract_type VALUE currently?
    # Actually, the Orchestrator code says:
    # "Check Asset Existence & Status" -> then "If contract_type == ASSET ... check constraint"
    # It doesn't explicitly fail if contract=VALUE but we pass a PENDING FILE asset. 
    # So we can abuse this for the test :)
    
    try:
        task_result = task_orch.validate_and_create_task(
            module_id="test-module-v1",
            input_map={"msg": pending_asset_id} 
        )
        task_id = task_result["task_id"]
        status = task_result["status"]
        print(f"Task Created: {task_id}, Status: {status}")
        
        if status != "BLOCKED":
            print("FAILED: Task should be BLOCKED")
            sys.exit(1)
            
    except Exception as e:
        print(f"FAILED to submit task: {e}")
        sys.exit(1)

    print("\n--- 4. Unblock Task (Fulfill Promise) ---")
    
    # Verify DB state
    task = task_orch.task_repo.get_task(task_id)
    print(f"DB Status before unblock: {task['status']}")
    print(f"Blocking Assets: {task['blocking_assets']}")
    
    # Fulfill the asset
    dummy_file = Path("temp_upstream_video.mp4")
    dummy_file.write_text("fake video")
    
    print(f"Fulfilling Asset {pending_asset_id}...")
    asset_mgr.fulfill_asset(pending_asset_id, str(dummy_file))
    
    # Trigger Event
    print(f"Triggering Asset Available Event...")
    task_orch.handle_asset_event("AVAILABLE", pending_asset_id)
    
    # Verify DB state
    updated_task = task_orch.task_repo.get_task(task_id)
    print(f"DB Status after unblock: {updated_task['status']}")
    
    if updated_task["status"] == "QUEUED":
        print("SUCCESS: Task promoted to QUEUED")
    else:
        print("FAILED: Task was not promoted")
        sys.exit(1)

    print("\nORCHESTRATOR TEST COMPLETE")
    # Cleanup
    if os.path.exists("temp_upstream_video.mp4"):
        os.remove("temp_upstream_video.mp4")

if __name__ == "__main__":
    test_orchestrator_flow()
