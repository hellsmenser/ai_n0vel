init python:
    import builtins
    import os

    STAGE0_TEST_MODE = renpy.game.args.command == "test"
    stage0_testexecution = renpy.test.testexecution if STAGE0_TEST_MODE else None

    STAGE0_SAVE_SLOT = "stage0-save-load-mid-scene"
    STAGE1_SAVE_SLOT = "stage1-playback-state"
    STAGE2_SAVE_SLOT = "stage2-save-load"
    STAGE3_HISTORY_SAVE_SLOT = "stage3-history-save-load"
    STAGE3_JSON_SAVE_SLOT = "stage3-save-json-metadata"
    STAGE3_EMPTY_SAVE_SLOT = "stage3-save-json-empty"
    STAGE3_INVALID_SAVE_SLOT = "stage3-after-load-invalid"
    STAGE4_INVALID_SESSION_SLOT = "stage4-after-load-invalid-session"

    STAGE4_PROVIDER_KIND = "stage4_fake"

    def stage0_state():
        state = getattr(stage0_testexecution, "stage0_probe", None)
        if state is None:
            # Ren'Py rewrites literal dicts to rollback-aware RevertableDict.
            # These counters intentionally measure process-global executions
            # across save/load and rollback, so keep this tree non-revertable.
            state = builtins.dict()
            stage0_testexecution.stage0_probe = state
        return state

    def stage0_prepare_test(case_name):
        if getattr(stage0_testexecution, "stage0_active_case", None) == case_name:
            return

        stage0_testexecution.stage0_active_case = case_name
        state = stage0_state()
        state.clear()
        state["lines"] = builtins.dict()
        state["cursor_by_probe"] = builtins.dict()
        state["markers"] = builtins.dict()
        state["animate_calls"] = builtins.dict(object=0, string=0)
        state["animate_atl_calls"] = builtins.dict(object=0, string=0)
        state["animate_shows"] = builtins.dict(object=0, string=0)
        state["preferences"] = builtins.dict(
            skip_unseen=_preferences.skip_unseen,
            afm_time=_preferences.afm_time,
            afm_enable=_preferences.afm_enable,
        )

        renpy.store._history = True
        renpy.store._history_list[:] = []
        renpy.store.main_menu = False
        renpy.game.context()._main_menu = False
        renpy.config.skipping = None

    def stage0_history_count(text):
        return sum(text in (entry.what or "") for entry in renpy.store._history_list)

    def stage0_probe_count(name):
        return stage0_state()["lines"].get(name, 0)

    def stage0_mark(name):
        stage0_state()["markers"][name] = True

    def stage0_marked(name):
        return stage0_state()["markers"].get(name, False)

    def stage0_artifact_path(filename):
        directory = os.path.join(renpy.config.basedir, "test-artifacts")
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, filename)

    def stage0_delete_save():
        try:
            renpy.unlink_save(STAGE0_SAVE_SLOT)
        except Exception:
            pass

    def stage0_enable_skip():
        _preferences.skip_unseen = True

    def stage0_stop_skip_for_marker():
        renpy.stop_skipping()

    def stage0_enable_auto():
        _preferences.afm_time = 0.1
        _preferences.afm_enable = True

    def stage0_stop_auto_for_marker():
        _preferences.afm_enable = False

    def stage0_restore_preferences():
        saved = stage0_state().get("preferences", {})
        renpy.stop_skipping()
        if saved:
            _preferences.skip_unseen = saved["skip_unseen"]
            _preferences.afm_time = saved["afm_time"]
            _preferences.afm_enable = saved["afm_enable"]

    def stage0_install_animate_spy():
        state = stage0_state()
        original = ACT_HANDLERS_REGISTRY["animate"]
        state["animate_original"] = original

        def animate_spy(step, chars):
            kind = "string" if step.get("effect") == "shake" else "object"
            state["animate_calls"][kind] += 1
            return original(step, chars)

        ACT_HANDLERS_REGISTRY["animate"] = animate_spy

    def stage0_restore_animate_handler():
        original = stage0_state().pop("animate_original", None)
        if original is not None:
            ACT_HANDLERS_REGISTRY["animate"] = original

    # Shared assertions for the public contract/state API.
    def stage1_error_field(error, field):
        if isinstance(error, dict):
            return error.get(field)
        return getattr(error, field, None)

    def stage1_assert_error(state, code, path):
        assert state.phase == "error"
        assert state.last_error is not None
        assert stage1_error_field(state.last_error, "code") == code
        assert stage1_error_field(state.last_error, "path") == path

    def stage1_assert_integrity_error(state, path):
        error = verify_playback_state(state)
        assert stage1_error_field(error, "code") == "state_integrity_error"
        assert stage1_error_field(error, "path") == path

    def stage1_assert_error_code(state, code):
        assert state.phase == "error"
        assert stage1_error_field(state.last_error, "code") == code

    def stage1_json_bytes(value):
        return json.dumps(value, separators=(",", ":")).encode("utf-8")

    def stage1_too_deep_bytes():
        value = 0
        for _ in range(MAX_SCENE_DEPTH + 1):
            value = [value]
        return stage1_json_bytes(value)

    def stage1_parser_recursion_bytes():
        return ("[" * 2000 + "0" + "]" * 2000).encode("utf-8")

    def stage1_too_many_nodes_bytes():
        return stage1_json_bytes([0] * MAX_SCENE_NODES)

    def stage1_too_many_actions_bytes():
        return stage1_json_bytes({
            "schema_version": 1,
            "scene_id": "stage1-too-many-actions",
            "characters": {},
            "dialogue": [{"type": "return"}] * (MAX_DIALOGUE_ACTIONS + 1),
        })

    def stage1_too_many_characters_bytes():
        characters = {}
        for index in range(MAX_CHARACTERS + 1):
            characters["c{}".format(index)] = "Character"
        return stage1_json_bytes({
            "schema_version": 1,
            "scene_id": "stage1-too-many-characters",
            "characters": characters,
            "dialogue": [],
        })

    def stage1_too_long_text_bytes():
        return stage1_json_bytes({
            "schema_version": 1,
            "scene_id": "stage1-too-long-text",
            "characters": {"lira": "Lira"},
            "dialogue": [{"type": "line", "speaker": "lira", "text": "x" * (MAX_LINE_TEXT_LENGTH + 1)}],
        })

    def stage1_snapshot(state):
        return state.snapshot

    def stage1_install_handler_guards():
        state = stage0_state()
        state["stage1_handler_guard_originals"] = dict(ACT_HANDLERS_REGISTRY)

        def forbidden_handler(*args, **kwargs):
            raise AssertionError("prepare_playback must not invoke an action handler")

        for action in ACT_HANDLERS_REGISTRY:
            ACT_HANDLERS_REGISTRY[action] = forbidden_handler

    def stage1_restore_handler_guards():
        originals = stage0_state().pop("stage1_handler_guard_originals", None)
        if originals is not None:
            ACT_HANDLERS_REGISTRY.clear()
            ACT_HANDLERS_REGISTRY.update(originals)

    def stage1_delete_save():
        try:
            renpy.unlink_save(STAGE1_SAVE_SLOT)
        except Exception:
            pass

    # Stage 2 public-player result helpers.
    def stage2_result_state(result):
        return getattr(result, "state", result)

    def stage2_result_control(result):
        return getattr(result, "control", None)

    def stage2_control_field(control, field):
        if isinstance(control, dict):
            return control.get(field)
        return getattr(control, field, None)

    def stage2_delete_save():
        try:
            renpy.unlink_save(STAGE2_SAVE_SLOT)
        except Exception:
            pass

    # Stage 3 RED helpers. These only inspect public Ren'Py save/history
    # surfaces; the production callback implementation belongs to Stage 3
    # GREEN and must not be smuggled into the test harness.
    def stage3_delete_save(slot_name):
        try:
            renpy.unlink_save(slot_name)
        except Exception:
            pass

    def stage3_history_entries_with_text(text):
        return [entry for entry in renpy.store._history_list if text in (entry.what or "")]

    def stage3_history_entry(text):
        entries = stage3_history_entries_with_text(text)
        assert len(entries) == 1
        return entries[0]

    def stage3_slot_json(slot_name):
        return renpy.slot_json(slot_name)

    def stage3_invalid_state_for_save():
        valid = prepare_json_scene_file(
            "test_fixtures/stage3_history.json",
            expected_scene_id="stage3-history",
        ).started()
        return PlaybackState(
            scene_id=valid.scene_id,
            schema_version=valid.schema_version,
            content_hash=valid.content_hash,
            snapshot=valid.snapshot,
            step_index=valid.step_index,
            scene_variables=valid.scene_variables,
            branch_trace=valid.branch_trace,
            phase=valid.phase,
            migrated_from_schema=valid.migrated_from_schema,
            state_version=999,
        )

    def stage3_assert_consume_ack_idempotent():
        tid = "000000000000000000000003"
        second = "000000000000000000000004"
        third = "000000000000000000000005"
        originals = {
            "tasks": renpy.store.tasks,
            "create_task": renpy.store.create_task,
            "check_status": renpy.store.check_status,
            "prefetch_depth": renpy.store.prefetch_depth,
            "queue_session_id": renpy.store.queue_session_id,
            "scene_tasks": renpy.store.scene_tasks,
            "task_status": renpy.store.task_status,
            "task_result": renpy.store.task_result,
            "last_consumed_task_id": renpy.store.last_consumed_task_id,
            "queue_fill_predecessor": renpy.store.queue_fill_predecessor,
        }

        class UpdateResult(object):
            def __init__(self, matched_count):
                self.matched_count = matched_count

        class FakeTasks(object):
            def __init__(self, statuses=None, fail=False):
                self.statuses = statuses if statuses is not None else {tid: "done"}
                self.fail = fail
                self.applied = []

            def update_one(self, query, update):
                if self.fail:
                    raise IOError("mongo offline")
                task_id = str(query.get("_id"))
                if query.get("status") == self.statuses.get(task_id):
                    self.statuses[task_id] = update["$set"]["status"]
                    self.applied.append((query, update))
                    return UpdateResult(1)
                return UpdateResult(0)

            def find_one(self, query, projection=None):
                status = self.statuses.get(str(query.get("_id")))
                return {"status": status} if status is not None else None

            def delete_one(self, query):
                raise AssertionError("consume_task must not delete task history")

        try:
            created_by_key = builtins.dict()
            create_attempts = builtins.list()
            statuses = {tid: "done", second: "new", third: "new"}

            def create_task_spy(task_type, payload=None, idempotency_key=None):
                create_attempts.append(idempotency_key)
                if idempotency_key not in created_by_key:
                    created_by_key[idempotency_key] = "000000000000000000000006"
                created_id = created_by_key[idempotency_key]
                statuses.setdefault(created_id, "new")
                return created_id

            def check_status_spy(task_id):
                return statuses.get(str(task_id)), None

            fake = FakeTasks(statuses)
            renpy.store.tasks = fake
            renpy.store.create_task = create_task_spy
            renpy.store.check_status = check_status_spy
            renpy.store.prefetch_depth = 3
            renpy.store.queue_session_id = "stage3-session"
            renpy.store.scene_tasks = [tid, second, third]
            renpy.store.task_status = {tid: "done", second: "new", third: "new"}
            renpy.store.task_result = {tid: {"scene": "ready"}}

            assert consume_task(tid)
            first_queue = builtins.list(renpy.store.scene_tasks)

            # Simulate a load/rollback to the local queue state before ack.
            renpy.store.scene_tasks = [tid, second, third]
            renpy.store.task_status = {tid: "done", second: "new", third: "new"}
            renpy.store.task_result = {tid: {"scene": "ready"}}
            assert consume_task(tid)
            second_queue = builtins.list(renpy.store.scene_tasks)

            assert len(fake.applied) == 1
            query, update = fake.applied[0]
            assert str(query["_id"]) == tid
            assert query["status"] == "done"
            assert update["$set"]["status"] == "consumed"
            assert "consumed_at" in update["$set"]
            assert first_queue == second_queue
            assert len(set(create_attempts)) == 1
            assert len(created_by_key) == 1
            assert tid not in renpy.store.task_status
            assert tid not in renpy.store.task_result
            assert renpy.store.last_consumed_task_id == tid

            for failing in (FakeTasks(fail=True), FakeTasks({tid: "error"})):
                renpy.store.tasks = failing
                renpy.store.scene_tasks = [tid]
                renpy.store.task_status = {tid: "done"}
                renpy.store.task_result = {tid: {"scene": "ready"}}
                assert not consume_task(tid)
                assert renpy.store.scene_tasks == [tid]
                assert renpy.store.task_status[tid] == "done"

            # An older save may point at a predecessor whose deterministic
            # successors have already reached terminal states externally.
            # Refill must walk that chain instead of stopping or replaying it.
            consumed = "000000000000000000000007"
            rejected = "000000000000000000000008"
            fresh_one = "000000000000000000000009"
            fresh_two = "00000000000000000000000a"
            fresh_three = "00000000000000000000000b"
            recovery_session = "stage3-recovery"
            recovery_chain = {
                "{}:{}".format(recovery_session, tid): consumed,
                "{}:{}".format(recovery_session, consumed): rejected,
                "{}:{}".format(recovery_session, rejected): fresh_one,
                "{}:{}".format(recovery_session, fresh_one): fresh_two,
                "{}:{}".format(recovery_session, fresh_two): fresh_three,
            }
            recovery_statuses = {
                consumed: "consumed",
                rejected: "error",
                fresh_one: "new",
                fresh_two: "new",
                fresh_three: "new",
            }
            recovery_attempts = builtins.list()

            def recovery_create_task(task_type, payload=None, idempotency_key=None):
                recovery_attempts.append(idempotency_key)
                return recovery_chain.get(idempotency_key)

            def recovery_check_status(task_id):
                return recovery_statuses.get(str(task_id)), None

            renpy.store.create_task = recovery_create_task
            renpy.store.check_status = recovery_check_status
            renpy.store.prefetch_depth = 3
            renpy.store.queue_session_id = recovery_session
            renpy.store.scene_tasks = []
            renpy.store.task_status = {}
            renpy.store.task_result = {}
            renpy.store.last_consumed_task_id = tid
            renpy.store.queue_fill_predecessor = tid
            fill_scene_queue()

            # A consumed predecessor may be traversed, but an externally
            # failed task remains visible for the provider error UI instead
            # of being silently skipped to a later scene.
            assert renpy.store.scene_tasks == [rejected, fresh_one, fresh_two]
            assert consumed not in renpy.store.scene_tasks
            assert renpy.store.task_status[rejected] == "error"
            assert recovery_attempts == [
                "{}:{}".format(recovery_session, tid),
                "{}:{}".format(recovery_session, consumed),
                "{}:{}".format(recovery_session, rejected),
                "{}:{}".format(recovery_session, fresh_one),
            ]
        finally:
            for name, value in originals.items():
                setattr(renpy.store, name, value)

    # Stage 4 RED helpers. The production boundary is intentionally absent
    # here: these fakes describe the minimal provider/controller protocol and
    # are installed through the public factory registry only.
    def stage4_error_field(error, field):
        if isinstance(error, dict):
            return error.get(field)
        return getattr(error, field, None)

    def stage4_assert_provider_contract():
        expected_symbols = (
            "SceneProviderResult",
            "SceneProviderError",
            "SceneSessionState",
            "MongoTaskSceneProvider",
            "TaskFileSceneProvider",
            "FixtureSceneProvider",
            "SCENE_PROVIDER_FACTORIES",
            "get_scene_provider",
            "scene_client_poll",
            "scene_client_acknowledge",
            "scene_client_retry",
            "scene_client_commit_boundary",
            "scene_client_autosave_boundary",
        )
        missing = [name for name in expected_symbols if not hasattr(renpy.store, name)]
        assert not missing, "missing SceneProvider boundary symbols: {}".format(", ".join(missing))

        session = SceneSessionState(provider_kind="fixture")
        assert session.provider_kind == "fixture"
        assert session.phase == "idle"
        assert session.pending_operation == "poll"
        assert session.boundary_serial == 0
        assert session.provider_cursor == 0
        assert session.state_version == SCENE_SESSION_STATE_VERSION
        assert session.active_ref is None
        assert verify_scene_session(session) is None
        mismatch_state = prepare_json_scene_file(
            "test_fixtures/stage4_provider_retry.json",
            expected_scene_id="stage4-provider-retry",
        )
        assert verify_scene_client_state(
            SceneSessionState(
                provider_kind="fixture",
                phase="ready",
                active_ref="different-scene",
            ),
            mismatch_state,
        ) is not None
        assert config.autosave_frequency == 0
        assert config.autosave_on_choice is False
        assert config.autosave_on_input is False
        assert not hasattr(renpy.store, "_scene_provider_runtime")

        error = SceneProviderError(
            code="provider_offline",
            operation="poll",
            message="Stage4 provider is offline.",
            retryable=True,
        )
        assert stage4_error_field(error, "code") == "provider_offline"
        assert stage4_error_field(error, "operation") == "poll"
        assert stage4_error_field(error, "message") == "Stage4 provider is offline."
        assert stage4_error_field(error, "retryable") is True
        assert stage4_error_field(error, "path") == "$"
        assert stage4_error_field(error, "source") == "provider"

        result = SceneProviderResult(kind="error", session=session, error=error)
        assert result.kind == "error"
        assert result.session is session
        assert result.error is error

        provider_methods = ("poll", "acknowledge")
        for provider_type in (MongoTaskSceneProvider, TaskFileSceneProvider, FixtureSceneProvider):
            assert all(callable(getattr(provider_type, method, None)) for method in provider_methods)

        fixture_provider = FixtureSceneProvider([(
            "test_fixtures/stage4_provider_retry.json",
            "stage4-provider-retry",
        )])
        fixture_ready = fixture_provider.poll(session)
        assert fixture_ready.kind == "ready"
        assert fixture_ready.scene_ref == "stage4-provider-retry"
        assert fixture_ready.playback_state.phase == "ready"
        fixture_ack = fixture_provider.acknowledge(session, fixture_ready.scene_ref)
        assert fixture_ack.kind == "acknowledged"
        assert fixture_ack.session.provider_cursor == 1
        assert fixture_provider.poll(fixture_ack.session).kind == "waiting"

        for code in ("scene_not_found", "scene_read_error", "unsupported_action",
                     "missing_resource", "missing_handler"):
            mapped = _provider_error_from_playback(
                PlaybackError(code, "dialogue[0]", "fixture failure"),
                task_id="fixture",
            )
            assert mapped.code == code
            assert mapped.operation == "prepare"

        # A playback retry resumes the failed cursor rather than preparing the
        # scene again from action zero.
        original_session = renpy.store.scene_session
        original_playback = renpy.store.playback_state
        try:
            failed = prepare_json_scene_file(
                "test_fixtures/stage4_provider_retry.json",
                expected_scene_id="stage4-provider-retry",
            ).with_step_index(1).started().failed(
                PlaybackError("handler_exception", "dialogue[1]", "retry fixture")
            )
            renpy.store.playback_state = failed
            renpy.store.scene_session = SceneSessionState(
                provider_kind="fixture",
                phase="error",
                pending_operation="playback",
                active_ref="stage4-provider-retry",
            )
            assert scene_client_retry() == "playback"
            assert playback_state.phase == "playing"
            assert playback_state.step_index == 1
            assert playback_state.last_error is None
        finally:
            renpy.store.scene_session = original_session
            renpy.store.playback_state = original_playback

        original_session = renpy.store.scene_session
        original_playback = renpy.store.playback_state
        original_error = renpy.store.scene_client_error
        try:
            line_failed = prepare_json_scene_file(
                "test_fixtures/stage4_provider_retry.json",
                expected_scene_id="stage4-provider-retry",
            ).started().failed(
                PlaybackError("handler_exception", "dialogue[0]", "post-line failure")
            )
            renpy.store.playback_state = line_failed
            renpy.store.scene_session = SceneSessionState(
                provider_kind="fixture",
                phase="ready",
                active_ref="stage4-provider-retry",
            )
            reported = scene_client_report_playback_error(line_failed.last_error)
            assert reported.error.retryable is False
        finally:
            renpy.store.scene_session = original_session
            renpy.store.playback_state = original_playback
            renpy.store.scene_client_error = original_error

        class InvalidAckSessionProvider(object):
            def acknowledge(self, session, scene_ref):
                return SceneProviderResult(
                    "acknowledged", session=object(), scene_ref=scene_ref,
                )

        original_session = renpy.store.scene_session
        original_playback = renpy.store.playback_state
        original_error = renpy.store.scene_client_error
        original_runtime = _get_scene_provider_runtime()
        try:
            completed = prepare_json_scene_file(
                "test_fixtures/stage4_provider_retry.json",
                expected_scene_id="stage4-provider-retry",
            ).started().after_success(
                PlaybackActionResult.continue_()
            ).after_success(PlaybackActionResult.scene_end())
            renpy.store.playback_state = completed
            renpy.store.scene_session = SceneSessionState(
                provider_kind="fixture",
                phase="ready",
                active_ref="stage4-provider-retry",
            )
            _set_scene_provider_runtime(InvalidAckSessionProvider())
            ack_result = scene_client_acknowledge()
            assert ack_result.kind == "error"
            assert ack_result.error.code == "session_integrity_error"
            assert ack_result.error.retryable is False
        finally:
            renpy.store.scene_session = original_session
            renpy.store.playback_state = original_playback
            renpy.store.scene_client_error = original_error
            _set_scene_provider_runtime(original_runtime)

        # Incompatible session data from a save is normalized to a structured,
        # non-retryable error before controller code can dereference it.
        original_session = renpy.store.scene_session
        original_error = renpy.store.scene_client_error
        try:
            renpy.store.scene_session = object()
            scene_client_after_load()
            assert isinstance(scene_session, SceneSessionState)
            assert scene_session.phase == "error"
            assert scene_client_error.code == "session_integrity_error"
            assert scene_client_error.retryable is False
        finally:
            renpy.store.scene_session = original_session
            renpy.store.scene_client_error = original_error

    def stage4_assert_terminal_task_visible():
        names = (
            "scene_tasks", "task_status", "task_result", "check_status",
            "fill_scene_queue", "scene_file_exists", "prepare_json_scene_task",
        )
        originals = {name: getattr(renpy.store, name) for name in names}
        task_id = "0000000000000000000000c4"
        try:
            renpy.store.fill_scene_queue = lambda *args, **kwargs: None
            renpy.store.scene_file_exists = lambda candidate: False
            for remote_status, expected_code, expected_local in (
                    ("error", "task_failed", "error"),
                    (None, "task_not_found", "missing")):
                renpy.store.scene_tasks = [task_id]
                renpy.store.task_status = {task_id: "new"}
                renpy.store.task_result = {}
                renpy.store.check_status = (
                    lambda candidate, value=remote_status: (value, None)
                )
                result = TaskFileSceneProvider().poll(
                    SceneSessionState(provider_kind="task_file")
                )
                assert result.kind == "error"
                assert result.error.code == expected_code
                assert result.error.operation == "poll"
                assert result.scene_ref == task_id
                assert renpy.store.scene_tasks == [task_id]
                assert renpy.store.task_status[task_id] == expected_local

            later_id = "0000000000000000000000c5"
            renpy.store.scene_tasks = [task_id, later_id]
            renpy.store.task_status = {task_id: "error", later_id: "done"}
            renpy.store.task_result = {}
            renpy.store.check_status = lambda candidate: (
                ("error", None) if candidate == task_id else ("done", None)
            )
            renpy.store.scene_file_exists = lambda candidate: candidate == later_id
            result = TaskFileSceneProvider().poll(
                SceneSessionState(provider_kind="task_file")
            )
            assert result.kind == "error"
            assert result.scene_ref == task_id
            assert result.error.code == "task_failed"

            snapshot = {
                "schema_version": SCENE_SCHEMA_VERSION,
                "scene_id": task_id,
                "characters": {},
                "dialogue": [],
            }
            renpy.store.scene_tasks = [task_id]
            renpy.store.task_status = {task_id: "missing"}
            renpy.store.check_status = lambda candidate: ("done", None)
            renpy.store.scene_file_exists = lambda candidate: candidate == task_id
            renpy.store.prepare_json_scene_task = lambda candidate: PlaybackState(
                scene_id=task_id,
                schema_version=SCENE_SCHEMA_VERSION,
                content_hash=compute_scene_hash(snapshot),
                snapshot=snapshot,
                phase="ready",
            )
            recovered = TaskFileSceneProvider().poll(
                SceneSessionState(provider_kind="task_file")
            )
            assert recovered.kind == "ready"
            assert recovered.scene_ref == task_id
        finally:
            for name, value in originals.items():
                setattr(renpy.store, name, value)

    def stage4_assert_poll_work_is_bounded():
        names = (
            "scene_tasks", "task_status", "task_result", "create_task",
            "check_status", "prefetch_depth", "queue_session_id",
            "last_consumed_task_id", "queue_fill_predecessor",
        )
        originals = {name: getattr(renpy.store, name) for name in names}
        attempts = builtins.list()
        try:
            first_id = "0000000000000000000000d1"
            second_id = "0000000000000000000000d2"

            def create_task_spy(task_type, payload=None, idempotency_key=None):
                attempts.append(idempotency_key)
                if idempotency_key.endswith(":root"):
                    return first_id
                if idempotency_key.endswith(":" + first_id):
                    return second_id
                raise AssertionError("bounded refill lost its predecessor cursor")

            renpy.store.create_task = create_task_spy
            renpy.store.check_status = lambda task_id: ("consumed", None)
            renpy.store.scene_tasks = []
            renpy.store.task_status = {}
            renpy.store.task_result = {}
            renpy.store.prefetch_depth = 3
            renpy.store.queue_session_id = "stage4-bounded-poll"
            renpy.store.last_consumed_task_id = None
            renpy.store.queue_fill_predecessor = None

            poll_scene_tasks(max_status_checks=3, max_fill_steps=1)
            assert len(attempts) == 1
            assert renpy.store.scene_tasks == []

            poll_scene_tasks(max_status_checks=3, max_fill_steps=1)
            assert len(attempts) == 2
            assert attempts == [
                "stage4-bounded-poll:root",
                "stage4-bounded-poll:" + first_id,
            ]
            assert renpy.store.scene_tasks == []
        finally:
            for name, value in originals.items():
                setattr(renpy.store, name, value)

    class Stage4FakeProvider(object):
        def __init__(self, mode):
            self.mode = mode
            self.poll_calls = 0
            self.ack_calls = 0
            self.ack_succeeded = False
            self.prepare_count = 0
            self.events = []

        def _offline(self, operation):
            return SceneProviderError(
                code="provider_offline",
                operation=operation,
                message="Stage4 provider is offline.",
                retryable=True,
            )

        def poll(self, session):
            self.poll_calls += 1
            self.events.append("poll:{}".format(self.poll_calls))
            if self.mode == "poll_error":
                return SceneProviderResult(
                    kind="error",
                    session=session,
                    error=self._offline("poll"),
                )

            if self.poll_calls == 1:
                self.prepare_count += 1
                prepared = prepare_json_scene_file(
                    "test_fixtures/stage4_provider_retry.json",
                    expected_scene_id="stage4-provider-retry",
                )
                return SceneProviderResult(
                    kind="ready",
                    session=session,
                    scene_ref="stage4-provider-retry",
                    playback_state=prepared,
                )

            # The public controller loops after a committed boundary. End the
            # deterministic native case before another scene is requested.
            renpy.jump("stage4_provider_retry_complete")

        def acknowledge(self, session, scene_ref):
            self.ack_calls += 1
            self.events.append("ack:{}".format(self.ack_calls))
            if self.mode == "ack_error_once" and self.ack_calls == 1:
                return SceneProviderResult(
                    kind="error",
                    session=session,
                    scene_ref=scene_ref,
                    error=self._offline("acknowledge"),
                )

            self.ack_succeeded = True
            self.events.append("ack:success")
            return SceneProviderResult(
                kind="acknowledged",
                session=session,
                scene_ref=scene_ref,
            )

        def report_failure(self, session, scene_ref, playback_error):
            raise AssertionError("valid Stage4 fixture must not be rejected")

    def stage4_install_provider_fake(mode):
        state = stage0_state()
        original_factory = SCENE_PROVIDER_FACTORIES.get(STAGE4_PROVIDER_KIND)
        state["stage4_original_provider_factory"] = original_factory
        state["stage4_original_force_autosave"] = renpy.force_autosave
        fake = Stage4FakeProvider(mode)
        state["stage4_provider_fake"] = fake
        state["stage4_autosave_observations"] = []

        if mode == "playback_error_once":
            original_return = ACT_HANDLERS_REGISTRY["return"]
            state["stage4_original_return_handler"] = original_return
            state["stage4_playback_handler_calls"] = 0

            def fail_return_once(action, chars):
                state["stage4_playback_handler_calls"] += 1
                if state["stage4_playback_handler_calls"] == 1:
                    raise RuntimeError("stage4 injected transient handler error")
                return original_return(action, chars)

            ACT_HANDLERS_REGISTRY["return"] = fail_return_once

        def factory(*args, **kwargs):
            return fake

        def force_autosave_spy(*args, **kwargs):
            assert kwargs.get("block") is True
            state["stage4_autosave_observations"].append({
                "ack_succeeded": fake.ack_succeeded,
                "phase": scene_session.phase,
                "active_ref": scene_session.active_ref,
                "pending_operation": scene_session.pending_operation,
                "boundary_serial": scene_session.boundary_serial,
            })
            fake.events.append("autosave")

        SCENE_PROVIDER_FACTORIES[STAGE4_PROVIDER_KIND] = factory
        _set_scene_provider_runtime(None)
        renpy.store.scene_session = SceneSessionState(provider_kind=STAGE4_PROVIDER_KIND)
        renpy.store.scene_client_error = None
        renpy.force_autosave = force_autosave_spy

    def stage4_restore_provider_fake():
        state = stage0_state()
        original_factory = state.pop("stage4_original_provider_factory", None)
        if original_factory is None:
            SCENE_PROVIDER_FACTORIES.pop(STAGE4_PROVIDER_KIND, None)
        else:
            SCENE_PROVIDER_FACTORIES[STAGE4_PROVIDER_KIND] = original_factory
        original_autosave = state.pop("stage4_original_force_autosave", None)
        if original_autosave is not None:
            renpy.force_autosave = original_autosave
        original_return = state.pop("stage4_original_return_handler", None)
        if original_return is not None:
            ACT_HANDLERS_REGISTRY["return"] = original_return
        _set_scene_provider_runtime(None)

    def stage2_prepare_counted(relative_path, expected_scene_id):
        state = stage0_state()
        state["stage2_prepare_calls"] = state.get("stage2_prepare_calls", 0) + 1
        return prepare_json_scene_file(
            relative_path,
            expected_scene_id=expected_scene_id,
        )

    def stage2_install_throwing_handler(action):
        state = stage0_state()
        state["stage2_throwing_action"] = action
        state["stage2_original_handler"] = ACT_HANDLERS_REGISTRY[action]

        def explode(step, chars):
            raise RuntimeError("stage2 injected handler failure")

        ACT_HANDLERS_REGISTRY[action] = explode

    def stage2_restore_throwing_handler():
        state = stage0_state()
        action = state.pop("stage2_throwing_action", None)
        original = state.pop("stage2_original_handler", None)
        if action is not None and original is not None:
            ACT_HANDLERS_REGISTRY[action] = original

    def stage2_install_pause_probe():
        state = stage0_state()
        state["stage2_pause_calls"] = 0
        state["stage2_pause_cursors"] = builtins.list()
        state["stage2_original_pause_handler"] = ACT_HANDLERS_REGISTRY["pause"]

        def pause_probe(step, chars):
            state["stage2_pause_calls"] += 1
            state["stage2_pause_cursors"].append(playback_state.step_index)
            return state["stage2_original_pause_handler"](step, chars)

        ACT_HANDLERS_REGISTRY["pause"] = pause_probe

    def stage2_restore_pause_probe():
        state = stage0_state()
        original = state.pop("stage2_original_pause_handler", None)
        if original is not None:
            ACT_HANDLERS_REGISTRY["pause"] = original

    def stage3_install_throwing_line_middleware(phase="pre"):
        state = stage0_state()

        def explode(step, who, text):
            raise RuntimeError("stage3 injected line middleware failure")

        explode._line_mw_phase = phase
        state["stage3_throwing_line_middleware"] = explode
        LINE_MIDDLEWARES.append(explode)

    def stage3_restore_throwing_line_middleware():
        middleware = stage0_state().pop("stage3_throwing_line_middleware", None)
        if middleware in LINE_MIDDLEWARES:
            LINE_MIDDLEWARES.remove(middleware)

    def stage2_install_jump_guard():
        state = stage0_state()
        state["stage2_original_renpy_jump"] = renpy.jump

        def forbidden_jump(*args, **kwargs):
            raise AssertionError("JSON jump handler must return explicit control")

        renpy.jump = forbidden_jump

    def stage2_restore_jump_guard():
        original = stage0_state().pop("stage2_original_renpy_jump", None)
        if original is not None:
            renpy.jump = original

    def stage1_install_queue_flow_spies():
        state = stage0_state()
        state["queue_flow_events"] = []
        state["queue_flow_originals"] = {
            "get_next_ready_task_id": renpy.store.get_next_ready_task_id,
            "prepare_json_scene_task": renpy.store.prepare_json_scene_task,
            "consume_task": renpy.store.consume_task,
        }
        state["queue_flow_original_force_autosave"] = renpy.force_autosave
        ready_ids = ["task-a", "task-b"]

        def get_next_ready_task_id_spy():
            task_id = ready_ids.pop(0)
            state["queue_flow_events"].append("ready:" + task_id)
            return task_id

        def prepare_json_scene_task_spy(task_id):
            state["queue_flow_events"].append("play:" + task_id)
            if task_id == "task-b":
                renpy.jump("stage1_queue_flow_complete")
            snapshot = {
                "schema_version": SCENE_SCHEMA_VERSION,
                "scene_id": task_id,
                "characters": {},
                "dialogue": [],
            }
            return PlaybackState(
                scene_id=task_id,
                schema_version=SCENE_SCHEMA_VERSION,
                content_hash=compute_scene_hash(snapshot),
                snapshot=snapshot,
                phase="ready",
            )

        def consume_task_spy(task_id, **kwargs):
            state["queue_flow_events"].append("consume:" + task_id)
            return True

        renpy.store.get_next_ready_task_id = get_next_ready_task_id_spy
        renpy.store.prepare_json_scene_task = prepare_json_scene_task_spy
        renpy.store.consume_task = consume_task_spy
        renpy.force_autosave = lambda *args, **kwargs: None

    def stage1_restore_queue_flow_spies():
        originals = stage0_state().pop("queue_flow_originals", None)
        if originals:
            for name, function in originals.items():
                setattr(renpy.store, name, function)
        original_autosave = stage0_state().pop("queue_flow_original_force_autosave", None)
        if original_autosave is not None:
            renpy.force_autosave = original_autosave

    def stage1_install_queue_rejection_spies():
        state = stage0_state()
        bad_id = "000000000000000000000001"
        good_id = "000000000000000000000002"
        state["queue_rejection_events"] = []
        state["queue_rejection_originals"] = {
            "get_next_ready_task_id": renpy.store.get_next_ready_task_id,
            "prepare_json_scene_task": renpy.store.prepare_json_scene_task,
            "consume_task": renpy.store.consume_task,
            "fill_scene_queue": renpy.store.fill_scene_queue,
            "tasks": renpy.store.tasks,
            "scene_tasks": renpy.store.scene_tasks,
            "task_status": renpy.store.task_status,
            "task_result": renpy.store.task_result,
        }
        renpy.store.scene_tasks = [bad_id, good_id]
        renpy.store.task_status = {bad_id: "done", good_id: "done"}
        renpy.store.task_result = {bad_id: {"kind": "invalid"}, good_id: {"kind": "valid"}}

        class FakeTasks(object):
            def update_one(self, query, update):
                state["queue_rejection_events"].append("reject:" + str(query["_id"]))
                state["queue_rejection_update"] = update

        def get_next_ready_task_id_spy():
            task_id = renpy.store.scene_tasks[0]
            state["queue_rejection_events"].append("ready:" + task_id)
            # Without rejection the old flow selects the same done task again.
            if state["queue_rejection_events"].count("ready:" + bad_id) > 1:
                renpy.jump("stage1_queue_rejection_complete")
            return task_id

        def prepare_json_scene_task_spy(task_id):
            state["queue_rejection_events"].append("play:" + task_id)
            if task_id == bad_id:
                rejected = PlaybackState(
                    scene_id=bad_id,
                    schema_version=SCENE_SCHEMA_VERSION,
                    phase="error",
                    last_error=PlaybackError(
                        "unsupported_action",
                        "dialogue[0].type",
                        "unsupported action: music",
                    ),
                )
                renpy.store.playback_state = rejected
                return rejected
            renpy.jump("stage1_queue_rejection_complete")

        def consume_task_spy(task_id, **kwargs):
            state["queue_rejection_events"].append("unexpected-consume:" + task_id)

        renpy.store.get_next_ready_task_id = get_next_ready_task_id_spy
        renpy.store.prepare_json_scene_task = prepare_json_scene_task_spy
        renpy.store.consume_task = consume_task_spy
        renpy.store.fill_scene_queue = lambda: None
        renpy.store.tasks = FakeTasks()

    def stage1_restore_queue_rejection_spies():
        state = stage0_state()
        state["queue_rejection_remaining"] = list(renpy.store.scene_tasks)
        state["queue_rejection_status"] = dict(renpy.store.task_status)
        state["queue_rejection_result"] = dict(renpy.store.task_result)
        originals = state.pop("queue_rejection_originals", None)
        if originals:
            for name, value in originals.items():
                setattr(renpy.store, name, value)

    if STAGE0_TEST_MODE:
        @register_line_middleware
        def stage0_probe_line(step, who, text):
            metadata = step.get("metadata", {})
            name = metadata.get("test_probe") if isinstance(metadata, dict) else None
            # Stage 0 fixtures predate the v1 action metadata contract. Keep
            # their probes while ensuring v1 tests prove the canonical form.
            if not name:
                name = step.get("test_probe")
            if name:
                lines = stage0_state()["lines"]
                lines[name] = lines.get(name, 0) + 1
                stage0_state()["cursor_by_probe"][name] = playback_state.step_index

        stage0_probe_line._line_mw_phase = "pre"


