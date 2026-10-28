testcase demo_story_metadata_first:
    $ story_metadata = None
    $ playback_state = None
    $ scene_session = SceneSessionState(provider_kind="demo_story")
    $ scene_client_start()
    $ metadata_poll = scene_client_poll()

    assert metadata_poll.kind == "waiting"
    assert playback_state is None
    assert story_metadata["story_id"] == "demo_after_bell"
    assert story_metadata["title"] == "После звонка"
    assert len(story_metadata["cast"]) == 2
    assert scene_session.provider_cursor == 1

    $ first_scene_poll = scene_client_poll()
    assert first_scene_poll.kind == "ready"
    assert playback_state.scene_id == "demo_after_bell_01"
    assert scene_session.provider_cursor == 1
    run Quit(confirm=False)


testcase demo_story_provider_does_not_leak_to_new_story:
    $ scene_session = SceneSessionState(provider_kind="demo_story")
    $ scene_client_start()
    assert scene_session.provider_kind == "demo_story"
    $ scene_client_start_production()
    assert scene_session.provider_kind == "mongo_file"
    assert story_metadata is None
    run Quit(confirm=False)


testcase demo_story_resources_and_contract:
    $ metadata = load_story_metadata_file("demo_story/story_metadata.json")
    assert metadata["story_id"] == "demo_after_bell"
    assert [member["character_id"] for member in metadata["cast"]] == ["akari", "ren"]

    python:
        expected = (
            ("demo_story/scene_01_corridor.json", "demo_after_bell_01"),
            ("demo_story/scene_02_rooftop.json", "demo_after_bell_02"),
            ("demo_story/scene_03_promise.json", "demo_after_bell_03"),
        )
        prepared_demo_scenes = []
        for relative_path, scene_id in expected:
            state = prepare_json_scene_file(relative_path, expected_scene_id=scene_id)
            assert state.phase == "ready", getattr(state.last_error, "message", "scene invalid")
            prepared_demo_scenes.append(state)
        assert all(state.snapshot["ui"]["theme_id"] == "literary" for state in prepared_demo_scenes)
        for state in prepared_demo_scenes:
            for action in state.snapshot["dialogue"]:
                if action["type"] != "show":
                    continue
                if action["target"].startswith("akari "):
                    assert action["transform"]["slot"] == "left"
                    assert not action["transform"].get("flip", False)
                elif action["target"].startswith("ren "):
                    assert action["transform"]["slot"] == "right"
                    assert action["transform"]["flip"] is True
    run Quit(confirm=False)


testcase demo_story_three_scene_flow:
    $ _test.timeout = 35.0
    $ _history = True
    $ _history_list[:] = []
    run Start("demo_story")
    click until "Договорились."

    assert playback_state.scene_id == "demo_after_bell_03"
    assert story_metadata["title"] == "После звонка"
    assert scene_session.provider_cursor == 3
    assert any(getattr(entry, "scene_id", None) == "demo_after_bell_01" for entry in _history_list)
    assert any(getattr(entry, "scene_id", None) == "demo_after_bell_02" for entry in _history_list)
    assert any(getattr(entry, "scene_id", None) == "demo_after_bell_03" for entry in _history_list)
    assert renpy.screenshot(stage0_artifact_path("demo-story-final-line.png"))

    click
    pause 0.8
    assert scene_session.phase == "waiting"
    assert scene_session.provider_cursor == 4
    assert scene_session.boundary_serial == 3
    run Quit(confirm=False)


testcase demo_story_save_load_resume:
    $ _test.timeout = 40.0
    $ _history = True
    $ _history_list[:] = []
    $ demo_save_slot = "demo-story-mid-scene"
    $ stage3_delete_save(demo_save_slot)
    run Start("demo_story")
    click until "Не трогай."

    assert playback_state.scene_id == "demo_after_bell_02"
    assert scene_session.provider_cursor == 2
    run FileSave(demo_save_slot, confirm=False, slot=True)

    click until "Договорились."
    run FileLoad(demo_save_slot, confirm=False, slot=True)
    click until "Договорились."

    assert story_metadata["story_id"] == "demo_after_bell"
    assert playback_state.scene_id == "demo_after_bell_03"
    assert scene_session.provider_kind == "demo_story"
    assert scene_session.provider_cursor == 3
    assert sum("Рэн! Ты тоже слышал" in (entry.what or "") for entry in _history_list) == 1
    assert sum("Не трогай. Корпус тёплый" in (entry.what or "") for entry in _history_list) == 1
    $ stage3_delete_save(demo_save_slot)
    run Quit(confirm=False)


testcase demo_story_first_scene_visual:
    $ _test.timeout = 20.0
    run Start("demo_story")
    click until "Рэн! Ты тоже слышал"
    assert playback_state.scene_id == "demo_after_bell_01"
    assert story_metadata["title"] == "После звонка"
    assert renpy.screenshot(stage0_artifact_path("demo-story-corridor.png"))
    run Quit(confirm=False)


testcase demo_story_second_scene_visual:
    $ _test.timeout = 30.0
    run Start("demo_story")
    click until "Он снова передал три импульса."
    assert playback_state.scene_id == "demo_after_bell_02"
    assert scene_session.provider_cursor == 2
    assert renpy.screenshot(stage0_artifact_path("demo-story-rooftop.png"))
    run Quit(confirm=False)


testcase demo_story_third_scene_visual:
    $ _test.timeout = 30.0
    run Start("demo_story")
    click until "Договорились."
    assert playback_state.scene_id == "demo_after_bell_03"
    assert scene_session.provider_cursor == 3
    assert renpy.screenshot(stage0_artifact_path("demo-story-promise.png"))
    run Quit(confirm=False)


testcase demo_story_history_visual:
    $ _test.timeout = 30.0
    run Start("demo_story")
    click until "Он снова передал три импульса."
    run config.game_menu_action
    pause 0.6
    assert renpy.get_screen("pause_menu") is not None
    assert any(getattr(entry, "scene_id", None) == "demo_after_bell_01" for entry in _history_list)
    assert any(getattr(entry, "scene_id", None) == "demo_after_bell_02" for entry in _history_list)
    assert renpy.screenshot(stage0_artifact_path("demo-story-history.png"))
    run Return()
    run Quit(confirm=False)
