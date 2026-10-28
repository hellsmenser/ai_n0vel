testcase default:
    run Start("test_json_fixture")
    click until "Fixture complete."

    assert stage0_marked("playback_offline")
    assert stage0_history_count("(fixture) Лира проверяет базовый проигрыватель.") == 1
    assert stage0_history_count("(fixture) Каэль видит вторую реплику.") == 1
    assert stage0_history_count("(fixture) Лира завершает проверку.") == 1
    assert renpy.screenshot(stage0_artifact_path("baseline-fixture.png"))
    run Quit(confirm=False)

testcase stage0_playback_offline:
    run Start("test_json_fixture")
    click until "Fixture complete."

    assert stage0_marked("playback_offline")
    assert stage0_history_count("(fixture) Лира проверяет базовый проигрыватель.") == 1
    assert stage0_history_count("(fixture) Каэль видит вторую реплику.") == 1
    assert stage0_history_count("(fixture) Лира завершает проверку.") == 1
    assert renpy.screenshot(stage0_artifact_path("stage0-playback-offline.png"))
    run Quit(confirm=False)

testcase stage0_handlers_return:
    run Start("stage0_handlers_return_label")
    click until "Stage0 handlers return complete."

    assert stage0_marked("handlers_return")
    assert stage0_probe_count("handlers_line_one") == 1
    assert stage0_probe_count("handlers_line_two") == 1
    assert stage0_probe_count("handlers_after_return") == 0
    assert stage0_history_count("Stage0 handlers line one.") == 1
    assert stage0_history_count("Stage0 handlers line two.") == 1
    run Quit(confirm=False)

testcase stage0_return:
    run Start("stage0_return_label")
    click until "Stage0 return complete."

    assert stage0_marked("return_complete")
    assert stage0_probe_count("before_return") == 1
    assert stage0_probe_count("after_return") == 0
    assert stage0_history_count("Stage0 return before.") == 1
    assert stage0_history_count("Stage0 return sentinel.") == 0
    run Quit(confirm=False)

testcase stage0_jump:
    run Start("stage0_jump_label")
    click until "Stage0 jump target reached."

    assert stage0_marked("jump_target")
    assert not stage0_marked("jump_fell_through")
    assert stage0_probe_count("jump_pre") == 1
    assert stage0_probe_count("jump_after") == 0
    assert stage0_history_count("Stage0 jump pre-line.") == 1
    run Quit(confirm=False)

testcase stage0_transition_fade:
    run Start("stage0_transition_fade_label")
    click until "Stage0 fade transition complete."

    assert stage0_marked("transition_fade")
    assert stage0_probe_count("fade_line") == 1
    assert stage0_history_count("Stage0 fade line.") == 1
    run Quit(confirm=False)

testcase stage0_scene_boundary:
    run Start("stage0_scene_boundary_label")
    click until "Stage0 scene boundary complete."

    assert stage0_marked("scene_boundary")
    assert stage0_probe_count("scene_a_end") == 1
    assert stage0_probe_count("scene_b_start") == 1
    assert stage0_history_count("Stage0 scene A end.") == 1
    assert stage0_history_count("Stage0 scene B start.") == 1
    run Quit(confirm=False)

testcase stage0_history_ui:
    run Start("stage0_history_ui_label")
    click until "Stage0 history ready."
    run ShowMenu("history")

    assert renpy.get_screen("history") is not None
    assert stage0_history_count("(fixture) Лира проверяет базовый проигрыватель.") == 1
    assert stage0_history_count("(fixture) Каэль видит вторую реплику.") == 1
    assert stage0_history_count("(fixture) Лира завершает проверку.") == 1
    assert renpy.screenshot(stage0_artifact_path("stage0-history-ui.png"))
    run Return()
    run Quit(confirm=False)

testcase stage0_skip:
    $ _test.timeout = 15.0
    run Start("stage0_skip_label")
    run Skip()
    pause 0.05 until "Stage0 skip complete."

    assert stage0_marked("skip")
    assert stage0_probe_count("automatic_one") == 1
    assert stage0_probe_count("automatic_two") == 1
    assert stage0_probe_count("automatic_three") == 1
    $ stage0_restore_preferences()
    run Quit(confirm=False)

testcase stage0_auto:
    $ _test.timeout = 15.0
    run Start("stage0_auto_label")
    pause 0.05 until "Stage0 auto complete."

    assert stage0_marked("auto")
    assert stage0_probe_count("automatic_one") == 1
    assert stage0_probe_count("automatic_two") == 1
    assert stage0_probe_count("automatic_three") == 1
    $ stage0_restore_preferences()
    run Quit(confirm=False)

