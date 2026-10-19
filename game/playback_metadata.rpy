default _playback_load_rejected = False
default _scene_session_load_rejected = False


init python:
    def ai_novel_history_context(history_entry):
        """Annotate Ren'Py's own history entry with immutable scene context."""
        state = renpy.store.playback_state
        if not isinstance(state, PlaybackState) or state.phase != "playing":
            return
        if verify_playback_state(state) is not None:
            return

        action = state.current_action()
        if not isinstance(action, dict) or action.get("type") != "line":
            return

        history_entry.scene_id = state.scene_id
        history_entry.step_index = state.step_index
        history_entry.speaker_id = action.get("speaker")


    def ai_novel_save_json(save_json):
        """Expose inert playback metadata to save-slot screens and tooling."""
        state = renpy.store.playback_state
        if not isinstance(state, PlaybackState):
            return
        if state.content_hash is None or verify_playback_state(state) is not None:
            return

        save_json["ai_novel"] = {
            "scene_id": state.scene_id,
            "step_index": state.step_index,
            "schema_version": state.schema_version,
            "state_version": state.state_version,
            "content_hash": state.content_hash,
            "phase": state.phase,
        }


    def ai_novel_after_load():
        """Reject incompatible/corrupted playback state before it can execute."""
        scene_client_after_load()
        if (isinstance(renpy.store.scene_client_error, SceneProviderError)
                and renpy.store.scene_client_error.code == "session_integrity_error"):
            renpy.store._scene_session_load_rejected = True
            renpy.store._playback_load_rejected = False
            renpy.block_rollback()
            return
        renpy.store._scene_session_load_rejected = False
        state = renpy.store.playback_state
        if state is None:
            renpy.store._playback_load_rejected = False
            return

        integrity_error = verify_playback_state(state)
        if integrity_error is None:
            renpy.store._playback_load_rejected = False
            return

        renpy.store.playback_state = PlaybackState(
            phase="error",
            last_error=integrity_error,
        )
        renpy.store._playback_load_rejected = True
        renpy.block_rollback()
        renpy.log("[playback] rejected incompatible state after load: {} at {}".format(
            integrity_error.code,
            integrity_error.path,
        ))


    if ai_novel_history_context not in config.history_callbacks:
        config.history_callbacks.append(ai_novel_history_context)
    if ai_novel_save_json not in config.save_json_callbacks:
        config.save_json_callbacks.append(ai_novel_save_json)
    if ai_novel_after_load not in config.after_load_callbacks:
        config.after_load_callbacks.append(ai_novel_after_load)


label after_load:
    if _scene_session_load_rejected:
        $ renpy.log("[scene_client] routing incompatible session after load")
        $ _scene_session_load_rejected = False
        jump scene_session_load_rejected
    if _playback_load_rejected:
        $ renpy.log("[playback] routing incompatible save to rejection label")
        $ _playback_load_rejected = False
        jump playback_load_rejected
    return


label scene_session_load_rejected:
    call screen scene_provider_error(scene_client_error)
    $ scene_client_abandon()
    jump _main_menu


label playback_load_rejected:
    $ renpy.log("[playback] incompatible-save rejection displayed")
    "This save contains an incompatible dynamic-scene state. Playback was stopped safely."
    jump _main_menu
