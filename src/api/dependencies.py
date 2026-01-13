from src.services.asset_service.manager import AssetManager
from src.services.task_runner.task_orchestrator import TaskOrchestrator
from src.services.task_runner.registry.orchestrator import RegistryOrchestrator
from src.services.task_runner.task_repository import TaskRepository
from src.services.asset_service.repository import AssetRepository
from src.shared.database.mongo import ModuleRegistryRepository

# Singletons for services
_asset_manager = AssetManager()
_task_orchestrator = TaskOrchestrator()
_registry_orchestrator = RegistryOrchestrator(modules_root="modules")
_task_repo = TaskRepository()
_asset_repo = AssetRepository()
_registry_repo = ModuleRegistryRepository()

def get_asset_manager():
    return _asset_manager

def get_task_orchestrator():
    return _task_orchestrator

def get_registry_orchestrator():
    return _registry_orchestrator

def get_task_repo():
    return _task_repo

def get_asset_repo():
    return _asset_repo

def get_registry_repo():
    return _registry_repo