label test_json_fixture:
    $ stage0_prepare_test("playback_offline")
    call run_json_scene_file("test_fixtures/playback_baseline.json")
    $ stage0_mark("playback_offline")
    "Fixture complete."
    return

label stage0_handlers_return_label:
    $ stage0_prepare_test("handlers_return")
    call run_json_scene_file("test_fixtures/handlers_return.json")
    $ stage0_mark("handlers_return")
    "Stage0 handlers return complete."
    return

label stage0_return_label:
    $ stage0_prepare_test("return")
    call run_json_scene_file("test_fixtures/return_semantics.json")
    $ stage0_mark("return_complete")
    "Stage0 return complete."
    return

label stage0_jump_label:
    $ stage0_prepare_test("jump")
    call run_json_scene_file("test_fixtures/jump.json")
    $ stage0_jump_result = _return
    if stage0_jump_result.control.kind == "goto":
        jump expression stage0_jump_result.control.target
    $ stage0_mark("jump_fell_through")
    "Stage0 jump unexpectedly fell through."
    return

label stage0_jump_target:
    $ stage0_mark("jump_target")
    "Stage0 jump target reached."
    return

label stage0_transition_fade_label:
    $ stage0_prepare_test("transition_fade")
    call run_json_scene_file("test_fixtures/transition_fade.json")
    $ stage0_mark("transition_fade")
    "Stage0 fade transition complete."
    return

