import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.shared.database.mongo import MongoDBConnection

class TaskRepository:
    COLLECTION_NAME = "tasks"

    def __init__(self):
        self.conn = MongoDBConnection()
        try:
            self.conn.db
        except ConnectionError:
            self.conn.connect()
        self.collection = self.conn.db[self.COLLECTION_NAME]

    def create_task(self, task_data: Dict[str, Any]) -> str:
        """
        Creates a new task record. Returns the task_id.
        """
        if "_id" not in task_data:
            task_data["_id"] = str(uuid.uuid4())
        
        task_data["created_at"] = datetime.utcnow()
        task_data["updated_at"] = datetime.utcnow()
        self.collection.insert_one(task_data)
        return task_data["_id"]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"_id": task_id})

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"_id": task_id},
            {"$set": updates}
        )

    def find_blocked_tasks_by_asset(self, asset_id: str) -> List[Dict[str, Any]]:
        """Finds all BLOCKED tasks waiting for a specific asset."""
        return list(self.collection.find({
            "status": "BLOCKED",
            "blocking_assets": asset_id
        }))

    def get_next_queued_task(self) -> Optional[Dict[str, Any]]:
        """Returns the oldest QUEUED task (FIFO)."""
        return self.collection.find_one(
            {"status": "QUEUED"},
            sort=[("created_at", 1)]
        )
