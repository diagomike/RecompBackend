import os
import json
import hashlib
from typing import Dict, Any, Optional

class ModuleScanner:
    """
    Scans the modules directory and validates module structure.
    """

    def scan_directory(self, modules_root: str) -> Dict[str, str]:
        """
        Returns a dict of {module_dir_name: full_path} for potential modules.
        """
        if not os.path.exists(modules_root):
            return {}
        
        modules = {}
        for entry in os.listdir(modules_root):
            full_path = os.path.join(modules_root, entry)
            if os.path.isdir(full_path):
                # Simple check: ignore __pycache__ or hidden dirs
                if not entry.startswith("__") and not entry.startswith("."):
                    modules[entry] = full_path
        return modules

    def validate_module(self, module_path: str) -> Optional[Dict[str, Any]]:
        """
        Checks if module.json and main.py exist.
        Returns parsed module.json if valid, else None.
        """
        json_path = os.path.join(module_path, "module.json")
        main_path = os.path.join(module_path, "main.py")

        if not os.path.exists(json_path) or not os.path.exists(main_path):
            return None

        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                # Basic schema check
                required_keys = ["name", "version", "entry_point", "inputs", "outputs"]
                if not all(k in data for k in required_keys):
                    return None
                
                # Extended Validation: Inputs
                for inp in data.get("inputs", []):
                    if "key" not in inp or "contract_type" not in inp:
                        # Invalid input definition
                        return None
                    if inp["contract_type"] not in ["ASSET", "VALUE"]:
                        return None
                        
                # Extended Validation: Resources (Optional but recommended)
                # If present, check structure? For now, just ensure it doesn't crash.
                    
                return data
        except Exception:
            pass
        
        return None

    def calculate_hash(self, module_path: str) -> str:
        """
        Calculates a hash of the module files to detect changes.
        In a real scenario, this should walk the dir and hash all relevant files.
        For now, we'll hash module.json and main.py.
        """
        hasher = hashlib.md5()
        for filename in ["module.json", "main.py", "requirements.txt"]:
            fpath = os.path.join(module_path, filename)
            if os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    buf = f.read()
                    hasher.update(buf)
        return hasher.hexdigest()