testcase stage0_save_load_mid_scene:
    $ _test.timeout = 15.0
    run Start("stage0_save_load_mid_scene_label")
    click until "Stage0 save middle."
    run FileSave(STAGE0_SAVE_SLOT, confirm=False, slot=True)
    click until "Stage0 save/load complete."

    assert stage0_probe_count("save_early") == 1
    assert stage0_probe_count("save_middle") == 1
    assert stage0_probe_count("save_late") == 1

    run FileLoad(STAGE0_SAVE_SLOT, confirm=False, slot=True)
    click until "Stage0 save/load complete."

    assert stage0_probe_count("save_early") == 1
    assert stage0_probe_count("save_middle") == 2
    assert stage0_probe_count("save_late") == 2
    $ stage0_delete_save()
    run Quit(confirm=False)

testcase stage0_rollback_mid_scene:
    $ _test.timeout = 15.0
    run Start("stage0_rollback_mid_scene_label")
    click until "Stage0 rollback middle."
    run Rollback(force=True)
    click until "Stage0 rollback complete."

    assert stage0_marked("rollback_finished")
    assert stage0_probe_count("rollback_early") == 2
    assert stage0_probe_count("rollback_middle") == 2
    assert stage0_probe_count("rollback_late") == 1
    run Quit(confirm=False)

testcase stage0_known_issue_unknown_action:
    run Start("stage0_unknown_action_label")
    click until "Stage0 unknown action rejected."

    $ stage1_assert_error(playback_state, "unsupported_action", "dialogue[1].type")
    assert stage0_probe_count("unknown_after") == 0
    assert stage0_history_count("Stage0 unknown action was skipped.") == 0
    run Quit(confirm=False)

testcase stage0_known_issue_animate_object:
    $ normalized = prepare_playback("test_fixtures/animate_object.json", expected_scene_id="animate_object")
    assert normalized.phase == "ready"
    assert normalized.snapshot["dialogue"][2]["effect"] == {"type": "shake"}
    assert normalized.snapshot["dialogue"][4]["effect"] == {"type": "shake"}
    run Start("stage0_animate_object_label")
    click until "Stage0 animate object characterization complete."

    assert stage0_marked("animate_object")
    assert stage0_state()["animate_calls"]["object"] == 2
    assert stage0_state()["animate_calls"]["string"] == 0
    run Quit(confirm=False)

testcase stage0_missing_background:
    run Start("stage0_missing_background_label")
    click until "Stage0 missing background rejected."

    $ stage1_assert_error(playback_state, "missing_resource", "dialogue[0].target")
    assert stage0_probe_count("missing_background_line") == 0
    assert stage0_history_count("Stage0 missing background fell through.") == 0
    run Quit(confirm=False)

testcase stage0_start_without_mongo:
    run Start("start")
    click until "Main Menu"
    assert stage4_error_field(scene_client_error, "code") == "provider_offline"
    assert main_menu
    run Quit(confirm=False)


testcase stage1_contract_valid_state:
    run Start("stage1_contract_valid_label")
    click until "Stage1 valid playback state prepared."

    assert playback_state.phase == "ready"
    assert playback_state.state_version == 2
    assert playback_state.schema_version == 1
    assert playback_state.scene_id == "stage1-valid-v1"
    assert playback_state.step_index == 0
    assert playback_state.scene_variables == {}
    assert playback_state.branch_trace == []
    assert playback_state.last_error is None
    assert playback_state.migrated_from_schema is None
    assert playback_state.content_hash.startswith("sha256:")
    assert len(playback_state.content_hash) == 71
    assert verify_playback_state(playback_state) is None
    run Quit(confirm=False)


testcase stage1_contract_hash_canonical:
    $ first = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ reordered = prepare_playback("test_fixtures/stage1_valid_v1_reordered.json")
    $ legacy = prepare_playback("test_fixtures/stage1_legacy_v0.json")

    assert first.phase == "ready"
    assert reordered.phase == "ready"
    assert first.content_hash == reordered.content_hash
    assert compute_scene_hash(stage1_snapshot(first)) == first.content_hash
    assert legacy.phase == "ready"
    assert first.content_hash != legacy.content_hash
    run Quit(confirm=False)


testcase stage1_contract_rejects_before_handlers:
    $ stage0_prepare_test("stage1_contract_rejects")
    $ stage1_install_handler_guards()
    $ unknown = prepare_playback("test_fixtures/stage1_unknown_action.json")
    $ missing = prepare_playback("test_fixtures/stage1_missing_image.json")
    $ stage1_restore_handler_guards()

    $ stage1_assert_error(unknown, "unsupported_action", "dialogue[0].type")
    $ stage1_assert_error(missing, "missing_resource", "dialogue[0].target")
    run Quit(confirm=False)


testcase stage1_contract_duplicate_key:
    $ duplicate = prepare_playback("test_fixtures/stage1_duplicate_key.invalid")

    $ stage1_assert_error(duplicate, "duplicate_json_key", "scene_id")
    run Quit(confirm=False)


