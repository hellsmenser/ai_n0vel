init python:
    gui_task_payloads = []
    gui_task_counter = 0

    def gui_capture_create_task(task_type, payload=None, idempotency_key=None):
        global gui_task_counter
        gui_task_counter += 1
        gui_task_payloads.append((task_type, copy.deepcopy(payload), idempotency_key))
        return "gui-task-{}".format(gui_task_counter)

    def gui_capture_check_status(task_id):
        return "new", None


label gui_no_system_history_jump_start:
    $ stage0_prepare_test("gui_no_system_history_jump")
    $ stage4_install_provider_fake("poll_error")
    jump next_scene


testcase gui_main_menu_visual:
    assert renpy.loadable(gui.main_menu_background)
    assert renpy.get_screen("main_menu") is not None
    pause 0.6
    assert renpy.screenshot(stage0_artifact_path("gui-main-menu.png"))
    run Quit(confirm=False)


testcase gui_story_builder_basic_visual:
    $ story_draft_reset("basic")
    $ story_draft_toggle_genre("adventure")
    $ story_draft_set("wishes", "A journey through a city that remembers every visitor.")
    run ShowMenu("story_builder")
    pause 0.6
    assert renpy.get_screen("story_builder") is not None
    assert renpy.get_displayable("story_builder", "story_builder_root") is not None
    assert renpy.screenshot(stage0_artifact_path("gui-story-builder-basic.png"))
    run Quit(confirm=False)


testcase gui_story_builder_advanced_visual:
    $ story_draft_reset("advanced")
    $ story_draft_toggle_genre("mystery")
    $ story_draft_set("wishes", "A character-driven mystery with no predetermined ending.")
    $ story_draft_set("tone", "melancholic")
    $ story_draft_set("length", "medium")
    $ story_draft_set("pacing", "measured")
    $ story_draft_toggle_cast("lira")
    $ story_draft_set_ui("literary", "", "")
    run ShowMenu("story_builder")
    pause 0.6
    assert renpy.get_screen("story_builder") is not None
    assert renpy.screenshot(stage0_artifact_path("gui-story-builder-advanced.png"))
    run Quit(confirm=False)


testcase gui_asset_library_visual:
    $ asset_catalog_reset_preferences()
    run ShowMenu("asset_library")
    pause 0.6
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_displayable("asset_library", "asset_library_root") is not None
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == asset_catalog_entries("characters", include_hidden=False)[0]["id"]
    assert renpy.get_displayable("asset_library", "asset_constructor_composite") is not None
    assert renpy.get_displayable("asset_library", "asset_outfit_section_title") is not None
    python:
        with renpy.open_file("product_gui.rpy", encoding=False) as product_gui_source_file:
            product_gui_source = product_gui_source_file.read().decode("utf-8")
        assert 'default selected_asset_id = "lira"' not in product_gui_source
        assert "add asset_catalog_constructor_composite(selected_asset_id)" not in product_gui_source
        assert 'idle_background (theme_compact_button_hover("default", neutral_shell=True) if asset["id"] == selected_asset_id' not in product_gui_source
        assert 'add Solid(theme_color("accent", theme_id="default", neutral_shell=True))' in product_gui_source
    assert renpy.screenshot(stage0_artifact_path("gui-asset-library.png"))
    assert renpy.get_displayable("asset_library", "asset_card_ren") is not None
    $ renpy.run(renpy.get_displayable("asset_library", "asset_card_ren").action)
    pause 0.2
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == "ren"
    assert asset_catalog_constructor("ren") is not None
    assert renpy.get_displayable("asset_library", "asset_constructor_composite") is not None
    assert renpy.get_displayable("asset_library", "asset_outfit_section_title") is not None
    assert renpy.get_displayable("asset_library", "asset_component_outfit_school") is not None
    assert renpy.get_displayable("asset_library", "asset_component_pose_neutral") is not None
    assert renpy.get_displayable("asset_library", "asset_component_pose_open") is not None
    assert renpy.get_displayable("asset_library", "asset_component_pose_concerned") is not None
    assert renpy.get_displayable("asset_library", "asset_variant_constructed") is None
    $ asset_catalog_select_component("ren", "pose", "open")
    assert asset_catalog_selected_components("ren") == {"pose": "open", "outfit": "school"}
    pause 0.2
    assert renpy.screenshot(stage0_artifact_path("gui-asset-library-ren.png"))
    $ renpy.get_screen("asset_library").scope["description_buffer"] = "Рэн — участник демонстрационной истории."
    $ renpy.restart_interaction()
    pause 0.1
    assert renpy.get_displayable("asset_library", "asset_description_save") is not None
    run renpy.get_displayable("asset_library", "asset_description_save").action
    assert asset_catalog_description("ren") == "Рэн — участник демонстрационной истории."
    run renpy.get_displayable("asset_library", "asset_toggle").action
    assert asset_catalog_is_enabled("ren") is False
    run renpy.get_displayable("asset_library", "asset_toggle").action
    assert asset_catalog_is_enabled("ren") is True
    "Локации"
    pause 0.4
    assert renpy.get_screen("asset_library").scope["asset_category"] == "locations"
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == "forest"
    assert renpy.screenshot(stage0_artifact_path("gui-asset-library-locations.png"))
    $ asset_catalog_reset_preferences()
    run Quit(confirm=False)


