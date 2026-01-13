from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.api.schemas import ModuleResponse
from src.api.dependencies import get_registry_repo, get_registry_orchestrator

router = APIRouter(prefix="/modules", tags=["Modules"])

@router.get("/", response_model=List[ModuleResponse])
def list_modules(repo=Depends(get_registry_repo)):
    modules = repo.list_modules()
    # Transform to schema if necessary, but repo returns dicts compatible with response_model
    # We need to map 'config.inputs' etc. if the schema expects flattened
    results = []
    for m in modules:
        results.append({
            "id": m["_id"],
            "status": m["status"],
            "inputs": m["config"].get("inputs", []),
            "outputs": m["config"].get("outputs", []),
            "path": m["path"],
            "version_hash": m["version_hash"]
        })
    return results

@router.get("/{module_id}", response_model=ModuleResponse)
def get_module(module_id: str, repo=Depends(get_registry_repo)):
    m = repo.get_module(module_id)
    if not m:
        raise HTTPException(status_code=404, detail="Module not found")
    return {
        "id": m["_id"],
        "status": m["status"],
        "inputs": m["config"].get("inputs", []),
        "outputs": m["config"].get("outputs", []),
        "path": m["path"],
        "version_hash": m["version_hash"]
    }

@router.post("/scan")
def scan_modules(orch=Depends(get_registry_orchestrator)):
    orch.discover_and_register()
    return {"status": "success", "message": "Scan initiated"}