label stage0_scene_boundary_label:
    $ stage0_prepare_test("scene_boundary")
    call run_json_scene_file("test_fixtures/scene_boundary_a.json")
    call run_json_scene_file("test_fixtures/scene_boundary_b.json")
    $ stage0_mark("scene_boundary")
    "Stage0 scene boundary complete."
    return

label stage0_history_ui_label:
    $ stage0_prepare_test("history_ui")
    call run_json_scene_file("test_fixtures/playback_baseline.json")
    $ stage0_mark("history_ready")
    "Stage0 history ready."
    return

label stage0_skip_label:
    $ stage0_prepare_test("skip")
    $ stage0_enable_skip()
    call run_json_scene_file("test_fixtures/multi_line.json")
    $ stage0_stop_skip_for_marker()
    $ stage0_mark("skip")
    "Stage0 skip complete."
    return

label stage0_auto_label:
    $ stage0_prepare_test("auto")
    $ stage0_enable_auto()
    call run_json_scene_file("test_fixtures/multi_line.json")
    $ stage0_stop_auto_for_marker()
    $ stage0_mark("auto")
    "Stage0 auto complete."
    return

label stage0_save_load_mid_scene_label:
    $ stage0_prepare_test("save_load_mid_scene")
    $ stage0_delete_save()
    call run_json_scene_file("test_fixtures/save_load_mid_scene.json")
    $ stage0_mark("save_load_finished")
    "Stage0 save/load complete."
    return

