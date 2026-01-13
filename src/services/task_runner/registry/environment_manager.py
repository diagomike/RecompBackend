import os
import sys
import subprocess
import venv
from typing import Tuple

class EnvironmentManager:
    """
    Manages Virtual Environments for modules.
    """

    def get_venv_path(self, module_path: str) -> str:
        return os.path.join(module_path, "venv")

    def get_python_exec(self, module_path: str) -> str:
        venv_path = self.get_venv_path(module_path)
        if sys.platform == "win32":
            return os.path.join(venv_path, "Scripts", "python.exe")
        else:
            return os.path.join(venv_path, "bin", "python")

    def create_venv(self, module_path: str) -> Tuple[bool, str]:
        """
        Creates a virtual environment in the module directory.
        Returns: (Success, Message)
        """
        venv_path = self.get_venv_path(module_path)
        try:
            builder = venv.EnvBuilder(with_pip=True)
            builder.create(venv_path)
            return True, f"Created venv at {venv_path}"
        except Exception as e:
            return False, f"Failed to create venv: {str(e)}"

    def install_requirements(self, module_path: str, logger_callback=None) -> bool:
        """
        Installs requirements.txt from the module path into the venv.
        """
        python_exec = self.get_python_exec(module_path)
        req_file = os.path.join(module_path, "requirements.txt")

        if not os.path.exists(req_file):
            if logger_callback:
                logger_callback("No requirements.txt found. Skipping pip install.")
            return True

        cmd = [python_exec, "-m", "pip", "install", "-r", "requirements.txt"]
        
        try:
            # We use Popen to stream output if needed, but for simplicity here check_output 
            # or a loop reading stdout is better for realtime logging.
            process = subprocess.Popen(
                cmd,
                cwd=module_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:
                if logger_callback:
                    logger_callback(line.strip())
            
            process.wait()
            return process.returncode == 0
        except Exception as e:
            if logger_callback:
                logger_callback(f"Pip install crashed: {str(e)}")
            return False
