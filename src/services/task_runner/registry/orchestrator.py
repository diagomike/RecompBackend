import os
import time
import json
from typing import List, Dict, Any

from src.shared.database.mongo import ModuleRegistryRepository
from src.services.task_runner.registry.scanner import ModuleScanner
from src.services.task_runner.registry.environment_manager import EnvironmentManager
from src.services.task_runner.registry.runner import ModuleRunner

class RegistryOrchestrator:
    """
    Coordinates the discovery, installation, and verification of modules.
    """

    def __init__(self, modules_root: str):
        self.modules_root = modules_root
        self.repo = ModuleRegistryRepository()
        self.scanner = ModuleScanner()
        self.env_manager = EnvironmentManager()
        self.runner = ModuleRunner()

    def discover_and_register(self):
        """
        Main entry point to scan and update registry.
        """
        print(f"Scanning modules in {self.modules_root}...")
        
        # 1. Scan Directory
        found_modules = self.scanner.scan_directory(self.modules_root)
        
        for dir_name, full_path in found_modules.items():
            self._process_module(dir_name, full_path)

    def _process_module(self, dir_name: str, full_path: str):
        # 2. Validate Structure
        module_def = self.scanner.validate_module(full_path)
        if not module_def:
            print(f"Skipping {dir_name}: Invalid structure (missing module.json or main.py)")
            return

        module_name = module_def.get("name", dir_name) # Use name from json or dirname
        current_hash = self.scanner.calculate_hash(full_path)
        
        # 3. Check DB
        existing_record = self.repo.get_module(module_name)
        
        needs_install = False
        
        if not existing_record:
            print(f"New module detected: {module_name}")
            self.repo.create_module({
                "_id": module_name,
                "status": "DETECTED",
                "path": full_path,
                "version_hash": current_hash,
                "config": module_def,
                "installation_logs": [],
                "capabilities": {
                    "inputs": module_def.get("inputs", []),
                    "outputs": module_def.get("outputs", [])
                }
            })
            needs_install = True
        elif existing_record.get("version_hash") != current_hash:
            print(f"Module changed: {module_name}")
            self.repo.update_module(module_name, {
                "status": "DETECTED",
                "version_hash": current_hash,
                "config": module_def,
                "installation_logs": [] # Clear old logs? or Append? Let's clear for new install.
            })
            needs_install = True
        elif existing_record.get("status") in ["ERROR", "DETECTED", "INSTALLING"]:
            # Retry if it was stuck or failed previously
            print(f"Retrying module: {module_name} (Status: {existing_record.get('status')})")
            needs_install = True
        
        if needs_install:
            self._install_module(module_name, full_path)

    def _install_module(self, module_name: str, full_path: str):
        print(f"Installing {module_name}...")
        self.repo.update_module(module_name, {"status": "INSTALLING"})
        
        # Create Venv
        success, msg = self.env_manager.create_venv(full_path)
        self.repo.append_log(module_name, f"[Setup] {msg}")
        
        if not success:
            self.repo.update_module(module_name, {"status": "ERROR"})
            return

        # Install Requirements
        def log_callback(line):
            self.repo.append_log(module_name, f"[Pip] {line}")

        install_success = self.env_manager.install_requirements(full_path, logger_callback=log_callback)
        
        if install_success:
            self.repo.update_module(module_name, {"status": "TESTING"})
            self._test_module(module_name, full_path)
        else:
            self.repo.update_module(module_name, {"status": "ERROR"})
            self.repo.append_log(module_name, "[Setup] Pip installation failed.")

    def _test_module(self, module_name: str, full_path: str):
        print(f"Testing {module_name}...")
        
        python_exec = self.env_manager.get_python_exec(full_path)
        script_path = os.path.join(full_path, "main.py")
        
        # Test Data as "Payload"
        test_file = os.path.join(full_path, "test_data.json")
        if not os.path.exists(test_file):
            self.repo.update_module(module_name, {"status": "ERROR"})
            self.repo.append_log(module_name, "[Test] Missing test_data.json")
            return
            
        # Create a temporary Manifest for the test
        manifest_path = os.path.join(full_path, "test_manifest.json")
        try:
            with open(test_file, 'r') as f:
                test_payload = json.load(f)
            
            # Wrap validation payload into a Manifest Structure
            # We assume for testing, the manifest simply contains the inputs directly, or 
            # maybe it has a "inputs" key. Let's assume the manifest IS the envelope.
            # { "mode": "test", "inputs": { ...test_data... } }
            
            test_manifest = {
                "mode": "test",
                "task_id": "TEST_RUN",
                "inputs": test_payload
            }
            
            with open(manifest_path, 'w') as f:
                json.dump(test_manifest, f)
                
        except Exception as e:
            self.repo.update_module(module_name, {"status": "ERROR"})
            self.repo.append_log(module_name, f"[Test] Failed to create manifest: {e}")
            return

        result = self.runner.run_module(
            python_exec=python_exec,
            script_path=script_path,
            manifest_path=manifest_path
        )

        # Cleanup Manifest
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

        # Log output
        for line in result["logs"]:
            self.repo.append_log(module_name, f"[Test Output] {line}")

        if result["success"]:
            res_json = result["result"]
            if res_json and res_json.get("status") == "success":
                self.repo.update_module(module_name, {
                    "status": "AVAILABLE",
                    "python_exec": python_exec,
                    "venv_path": self.env_manager.get_venv_path(full_path)
                })
                print(f"Module {module_name} is now AVAILABLE.")
            else:
                self.repo.update_module(module_name, {"status": "ERROR"})
                self.repo.append_log(module_name, f"[Test] Validation failed. Result: {res_json}")
        else:
            self.repo.update_module(module_name, {"status": "ERROR"})
            self.repo.append_log(module_name, f"[Test] Execution failed: {result['error']}")
