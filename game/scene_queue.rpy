init -50 python:
    # Логика очереди сцен (prefetch N)
    import os
    from datetime import datetime
    from bson import ObjectId

    prefetch_depth = 3              # Глубина префетча (можно менять через init_scene_queue)
    scene_tasks = []                # Список task_id в порядке создания
    task_status = {}                # task_id -> статус
    task_result = {}                # task_id -> result (если используется)
    last_consumed_task_id = None    # Последний проигранный task_id (для связывания)
    queue_session_id = None         # Идентичность одной цепочки префетча
    queue_fill_predecessor = None   # Continuation across bounded provider polls.

    def init_scene_queue(prefetch_depth_override=None, reset_last=True, fill=True):
        """Инициализация/переинициализация очереди сцен."""
        global prefetch_depth, scene_tasks, task_status, task_result, last_consumed_task_id, queue_session_id, queue_fill_predecessor
        if prefetch_depth_override is not None:
            prefetch_depth = int(prefetch_depth_override)
        scene_tasks = []
        task_status = {}
        task_result = {}
        if reset_last:
            last_consumed_task_id = None
            queue_session_id = str(ObjectId())
            queue_fill_predecessor = None
        if fill:
            fill_scene_queue()

    def fill_scene_queue(max_remote_steps=5):
        """Создаёт новые задачи до глубины префетча."""
        global scene_tasks, queue_session_id, queue_fill_predecessor
        if queue_session_id is None:
            queue_session_id = str(ObjectId())
        previous_id = (scene_tasks[-1] if scene_tasks
                       else queue_fill_predecessor or last_consumed_task_id)
        visited = set()
        while (len(scene_tasks) < prefetch_depth
                and len(visited) < max_remote_steps):
            payload = {
                "queue_session_id": queue_session_id,
                "previous": str(previous_id) if previous_id else None,
            }
            idempotency_key = "{}:{}".format(queue_session_id, previous_id or "root")
            new_id = create_task("demo_test", payload, idempotency_key=idempotency_key)
            if not new_id:
                break
            new_id = str(new_id)
            if new_id in visited or new_id in scene_tasks:
                break
            visited.add(new_id)
            status, result = check_status(new_id)
            if status == "consumed":
                previous_id = new_id
                queue_fill_predecessor = new_id
                continue
            scene_tasks.append(new_id)
            queue_fill_predecessor = new_id
            if status is not None:
                task_status[new_id] = status
            if result is not None:
                task_result[new_id] = result
            previous_id = new_id

    def scene_file_exists(task_id):
        try:
            fp = renpy.loader.transfn(f"scenes/scene_{task_id}.json")
            return os.path.isfile(fp) and os.path.getsize(fp) > 0
        except Exception:
            return False

    def poll_scene_tasks(dummy=None, max_status_checks=3, max_fill_steps=1):
        """Обновляет статусы задач в очереди и восполняет её."""
        global scene_tasks, task_status, task_result, queue_fill_predecessor
        changed = False
        for tid in list(scene_tasks)[:max_status_checks]:
            status, result = check_status(tid)
            if status is None:
                if task_status.get(tid) != "missing":
                    task_status[tid] = "missing"
                    changed = True
                continue
            prev_status = task_status.get(tid)
            task_status[tid] = status
            if result is not None:
                task_result[tid] = result
            if prev_status != status:
                changed = True
            if status == "consumed":
                queue_fill_predecessor = tid
                scene_tasks.remove(tid)
                task_status.pop(tid, None)
                task_result.pop(tid, None)
                changed = True
        fill_scene_queue(max_remote_steps=max_fill_steps)

    def get_next_ready_task_id():
        for tid in scene_tasks:
            if task_status.get(tid) == "done" and scene_file_exists(tid):
                return tid
        return None

    def consume_task(tid, raise_errors=False):
        """Acknowledge playback without deleting external history.

        The ``status == done`` predicate makes retries idempotent. Cleanup and
        retention belong to the non-rollbackable worker/service boundary.
        """
        global last_consumed_task_id, queue_fill_predecessor
        acknowledged = False
        try:
            now = datetime.utcnow()
            result = tasks.update_one(
                {"_id": ObjectId(tid), "status": "done"},
                {"$set": {
                    "status": "consumed",
                    "consumed_at": now,
                    "updated_at": now,
                }},
            )
            acknowledged = getattr(result, "matched_count", 0) == 1
            if not acknowledged:
                current = tasks.find_one({"_id": ObjectId(tid)}, {"status": 1})
                acknowledged = bool(current and current.get("status") == "consumed")
        except Exception:
            if raise_errors:
                raise
            return False

        if not acknowledged:
            return False

        if tid in scene_tasks:
            scene_tasks.remove(tid)
        task_status.pop(tid, None)
        task_result.pop(tid, None)
        last_consumed_task_id = tid
        queue_fill_predecessor = tid
        fill_scene_queue(max_remote_steps=1)
        return True

    def reject_task(tid, playback_error=None):
        """Evict an unplayable done task and best-effort persist its cause.

        ``playback_state`` deliberately remains untouched so the UI and logs
        can inspect the exact contract error until another scene is prepared.
        """
        global queue_fill_predecessor
        if tid in scene_tasks:
            scene_tasks.remove(tid)
        queue_fill_predecessor = tid
        task_status.pop(tid, None)
        task_result.pop(tid, None)

        def error_field(name, fallback):
            if isinstance(playback_error, dict):
                value = playback_error.get(name)
            else:
                value = getattr(playback_error, name, None)
            return value if isinstance(value, str) and value else fallback

        structured_error = {
            "code": error_field("code", "client_playback_rejected"),
            "path": error_field("path", "$"),
            "message": error_field("message", "Ren'Py client rejected the prepared scene."),
            "source": "renpy_client",
        }
        try:
            tasks.update_one(
                {"_id": ObjectId(tid)},
                {"$set": {
                    "status": "error",
                    "error": structured_error,
                    "updated_at": datetime.utcnow(),
                }},
            )
        except Exception:
            # Local eviction is authoritative for preventing a replay loop;
            # Mongo diagnostics are best-effort when the service is offline.
            pass

        try:
            fill_scene_queue(max_remote_steps=1)
        except Exception:
            pass

screen wait_task(task_id=None, msg="Думаю..."):
    text msg xalign 0.5 yalign 0.4
    timer 0.5 action Return()

screen scene_poll():
    timer 1.0 action Function(poll_scene_tasks) repeat True
