from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.api.schemas import TaskCreateRequest, TaskResponse
from src.api.dependencies import get_task_orchestrator, get_task_repo

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/", response_model=TaskResponse)
def create_task(req: TaskCreateRequest, orch=Depends(get_task_orchestrator)):
    try:
        result = orch.validate_and_create_task(
            module_id=req.module_id,
            input_map=req.input_mapping,
            config=req.config
        )
        # Fetch the full task record
        task = orch.task_repo.get_task(result["task_id"])
        return task
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, repo=Depends(get_task_repo)):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/{task_id}/logs")
def get_task_logs(task_id: str, repo=Depends(get_task_repo)):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "status": task["status"],
        "error_log": task.get("error_log"),
        "logs": task.get("logs", [])
    }