testcase gui_asset_disable_click_keeps_library_open:
    $ asset_catalog_reset_preferences()
    $ visible_character_id = asset_catalog_entries("characters", include_hidden=False)[0]["id"]
    $ asset_catalog_toggle(visible_character_id) if not asset_catalog_is_enabled(visible_character_id) else None
    assert renpy.get_screen("main_menu") is not None
    "Библиотека ассетов"
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ action_result = renpy.run(renpy.get_displayable("asset_library", "asset_toggle").action)
    assert action_result is None
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == visible_character_id
    assert asset_catalog_is_enabled(visible_character_id) is False
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_asset_enable_click_keeps_library_open:
    $ asset_catalog_reset_preferences()
    $ visible_character_id = asset_catalog_entries("characters", include_hidden=False)[0]["id"]
    assert asset_catalog_is_enabled(visible_character_id) is False
    assert renpy.get_screen("main_menu") is not None
    "Библиотека ассетов"
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ action_result = renpy.run(renpy.get_displayable("asset_library", "asset_toggle").action)
    assert action_result is None
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == visible_character_id
    assert asset_catalog_is_enabled(visible_character_id) is True
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_asset_variant_click_keeps_library_open:
    $ asset_catalog_reset_preferences()
    assert renpy.get_screen("main_menu") is not None
    "Библиотека ассетов"
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ visible_character_id = renpy.get_screen("asset_library").scope["selected_asset_id"]
    $ visible_constructor = asset_catalog_constructor(visible_character_id)
    assert visible_constructor is not None and len(visible_constructor["poses"]) > 1
    $ target_pose_id = visible_constructor["poses"][1]["id"]
    $ target_pose_title = visible_constructor["poses"][1]["title"]
    $ pose_focus = renpy.test.testfocus.find_focus(target_pose_title)
    assert pose_focus is not None and pose_focus.widget.action is not None
    $ action_result = renpy.run(pose_focus.widget.action)
    assert action_result is None
    assert asset_catalog_selected_components(visible_character_id)["pose"] == target_pose_id
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_asset_reset_click_keeps_library_open:
    $ asset_catalog_reset_preferences()
    $ visible_character_id = asset_catalog_entries("characters", include_hidden=False)[0]["id"]
    $ asset_catalog_set_description(visible_character_id, "Temporary override")
    assert renpy.get_screen("main_menu") is not None
    "Библиотека ассетов"
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ reset_button = renpy.get_displayable("asset_library", "asset_description_reset")
    assert reset_button is not None and reset_button.action is not None
    $ action_result = renpy.run(reset_button.action)
    assert action_result is None
    assert asset_catalog_description(visible_character_id) == asset_catalog_get(visible_character_id)["description"]
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_asset_save_click_keeps_library_open:
    $ asset_catalog_reset_preferences()
    assert renpy.get_screen("main_menu") is not None
    "Библиотека ассетов"
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ action_result = renpy.run(renpy.get_displayable("asset_library", "asset_description_save").action)
    assert action_result is None
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_asset_constructor_clicks_keep_library_open:
    $ asset_catalog_reset_preferences()
    run ShowMenu("asset_library")
    pause 0.3
    assert renpy.get_screen("asset_library") is not None
    $ akari_card = renpy.get_displayable("asset_library", "asset_card_akari")
    assert akari_card is not None
    $ card_result = renpy.run(akari_card.action)
    assert card_result is None
    pause 0.1
    assert renpy.get_screen("asset_library").scope["selected_asset_id"] == "akari"
    assert renpy.get_displayable("asset_library", "asset_constructor_composite") is not None
    $ akari_constructor = asset_catalog_constructor("akari")
    $ current_outfit_id = akari_constructor["outfits"][0]["id"]
    assert renpy.get_displayable("asset_library", "asset_outfit_section_title") is not None
    python:
        assert len(akari_constructor["poses"]) == 7
        for outfit in akari_constructor["outfits"]:
            assert renpy.get_displayable("asset_library", "asset_component_outfit_" + outfit["id"]) is not None
        for pose in akari_constructor["poses"]:
            assert renpy.get_displayable("asset_library", "asset_component_pose_" + pose["id"]) is not None
    $ initial_composite_path = stage0_artifact_path("gui-asset-library-akari-neutral.png")
    assert renpy.screenshot(initial_composite_path)
    $ pose_focus = renpy.test.testfocus.find_focus("Решительная")
    assert pose_focus is not None and pose_focus.widget.action is not None
    $ pose_result = renpy.run(pose_focus.widget.action)
    pause 0.1
    assert renpy.get_displayable("asset_library", "asset_outfit_section_title") is not None
    $ school_focus = renpy.test.testfocus.find_focus("Академия")
    assert school_focus is not None and school_focus.widget.action is not None
    $ outfit_result = renpy.run(school_focus.widget.action)
    pause 0.1
    assert pose_result is None
    assert outfit_result is None
    assert asset_catalog_selected_components("akari") == {"pose": "determined", "outfit": "school"}
    assert renpy.get_screen("asset_library") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    pause 0.3
    $ selected_composite_path = stage0_artifact_path("gui-asset-library-akari-constructor.png")
    assert renpy.screenshot(selected_composite_path)
    python:
        import hashlib
        with open(initial_composite_path, "rb") as initial_file:
            initial_composite_hash = hashlib.sha256(initial_file.read()).hexdigest()
        with open(selected_composite_path, "rb") as selected_file:
            selected_composite_hash = hashlib.sha256(selected_file.read()).hexdigest()
    assert initial_composite_hash != selected_composite_hash
    run Quit(confirm=False)


