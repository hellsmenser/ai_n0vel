init -100 python:
    import hashlib
    import pymongo, os, json
    from datetime import datetime
    from bson import ObjectId

    # Bound every database operation so an unavailable prototype backend does
    # not freeze the Ren'Py interaction loop for PyMongo's long defaults.
    client = pymongo.MongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=600,
        connectTimeoutMS=400,
        socketTimeoutMS=700,
        timeoutMS=750,
        retryWrites=False,
    )
    db = client["novel"]
    tasks = db["tasks"]

    def create_task(task_type, payload=None, idempotency_key=None):
        task = {
            "type": task_type,
            "payload": payload or {},
            "status": "new",
            "created_at": datetime.utcnow(),
            "updated_at": None,
            "result": None,
            "error": None,
        }
        if idempotency_key is None:
            result = tasks.insert_one(task)
            return result.inserted_id

        deterministic_hex = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
        deterministic_id = ObjectId(deterministic_hex)
        task["_id"] = deterministic_id
        task["idempotency_key"] = idempotency_key
        try:
            tasks.insert_one(task)
        except pymongo.errors.DuplicateKeyError:
            pass
        return deterministic_id

    def check_status(task_id):
        # A missing record and an unavailable provider are different states.
        # Let transport failures reach the SceneProvider error boundary.
        t = tasks.find_one({"_id": ObjectId(task_id)})
        if not t:
            return None, None
        return t.get("status"), t.get("result")

