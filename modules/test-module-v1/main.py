import sys
import argparse
import json

def run_from_manifest(manifest_path):
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        mode = manifest.get("mode", "run")
        inputs = manifest.get("inputs", {})
        
        if mode == "test":
            # Test logic
            if "msg" in inputs:
                print(json.dumps({"status": "success", "echo": inputs["msg"]}))
            elif "test_key" in inputs:
                 print(json.dumps({"status": "success", "echo": inputs["test_key"]}))
            else:
                print(json.dumps({"status": "success", "message": "No input key found, but alive"}))
                
        elif mode == "run":
            # Task logic
            print(f"Processing task {manifest.get('task_id', 'unknown')}")
            result = {
                "status": "success",
                "response": f"Echo: {inputs.get('msg', 'no msg')}"
            }
            print(json.dumps(result))
            
    except Exception as e:
        print(f"Error reading manifest: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path to input manifest JSON")
    
    args = parser.parse_args()
    run_from_manifest(args.manifest)