testcase gui_story_mode_click_keeps_builder_open:
    $ story_draft_reset("basic")
    assert renpy.get_screen("main_menu") is not None
    "Новая история"
    pause 0.3
    assert renpy.get_screen("story_builder") is not None
    $ mode_focus = renpy.test.testfocus.find_focus("Продвинутый")
    assert mode_focus is not None
    assert mode_focus.widget.action is not None
    $ action_result = renpy.run(mode_focus.widget.action)
    assert action_result is None
    assert story_draft_get()["mode"] == "advanced"
    assert renpy.get_screen("story_builder") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_story_genre_click_keeps_builder_open:
    $ story_draft_reset("basic")
    assert renpy.get_screen("main_menu") is not None
    "Новая история"
    pause 0.3
    assert renpy.get_screen("story_builder") is not None
    $ genre_focus = renpy.test.testfocus.find_focus("Приключения")
    assert genre_focus is not None
    assert genre_focus.widget.action is not None
    $ action_result = renpy.run(genre_focus.widget.action)
    assert action_result is None
    assert "adventure" in story_draft_get()["genres"]
    assert renpy.get_screen("story_builder") is not None
    assert renpy.get_screen("scene_provider_error") is None
    assert story_launch_payload is None
    run Quit(confirm=False)


testcase gui_story_create_starts_gracefully:
    $ story_draft_reset("basic")
    $ story_draft_toggle_genre("adventure")
    $ story_draft_set("wishes", "A provider-bound story request.")
    $ stage4_install_provider_fake("poll_error")
    run ProductGuiStartStory()
    pause 0.8
    assert story_launch_payload["story_request"]["genres"] == ["adventure"]
    assert renpy.get_screen("scene_provider_error") is not None
    "Main Menu"
    pause 0.2
    $ stage4_restore_provider_fake()
    assert renpy.get_screen("main_menu") is not None
    run Quit(confirm=False)