testcase stage1_contract_malformed_inputs:
    $ scalar = prepare_playback("test_fixtures/stage1_scalar_root.json")
    $ bad_legacy = prepare_playback("test_fixtures/stage1_legacy_bad_dialogue.json")
    $ boolean_schema = prepare_playback("test_fixtures/stage1_schema_bool.json")
    $ future_schema = prepare_playback("test_fixtures/stage1_schema_future.json")

    $ stage1_assert_error(scalar, "contract_violation", "$")
    $ stage1_assert_error(bad_legacy, "contract_violation", "dialogue")
    $ stage1_assert_error(boolean_schema, "contract_violation", "schema_version")
    $ stage1_assert_error(future_schema, "unsupported_schema_version", "schema_version")
    run Quit(confirm=False)


testcase stage1_contract_untrusted_limits:
    $ oversized = prepare_playback_bytes(b"x" * (MAX_SCENE_RAW_BYTES + 1))
    $ deep = prepare_playback_bytes(stage1_too_deep_bytes())
    $ parser_deep = prepare_playback_bytes(stage1_parser_recursion_bytes())
    $ nodes = prepare_playback_bytes(stage1_too_many_nodes_bytes())
    $ actions = prepare_playback_bytes(stage1_too_many_actions_bytes())
    $ characters = prepare_playback_bytes(stage1_too_many_characters_bytes())
    $ long_text = prepare_playback_bytes(stage1_too_long_text_bytes())

    $ stage1_assert_error_code(oversized, "contract_violation")
    $ stage1_assert_error_code(deep, "contract_violation")
    $ stage1_assert_error_code(parser_deep, "contract_violation")
    $ stage1_assert_error_code(nodes, "contract_violation")
    $ stage1_assert_error_code(actions, "contract_violation")
    $ stage1_assert_error_code(characters, "contract_violation")
    $ stage1_assert_error_code(long_text, "contract_violation")
    run Quit(confirm=False)


testcase stage1_contract_legacy_migration:
    $ legacy = prepare_playback("test_fixtures/stage1_legacy_v0.json")

    assert legacy.phase == "ready"
    assert legacy.schema_version == 1
    assert legacy.scene_id == "stage1-legacy-v0"
    assert legacy.migrated_from_schema == 0
    assert stage1_snapshot(legacy)["metadata"]["test_probe"] == "legacy-top-level-probe"
    assert stage1_snapshot(legacy)["dialogue"][0] == {"type": "scene", "target": "bg_tavern_interior"}
    assert stage1_snapshot(legacy)["dialogue"][1]["effect"] == {"type": "shake"}
    assert verify_playback_state(legacy) is None
    run Quit(confirm=False)


testcase stage1_state_save_load_roundtrip:
    $ stage1_delete_save()
    run Start("stage1_state_save_load_label")
    click until "Stage1 state save point."
    run FileSave(STAGE1_SAVE_SLOT, confirm=False, slot=True)
    click until "Stage1 state mutated."

    assert playback_state.step_index == 4
    run FileLoad(STAGE1_SAVE_SLOT, confirm=False, slot=True)
    assert playback_state.phase == "ready"
    assert playback_state.step_index == 0
    assert playback_state.content_hash == compute_scene_hash(stage1_snapshot(playback_state))
    assert verify_playback_state(playback_state) is None
    $ stage1_delete_save()
    run Quit(confirm=False)


testcase stage1_state_integrity_tampering:
    $ state_version_bool = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ state_version_bool.state_version = True
    $ stage1_assert_integrity_error(state_version_bool, "state_version")

    $ schema_version_bool = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ schema_version_bool.schema_version = True
    $ stage1_assert_integrity_error(schema_version_bool, "schema_version")

    $ out_of_range_step = prepare_playback("test_fixtures/stage1_valid_v1.json").with_step_index(99)
    $ stage1_assert_integrity_error(out_of_range_step, "step_index")

    $ bad_variables = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ bad_variables.scene_variables = {"bad": set([1])}
    $ stage1_assert_integrity_error(bad_variables, "scene_variables.bad")

    $ bad_trace = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ bad_trace.branch_trace = {"not": "a list"}
    $ stage1_assert_integrity_error(bad_trace, "branch_trace")

    $ error_on_ready = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ error_on_ready.last_error = PlaybackError("contract_violation", "x", "must not exist on ready state")
    $ stage1_assert_integrity_error(error_on_ready, "last_error")

    $ ready_with_cursor = prepare_playback("test_fixtures/stage1_valid_v1.json").with_step_index(1)
    $ stage1_assert_integrity_error(ready_with_cursor, "step_index")

    $ playing_at_end = prepare_playback("test_fixtures/stage1_valid_v1.json").started().with_step_index(len(stage1_snapshot(prepare_playback("test_fixtures/stage1_valid_v1.json"))["dialogue"]))
    $ stage1_assert_integrity_error(playing_at_end, "step_index")

    $ completed_at_start = prepare_playback("test_fixtures/stage1_valid_v1.json")
    $ completed_at_start.phase = "completed"
    $ stage1_assert_integrity_error(completed_at_start, "step_index")

    $ completed_after_nonterminal = prepare_playback("test_fixtures/stage1_valid_v1.json").with_step_index(1)
    $ completed_after_nonterminal.phase = "completed"
    $ stage1_assert_integrity_error(completed_after_nonterminal, "step_index")

    $ legitimate_error = prepare_playback("test_fixtures/stage1_scalar_root.json")
    assert legitimate_error.phase == "error"
    assert verify_playback_state(legitimate_error) is None
    run Quit(confirm=False)


