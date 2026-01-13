import uuid
from typing import Dict, Any, List, Optional
from src.services.task_runner.task_repository import TaskRepository
from src.services.asset_service.manager import AssetManager
from src.services.asset_service.repository import AssetRepository
from src.shared.database.mongo import ModuleRegistryRepository

class TaskOrchestrator:
    """
    The Brain. Validates contracts, manages state, and resolves dependencies.
    """

    def __init__(self):
        self.task_repo = TaskRepository()
        self.asset_manager = AssetManager()
        self.asset_repo = AssetRepository()
        self.registry_repo = ModuleRegistryRepository()

    def validate_and_create_task(self, module_id: str, input_map: Dict[str, str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main Entry Point.
        1. Validates inputs against Module Contract.
        2. Creates PENDING assets for outputs.
        3. Creates Task Record.
        4. Sets status (BLOCKED or QUEUED).
        """
        # 1. Fetch Module Contract
        module = self.registry_repo.get_module(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found.")

        module_inputs = module.get("config", {}).get("inputs", [])
        module_outputs = module.get("config", {}).get("outputs", [])

        # 2. Validate Inputs & Identify Blockers
        blocking_assets = []
        validated_input_map = {}

        for inp_def in module_inputs:
            key = inp_def["key"]
            contract_type = inp_def["contract_type"]
            input_asset_id = input_map.get(key)

            if not input_asset_id:
                raise ValueError(f"Missing required input: {key}")

            # Check Asset Existence & Status
            asset = self.asset_repo.get_asset(input_asset_id)
            if not asset:
                raise ValueError(f"Input asset {input_asset_id} not found.")

            if asset["status"] == "FAILED":
                 raise ValueError(f"Input asset {input_asset_id} is FAILED.")
            
            # Type Check (Basic Media Type check if applicable)
            if contract_type == "ASSET":
                allowed_types = inp_def.get("constraints", {}).get("media_types", [])
                if allowed_types and asset["media_type"] not in allowed_types:
                    raise ValueError(f"Asset {asset['label']} type {asset['media_type']} not allowed. Expected: {allowed_types}")

            if asset["status"] == "PENDING":
                blocking_assets.append(input_asset_id)
            
            validated_input_map[key] = input_asset_id

        # 3. Create Output Promises
        task_id = str(uuid.uuid4())
        output_map = {}
        
        for out_def in module_outputs:
            key = out_def["key"]
            label = out_def.get("label", f"{key}_output")
            media_type = out_def.get("media_type", "application/octet-stream")
            
            asset_id = self.asset_manager.create_pending_asset(
                task_id=task_id,
                label=label,
                media_type=media_type
            )
            output_map[key] = asset_id

        # 4. Create Task Record
        status = "BLOCKED" if blocking_assets else "QUEUED"
        
        task_data = {
            "_id": task_id,
            "module_id": module_id,
            "status": status,
            "input_map": validated_input_map,
            "output_map": output_map,
            "config": config or {},
            "blocking_assets": blocking_assets,
            "error_log": None
        }
        
        self.task_repo.create_task(task_data)
        
        return {
            "task_id": task_id,
            "status": status,
            "outputs": output_map
        }

    def handle_asset_event(self, event_type: str, asset_id: str):
        """
        Triggered when an asset becomes AVAILABLE.
        Unblocks tasks waiting for this asset.
        """
        if event_type != "AVAILABLE":
            return

        blocked_tasks = self.task_repo.find_blocked_tasks_by_asset(asset_id)
        
        for task in blocked_tasks:
            # Remove this asset from blocking list
            new_blockers = [a for a in task["blocking_assets"] if a != asset_id]
            
            updates = {"blocking_assets": new_blockers}
            
            # If no more blockers, promote to QUEUED
            if not new_blockers:
                updates["status"] = "QUEUED"
                print(f"Task {task['_id']} promoted to QUEUED.")
            
            self.task_repo.update_task(task["_id"], updates)

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        return self.task_repo.get_next_queued_task()