testcase gui_story_create_rejects_invalid_draft:
    $ story_draft_reset("basic")
    $ story_launch_payload = None
    assert renpy.get_screen("main_menu") is not None
    "Новая история"
    pause 0.3
    assert renpy.get_screen("story_builder") is not None
    $ action_result = renpy.run(ProductGuiStartStory())
    assert action_result is None
    assert story_launch_payload is None
    assert renpy.get_screen("story_builder") is not None
    assert renpy.get_screen("scene_provider_error") is None
    run Quit(confirm=False)


testcase gui_story_multifield_focus_survives_restart:
    $ story_draft_reset("advanced")
    $ wishes_before_focus_test = story_draft_get()["wishes"]
    assert renpy.get_screen("main_menu") is not None
    "Новая история"
    pause 0.3
    $ title_editor = renpy.get_displayable("story_builder", "story_title_input")
    assert isinstance(title_editor, ProjectMultilineInput)
    $ title_render = renpy.render(title_editor, 480, 58, 0.0, 0.0)
    $ title_click = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})
    python:
        try:
            title_editor.event(title_click, 0, 0, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    pause 0.2
    $ title_editor = renpy.get_displayable("story_builder", "story_title_input")
    assert isinstance(title_editor.value, StoryDraftInputValue)
    assert title_editor.value.field == "title_seed"
    assert title_editor.editable
    $ title_text = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.TEXTINPUT, {"text": "Draft title"})
    python:
        try:
            title_editor.event(title_text, 0, 0, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    pause 0.2
    assert story_draft_get()["title_seed"] == "Draft title"
    assert story_draft_get()["wishes"] == wishes_before_focus_test
    $ setting_editor = renpy.get_displayable("story_builder", "story_setting_input")
    assert isinstance(setting_editor, ProjectMultilineInput)
    $ setting_render = renpy.render(setting_editor, 480, 58, 0.0, 0.0)
    $ setting_click = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})
    python:
        try:
            setting_editor.event(setting_click, 0, 0, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    pause 0.2
    $ setting_editor = renpy.get_displayable("story_builder", "story_setting_input")
    assert isinstance(setting_editor.value, StoryDraftInputValue)
    assert setting_editor.value.field == "setting"
    assert setting_editor.editable
    $ setting_text = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.TEXTINPUT, {"text": "Forest school"})
    python:
        try:
            setting_editor.event(setting_text, 0, 0, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    pause 0.2
    assert story_draft_get()["setting"] == "Forest school"
    assert story_draft_get()["title_seed"] == "Draft title"
    assert story_draft_get()["wishes"] == wishes_before_focus_test
    run Quit(confirm=False)


testcase gui_multiline_input_navigation_contract:
    $ editor = ProjectMultilineInput("test_editor", default="alpha beta gamma delta epsilon zeta eta theta", multiline=True, font=theme_font("body", theme_id="default", neutral_shell=True), size=28)
    $ editor_render = renpy.render(editor, 190, 160, 0.0, 0.0)
    $ editor_layout, editor_lines, editor_caret = editor._layout_geometry()
    assert editor_layout is not None
    assert len(editor_lines) >= 2
    assert editor_caret is not None
    $ editor_before_up = editor.caret_pos
    assert editor._move_vertical(-1)
    assert editor.caret_pos < editor_before_up
    $ editor_after_up = editor.caret_pos
    $ editor_render = renpy.render(editor, 190, 160, 0.0, 0.0)
    assert editor._move_vertical(1)
    assert editor.caret_pos > editor_after_up
    $ editor_render = renpy.render(editor, 190, 160, 0.0, 0.0)
    $ editor_layout, editor_lines, editor_caret = editor._layout_geometry()
    $ second_line = editor_lines[1][0]
    $ second_boundary = editor_lines[1][1][-1]
    $ editor_click_x = (second_boundary[0] + editor_layout.add_left) / editor_layout.oversample
    $ editor_click_y = (second_line.y + second_line.height / 2.0 + editor_layout.add_top) / editor_layout.oversample
    $ editor_click_target = editor._caret_from_point(editor_click_x, editor_click_y)
    assert editor_click_target == second_boundary[1]
    assert editor_click_target > 0
    $ editor_mouse_event = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (editor_click_x, editor_click_y)})
    python:
        try:
            editor.event(editor_mouse_event, editor_click_x, editor_click_y, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    assert editor.caret_pos == editor_click_target
    $ ligature_editor = ProjectMultilineInput("ligature_editor", default="office efficient", multiline=True, font=theme_font("body", theme_id="default", neutral_shell=True), size=28)
    $ ligature_render = renpy.render(ligature_editor, 520, 100, 0.0, 0.0)
    $ ligature_layout, ligature_lines, ligature_caret = ligature_editor._layout_geometry()
    assert ligature_lines[-1][1][-1][1] == len(ligature_editor.content)
    assert ligature_editor.style.shaper == "freetype"
    run Quit(confirm=False)


testcase gui_multiline_input_blank_line_contract:
    $ blank_editor_state = {"text": "alpha\n\nbeta"}
    $ blank_editor_value = DictInputValue(blank_editor_state, "text")
    $ blank_editor = ProjectMultilineInput("blank_line_editor", value=blank_editor_value, multiline=True, font=theme_font("body", theme_id="default", neutral_shell=True), size=28)
    $ blank_render = renpy.render(blank_editor, 360, 220, 0.0, 0.0)
    $ blank_layout, blank_lines, blank_caret = blank_editor._layout_geometry()
    assert len(blank_lines) == 3
    assert blank_lines[1][1]
    assert blank_lines[1][1][0][1] == 6
    $ blank_line = blank_lines[1][0]
    $ blank_boundary = blank_lines[1][1][0]
    $ blank_click_x = (blank_boundary[0] + blank_layout.add_left) / blank_layout.oversample
    $ blank_click_y = (blank_line.y + blank_line.height / 2.0 + blank_layout.add_top) / blank_layout.oversample
    assert blank_editor._caret_from_point(blank_click_x, blank_click_y) == 6
    $ blank_mouse_event = renpy.display.behavior.pygame.event.Event(renpy.display.behavior.pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (blank_click_x, blank_click_y)})
    python:
        try:
            blank_editor.event(blank_mouse_event, blank_click_x, blank_click_y, 0.0)
        except renpy.display.core.IgnoreEvent:
            pass
    assert blank_editor.caret_pos == 6
    assert blank_editor_state["text"] == "alpha\n\nbeta"
    $ blank_render = renpy.render(blank_editor, 360, 220, 0.0, 0.0)
    assert blank_editor._move_vertical(-1)
    assert blank_editor.caret_pos <= 5
    $ blank_render = renpy.render(blank_editor, 360, 220, 0.0, 0.0)
    assert blank_editor._move_vertical(1)
    assert blank_editor.caret_pos == 6
    $ blank_render = renpy.render(blank_editor, 360, 220, 0.0, 0.0)
    assert blank_editor._move_vertical(1)
    assert blank_editor.caret_pos >= 7
    run Quit(confirm=False)