label stage0_rollback_mid_scene_label:
    $ stage0_prepare_test("rollback_mid_scene")
    call run_json_scene_file("test_fixtures/rollback_mid_scene.json")
    $ stage0_mark("rollback_finished")
    "Stage0 rollback complete."
    return

label stage0_unknown_action_label:
    $ stage0_prepare_test("unknown_action")
    call run_json_scene_file("test_fixtures/unknown_action.json")
    "Stage0 unknown action rejected."
    return

label stage0_animate_object_label:
    $ stage0_prepare_test("animate_object")
    $ stage0_install_animate_spy()
    call run_json_scene_file("test_fixtures/animate_object.json")
    $ stage0_restore_animate_handler()
    $ stage0_mark("animate_object")
    "Stage0 animate object characterization complete."
    return

label stage0_missing_background_label:
    $ stage0_prepare_test("missing_background")
    call run_json_scene_file("test_fixtures/missing_background.json")
    "Stage0 missing background rejected."
    return


label stage1_contract_valid_label:
    $ stage0_prepare_test("stage1_contract_valid")
    $ playback_state = prepare_playback("test_fixtures/stage1_valid_v1.json", expected_scene_id="stage1-valid-v1")
    "Stage1 valid playback state prepared."
    return

label stage1_contract_jump_target:
    "Stage1 contract jump target."
    return