# Integration cases intentionally exercise the public player entry point rather
# than prepare_playback directly. They begin RED until Stage 1 connects the
# contract/state layer to playback.rpy.
testcase stage1_player_valid_v1:
    run Start("stage1_player_valid_label")
    click until "Stage1 player valid playback complete."

    assert playback_state.phase == "completed"
    assert playback_state.scene_id == "stage1-player-valid-v1"
    assert stage0_probe_count("stage1_player_valid_line") == 1
    assert stage0_history_count("Stage1 player valid line.") == 1
    run Quit(confirm=False)


testcase stage1_player_rejects_before_handler:
    run Start("stage1_player_invalid_label")
    click until "Stage1 player invalid playback rejected."

    $ stage1_assert_error(playback_state, "unsupported_action", "dialogue[0].type")
    assert stage0_probe_count("stage1_player_invalid_line") == 0
    assert stage0_history_count("Stage1 invalid line must not execute.") == 0
    run Quit(confirm=False)


testcase stage1_queue_consumes_once:
    run Start("stage1_queue_flow_test_start")
    click until "Stage1 queue flow complete."

    assert stage0_state()["queue_flow_events"] == [
        "ready:task-a",
        "play:task-a",
        "consume:task-a",
        "ready:task-b",
        "play:task-b",
    ]
    run Quit(confirm=False)


testcase stage1_contract_handler_registry:
    assert set(_ACTION_FIELDS.keys()) == set(get_act_handlers().keys())
    run Quit(confirm=False)


testcase stage1_queue_rejects_invalid_once:
    run Start("stage1_queue_rejection_test_start")
    click until "Main Menu"

    $ bad_id = "000000000000000000000001"
    $ good_id = "000000000000000000000002"
    assert stage0_state()["queue_rejection_events"] == [
        "ready:" + bad_id,
        "play:" + bad_id,
        "reject:" + bad_id,
    ]
    assert scene_tasks == [good_id]
    assert bad_id not in task_status
    assert bad_id not in task_result
    assert stage0_state()["queue_rejection_update"]["$set"]["status"] == "error"
    assert stage0_state()["queue_rejection_update"]["$set"]["error"]["code"] == "unsupported_action"
    assert playback_state.phase == "error"
    assert main_menu
    $ stage1_restore_queue_rejection_spies()
    run Quit(confirm=False)


# Stage 2 action-granular player semantics.
testcase stage2_cursor_progression:
    $ _test.timeout = 20.0
    run Start("stage2_progression_label")
    click until "Stage2 progression complete."
    assert stage0_state()["cursor_by_probe"]["stage2_progress_1"] == 0
    assert stage0_state()["cursor_by_probe"]["stage2_progress_3"] == 2
    assert stage0_state()["cursor_by_probe"]["stage2_progress_12"] == 11
    assert stage2_result_state(stage2_result).phase == "completed"
    assert playback_state.step_index == 13
    assert stage0_marked("stage2_progression_complete")
    assert all(stage0_probe_count("stage2_progress_%d" % index) == 1 for index in range(1, 13))
    run Quit(confirm=False)


testcase stage2_save_load_repeats_current_only:
    $ _test.timeout = 20.0
    run Start("stage2_save_load_label")
    click until "Stage2 save 2."
    assert playback_state.step_index == 1
    assert stage0_state()["stage2_prepare_calls"] == 1
    run FileSave(STAGE2_SAVE_SLOT, confirm=False, slot=True)

    click until "Stage2 save/load complete."
    assert stage0_probe_count("stage2_save_1") == 1
    assert stage0_probe_count("stage2_save_2") == 1
    assert stage0_probe_count("stage2_save_3") == 1

    run FileLoad(STAGE2_SAVE_SLOT, confirm=False, slot=True)
    click until "Stage2 save/load complete."
    assert stage0_state()["stage2_prepare_calls"] == 1
    assert stage0_probe_count("stage2_save_1") == 1
    assert stage0_probe_count("stage2_save_2") == 2
    assert stage0_probe_count("stage2_save_3") == 2
    $ stage2_delete_save()
    run Quit(confirm=False)