testcase gui_navigation_flow:
    assert renpy.get_screen("main_menu") is not None
    "Новая история"
    pause 0.2
    assert renpy.get_screen("story_builder") is not None
    $ navigation_action_result = renpy.run(Function(product_gui_update, story_draft_set_mode, "advanced"))
    assert navigation_action_result is None
    assert story_draft_get()["mode"] == "advanced"
    run ShowMenu("main_menu")
    pause 0.2
    assert renpy.get_screen("main_menu") is not None
    run ShowMenu("asset_library")
    pause 0.2
    assert renpy.get_screen("asset_library") is not None
    assert [item["id"] for item in asset_catalog_entries("locations")] == ["forest", "tavern_interior", "academy_corridor_evening", "academy_rooftop_blue_hour"]
    run Quit(confirm=False)


testcase gui_story_payload_reaches_root_task:
    $ story_draft_reset("advanced")
    $ story_draft_toggle_genre("fantasy")
    $ story_draft_set("wishes", "A small root-task payload probe.")
    $ story_draft_set_ui("high_fantasy", "", "")
    assert story_builder_commit()
    $ original_create_task = renpy.store.create_task
    $ original_check_status = renpy.store.check_status
    $ gui_task_payloads[:] = []
    $ gui_task_counter = 0
    $ renpy.store.create_task = gui_capture_create_task
    $ renpy.store.check_status = gui_capture_check_status
    $ init_scene_queue(2, reset_last=True, fill=False)
    $ fill_scene_queue(max_remote_steps=2)
    assert len(gui_task_payloads) == 2
    assert gui_task_payloads[0][0] == "demo_test"
    assert gui_task_payloads[0][1]["story_request"]["genres"] == ["fantasy"]
    assert gui_task_payloads[0][1]["ui"]["theme_id"] == "high_fantasy"
    assert gui_task_payloads[0][1]["previous"] is None
    assert "story_request" not in gui_task_payloads[1][1]
    assert gui_task_payloads[1][1]["ui"]["theme_id"] == "high_fantasy"
    assert gui_task_payloads[1][1]["previous"] == "gui-task-1"
    $ renpy.store.create_task = original_create_task
    $ renpy.store.check_status = original_check_status
    $ init_scene_queue(3, reset_last=True, fill=False)
    run Quit(confirm=False)