label stage1_state_save_load_label:
    $ stage0_prepare_test("stage1_state_save_load")
    $ playback_state = prepare_playback("test_fixtures/stage1_valid_v1.json")
    "Stage1 state save point."
    $ playback_state = playback_state.with_step_index(4)
    "Stage1 state mutated."
    return


label stage1_player_valid_label:
    $ stage0_prepare_test("stage1_player_valid_v1")
    call run_json_scene_file("test_fixtures/stage1_player_valid_v1.json", expected_scene_id="stage1-player-valid-v1")
    "Stage1 player valid playback complete."
    return


label stage1_player_invalid_label:
    $ stage0_prepare_test("stage1_player_rejects_before_handler")
    call run_json_scene_file("test_fixtures/stage1_player_invalid_v1.json", expected_scene_id="stage1-player-invalid-v1")
    "Stage1 player invalid playback rejected."
    return


label stage1_queue_flow_test_start:
    $ stage0_prepare_test("stage1_queue_flow")
    $ stage1_install_queue_flow_spies()
    jump play_next_scene


label stage1_queue_flow_complete:
    $ stage1_restore_queue_flow_spies()
    "Stage1 queue flow complete."
    return


label stage1_queue_rejection_test_start:
    $ stage0_prepare_test("stage1_queue_rejection")
    $ stage1_install_queue_rejection_spies()
    jump play_next_scene


