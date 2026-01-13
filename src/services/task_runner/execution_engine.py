import os
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.services.task_runner.task_repository import TaskRepository
from src.services.asset_service.manager import AssetManager
from src.services.task_runner.registry.runner import ModuleRunner
from src.shared.database.mongo import ModuleRegistryRepository

class ExecutionEngine:
    """
    The Muscle. Stateless consumer that runs QUEUED tasks.
    """

    def __init__(self):
        self.task_repo = TaskRepository()
        self.asset_mgr = AssetManager()
        self.registry_repo = ModuleRegistryRepository()
        self.runner = ModuleRunner()

    def run_once(self) -> bool:
        """
        Polls for one QUEUED task and executes it.
        Returns True if a task was processed, False otherwise.
        """
        # 1. Poll for next QUEUED task
        # Note: In a real system we'd use find_one_and_update to avoid race conditions.
        # But for now, we'll simplify.
        task = self.task_repo.get_next_queued_task()
        if not task:
            return False

        task_id = task["_id"]
        print(f"[Engine] Starting Task: {task_id}")

        # Mark as RUNNING
        self.task_repo.update_task(task_id, {
            "status": "RUNNING",
            "started_at": datetime.utcnow()
        })

        try:
            # 2. Prepare Execution
            # Get Module Info
            module_id = task["module_id"]
            module = self.registry_repo.get_module(module_id)
            if not module or module["status"] != "AVAILABLE":
                raise Exception(f"Module {module_id} is not AVAILABLE")

            python_exec = module["python_exec"]
            script_path = os.path.join(module["path"], module["config"]["entry_point"])

            # Materialize Manifest
            manifest_path = self._prepare_manifest(task)
            print(f"[Engine] Manifest generated: {manifest_path}")

            # 3. Execute
            print(f"[Engine] Executing {module_id}...")
            result = self.runner.run_module(
                python_exec=python_exec,
                script_path=script_path,
                manifest_path=manifest_path,
                timeout=task.get("config", {}).get("timeout", 600)
            )

            # 4. Finalize
            self._finalize_task(task, result)
            
            # Cleanup manifest
            if os.path.exists(manifest_path):
                os.remove(manifest_path)
            
            return True

        except Exception as e:
            print(f"[Engine] Task {task_id} FAILED: {str(e)}")
            self.task_repo.update_task(task_id, {
                "status": "FAILED",
                "error_log": str(e),
                "finished_at": datetime.utcnow()
            })
            # Fail all output assets
            for output_key, asset_id in task["output_map"].items():
                self.asset_mgr.fail_asset(asset_id, f"Parent task {task_id} failed: {str(e)}")
            
            return True

    def _prepare_manifest(self, task: Dict[str, Any]) -> str:
        """
        Resolves asset IDs to physical paths and creates a temporary manifest JSON.
        """
        input_map = task["input_map"]
        resolved_inputs = {}

        # Create a task-specific temp dir for Config VALUES materialized as files
        temp_dir = tempfile.mkdtemp(prefix=f"task_{task['_id']}_")
        
        for key, asset_id in input_map.items():
            path = self.asset_mgr.resolve_to_path(asset_id, temp_dir=temp_dir)
            if not path:
                raise Exception(f"Could not resolve input asset {asset_id} for key {key}")
            resolved_inputs[key] = path

        manifest = {
            "mode": "run",
            "task_id": task["_id"],
            "inputs": resolved_inputs,
            "config": task.get("config", {})
        }

        fd, manifest_path = tempfile.mkstemp(suffix=".json", prefix=f"manifest_{task['_id']}_")
        with os.fdopen(fd, 'w') as f:
            json.dump(manifest, f)
        
        return manifest_path

    def _finalize_task(self, task: Dict[str, Any], result: Dict[str, Any]):
        """
        Handles fulfillment of output assets based on execution result and module contract.
        """
        task_id = task["_id"]
        
        if result["success"]:
            print(f"[Engine] Task {task_id} succeeded.")
            res_data = result.get("result")
            
            # Fetch module contract to know output types
            module = self.registry_repo.get_module(task["module_id"])
            output_defs = {o["key"]: o for o in module.get("config", {}).get("outputs", [])}

            if res_data and isinstance(res_data, dict):
                # Check for "outputs" sub-dict or top-level keys
                outputs_from_module = res_data.get("outputs") or res_data

                for key, asset_id in task["output_map"].items():
                    val = outputs_from_module.get(key)
                    out_def = output_defs.get(key, {})
                    contract_type = out_def.get("contract_type", "VALUE")

                    if val is not None:
                        try:
                            if contract_type == "ASSET":
                                # Fulfill as Path
                                self.asset_mgr.fulfill_asset(asset_id, value=str(val), is_path=True)
                            else:
                                # Fulfill as Value
                                self.asset_mgr.fulfill_asset(asset_id, value=val, is_path=False)
                        except Exception as e:
                            self.asset_mgr.fail_asset(asset_id, f"Fulfillment failed: {e}")
                    else:
                        self.asset_mgr.fail_asset(asset_id, f"Module did not provide output for key: {key}")

            self.task_repo.update_task(task_id, {
                "status": "COMPLETED",
                "finished_at": datetime.utcnow(),
                "logs": result["logs"]
            })
            
            # Trigger unblocking of dependent tasks
            from src.services.task_runner.task_orchestrator import TaskOrchestrator
            orch = TaskOrchestrator()
            for asset_id in task["output_map"].values():
                 orch.handle_asset_event("AVAILABLE", asset_id)

        else:
            print(f"[Engine] Task {task_id} failed: {result['error']}")
            self.task_repo.update_task(task_id, {
                "status": "FAILED",
                "error_log": result["error"],
                "logs": result["logs"],
                "finished_at": datetime.utcnow()
            })
            # Fail all output assets
            for asset_id in task["output_map"].values():
                self.asset_mgr.fail_asset(asset_id, f"Execution failed: {result['error']}")

