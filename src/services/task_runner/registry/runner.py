import subprocess
import json
import logging
from typing import Dict, Any, Optional

class ModuleRunner:
    """
    Executes a module in its isolated environment.
    """

    def run_module(
        self,
        python_exec: str,
        script_path: str,
        mode: str,
        args: Dict[str, Any] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Runs the module via CLI.
        Command constructed: <python_exec> <script_path> --mode <mode> --<key> <value> ...
        
        Returns:
            Dict containing:
            - success: bool
            - logs: list of strings (stdout/stderr)
            - result: parsed JSON result (if any)
            - error: error message (if any)
        """
        if args is None:
            args = {}

        cmd = [python_exec, script_path, "--mode", mode]
        
        # Convert args to CLI flags
        for key, value in args.items():
            cmd.append(f"--{key}")
            # If complex object, maybe stringify or pass file path. 
            # For strict CLI, we assume strings or file paths.
            cmd.append(str(value))

        logs = []
        result_data = None
        success = False
        error_msg = None

        try:
            # Run subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Capture output
            for line in process.stdout:
                line_stripped = line.strip()
                logs.append(line_stripped)
                
                # Check for magic prefix if we want to parse specific result, 
                # or just parse the last line as JSON? 
                # The spec said: "The final line of output (or a specific JSON block) is parsed as the result."
                # Let's try to parse every line as JSON to see if it's the result, 
                # otherwise treat as log. A robust way is to have the module print 
                # a specific prefix like "RESULT: {...}" but we can try parsing the last valid JSON.
                pass

            process.wait(timeout=timeout)

            # Attempt to extract result from logs
            # Strategy: Reverse iterate logs to find valid JSON
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
