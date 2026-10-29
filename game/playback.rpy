init python:
    def escape_dynamic_text(value):
        """Render untrusted scene text literally, without Ren'Py control tags."""
        return value.replace("[", "[[").replace("{", "{{").replace("【", "【【")

    def _legacy_basename_scene_id(relative_path):
        filename = relative_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return filename.rsplit(".", 1)[0]

    def prepare_json_scene_file(relative_path, expected_scene_id=None):
        """Prepare one immutable scene snapshot without executing actions."""
        state = prepare_playback(relative_path, expected_scene_id=expected_scene_id)

        # A v0 scene without its own id needs a stable identity for migration.
        # Strict v1 scenes are never assigned a filename-derived id.
        if (expected_scene_id is None and state.phase == "error"
                and getattr(state.last_error, "path", None) == "scene_id"):
            state = prepare_playback(
                relative_path,
                expected_scene_id=_legacy_basename_scene_id(relative_path),
            )
        return state

    def prepare_json_scene_task(task_id):
        task_id = str(task_id)
        return prepare_json_scene_file(
            "scenes/scene_{}.json".format(task_id),
            expected_scene_id=task_id,
        )

    def _characters_for_playback(state):
        chars = {}
        for key, name in state.snapshot.get("characters", {}).items():
            chars[key] = Character(
                escape_dynamic_text(name),
                who_color=speaker_name_color(key),
            )
        return chars

    def current_speaker_identity(display_name=None):
        """Prefer the stable scene speaker id while a dynamic line is visible."""
        state = getattr(renpy.store, "playback_state", None)
        if isinstance(state, PlaybackState) and state.phase == "playing":
            action = state.current_action()
            if isinstance(action, dict) and action.get("type") == "line":
                speaker_id = action.get("speaker")
                if isinstance(speaker_id, str) and speaker_id:
                    return speaker_id
        return display_name or "narrator"

    def history_speaker_identity(history_entry):
        speaker_id = getattr(history_entry, "speaker_id", None)
        if isinstance(speaker_id, str) and speaker_id:
            return speaker_id
        return getattr(history_entry, "who", None) or "narrator"

    def execute_current_playback_action(state):
        """Execute exactly the current action and return explicit control.

        Cursor advancement deliberately happens outside this function in a
        separate Ren'Py statement. An interaction save therefore retains the
        index of the action that is still visible/unfinished.
        """
        integrity_error = verify_playback_state(state)
        if integrity_error is not None:
            return PlaybackActionResult.failed(integrity_error)
        if state.phase == "error":
            return PlaybackActionResult.failed(state.last_error)
        if state.phase != "playing":
            return PlaybackActionResult.failed(PlaybackError(
                "state_integrity_error",
                "phase",
                "an action can execute only while playback is playing",
            ))

        action = state.current_action()
        if action is None:
            return PlaybackActionResult.scene_end()

        action_type = action.get("type")
        handler = get_act_handlers().get(action_type)
        if handler is None:
            return PlaybackActionResult.failed(PlaybackError(
                "missing_handler",
                "dialogue[{}].type".format(state.step_index),
                "no handler registered for action: {}".format(action_type),
            ))

        try:
            result = handler(action, _characters_for_playback(state))
        except renpy.game.CONTROL_EXCEPTIONS:
            raise
        except Exception as error:
            return PlaybackActionResult.failed(PlaybackError(
                "handler_exception",
                "dialogue[{}]".format(state.step_index),
                "{}: {}".format(error.__class__.__name__, str(error)),
            ))

        if not isinstance(result, PlaybackActionResult):
            return PlaybackActionResult.failed(PlaybackError(
                "invalid_handler_result",
                "dialogue[{}]".format(state.step_index),
                "handler must return PlaybackActionResult",
            ))
        if result.kind not in ("continue", "scene_end", "goto", "error"):
            return PlaybackActionResult.failed(PlaybackError(
                "invalid_handler_result",
                "dialogue[{}]".format(state.step_index),
                "unsupported handler result kind: {}".format(result.kind),
            ))
        if result.kind == "goto" and (not isinstance(result.target, str) or not result.target):
            return PlaybackActionResult.failed(PlaybackError(
                "invalid_handler_result",
                "dialogue[{}]".format(state.step_index),
                "goto result requires a target",
            ))
        if result.kind == "error" and not isinstance(result.error, PlaybackError):
            return PlaybackActionResult.failed(PlaybackError(
                "invalid_handler_result",
                "dialogue[{}]".format(state.step_index),
                "error result requires PlaybackError",
            ))
        return result

    def failed_playback_state(state, error):
        """Preserve trusted runtime state, but sanitize corrupted load state."""
        if verify_playback_state(state) is None:
            return state.failed(error)
        return PlaybackState(phase="error", last_error=error)


label run_json_scene_file(relative_path, expected_scene_id=None):
    $ playback_state = prepare_json_scene_file(relative_path, expected_scene_id=expected_scene_id)
    jump _run_prepared_json_scene


label run_json_scene_task(task_id):
    $ playback_state = prepare_json_scene_task(task_id)
    jump _run_prepared_json_scene


label _run_prepared_json_scene:
    $ _playback_integrity_error = verify_playback_state(playback_state)
    if _playback_integrity_error is not None:
        $ playback_state = failed_playback_state(playback_state, _playback_integrity_error)
        return PlaybackResult(playback_state, PlaybackActionResult.failed(_playback_integrity_error))

    if playback_state.phase == "error":
        return PlaybackResult(playback_state, PlaybackActionResult.failed(playback_state.last_error))

    if playback_state.phase == "ready":
        $ playback_state = playback_state.started()

    if playback_state.phase == "completed":
        return PlaybackResult(playback_state, PlaybackActionResult.scene_end())

    if playback_state.current_action() is None:
        $ playback_state = playback_state.completed()
        return PlaybackResult(playback_state, PlaybackActionResult.scene_end())

    # These must remain separate Ren'Py statements: the handler may interact,
    # while the following statement commits its successful completion.
    $ _playback_action_result = execute_current_playback_action(playback_state)

    if _playback_action_result.kind == "error":
        $ playback_state = failed_playback_state(playback_state, _playback_action_result.error)
        return PlaybackResult(playback_state, _playback_action_result)

    $ playback_state = playback_state.after_success(_playback_action_result)

    if _playback_action_result.kind in ("scene_end", "goto"):
        return PlaybackResult(playback_state, _playback_action_result)

    jump _run_prepared_json_scene
