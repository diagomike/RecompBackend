import os
import sys
import time
import sys
import os

# Add root to sys.path to allow src.* imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.task_runner.registry.orchestrator import RegistryOrchestrator
from src.shared.database.mongo import ModuleRegistryRepository

def main():
    # Ensure raw paths for windows compatibility if needed, but python usually handles typical paths fine.
    root_dir = os.getcwd()
    modules_dir = os.path.join(root_dir, "modules")
    
    print(f"Testing Registry with modules in: {modules_dir}")
    
    orchestrator = RegistryOrchestrator(modules_dir)
    orchestrator.discover_and_register()
    
    # Check status
    repo = ModuleRegistryRepository()
    module = repo.get_module("test-module-v1")
    
    if not module:
        print("FAILED: Module not found in DB")
        sys.exit(1)
        
    print(f"Module Status: {module.get('status')}")
    print("Logs:")
    for log in module.get('installation_logs', []):
        print(f"  {log}")
        
    if module.get('status') == "AVAILABLE":
        print("SUCCESS: Module is available.")
        # Verify inputs schema was captured
        inputs = module.get("config", {}).get("inputs", [])
        if inputs and inputs[0].get("contract_type") == "VALUE":
             print("SUCCESS: Module contract (inputs) correctly registered.")
        else:
             print("FAILED: Module contract not captured.")
             sys.exit(1)
    else:
        print("FAILED: Module is not available.")
        sys.exit(1)

if __name__ == "__main__":
    main()
