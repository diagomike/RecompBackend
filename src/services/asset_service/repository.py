import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.shared.database.mongo import MongoDBConnection

class AssetRepository:
    COLLECTION_NAME = "assets"

    def __init__(self):
        self.conn = MongoDBConnection()
        try:
            self.conn.db
        except ConnectionError:
            self.conn.connect()
        self.collection = self.conn.db[self.COLLECTION_NAME]

    def create_asset(self, asset_data: Dict[str, Any]) -> str:
        """
        Creates a new asset record. Returns the asset_id.
        """
        if "_id" not in asset_data:
            asset_data["_id"] = str(uuid.uuid4())
        
        asset_data["created_at"] = datetime.utcnow()
        asset_data["updated_at"] = datetime.utcnow()
        self.collection.insert_one(asset_data)
        return asset_data["_id"]

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"_id": asset_id})

    def update_asset(self, asset_id: str, updates: Dict[str, Any]):
        updates["updated_at"] = datetime.utcnow()
        self.collection.update_one(
            {"_id": asset_id},
            {"$set": updates}
        )

    def list_assets(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        return list(self.collection.find(query or {}))

    def delete_asset(self, asset_id: str):
        self.collection.delete_one({"_id": asset_id})
