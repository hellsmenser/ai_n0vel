label start:
    scene bg_tavern_interior
    $ scene_client_start_production()
    jump play_next_scene

label play_next_scene:
    $ provider_poll = scene_client_poll()
    $ renpy.log("[scene_client] poll result: {}".format(provider_poll.kind))
    if provider_poll.kind == "error":
        jump scene_provider_error_flow
    if provider_poll.kind == "waiting":
        call screen wait_task(None, "Генерирую следующую сцену...")
        jump play_next_scene
    $ next_id = provider_poll.scene_ref
    jump play_prepared_scene

label play_prepared_scene:
    call _run_prepared_json_scene
    $ completed_playback = _return
    if completed_playback.control.kind == "error":
        $ scene_client_report_playback_error(completed_playback.state.last_error)
        jump scene_provider_error_flow
    jump acknowledge_played_scene

label acknowledge_played_scene:
    $ provider_ack = scene_client_acknowledge()
    $ renpy.log("[scene_client] acknowledge result: {}".format(provider_ack.kind))
    if provider_ack.kind == "error":
        jump scene_provider_error_flow
    $ scene_client_commit_boundary()
    $ scene_client_autosave_boundary()
    if completed_playback.control.kind == "goto":
        jump expression completed_playback.control.target
    jump play_next_scene

label scene_provider_error_flow:
    $ renpy.log("[scene_client] showing {} error for {}".format(scene_client_error.code, scene_client_error.operation))
    call screen scene_provider_error(scene_client_error)
    $ provider_choice = _return
    $ renpy.log("[scene_client] error choice: {}".format(provider_choice))
    if provider_choice == "retry":
        $ retry_operation = scene_client_retry()
        if retry_operation == "acknowledge":
            jump acknowledge_played_scene
        if retry_operation == "playback":
            jump play_prepared_scene
        if retry_operation == "error":
            jump scene_provider_error_flow
        jump play_next_scene
    $ scene_client_abandon()
    jump _main_menu

label next_scene:
    with dissolve
    jump play_next_scene
