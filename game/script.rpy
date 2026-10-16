label start:
    scene bg room
    "Запуск. Формирую очередь сцен..."
    $ init_scene_queue(3)
    show screen scene_poll
    jump play_next_scene

label play_next_scene:
    $ next_id = get_next_ready_task_id()
    if next_id is None:
        call screen wait_task(None, "Генерирую следующую сцену...")
        jump play_next_scene
    "Проигрываю сцену"
    $ play_json_scene(next_id)
    jump play_next_scene

label next_scene:
    $ consume_task(next_id)
    with dissolve
    "Это следующая сцена."
    jump play_next_scene