label stage1_queue_rejection_complete:
    $ stage1_restore_queue_rejection_spies()
    "Stage1 queue rejection complete."
    return


label stage2_progression_label:
    $ stage0_prepare_test("stage2_cursor_progression")
    call run_json_scene_file("test_fixtures/stage2_progression_12_lines.json", expected_scene_id="stage2-progression-12")
    $ stage2_result = _return
    $ stage0_mark("stage2_progression_complete")
    "Stage2 progression complete."
    return


label stage2_save_load_label:
    $ stage0_prepare_test("stage2_save_load")
    $ stage2_delete_save()
    $ playback_state = stage2_prepare_counted("test_fixtures/stage2_save_load.json", "stage2-save-load")
    call _run_prepared_json_scene
    $ stage2_result = _return
    $ stage0_mark("stage2_save_load_complete")
    "Stage2 save/load complete."
    return


label stage2_return_label:
    $ stage0_prepare_test("stage2_return")
    call run_json_scene_file("test_fixtures/stage2_return.json", expected_scene_id="stage2-return")
    $ stage2_result = _return
    $ stage0_mark("stage2_return_complete")
    "Stage2 return complete."
    return


label stage2_natural_end_label:
    $ stage0_prepare_test("stage2_natural_end")
    call run_json_scene_file("test_fixtures/stage2_natural_end.json", expected_scene_id="stage2-natural-end")
    $ stage2_result = _return
    $ stage0_mark("stage2_natural_end_complete")
    "Stage2 natural end complete."
    return