testcase gui_controller_has_no_system_history_dialogue:
    $ _test.timeout = 10.0
    run Start("gui_no_system_history_jump_start")
    pause 0.8
    assert renpy.get_screen("scene_provider_error") is not None
    "Main Menu"
    pause 0.3
    assert main_menu
    assert stage0_history_count("Запуск. Формирую очередь сцен...") == 0
    assert stage0_history_count("Проигрываю сцену") == 0
    assert stage0_history_count("Это следующая сцена.") == 0
    run Quit(confirm=False)


testcase gui_small_touch_visual:
    assert renpy.variant("small")
    assert renpy.variant("touch")
    $ asset_catalog_reset_preferences()
    pause 0.8
    assert renpy.screenshot(stage0_artifact_path("gui-small-main-menu.png"))
    $ story_draft_reset("basic")
    $ story_draft_toggle_genre("romance")
    $ story_draft_set("wishes", "A compact touch-layout probe.")
    run ShowMenu("story_builder")
    pause 0.8
    assert renpy.screenshot(stage0_artifact_path("gui-small-story-builder.png"))
    run ShowMenu("asset_library")
    pause 0.8
    assert renpy.screenshot(stage0_artifact_path("gui-small-asset-library.png"))
    $ product_gui_select_asset("akari")
    pause 0.8
    assert renpy.screenshot(stage0_artifact_path("gui-small-asset-library-akari.png"))
    run Quit(confirm=False)
