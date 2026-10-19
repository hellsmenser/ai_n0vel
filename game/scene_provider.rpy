default scene_session = SceneSessionState()
default scene_client_error = None

# Dynamic-scene progress is only autosaved after the external task has been
# acknowledged. Ordinary interaction/choice autosaves can otherwise capture a
# state between playback completion and acknowledgement.
define config.autosave_frequency = 0
define config.autosave_on_choice = False
define config.autosave_on_input = False

init -40 python:
    SCENE_SESSION_STATE_VERSION = 1
    SCENE_PROVIDER_RUNTIME_KEY = "ai_novel_scene_provider_runtime"

    class SceneProviderError(object):
        def __init__(self, code, operation, message, retryable=True,
                     path="$", source="provider", task_id=None):
            self.code = str(code)
            self.operation = str(operation)
            self.message = str(message)
            self.retryable = bool(retryable)
            self.path = str(path)
            self.source = str(source)
            self.task_id = None if task_id is None else str(task_id)

    class SceneSessionState(object):
        def __init__(self, provider_kind="mongo_file", phase="idle",
                     pending_operation="poll", active_ref=None,
                     boundary_serial=0, provider_cursor=0,
                     state_version=SCENE_SESSION_STATE_VERSION):
            self.state_version = state_version
            self.provider_kind = str(provider_kind)
            self.phase = str(phase)
            self.pending_operation = str(pending_operation)
            self.active_ref = None if active_ref is None else str(active_ref)
            self.boundary_serial = int(boundary_serial)
            self.provider_cursor = int(provider_cursor)

        def replaced(self, phase=None, pending_operation=None,
                     active_ref="__keep__", boundary_serial=None,
                     provider_cursor=None):
            return SceneSessionState(
                state_version=self.state_version,
                provider_kind=self.provider_kind,
                phase=self.phase if phase is None else phase,
                pending_operation=(self.pending_operation if pending_operation is None
                                   else pending_operation),
                active_ref=(self.active_ref if active_ref == "__keep__" else active_ref),
                boundary_serial=(self.boundary_serial if boundary_serial is None
                                 else boundary_serial),
                provider_cursor=(self.provider_cursor if provider_cursor is None
                                 else provider_cursor),
            )

    def verify_scene_session(state):
        if not isinstance(state, SceneSessionState):
            return "scene session has an unsupported type"
        if (isinstance(state.state_version, bool)
                or state.state_version != SCENE_SESSION_STATE_VERSION):
            return "scene session version is incompatible"
        if not isinstance(state.provider_kind, str) or not state.provider_kind:
            return "scene provider kind is invalid"
        if state.phase not in (
                "idle", "waiting", "ready", "playing", "error",
                "acknowledging", "acknowledged", "boundary"):
            return "scene session phase is invalid"
        if state.pending_operation not in ("poll", "prepare", "playback", "acknowledge"):
            return "scene session operation is invalid"
        if state.active_ref is not None and not isinstance(state.active_ref, str):
            return "scene session active reference is invalid"
        for value in (state.boundary_serial, state.provider_cursor):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return "scene session counter is invalid"
        return None

    def verify_scene_client_state(session, playback):
        session_error = verify_scene_session(session)
        if session_error is not None:
            return session_error
        active_phases = ("ready", "playing", "acknowledging", "acknowledged")
        if session.phase in active_phases:
            if not isinstance(session.active_ref, str) or not session.active_ref:
                return "active scene reference is required for this phase"
            if (not isinstance(playback, PlaybackState)
                    or verify_playback_state(playback) is not None):
                return "active scene requires valid playback state"
            if session.active_ref != playback.scene_id:
                return "active scene does not match playback state"
        if session.phase == "boundary" and session.active_ref is not None:
            return "boundary state cannot retain an active scene reference"
        if session.phase in ("acknowledged", "boundary"):
            if (not isinstance(playback, PlaybackState)
                    or verify_playback_state(playback) is not None
                    or playback.phase != "completed"):
                return "stable scene boundary requires completed playback"
        return None

    class SceneProviderResult(object):
        def __init__(self, kind, session=None, error=None, scene_ref=None,
                     playback_state=None):
            self.kind = str(kind)
            self.session = session
            self.error = error
            self.scene_ref = None if scene_ref is None else str(scene_ref)
            self.playback_state = playback_state

    def _provider_error_from_playback(error, operation="prepare", task_id=None,
                                      retryable=True):
        return SceneProviderError(
            code=getattr(error, "code", "scene_invalid"),
            operation=operation,
            message=getattr(error, "message", "The scene could not be prepared."),
            retryable=retryable,
            path=getattr(error, "path", "$"),
            task_id=task_id,
        )

    def _provider_error_from_exception(error, operation, task_id=None):
        try:
            is_mongo_error = isinstance(error, pymongo.errors.PyMongoError)
        except Exception:
            is_mongo_error = False
        return SceneProviderError(
            code="provider_offline" if is_mongo_error else "provider_failure",
            operation=operation,
            message=("Scene provider is offline."
                     if is_mongo_error else "Scene provider failed: {}".format(error.__class__.__name__)),
            retryable=True,
            task_id=task_id,
        )

    def _reraise_control_flow(error):
        if isinstance(error, renpy.game.CONTROL_EXCEPTIONS):
            raise error

    def _set_scene_provider_runtime(provider):
        if provider is None:
            renpy.session.pop(SCENE_PROVIDER_RUNTIME_KEY, None)
        else:
            renpy.session[SCENE_PROVIDER_RUNTIME_KEY] = provider

    def _get_scene_provider_runtime():
        return renpy.session.get(SCENE_PROVIDER_RUNTIME_KEY)

    class TaskFileSceneProvider(object):
        """Adapter for the current task queue plus local JSON scene files."""

        def poll(self, session):
            # The queue is ordered. A terminal/missing predecessor must be
            # surfaced before a later ready scene can be played.
            ready_id = None
            if scene_tasks and task_status.get(scene_tasks[0]) in ("error", "missing"):
                # Retry must recheck the same predecessor rather than replay a
                # cached terminal status forever. Do not advance/refill here.
                poll_scene_tasks(max_status_checks=1, max_fill_steps=0)
            if scene_tasks and task_status.get(scene_tasks[0]) in ("done", "error", "missing"):
                ready_id = scene_tasks[0]
            elif not scene_tasks:
                # Preserve the legacy test seam used by focused queue tests.
                ready_id = get_next_ready_task_id()
            if ready_id is None:
                poll_scene_tasks()
                if scene_tasks:
                    ready_id = scene_tasks[0]

            if ready_id is None:
                return SceneProviderResult("waiting", session=session)

            status = task_status.get(ready_id)
            if status in ("error", "missing"):
                code = "task_failed" if status == "error" else "task_not_found"
                message = ("Scene generation failed." if status == "error"
                           else "The scene task no longer exists.")
                return SceneProviderResult(
                    "error",
                    session=session,
                    scene_ref=ready_id,
                    error=SceneProviderError(
                        code,
                        "poll",
                        message,
                        retryable=True,
                        task_id=ready_id,
                    ),
                )
            file_ready = (status == "done"
                          and get_next_ready_task_id() == ready_id)
            if status == "done" and not file_ready:
                return SceneProviderResult(
                    "error",
                    session=session,
                    scene_ref=ready_id,
                    error=SceneProviderError(
                        "scene_not_found",
                        "prepare",
                        "The generated scene file is missing.",
                        retryable=True,
                        task_id=ready_id,
                    ),
                )
            if status != "done" and ready_id in scene_tasks:
                return SceneProviderResult("waiting", session=session)

            prepared = prepare_json_scene_task(ready_id)
            if prepared.phase == "error":
                return SceneProviderResult(
                    "error",
                    session=session,
                    scene_ref=ready_id,
                    error=_provider_error_from_playback(
                        prepared.last_error,
                        operation="prepare",
                        task_id=ready_id,
                    ),
                    playback_state=prepared,
                )
            return SceneProviderResult(
                "ready",
                session=session,
                scene_ref=ready_id,
                playback_state=prepared,
            )

        def acknowledge(self, session, scene_ref):
            if consume_task(scene_ref, raise_errors=True):
                return SceneProviderResult(
                    "acknowledged",
                    session=session,
                    scene_ref=scene_ref,
                )
            return SceneProviderResult(
                "error",
                session=session,
                scene_ref=scene_ref,
                error=SceneProviderError(
                    "acknowledge_failed",
                    "acknowledge",
                    "The completed scene could not be acknowledged.",
                    retryable=True,
                    task_id=scene_ref,
                ),
            )

        def report_failure(self, session, scene_ref, playback_error):
            reject_task(scene_ref, playback_error)

    class MongoTaskSceneProvider(TaskFileSceneProvider):
        pass

    class FixtureSceneProvider(object):
        def __init__(self, fixtures=None):
            self.fixtures = list(fixtures or [])

        def poll(self, session):
            if session.provider_cursor >= len(self.fixtures):
                return SceneProviderResult("waiting", session=session)
            relative_path, scene_id = self.fixtures[session.provider_cursor]
            prepared = prepare_json_scene_file(relative_path, expected_scene_id=scene_id)
            if prepared.phase == "error":
                return SceneProviderResult(
                    "error",
                    session=session,
                    scene_ref=scene_id,
                    error=_provider_error_from_playback(prepared.last_error, task_id=scene_id),
                    playback_state=prepared,
                )
            return SceneProviderResult(
                "ready",
                session=session,
                scene_ref=scene_id,
                playback_state=prepared,
            )

        def acknowledge(self, session, scene_ref):
            return SceneProviderResult(
                "acknowledged",
                session=session.replaced(provider_cursor=session.provider_cursor + 1),
                scene_ref=scene_ref,
            )

        def report_failure(self, session, scene_ref, playback_error):
            return None

    SCENE_PROVIDER_FACTORIES = {
        "mongo_file": MongoTaskSceneProvider,
        "task_file": TaskFileSceneProvider,
        "fixture": FixtureSceneProvider,
    }
    def get_scene_provider():
        session_error = verify_scene_session(scene_session)
        if session_error is not None:
            raise ValueError(session_error)
        runtime = _get_scene_provider_runtime()
        if runtime is None:
            factory = SCENE_PROVIDER_FACTORIES.get(scene_session.provider_kind)
            if factory is None:
                raise ValueError("unknown scene provider: {}".format(scene_session.provider_kind))
            runtime = factory()
            _set_scene_provider_runtime(runtime)
        return runtime

    def scene_client_after_load():
        """Discard live clients; saved state contains only inert session data."""
        _set_scene_provider_runtime(None)
        session_error = verify_scene_client_state(scene_session, renpy.store.playback_state)
        if session_error is not None:
            error = SceneProviderError(
                "session_integrity_error",
                "poll",
                session_error,
                retryable=False,
            )
            renpy.store.scene_session = SceneSessionState(
                phase="error",
                pending_operation="poll",
            )
            renpy.store.scene_client_error = error

    def scene_client_start():
        provider_kind = (scene_session.provider_kind
                         if verify_scene_session(scene_session) is None
                         else "mongo_file")
        if provider_kind in ("mongo_file", "task_file"):
            # Establish a stable queue identity without performing I/O. The
            # first provider poll fills it inside the bounded error boundary.
            init_scene_queue(3, reset_last=True, fill=False)
        _set_scene_provider_runtime(None)
        renpy.store.scene_session = SceneSessionState(provider_kind=provider_kind)
        renpy.store.scene_client_error = None

    def _scene_client_fail(error, operation=None, scene_ref=None):
        if not isinstance(error, SceneProviderError):
            error = SceneProviderError(
                "provider_failure",
                operation or "poll",
                "Scene provider returned an invalid error.",
                retryable=True,
                task_id=scene_ref,
            )
        base_session = scene_session
        if verify_scene_session(base_session) is not None:
            base_session = SceneSessionState()
        active_ref = base_session.active_ref if scene_ref is None else scene_ref
        renpy.store.scene_client_error = error
        renpy.store.scene_session = base_session.replaced(
            phase="error",
            pending_operation=error.operation,
            active_ref=active_ref,
        )
        return SceneProviderResult(
            "error",
            session=renpy.store.scene_session,
            error=error,
            scene_ref=active_ref,
        )

    def scene_client_poll():
        session_error = verify_scene_session(scene_session)
        if session_error is not None:
            return _scene_client_fail(SceneProviderError(
                "session_integrity_error", "poll", session_error, retryable=False,
            ))
        renpy.store.scene_session = scene_session.replaced(
            phase="waiting",
            pending_operation="poll",
        )
        try:
            result = get_scene_provider().poll(renpy.store.scene_session)
        except Exception as error:
            _reraise_control_flow(error)
            return _scene_client_fail(_provider_error_from_exception(error, "poll"))

        if not isinstance(result, SceneProviderResult):
            return _scene_client_fail(None, operation="poll")
        result_session = result.session
        if verify_scene_session(result_session) is not None:
            return _scene_client_fail(SceneProviderError(
                "session_integrity_error", "poll",
                "Scene provider returned an invalid session.", retryable=False,
            ))
        if result.kind == "error":
            return _scene_client_fail(result.error, scene_ref=result.scene_ref)
        if result.kind == "waiting":
            renpy.store.scene_client_error = None
            renpy.store.scene_session = result_session.replaced(
                phase="waiting",
                pending_operation="poll",
            )
            result.session = renpy.store.scene_session
            return result
        if result.kind != "ready" or result.playback_state is None or result.scene_ref is None:
            return _scene_client_fail(None, operation="poll")

        renpy.store.playback_state = result.playback_state
        renpy.store.scene_client_error = None
        renpy.store.scene_session = result_session.replaced(
            phase="ready",
            pending_operation="poll",
            active_ref=result.scene_ref,
        )
        result.session = renpy.store.scene_session
        return result

    def scene_client_report_playback_error(playback_error):
        current_action = (renpy.store.playback_state.current_action()
                          if isinstance(renpy.store.playback_state, PlaybackState)
                          else None)
        retryable = (isinstance(current_action, dict)
                     and current_action.get("type") in ("return", "jump"))
        return _scene_client_fail(
            _provider_error_from_playback(
                playback_error,
                operation="playback",
                task_id=scene_session.active_ref,
                retryable=retryable,
            ),
            scene_ref=scene_session.active_ref,
        )

    def scene_client_acknowledge():
        session_error = verify_scene_client_state(
            scene_session,
            renpy.store.playback_state,
        )
        if session_error is not None:
            return _scene_client_fail(SceneProviderError(
                "session_integrity_error", "acknowledge", session_error,
                retryable=False,
            ))
        scene_ref = scene_session.active_ref
        renpy.store.scene_session = scene_session.replaced(
            phase="acknowledging",
            pending_operation="acknowledge",
        )
        try:
            result = get_scene_provider().acknowledge(
                renpy.store.scene_session,
                scene_ref,
            )
        except Exception as error:
            _reraise_control_flow(error)
            return _scene_client_fail(
                _provider_error_from_exception(error, "acknowledge", scene_ref),
                scene_ref=scene_ref,
            )
        if not isinstance(result, SceneProviderResult) or result.kind != "acknowledged":
            error = result.error if isinstance(result, SceneProviderResult) else None
            return _scene_client_fail(error, operation="acknowledge", scene_ref=scene_ref)
        acknowledged_session = result.session
        if verify_scene_session(acknowledged_session) is not None:
            return _scene_client_fail(SceneProviderError(
                "session_integrity_error", "acknowledge",
                "Scene provider returned an invalid session.", retryable=False,
                task_id=scene_ref,
            ), scene_ref=scene_ref)
        renpy.store.scene_client_error = None
        renpy.store.scene_session = acknowledged_session.replaced(
            phase="acknowledged",
            pending_operation="acknowledge",
        )
        result.session = renpy.store.scene_session
        return result

    def scene_client_retry():
        operation = scene_session.pending_operation
        if operation == "playback":
            state = renpy.store.playback_state
            if (not isinstance(state, PlaybackState)
                    or verify_playback_state(state) is not None
                    or state.phase != "error"):
                _scene_client_fail(SceneProviderError(
                    "state_integrity_error", "playback",
                    "The failed scene cannot be resumed safely.", retryable=False,
                    task_id=scene_session.active_ref,
                ))
                return "error"
            renpy.store.playback_state = state.retry_current()
        renpy.store.scene_client_error = None
        renpy.store.scene_session = scene_session.replaced(
            phase=("acknowledging" if operation == "acknowledge"
                   else "playing" if operation == "playback" else "waiting"),
        )
        return operation

    def scene_client_abandon():
        error = scene_client_error
        if (scene_session.active_ref is not None and error is not None
                and error.operation in ("prepare", "playback")):
            try:
                get_scene_provider().report_failure(
                    scene_session,
                    scene_session.active_ref,
                    error,
                )
            except Exception as error:
                _reraise_control_flow(error)
                pass
        _set_scene_provider_runtime(None)

    def scene_client_commit_boundary():
        client_error = verify_scene_client_state(scene_session, renpy.store.playback_state)
        if client_error is not None or scene_session.phase != "acknowledged":
            raise ValueError(client_error or "autosave boundary requires a confirmed acknowledgement")
        renpy.store.scene_session = scene_session.replaced(
            phase="boundary",
            pending_operation="poll",
            active_ref=None,
            boundary_serial=scene_session.boundary_serial + 1,
        )
        renpy.store.scene_client_error = None
        return renpy.store.scene_session

    def scene_client_autosave_boundary():
        if scene_session.phase != "boundary" or scene_session.active_ref is not None:
            raise ValueError("autosave requires a stable scene boundary")
        renpy.force_autosave(take_screenshot=True, block=True)
        return renpy.store.scene_session