testcase stage2_rollback_one_line:
    $ _test.timeout = 20.0
    run Start("stage2_progression_label")
    click until "Stage2 progress 12."
    run Rollback(force=True, checkpoints=1, greedy=False)
    click until "Stage2 progress 11."
    assert playback_state.scene_id == "stage2-progression-12"
    assert playback_state.step_index == 10
    click until "Stage2 progression complete."
    run Quit(confirm=False)


testcase stage2_rollback_three_lines:
    $ _test.timeout = 20.0
    run Start("stage2_progression_label")
    click until "Stage2 progress 12."
    run Rollback(force=True, checkpoints=3, greedy=False)
    click until "Stage2 progress 9."
    assert playback_state.scene_id == "stage2-progression-12"
    assert playback_state.step_index == 8
    click until "Stage2 progression complete."
    run Quit(confirm=False)


testcase stage2_rollback_ten_lines:
    $ _test.timeout = 20.0
    run Start("stage2_progression_label")
    click until "Stage2 progress 12."
    run Rollback(force=True, checkpoints=10, greedy=False)
    click until "Stage2 progress 2."
    assert playback_state.scene_id == "stage2-progression-12"
    assert playback_state.step_index == 1
    click until "Stage2 progression complete."
    run Quit(confirm=False)


testcase stage2_rollback_across_scene_boundary:
    $ _test.timeout = 20.0
    run Start("stage2_boundary_label")
    click until "Stage2 boundary B."
    assert playback_state.scene_id == "stage2-boundary-b"

    run Rollback(force=True, checkpoints=1, greedy=False)
    click until "Stage2 boundary A."
    assert playback_state.scene_id == "stage2-boundary-a"
    click until "Stage2 boundary complete."
    run Quit(confirm=False)


testcase stage2_return_explicit_completed:
    run Start("stage2_return_label")
    click until "Stage2 return complete."

    assert stage2_result_state(stage2_result).phase == "completed"
    assert playback_state.step_index == 2
    assert stage0_probe_count("stage2_return_before") == 1
    assert stage0_probe_count("stage2_return_after") == 0
    run Quit(confirm=False)


testcase stage2_natural_end_completed:
    run Start("stage2_natural_end_label")
    click until "Stage2 natural end complete."

    assert stage2_result_state(stage2_result).phase == "completed"
    assert playback_state.step_index == 1
    assert stage0_probe_count("stage2_natural_end") == 1
    run Quit(confirm=False)


testcase stage2_jump_returns_control_and_dispatches:
    $ stage0_prepare_test("stage2_jump_guard")
    $ stage2_install_jump_guard()
    $ guarded_state = prepare_json_scene_file("test_fixtures/stage2_jump.json", expected_scene_id="stage2-jump").started()
    $ guarded_control = execute_current_playback_action(guarded_state)
    $ guarded_result = PlaybackResult(guarded_state, guarded_control)
    $ stage2_restore_jump_guard()

    assert stage2_control_field(stage2_result_control(guarded_result), "kind") == "goto"
    assert stage2_control_field(stage2_result_control(guarded_result), "target") == "stage2_jump_control_target"
    assert stage2_result_state(guarded_result).step_index == 0

    run Start("stage2_jump_dispatch_label")
    click until "Stage2 jump control target reached."
    assert stage0_marked("stage2_jump_target")
    assert not stage0_marked("stage2_jump_fell_through")
    assert playback_state.phase == "completed"
    assert playback_state.step_index == 1
    assert playback_state.branch_trace == [{
        "kind": "goto",
        "step_index": 0,
        "target": "stage2_jump_control_target",
    }]
    run Quit(confirm=False)


testcase stage2_handler_exception_preserves_cursor:
    $ stage0_prepare_test("stage2_handler_exception")
    $ stage2_install_throwing_handler("transition")
    run Start("stage2_handler_error_label")
    click until "Stage2 handler error complete."

    $ handler_state = stage2_result_state(stage2_handler_result)
    assert handler_state.phase == "error"
    assert stage1_error_field(handler_state.last_error, "code") == "handler_exception"
    assert stage1_error_field(handler_state.last_error, "path") == "dialogue[1]"
    assert handler_state.step_index == 1
    assert stage0_probe_count("stage2_handler_after_error") == 0
    run Quit(confirm=False)


