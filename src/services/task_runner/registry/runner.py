import subprocess
import json
import logging
from typing import Dict, Any, Optional

class ModuleRunner:
    """
    Executes a module in its isolated environment via Manifest.
    """

    def run_module(
        self,
        python_exec: str,
        script_path: str,
        manifest_path: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Runs the module via CLI using the standardized --manifest argument.
        Command: <python_exec> <script_path> --manifest <manifest_path>
        
        Returns:
            Dict containing:
            - success: bool
            - logs: list of strings (stdout/stderr)
            - result: parsed JSON result (if any)
            - error: error message (if any)
        """
        cmd = [python_exec, script_path, "--manifest", manifest_path]
        
        logs = []
        result_data = None
        success = False
        error_msg = None

        try:
            # Run subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr into stdout for simple logging
                text=True
            )

            # Capture output
            for line in process.stdout:
                line_stripped = line.strip()
                logs.append(line_stripped)
                pass

            process.wait(timeout=timeout)

            # Attempt to extract result from logs (Last valid JSON wins)
            for line in reversed(logs):
                try:
                    possible_json = json.loads(line)
                    if isinstance(possible_json, dict):
                        result_data = possible_json
                        break
                except json.JSONDecodeError:
                    continue

            if process.returncode == 0:
                success = True
            else:
                error_msg = f"Process exited with code {process.returncode}"

        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "Process timed out"
            logs.append(error_msg)
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            logs.append(error_msg)

        return {
            "success": success,
            "logs": logs,
            "result": result_data,
            "error": error_msg
        }