label stage2_boundary_label:
    $ stage0_prepare_test("stage2_boundary")
    call run_json_scene_file("test_fixtures/stage2_boundary_a.json", expected_scene_id="stage2-boundary-a")
    $ stage2_boundary_a_result = _return
    call run_json_scene_file("test_fixtures/stage2_boundary_b.json", expected_scene_id="stage2-boundary-b")
    $ stage2_boundary_b_result = _return
    $ stage0_mark("stage2_boundary_complete")
    "Stage2 boundary complete."
    return


label stage2_jump_dispatch_label:
    $ stage0_prepare_test("stage2_jump_dispatch")
    call run_json_scene_file("test_fixtures/stage2_jump.json", expected_scene_id="stage2-jump")
    $ stage2_jump_result = _return
    if stage2_control_field(stage2_result_control(stage2_jump_result), "kind") == "goto":
        jump expression stage2_control_field(stage2_result_control(stage2_jump_result), "target")
    $ stage0_mark("stage2_jump_fell_through")
    "Stage2 jump unexpectedly fell through."
    return


label stage2_jump_control_target:
    $ stage0_mark("stage2_jump_target")
    "Stage2 jump control target reached."
    return


label stage2_handler_error_label:
    call run_json_scene_file("test_fixtures/stage2_handler_error.json", expected_scene_id="stage2-handler-error")
    $ stage2_handler_result = _return
    $ stage2_restore_throwing_handler()
    $ stage0_mark("stage2_handler_error_complete")
    "Stage2 handler error complete."
    return