testcase stage2_pause_hard_checkpoint:
    $ _test.timeout = 20.0
    run Start("stage2_pause_checkpoint_label")
    click until "Stage2 pause after."
    assert playback_state.step_index == 2
    assert stage0_probe_count("stage2_pause_before") == 1
    assert stage0_probe_count("stage2_pause_after") == 1
    assert stage0_state()["stage2_pause_calls"] == 1
    assert stage0_state()["stage2_pause_cursors"] == [1]

    run Rollback(force=True, checkpoints=1, greedy=False)
    click until "Stage2 pause sentinel."
    assert playback_state.step_index == 3
    assert stage0_probe_count("stage2_pause_before") == 1
    assert stage0_probe_count("stage2_pause_after") == 2
    assert stage0_probe_count("stage2_pause_sentinel") == 1
    assert stage0_state()["stage2_pause_calls"] == 2
    assert stage0_state()["stage2_pause_cursors"] == [1, 1]

    click until "Stage2 pause checkpoint complete."
    assert stage2_result_state(stage2_pause_result).phase == "completed"
    assert playback_state.step_index == 5
    assert stage0_marked("stage2_pause_checkpoint_complete")
    run Quit(confirm=False)


# Stage 3 RED: supported callback surfaces must replace private
# _history_list mutation and expose save-slot metadata.
testcase stage3_history_annotations:
    run Start("stage3_history_annotations_label")
    click until "Stage3 history annotations complete."

    $ first = stage3_history_entry("Stage3 history one.")
    $ second = stage3_history_entry("Stage3 history two.")
    $ third = stage3_history_entry("Stage3 history three.")
    assert len(stage3_history_entries_with_text("Stage3 history one.")) == 1
    assert len(stage3_history_entries_with_text("Stage3 history two.")) == 1
    assert len(stage3_history_entries_with_text("Stage3 history three.")) == 1
    assert (first.who, first.what) == ("Lira", "Stage3 history one.")
    assert (second.who, second.what) == ("Kael", "Stage3 history two.")
    assert (third.who, third.what) == ("Lira", "Stage3 history three.")
    assert (first.scene_id, first.step_index, first.speaker_id) == ("stage3-history", 1, "lira")
    assert (second.scene_id, second.step_index, second.speaker_id) == ("stage3-history", 2, "kael")
    assert (third.scene_id, third.step_index, third.speaker_id) == ("stage3-history", 3, "lira")
    run Quit(confirm=False)


testcase stage3_history_save_load_no_earlier_duplicates:
    $ _test.timeout = 20.0
    run Start("stage3_history_save_load_label")
    click until "Stage3 history two."
    pause 0.1
    assert playback_state.phase == "playing"
    assert playback_state.step_index == 2
    run FileSave(STAGE3_HISTORY_SAVE_SLOT, confirm=False, slot=True)

    click until "Stage3 history save/load complete."
    run FileLoad(STAGE3_HISTORY_SAVE_SLOT, confirm=False, slot=True)
    click until "Stage3 history save/load complete."

    $ first_entries = stage3_history_entries_with_text("Stage3 history one.")
    $ second_entries = stage3_history_entries_with_text("Stage3 history two.")
    $ third_entries = stage3_history_entries_with_text("Stage3 history three.")
    assert len(first_entries) == 1
    assert len(second_entries) == 1
    assert len(third_entries) == 1
    assert (first_entries[0].scene_id, first_entries[0].step_index, first_entries[0].speaker_id) == ("stage3-history", 1, "lira")
    assert (second_entries[0].scene_id, second_entries[0].step_index, second_entries[0].speaker_id) == ("stage3-history", 2, "kael")
    assert (third_entries[0].scene_id, third_entries[0].step_index, third_entries[0].speaker_id) == ("stage3-history", 3, "lira")
    $ stage3_delete_save(STAGE3_HISTORY_SAVE_SLOT)
    run Quit(confirm=False)


testcase stage3_save_slot_json_metadata:
    run Start("stage3_save_json_label")
    click until "Stage3 save JSON point."
    assert playback_state.phase == "playing"
    assert playback_state.step_index == 1
    run FileSave(STAGE3_JSON_SAVE_SLOT, confirm=False, slot=True)

    $ slot_json = stage3_slot_json(STAGE3_JSON_SAVE_SLOT)
    $ metadata = slot_json["ai_novel"]
    assert metadata == {
        "scene_id": "stage3-history",
        "step_index": 1,
        "schema_version": 1,
        "state_version": 2,
        "content_hash": playback_state.content_hash,
        "phase": "playing",
    }
    $ stage3_delete_save(STAGE3_JSON_SAVE_SLOT)
    run Quit(confirm=False)


testcase stage3_save_slot_json_omits_untrusted_state:
    run Start("stage3_empty_save_json_label")
    click until "Stage3 empty save JSON point."
    run FileSave(STAGE3_EMPTY_SAVE_SLOT, confirm=False, slot=True)

    $ slot_json = stage3_slot_json(STAGE3_EMPTY_SAVE_SLOT)
    assert "ai_novel" not in slot_json
    $ stage3_delete_save(STAGE3_EMPTY_SAVE_SLOT)
    run Quit(confirm=False)


