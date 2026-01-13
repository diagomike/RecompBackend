import os
import pymongo
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, Dict, Any, List

class MongoDBConnection:
    _instance = None
    _client: Optional[MongoClient] = None
    _db: Optional[Any] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBConnection, cls).__new__(cls)
        return cls._instance

    def connect(self, uri: str = "mongodb://localhost:27017/task_runner", db_name: str = "task_runner_db"):
        if not self._client:
            self._client = MongoClient(uri)
            self._db = self._client[db_name]
            print(f"[MongoDB] Connected to {uri} (DB: {db_name})")

    @property
    def db(self):
        if self._db is None:
            raise ConnectionError("Database not initialized. Call connect() first.")
        return self._db

class ModuleRegistryRepository:
    COLLECTION_NAME = "module_registry"

    def __init__(self):
        self.conn = MongoDBConnection()
        # Ensure connection (in a real app, this might be done at startup)
        try:
            self.conn.db
        except ConnectionError:
            self.conn.connect()
        
        self.collection = self.conn.db[self.COLLECTION_NAME]

    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"_id": module_id})

    def create_module(self, module_data: Dict[str, Any]):
        """
        Creates a new module record.
        module_data must contain '_id'.
        """
        module_data["created_at"] = datetime.utcnow()
        module_data["updated_at"] = datetime.utcnow()
        self.collection.insert_one(module_data)

    def update_module(self, module_id: str, updates: Dict[str, Any]):
        """
        Updates an existing module record.
        """
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"_id": module_id},
            {"$set": updates}
        )
    
    def append_log(self, module_id: str, log_line: str):
        """
        Appends a log line to the installation_logs array.
        """
        self.collection.update_one(
            {"_id": module_id},
            {
                "$push": {"installation_logs": log_line},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    def list_modules(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {}
        if status:
            query["status"] = status
        return list(self.collection.find(query))
