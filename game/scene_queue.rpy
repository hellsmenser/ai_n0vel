init -50 python:
    # Логика очереди сцен (prefetch N)
    import os
    from bson import ObjectId

    prefetch_depth = 3              # Глубина префетча (можно менять через init_scene_queue)
    scene_tasks = []                # Список task_id в порядке создания
    task_status = {}                # task_id -> статус
    task_result = {}                # task_id -> result (если используется)
    last_consumed_task_id = None    # Последний проигранный task_id (для связывания)

    def init_scene_queue(prefetch_depth_override=None, reset_last=True):
        """Инициализация/переинициализация очереди сцен."""
        global prefetch_depth, scene_tasks, task_status, task_result, last_consumed_task_id
        if prefetch_depth_override is not None:
            prefetch_depth = int(prefetch_depth_override)
        scene_tasks = []
        task_status = {}
        task_result = {}
        if reset_last:
            last_consumed_task_id = None
        fill_scene_queue()

    def fill_scene_queue():
        """Создаёт новые задачи до глубины префетча."""
        global scene_tasks
        while len(scene_tasks) < prefetch_depth:
            payload = {"previous": str(last_consumed_task_id)} if last_consumed_task_id else {}
            new_id = create_task("demo_test", payload)
            if not new_id:
                break
            scene_tasks.append(str(new_id))

    def scene_file_exists(task_id):
        try:
            fp = renpy.loader.transfn(f"scenes/scene_{task_id}.json")
            return os.path.isfile(fp) and os.path.getsize(fp) > 0
        except Exception:
            return False

    def poll_scene_tasks(dummy=None):
        """Обновляет статусы задач в очереди и восполняет её."""
        global scene_tasks, task_status, task_result
        changed = False
        for tid in list(scene_tasks):
            status, result = check_status(tid)
            if status is None:
                scene_tasks.remove(tid)
                task_status.pop(tid, None)
                task_result.pop(tid, None)
                changed = True
                continue
            prev_status = task_status.get(tid)
            task_status[tid] = status
            if result is not None:
                task_result[tid] = result
            if prev_status != status:
                changed = True
            if status == "error":
                scene_tasks.remove(tid)
                task_status.pop(tid, None)
                task_result.pop(tid, None)
                changed = True
        fill_scene_queue()

    def get_next_ready_task_id():
        for tid in scene_tasks:
            if task_status.get(tid) == "done" and scene_file_exists(tid):
                return tid
        return None

    def consume_task(tid):
        global last_consumed_task_id
        if tid in scene_tasks:
            scene_tasks.remove(tid)
        task_status.pop(tid, None)
        task_result.pop(tid, None)
        try:
            tasks.delete_one({"_id": ObjectId(tid)})
        except Exception as e:
            pass
        last_consumed_task_id = tid
        fill_scene_queue()

screen wait_task(task_id=None, msg="Думаю..."):
    text msg xalign 0.5 yalign 0.4
    timer 0.5 action Return()

screen scene_poll():
    timer 1.0 action Function(poll_scene_tasks) repeat True
