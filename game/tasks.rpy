init -100 python:
    import pymongo, os, json
    from datetime import datetime
    from bson import ObjectId

    client = pymongo.MongoClient("mongodb://localhost:27017/?directConnection=true")
    db = client["novel"]
    tasks = db["tasks"]

    def create_task(task_type, payload=None):
        task = {
            "type": task_type,
            "payload": payload or {},
            "status": "new",
            "created_at": datetime.utcnow(),
            "updated_at": None,
            "result": None,
            "error": None,
        }
        result = tasks.insert_one(task)
        return result.inserted_id

    def check_status(task_id):
        try:
            t = tasks.find_one({"_id": ObjectId(task_id)})
        except Exception:
            return None, None
        if not t:
            return None, None
        return t.get("status"), t.get("result")

