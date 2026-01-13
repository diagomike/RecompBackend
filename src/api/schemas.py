from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

# --- Module Schemas ---

class ModuleContractInput(BaseModel):
    key: str
    label: Optional[str] = None
    contract_type: Literal["ASSET", "VALUE"]
    type: str
    description: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None

class ModuleContractOutput(BaseModel):
    key: str
    label: Optional[str] = None
    contract_type: Literal["ASSET", "VALUE"]
    media_type: Optional[str] = None
    description: Optional[str] = None

class ModuleResponse(BaseModel):
    id: str
    status: str
    inputs: List[ModuleContractInput]
    outputs: List[ModuleContractOutput]
    path: str
    version_hash: str

# --- Asset Schemas ---

class AssetResponse(BaseModel):
    id: str = Field(alias="_id")
    label: str
    status: Literal["PENDING", "AVAILABLE", "FAILED"]
    type: Literal["FILE", "VALUE"]
    media_type: str
    created_at: Optional[datetime] = None
    tags: List[str] = []
    error: Optional[str] = None

    class Config:
        populate_by_name = True

# --- Task Schemas ---

class TaskCreateRequest(BaseModel):
    module_id: str
    input_mapping: Dict[str, str]
    config: Optional[Dict[str, Any]] = {}

class TaskResponse(BaseModel):
    id: str = Field(alias="_id")
    module_id: str
    status: Literal["CREATED", "BLOCKED", "QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    input_map: Dict[str, str]
    output_map: Dict[str, str]
    config: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_log: Optional[str] = None

    class Config:
        populate_by_name = True