testcase stage3_after_load_rejects_invalid_state:
    assert ai_novel_after_load in config.after_load_callbacks
    $ stage0_prepare_test("stage3_invalid_after_load")
    $ invalid_loaded_state = stage3_invalid_state_for_save()
    $ guarded_control = execute_current_playback_action(invalid_loaded_state)
    assert guarded_control.kind == "error"
    assert stage1_error_field(guarded_control.error, "code") == "state_integrity_error"
    assert stage1_error_field(guarded_control.error, "path") == "state_version"
    $ playback_state = invalid_loaded_state
    $ ai_novel_after_load()
    $ stage1_assert_error(playback_state, "state_integrity_error", "state_version")
    assert stage0_probe_count("stage3_history_one") == 0
    assert not stage0_marked("stage3_invalid_after_load_resumed")
    run Quit(confirm=False)


testcase stage3_fileload_rejects_invalid_state:
    $ _test.timeout = 20.0
    run Start("stage3_invalid_fileload_label")
    click until "Stage3 invalid save ready to load."
    assert renpy.can_load(STAGE3_INVALID_SAVE_SLOT)
    $ stage0_state()["markers"].pop("stage3_invalid_after_load_resumed", None)
    $ playback_state = None
    run FileLoad(STAGE3_INVALID_SAVE_SLOT, confirm=False, slot=True)
    click until "This save contains an incompatible dynamic-scene state. Playback was stopped safely."
    click

    $ stage1_assert_error(playback_state, "state_integrity_error", "state_version")
    assert not stage0_marked("stage3_invalid_after_load_resumed")
    assert main_menu
    $ stage3_delete_save(STAGE3_INVALID_SAVE_SLOT)
    run Quit(confirm=False)


testcase stage3_history_rollback_identifier:
    $ _test.timeout = 20.0
    run Start("stage3_history_rollback_identifier_label")
    click until "Stage3 history three."

    $ second = stage3_history_entry("Stage3 history two.")
    assert second.rollback_identifier is not None
    assert RollbackToIdentifier(second.rollback_identifier).get_sensitive()
    $ stage3_rollback_identifier = second.rollback_identifier
    run RollbackToIdentifier(stage3_rollback_identifier)
    click until "Stage3 history two."
    $ replayed_second = stage3_history_entry("Stage3 history two.")
    assert (replayed_second.scene_id, replayed_second.step_index, replayed_second.speaker_id) == ("stage3-history", 2, "kael")
    run Quit(confirm=False)


testcase stage3_history_screen_rolls_back_to_entry:
    $ _test.timeout = 20.0
    run Start("stage3_history_rollback_identifier_label")
    click until "Stage3 history three."
    run ShowMenu("history")
    "Stage3 history two."
    click until "Stage3 history two."

    assert playback_state.phase == "playing"
    assert playback_state.step_index == 2
    $ ui_replayed_second = stage3_history_entry("Stage3 history two.")
    assert (ui_replayed_second.scene_id, ui_replayed_second.step_index, ui_replayed_second.speaker_id) == ("stage3-history", 2, "kael")
    run Quit(confirm=False)


testcase stage3_line_middleware_exception_is_visible:
    run Start("stage3_line_middleware_error_label")
    click until "Stage3 line middleware error complete."

    $ middleware_state = stage2_result_state(stage3_line_middleware_result)
    assert middleware_state.phase == "error"
    assert stage1_error_field(middleware_state.last_error, "code") == "handler_exception"
    assert stage1_error_field(middleware_state.last_error, "path") == "dialogue[1]"
    assert middleware_state.step_index == 1
    assert stage0_probe_count("stage3_history_one") == 1
    assert len(stage3_history_entries_with_text("Stage3 history one.")) == 0
    run Quit(confirm=False)


testcase stage3_post_line_middleware_exception_is_visible:
    run Start("stage3_post_line_middleware_error_label")
    click until "Stage3 post line middleware error complete."

    $ post_state = stage2_result_state(stage3_post_line_middleware_result)
    assert post_state.phase == "error"
    assert stage1_error_field(post_state.last_error, "code") == "handler_exception"
    assert stage1_error_field(post_state.last_error, "path") == "dialogue[1]"
    assert post_state.step_index == 1
    assert stage0_probe_count("stage3_history_one") == 1
    $ post_entry = stage3_history_entry("Stage3 history one.")
    assert (post_entry.scene_id, post_entry.step_index, post_entry.speaker_id) == ("stage3-history", 1, "lira")
    run Quit(confirm=False)


testcase stage3_untrusted_text_is_literal:
    run Start("stage3_untrusted_text_label")
    click until "Stage3 untrusted text complete."

    assert stage2_result_state(stage3_untrusted_text_result).phase == "completed"
    assert stage0_probe_count("stage3_untrusted_text") == 1
    $ unsafe_entry = stage3_history_entry("stage3_missing_secret")
    assert "[[" not in unsafe_entry.what
    assert "[stage3_missing_secret]" in unsafe_entry.what
    assert "{{a=jump:start}" in unsafe_entry.what
    run Quit(confirm=False)


