init python:
    _UI_TEST_OMITTED = object()

    def ui_contract_test_bytes(scene_id, ui=_UI_TEST_OMITTED, legacy=False):
        if legacy:
            scene = {
                "id": scene_id,
                "characters": {},
                "dialogue": [],
            }
        else:
            scene = {
                "schema_version": 1,
                "scene_id": scene_id,
                "characters": {},
                "dialogue": [],
            }
        if ui is not _UI_TEST_OMITTED:
            scene["ui"] = ui
        return json.dumps(scene, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


testcase ui_contract_optional_unknown_and_hash:
    $ absent = prepare_playback_bytes(ui_contract_test_bytes("ui-absent"))
    $ selected = prepare_playback_bytes(ui_contract_test_bytes("ui-selected", {"theme_id": "literary", "palette_id": "warm_parchment", "font_pack_id": "editorial-serif-2"}))
    $ future = prepare_playback_bytes(ui_contract_test_bytes("ui-future", {"theme_id": "future_theme_99"}))
    $ selected_without_ui = prepare_playback_bytes(ui_contract_test_bytes("ui-selected"))

    assert absent.phase == "ready"
    assert "ui" not in stage1_snapshot(absent)
    assert selected.phase == "ready"
    assert stage1_snapshot(selected)["ui"] == {"theme_id": "literary", "palette_id": "warm_parchment", "font_pack_id": "editorial-serif-2"}
    assert future.phase == "ready"
    assert stage1_snapshot(future)["ui"]["theme_id"] == "future_theme_99"
    assert selected.content_hash != selected_without_ui.content_hash
    assert selected.content_hash == compute_scene_hash(stage1_snapshot(selected))
    run Quit(confirm=False)


testcase ui_contract_malformed_rejected:
    python:
        malformed_values = [
            None,
            [],
            {"theme_id": ""},
            {"theme_id": "Literary"},
            {"theme_id": "../literary"},
            {"theme_id": "a" * 65},
            {"palette_id": 42},
            {"font_pack_id": float("nan")},
            {"theme_id": "literary", "future": "field"},
            {"theme_id": {"nested": "literary"}},
        ]
        for ui_value in malformed_values:
            malformed = prepare_playback_bytes(ui_contract_test_bytes("ui-invalid", ui_value))
            assert malformed.phase == "error"
            assert stage1_error_field(malformed.last_error, "code") in ("contract_violation", "invalid_json")
    run Quit(confirm=False)


testcase ui_contract_legacy_migration:
    $ legacy_absent = prepare_playback_bytes(ui_contract_test_bytes("ui-legacy-absent", legacy=True))
    $ legacy_selected = prepare_playback_bytes(ui_contract_test_bytes("ui-legacy-selected", {"theme_id": "romantic"}, legacy=True))

    assert legacy_absent.phase == "ready"
    assert legacy_absent.migrated_from_schema == 0
    assert "ui" not in stage1_snapshot(legacy_absent)
    assert legacy_selected.phase == "ready"
    assert legacy_selected.migrated_from_schema == 0
    assert stage1_snapshot(legacy_selected)["ui"] == {"theme_id": "romantic"}
    run Quit(confirm=False)