label stage2_pause_checkpoint_label:
    $ stage0_prepare_test("stage2_pause_checkpoint")
    $ stage2_install_pause_probe()
    call run_json_scene_file("test_fixtures/stage2_pause_checkpoint.json", expected_scene_id="stage2-pause-checkpoint")
    $ stage2_pause_result = _return
    $ stage2_restore_pause_probe()
    $ stage0_mark("stage2_pause_checkpoint_complete")
    "Stage2 pause checkpoint complete."
    return


# Stage 3 RED labels. They deliberately use the Stage 2 public player and
# native FileSave/FileLoad actions. Production history/save callbacks are not
# installed here.
label stage3_history_annotations_label:
    $ stage0_prepare_test("stage3_history_annotations")
    call run_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history")
    $ stage3_history_result = _return
    "Stage3 history annotations complete."
    return


label stage3_history_save_load_label:
    $ stage0_prepare_test("stage3_history_save_load")
    $ stage3_delete_save(STAGE3_HISTORY_SAVE_SLOT)
    call run_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history")
    $ stage3_history_save_load_result = _return
    "Stage3 history save/load complete."
    return


label stage3_save_json_label:
    $ stage0_prepare_test("stage3_save_json")
    $ stage3_delete_save(STAGE3_JSON_SAVE_SLOT)
    $ playback_state = prepare_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history").started().with_step_index(1)
    "Stage3 save JSON point."
    return


label stage3_empty_save_json_label:
    $ stage0_prepare_test("stage3_empty_save_json")
    $ stage3_delete_save(STAGE3_EMPTY_SAVE_SLOT)
    $ playback_state = None
    "Stage3 empty save JSON point."
    return


label stage3_history_rollback_identifier_label:
    $ stage0_prepare_test("stage3_history_rollback_identifier")
    call run_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history")
    $ stage3_history_rollback_result = _return
    "Stage3 history rollback identifier complete."
    return


label stage3_line_middleware_error_label:
    $ stage0_prepare_test("stage3_line_middleware_error")
    $ stage3_install_throwing_line_middleware()
    call run_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history")
    $ stage3_line_middleware_result = _return
    $ stage3_restore_throwing_line_middleware()
    "Stage3 line middleware error complete."
    return


label stage3_post_line_middleware_error_label:
    $ stage0_prepare_test("stage3_post_line_middleware_error")
    $ stage3_install_throwing_line_middleware("post")
    call run_json_scene_file("test_fixtures/stage3_history.json", expected_scene_id="stage3-history")
    $ stage3_post_line_middleware_result = _return
    $ stage3_restore_throwing_line_middleware()
    "Stage3 post line middleware error complete."
    return


label stage3_untrusted_text_label:
    $ stage0_prepare_test("stage3_untrusted_text")
    call run_json_scene_file("test_fixtures/stage3_untrusted_text.json", expected_scene_id="stage3-untrusted-text")
    $ stage3_untrusted_text_result = _return
    "Stage3 untrusted text complete."
    return


label stage3_invalid_fileload_label:
    $ stage0_prepare_test("stage3_invalid_fileload")
    $ stage3_delete_save(STAGE3_INVALID_SAVE_SLOT)
    $ playback_state = stage3_invalid_state_for_save()
    "Stage3 invalid save setup."
    $ renpy.save(STAGE3_INVALID_SAVE_SLOT)
    $ stage0_mark("stage3_invalid_after_load_resumed")
    "Stage3 invalid save ready to load."
    return


# Stage 4 RED entry points retain the public `start` flow. Only the provider
# factory is replaced, so the tests cover the real controller and UI routing.
label stage4_provider_retry_start:
    $ stage0_prepare_test("stage4_provider_retry")
    $ stage4_install_provider_fake("ack_error_once")
    jump start


label stage4_playback_retry_start:
    $ stage0_prepare_test("stage4_playback_retry")
    $ stage4_install_provider_fake("playback_error_once")
    jump start


label stage4_provider_retry_complete:
    $ stage4_retry_fake = stage0_state()["stage4_provider_fake"]
    $ stage4_retry_autosaves = list(stage0_state()["stage4_autosave_observations"])
    $ stage4_retry_events = list(stage4_retry_fake.events)
    $ stage4_restore_provider_fake()
    "Stage4 provider retry complete."
    return


label stage4_provider_main_menu_start:
    $ stage0_prepare_test("stage4_provider_main_menu")
    $ stage4_install_provider_fake("poll_error")
    jump start


label stage4_real_autosave_start:
    $ stage0_prepare_test("stage4_real_autosave")
    python:
        for slot_number in range(1, 11):
            try:
                renpy.unlink_save("auto-{}".format(slot_number))
            except Exception:
                pass
        playback_state = prepare_json_scene_file(
            "test_fixtures/stage4_provider_retry.json",
            expected_scene_id="stage4-provider-retry",
        )
        playback_state = playback_state.started().after_success(
            PlaybackActionResult.continue_()
        ).after_success(PlaybackActionResult.scene_end())
        scene_session = SceneSessionState(
            provider_kind="fixture",
            phase="acknowledged",
            pending_operation="acknowledge",
            active_ref="stage4-provider-retry",
        )
    $ scene_client_commit_boundary()
    $ scene_client_autosave_boundary()
    if stage0_state().get("stage4_autosave_load_requested"):
        python:
            stage0_state()["stage4_restored_boundary"] = {
                "phase": scene_session.phase,
                "active_ref": scene_session.active_ref,
                "boundary_serial": scene_session.boundary_serial,
                "scene_id": playback_state.scene_id,
                "playback_phase": playback_state.phase,
                "step_index": playback_state.step_index,
            }
        "Stage4 boundary autosave restored."
        return
    "Stage4 boundary autosave ready."
    $ scene_session = SceneSessionState(provider_kind="fixture", phase="waiting")
    $ playback_state = None
    "Stage4 boundary state mutated."
    $ stage0_state()["stage4_autosave_load_requested"] = True
    $ renpy.load("auto-1")


label stage4_invalid_session_fileload_start:
    $ stage0_prepare_test("stage4_invalid_session_fileload")
    python:
        try:
            renpy.unlink_save(STAGE4_INVALID_SESSION_SLOT)
        except Exception:
            pass
        playback_state = prepare_json_scene_file(
            "test_fixtures/stage4_provider_retry.json",
            expected_scene_id="stage4-provider-retry",
        ).started().after_success(
            PlaybackActionResult.continue_()
        ).after_success(PlaybackActionResult.scene_end())
        scene_session = SceneSessionState(
            provider_kind="fixture",
            phase="boundary",
            pending_operation="poll",
            active_ref=None,
            boundary_serial=1,
            state_version=999,
        )
    "Stage4 invalid session save setup."
    $ renpy.save(STAGE4_INVALID_SESSION_SLOT)
    "Stage4 invalid session ready to load."
    $ renpy.load(STAGE4_INVALID_SESSION_SLOT)