testcase stage3_unapproved_jump_rejected:
    $ rejected_jump = prepare_playback("test_fixtures/stage3_unapproved_jump.json", expected_scene_id="stage3-unapproved-jump")
    $ stage1_assert_error(rejected_jump, "contract_violation", "dialogue[0].target")
    run Quit(confirm=False)


testcase stage3_consumption_is_idempotent_ack:
    $ stage0_prepare_test("stage3_consumption_ack")
    $ stage3_assert_consume_ack_idempotent()
    run Quit(confirm=False)


# Stage 4 RED: provider boundary, bounded failures, explicit recovery actions,
# retry without replay, and stable-boundary-only autosave.
testcase stage4_scene_provider_contract:
    $ stage4_assert_provider_contract()
    run Quit(confirm=False)


testcase stage4_task_errors_are_visible:
    $ stage4_assert_terminal_task_visible()
    run Quit(confirm=False)


testcase stage4_poll_work_is_bounded:
    $ stage4_assert_poll_work_is_bounded()
    run Quit(confirm=False)


testcase stage4_offline_timeout_is_bounded:
    $ _test.timeout = 7.0
    run Start("start")
    pause 3.0
    assert renpy.get_screen("scene_provider_error") is not None
    "Main Menu"
    pause 0.3
    assert main_menu
    assert stage4_error_field(scene_client_error, "code") == "provider_offline"
    assert stage4_error_field(scene_client_error, "operation") == "poll"
    assert main_menu
    run Quit(confirm=False)


testcase stage4_structured_error_main_menu:
    $ _test.timeout = 10.0
    run Start("stage4_provider_main_menu_start")
    pause 0.5
    assert renpy.get_screen("scene_provider_error") is not None
    "Main Menu"
    pause 0.3
    assert main_menu
    assert stage4_error_field(scene_client_error, "code") == "provider_offline"
    assert stage4_error_field(scene_client_error, "operation") == "poll"
    assert stage4_error_field(scene_client_error, "retryable") is True
    assert scene_session.pending_operation == "poll"
    assert main_menu
    run Quit(confirm=False)


testcase stage4_retry_ack_without_replay_and_boundary_autosave:
    $ _test.timeout = 15.0
    run Start("stage4_provider_retry_start")
    click until "Stage4 provider scene line."
    click until "Retry"
    click until "Stage4 provider retry complete."

    assert stage0_probe_count("stage4_provider_line") == 1
    assert stage4_retry_fake.ack_calls == 2
    assert stage4_retry_events.count("autosave") == 1
    assert stage4_retry_events.index("ack:success") < stage4_retry_events.index("autosave")
    assert stage0_history_count("Запуск. Формирую очередь сцен...") == 0
    assert stage0_history_count("Проигрываю сцену") == 0
    assert len(stage4_retry_autosaves) == 1
    assert stage4_retry_autosaves[0]["ack_succeeded"] is True
    assert stage4_retry_autosaves[0]["active_ref"] is None
    assert stage4_retry_autosaves[0]["boundary_serial"] == 1
    run Quit(confirm=False)


testcase stage4_retry_playback_from_current_action:
    $ _test.timeout = 15.0
    run Start("stage4_playback_retry_start")
    click until "Stage4 provider scene line."
    click until "Retry"
    click until "Stage4 provider retry complete."
    assert stage0_probe_count("stage4_provider_line") == 1
    assert stage0_state()["stage4_playback_handler_calls"] == 2
    assert stage4_retry_fake.prepare_count == 1
    assert stage4_retry_fake.ack_calls == 1
    run Quit(confirm=False)


testcase stage4_real_autosave_restores_boundary:
    $ _test.timeout = 15.0
    run Start("stage4_real_autosave_start")
    click until "Stage4 boundary autosave ready."
    click until "Stage4 boundary state mutated."
    click until "Stage4 boundary autosave restored."
    $ stage4_restored = stage0_state()["stage4_restored_boundary"]
    assert stage4_restored["phase"] == "boundary"
    assert stage4_restored["active_ref"] is None
    assert stage4_restored["boundary_serial"] == 1
    assert stage4_restored["scene_id"] == "stage4-provider-retry"
    assert stage4_restored["playback_phase"] == "completed"
    assert stage4_restored["step_index"] == 2
    run Quit(confirm=False)


testcase stage4_fileload_rejects_invalid_session:
    $ _test.timeout = 15.0
    run Start("stage4_invalid_session_fileload_start")
    click until "Stage4 invalid session save setup."
    click until "Stage4 invalid session ready to load."
    click until "Main Menu"
    assert scene_client_error.code == "session_integrity_error"
    assert scene_client_error.retryable is False
    assert main_menu
    $ renpy.unlink_save(STAGE4_INVALID_SESSION_SLOT)
    run Quit(confirm=False)
