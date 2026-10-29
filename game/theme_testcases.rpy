init python:
    import hashlib
    import json

    class ThemePlaybackStub(object):
        def __init__(self, snapshot):
            self.snapshot = snapshot

    def theme_test_relative_luminance(color):
        value = color.lstrip("#")[:6]
        channels = [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def theme_test_contrast_ratio(foreground, background):
        foreground_luminance = theme_test_relative_luminance(foreground)
        background_luminance = theme_test_relative_luminance(background)
        lighter = max(foreground_luminance, background_luminance)
        darker = min(foreground_luminance, background_luminance)
        return (lighter + 0.05) / (darker + 0.05)


define theme_short_name_character = Character("Ли")
define theme_long_name_character = Character("Александрия Монтморенси")

label theme_namebox_host_label:
    $ persistent.ai_novel_theme_preference = "modern_muted"
    theme_short_name_character "Short-name probe."
    theme_long_name_character "Long-name probe."
    return


label theme_pause_host_label:
    $ persistent.ai_novel_theme_preference = "literary"
    "Theme pause oldest line."
    "Theme pause newest line."
    return


default theme_wait_task_returned = False
default theme_provider_choice = None

label theme_runtime_status_host:
    $ persistent.ai_novel_theme_preference = "science_fiction"
    $ theme_wait_task_returned = False
    $ theme_provider_choice = None
    call screen wait_task(None, "Preparing a themed scene...")
    $ theme_wait_task_returned = True
    $ theme_error = SceneProviderError("provider_offline", "poll", "The scene provider is unavailable.", retryable=True)
    call screen scene_provider_error(theme_error)
    $ theme_provider_choice = _return
    if theme_provider_choice == "retry":
        "Theme provider retry action returned."
    return


screen theme_palette_chrome_probe(palette_id):
    modal True

    add Solid("#101419")

    frame:
        xalign 0.5
        yalign 0.5
        xsize 900
        ysize 420
        padding (80, 70)
        background theme_frame("pause_menu_frame.png", theme_id="default", palette_id=palette_id)

        vbox:
            xfill True
            spacing 36

            text "Palette chrome":
                xalign 0.5
                font theme_font("title", theme_id="default")
                color "#ffffff"

            textbutton "Decorative button":
                xalign 0.5
                xsize 650
                ysize 80
                text_xalign 0.5
                idle_background theme_button_idle("default", palette_id=palette_id)
                hover_background theme_button_hover("default", palette_id=palette_id)
                text_font theme_font("body", theme_id="default")
                text_color "#ffffff"


testcase theme_registry_contract:
    assert THEME_IDS == (
        "default",
        "modern_muted",
        "literary",
        "romantic",
        "lovecraft_biopunk",
        "high_fantasy",
        "science_fiction",
    )
    assert set(THEME_REGISTRY.keys()) == set(THEME_IDS)
    assert THEME_PREFERENCE_IDS == ("auto",) + THEME_IDS
    run Quit(confirm=False)


testcase theme_resolution_default_and_invalid:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    $ persistent.ai_novel_theme_preference = "auto"
    assert resolve_theme_selection(playback=None)["theme_id"] == "default"
    assert resolve_theme_selection(playback=ThemePlaybackStub({}))["theme_id"] == "default"
    assert resolve_theme_selection(playback=ThemePlaybackStub({"ui": "invalid"}))["theme_id"] == "default"
    assert resolve_theme_selection(preference="unknown", playback=ThemePlaybackStub({"ui": {"theme_id": "literary"}}))["theme_id"] == "default"
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_resolution_auto_scene_recommendation:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    $ previous_playback = playback_state
    $ persistent.ai_novel_theme_preference = "auto"
    $ recommended = ThemePlaybackStub({"ui": {"theme_id": "romantic", "palette_id": "rose", "font_pack_id": "romantic_serif"}})
    $ playback_state = recommended
    $ resolved = resolve_theme_selection(playback=recommended)
    assert resolved["theme_id"] == "romantic"
    assert resolved["palette_id"] == "rose"
    assert resolved["font_pack_id"] == "romantic_serif"
    assert resolved["source"] == "scene"
    assert theme_font("body", theme_id=resolved["theme_id"]) == "gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"
    $ invalid_variant = resolve_theme_selection(playback=ThemePlaybackStub({"ui": {"theme_id": "romantic", "palette_id": "not-installed", "font_pack_id": "not-installed"}}))
    assert invalid_variant["palette_id"] == THEME_REGISTRY["romantic"]["default_palette_id"]
    assert invalid_variant["font_pack_id"] == THEME_REGISTRY["romantic"]["default_font_pack_id"]
    $ unknown = resolve_theme_selection(playback=ThemePlaybackStub({"ui": {"theme_id": "not-installed", "palette_id": "x", "font_pack_id": "y"}}))
    assert unknown["theme_id"] == "default"
    assert unknown["palette_id"] == THEME_REGISTRY["default"]["default_palette_id"]
    assert unknown["font_pack_id"] == THEME_REGISTRY["default"]["default_font_pack_id"]
    $ playback_state = previous_playback
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_resolution_explicit_override:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    $ previous_playback = playback_state
    $ persistent.ai_novel_theme_preference = "science_fiction"
    $ playback_state = ThemePlaybackStub({"ui": {"theme_id": "literary", "palette_id": "sepia", "font_pack_id": "literary_serif"}})
    $ resolved = resolve_theme_selection(playback=playback_state)
    assert resolved["theme_id"] == "science_fiction"
    assert resolved["font_pack_id"] == "scifi_sans"
    assert resolved["source"] == "preference"
    assert theme_font("body", theme_id=resolved["theme_id"]) == "gui/themes/fonts/play/Play-Regular.ttf"
    $ set_theme_preference("lovecraft_biopunk")
    assert persistent.ai_novel_theme_preference == "lovecraft_biopunk"
    $ set_theme_preference("invalid")
    assert persistent.ai_novel_theme_preference == "auto"
    $ playback_state = previous_playback
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_main_menu_submenu_neutral_variants:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    $ previous_playback = playback_state
    $ previous_main_menu = main_menu
    $ persistent.ai_novel_theme_preference = "auto"
    $ playback_state = ThemePlaybackStub({"ui": {"theme_id": "default", "palette_id": "muted_blue", "font_pack_id": "interface"}})
    $ main_menu = True
    assert active_theme_id() == "default"
    assert theme_color("accent", theme_id="default") == THEME_REGISTRY["default"]["colors"]["accent"]
    assert theme_palette_chrome_tint(theme_id="default") is None
    assert theme_font("body", theme_id="default") == "gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"
    run Show("preferences")
    pause 0.4
    assert renpy.get_screen("preferences") is not None
    assert renpy.screenshot(stage0_artifact_path("theme-main-menu-preferences-neutral.png"))
    run Hide("preferences")
    $ main_menu = previous_main_menu
    $ playback_state = previous_playback
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_asset_and_font_fallback:
    $ previous_main_menu = main_menu
    $ main_menu = False
    $ default_dialogue = theme_asset("dialogue_frame.png", theme_id="default")
    assert theme_asset("dialogue_frame.png", theme_id="not-installed") == default_dialogue
    assert theme_asset("missing-file.png", theme_id="romantic", legacy="gui/frame.png") == "gui/frame.png"
    assert theme_font("body", theme_id="not-installed") == theme_font("body", theme_id="default")
    assert theme_font("body", theme_id="default", font_pack_id="not-installed") == "gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"
    assert theme_color("accent", theme_id="default", palette_id="muted_blue") != theme_color("accent", theme_id="default", palette_id="default")
    assert theme_asset_slice("dialogue_frame.png", theme_id="default") == (160, 60, 160, 60)
    assert theme_asset_slice("nav_idle.png", theme_id="literary") == (80, 28, 80, 28)
    assert theme_asset_slice("missing-file.png", theme_id="default", fallback=(1, 2, 3, 4)) == (1, 2, 3, 4)
    python:
        for packaged_theme_id in THEME_IDS:
            manifest_path = "gui/themes/{}/manifest.json".format(packaged_theme_id)
            with renpy.file(manifest_path) as manifest_source:
                packaged_manifest = json.loads(manifest_source.read().decode("utf-8"))
            assert packaged_manifest["id"] == packaged_theme_id
            for asset_id, expected_slice in THEME_ASSET_SLICES.items():
                assert tuple(packaged_manifest["assets"][asset_id]["slice"]) == expected_slice
            packaged_font_id = THEME_REGISTRY[packaged_theme_id]["default_font_pack_id"]
            for font_role, candidates in THEME_FONT_CANDIDATES[packaged_font_id].items():
                assert tuple(packaged_manifest["fonts"][font_role]) == candidates
                assert all(renpy.loadable(candidate) for candidate in candidates)
    $ main_menu = previous_main_menu
    run Quit(confirm=False)


testcase theme_semantic_foreground_contrast:
    python:
        for packaged_theme_id in THEME_IDS:
            manifest_path = "gui/themes/{}/manifest.json".format(packaged_theme_id)
            with renpy.file(manifest_path) as manifest_source:
                packaged_manifest = json.loads(manifest_source.read().decode("utf-8"))
            colors = packaged_manifest["colors"]
            assert theme_test_contrast_ratio(colors["heading_text"], colors["panel"]) >= 4.5
            assert theme_test_contrast_ratio(colors["text"], colors["panel_alt"]) >= 4.5
            assert theme_test_contrast_ratio(colors["button_hover_text"], colors["hover"]) >= 4.5
            assert theme_color("heading_text", theme_id=packaged_theme_id) == colors["heading_text"]
            assert theme_color("overlay_text", theme_id=packaged_theme_id) == colors["overlay_text"]
            assert theme_color("button_hover_text", theme_id=packaged_theme_id) == colors["button_hover_text"]
            assert theme_color("panel", theme_id=packaged_theme_id) == colors["panel"]
            assert theme_color("panel_alt", theme_id=packaged_theme_id) == colors["panel_alt"]
        for runtime_theme_id in THEME_IDS:
            for runtime_palette_id in THEME_REGISTRY[runtime_theme_id]["palette_ids"]:
                hover_background = theme_color("hover", theme_id=runtime_theme_id, palette_id=runtime_palette_id)
                hover_foreground = theme_color("button_hover_text", theme_id=runtime_theme_id, palette_id=runtime_palette_id)
                assert theme_test_contrast_ratio(hover_foreground, hover_background) >= 4.5
    run Quit(confirm=False)


testcase theme_speaker_name_colors_are_distinct_and_readable:
    $ previous_metadata = story_metadata
    python:
        test_cast = []
        for cast_index in range(STORY_METADATA_MAX_CAST):
            test_cast.append({
                "character_id": "speaker_{:02d}".format(cast_index),
                "display_name": "Speaker {:02d}".format(cast_index),
                "asset_id": "speaker_{:02d}".format(cast_index),
            })
        story_metadata = validate_story_metadata({
            "schema_version": 1,
            "story_id": "speaker-color-probe",
            "title": "Speaker color probe",
            "synopsis": "",
            "cast": test_cast,
            "ui": {},
        })
        cast_ids = [member["character_id"] for member in story_metadata["cast"]] + ["narrator"]
        for packaged_theme_id in THEME_IDS:
            for runtime_palette_id in THEME_REGISTRY[packaged_theme_id]["palette_ids"]:
                colors = [speaker_name_color(speaker_id, theme_id=packaged_theme_id, palette_id=runtime_palette_id) for speaker_id in cast_ids]
                background = theme_color("panel", theme_id=packaged_theme_id, palette_id=runtime_palette_id)
                assert len(colors) == len(set(colors))
                assert all(theme_test_contrast_ratio(color, background) >= 4.5 for color in colors)
                assert colors[0] == speaker_name_color(cast_ids[0], theme_id=packaged_theme_id, palette_id=runtime_palette_id)
        story_metadata = validate_story_metadata({
            "schema_version": 1,
            "story_id": "known-collision-probe",
            "title": "Known collision probe",
            "synopsis": "",
            "cast": [
                {"character_id": speaker_id, "display_name": speaker_id.title(), "asset_id": speaker_id}
                for speaker_id in ("akari", "ren", "lira", "kael")
            ],
            "ui": {},
        })
        known_ids = ["akari", "ren", "lira", "kael", "narrator"]
        known_colors = [speaker_name_color(speaker_id, theme_id="romantic") for speaker_id in known_ids]
        assert len(known_colors) == len(set(known_colors))
    $ story_metadata = previous_metadata
    run Quit(confirm=False)


testcase theme_namebox_stable_size:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    run Start("theme_namebox_host_label")
    click until "Short-name probe."
    $ short_namebox = renpy.get_displayable("say", "namebox")
    assert short_namebox is not None
    $ short_namebox_size = renpy.render(short_namebox, config.screen_width, config.screen_height, 0.0, 0.0).get_size()
    assert short_namebox_size == (300, 64)
    $ short_namebox_placement = short_namebox.get_placement()
    assert short_namebox_placement[0] == gui.dialogue_xpos
    assert short_namebox_placement[2] == 0.0
    assert renpy.screenshot(stage0_artifact_path("theme-namebox-modern-muted-short.png"))
    click until "Long-name probe."
    $ long_namebox = renpy.get_displayable("say", "namebox")
    assert long_namebox is not None
    $ long_namebox_size = renpy.render(long_namebox, config.screen_width, config.screen_height, 0.0, 0.0).get_size()
    assert long_namebox_size[0] > short_namebox_size[0]
    assert long_namebox_size[1] == 64
    assert renpy.screenshot(stage0_artifact_path("theme-namebox-modern-muted-long.png"))
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_main_menu_hover_text_contrast:
    $ hover_background = theme_color("hover", theme_id="default", neutral_shell=True)
    $ hover_text = ai_shell_hover_text_color()
    assert hover_text == theme_color("button_hover_text", theme_id="default", neutral_shell=True)
    assert theme_test_contrast_ratio(hover_text, hover_background) >= 4.5
    run ShowMenu("main_menu")
    pause 0.3
    move (0.5, 0.5) pattern "Новая история"
    pause 0.2
    assert renpy.screenshot(stage0_artifact_path("theme-main-menu-hover-contrast.png"))
    run Quit(confirm=False)


testcase theme_pause_screen:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    run Start("theme_pause_host_label")
    click until "Theme pause newest line."
    run config.game_menu_action
    pause 0.6
    assert renpy.get_screen("pause_menu") is not None
    assert resolve_theme_selection()["theme_id"] == "literary"
    assert [entry.what for entry in _history_list][-2:] == ["Theme pause oldest line.", "Theme pause newest line."]
    assert renpy.screenshot(stage0_artifact_path("theme-pause-literary.png"))
    run Return()
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_runtime_status_screens:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    run Start("theme_runtime_status_host")
    pause 0.1
    assert active_theme_id() == "science_fiction"
    assert renpy.get_screen("wait_task") is not None
    assert renpy.get_displayable("wait_task", "themed_wait_panel") is not None
    assert renpy.screenshot(stage0_artifact_path("theme-wait-task-science-fiction.png"))
    pause 0.7
    assert theme_wait_task_returned
    assert renpy.get_screen("scene_provider_error") is not None
    assert renpy.get_displayable("scene_provider_error", "themed_provider_panel") is not None
    $ retry_button = renpy.get_displayable("scene_provider_error", "retry")
    $ main_menu_button = renpy.get_displayable("scene_provider_error", "main_menu")
    assert retry_button is not None
    assert main_menu_button is not None
    assert renpy.screenshot(stage0_artifact_path("theme-provider-error-science-fiction.png"))
    "Retry"
    click until "Theme provider retry action returned."
    assert theme_provider_choice == "retry"
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_game_menu_surfaces:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    $ persistent.ai_novel_theme_preference = "literary"
    assert active_theme_id(neutral_shell=True) == "default"
    assert renpy.screenshot(stage0_artifact_path("theme-main-menu-neutral.png"))
    run Start("theme_pause_host_label")
    click until "Theme pause newest line."
    run ShowMenu("save")
    pause 0.4
    assert renpy.get_screen("save") is not None
    assert renpy.screenshot(stage0_artifact_path("theme-save-literary.png"))
    run ShowMenu("preferences")
    pause 0.4
    assert renpy.get_screen("preferences") is not None
    $ preferences_viewport = renpy.get_displayable("preferences", "themed_game_menu_viewport")
    assert preferences_viewport is not None
    assert preferences_viewport.yadjustment.range > 0
    assert renpy.screenshot(stage0_artifact_path("theme-preferences-literary.png"))
    run Show("confirm", message="Theme confirmation", yes_action=Hide("confirm"), no_action=Hide("confirm"))
    pause 0.4
    assert renpy.get_screen("confirm") is not None
    assert renpy.screenshot(stage0_artifact_path("theme-confirm-literary.png"))
    run Hide("confirm")
    run Return()
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_game_menu_navigation_card_alignment:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    run Start("theme_pause_host_label")
    click until "Theme pause newest line."
    $ persistent.ai_novel_theme_preference = "modern_muted"
    run ShowMenu("preferences")
    pause 0.4
    $ navigation_card = renpy.get_displayable("preferences", "themed_game_menu_navigation_card")
    $ navigation_controls = renpy.get_displayable("preferences", "themed_navigation_controls")
    $ navigation_return = renpy.get_displayable("preferences", "themed_navigation_return")
    assert navigation_card is not None
    assert navigation_controls is not None
    assert navigation_return is not None
    $ navigation_placement = navigation_controls.get_placement()
    assert navigation_placement[0] == 0.5 and navigation_placement[1] == 0.5
    assert navigation_placement[2] == 0.5 and navigation_placement[3] == 0.5
    assert renpy.screenshot(stage0_artifact_path("theme-game-menu-navigation-modern-muted.png"))
    run Return()
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_pause_main_menu_confirm_layer:
    $ previous_preference = getattr(persistent, "ai_novel_theme_preference", None)
    run Start("theme_pause_host_label")
    click until "Theme pause newest line."
    $ persistent.ai_novel_theme_preference = "high_fantasy"
    run config.game_menu_action
    pause 0.3
    $ pause_screen = renpy.get_screen("pause_menu")
    assert pause_screen is not None
    run MainMenu()
    pause 0.3
    $ confirm_screen = renpy.get_screen("confirm")
    assert confirm_screen is not None
    assert confirm_screen.modal
    assert confirm_screen.zorder > pause_screen.zorder
    assert renpy.get_displayable("confirm", "confirm_no") is not None
    assert renpy.screenshot(stage0_artifact_path("theme-pause-main-menu-confirm-high-fantasy.png"))
    "No"
    pause 0.3
    assert renpy.get_screen("confirm") is None
    assert renpy.get_screen("pause_menu") is not None
    $ persistent.ai_novel_theme_preference = previous_preference
    run Quit(confirm=False)


testcase theme_palette_chrome_and_compact_controls:
    $ previous_main_menu = main_menu
    $ main_menu = False
    $ default_frame = theme_frame("nav_idle.png", theme_id="default", palette_id="default")
    $ muted_blue_frame = theme_frame("nav_idle.png", theme_id="default", palette_id="muted_blue")
    assert default_frame.__class__ is not muted_blue_frame.__class__
    assert theme_palette_chrome_tint("default", "default") is None
    assert theme_palette_chrome_tint("default", "muted_blue") == theme_color("accent", theme_id="default", palette_id="muted_blue")
    assert theme_compact_button_idle("literary").__class__ is not theme_button_idle("literary").__class__
    assert theme_touch_button_idle("literary").__class__ is theme_compact_button_idle("literary").__class__
    $ default_palette_path = stage0_artifact_path("theme-palette-default.png")
    $ muted_blue_palette_path = stage0_artifact_path("theme-palette-muted-blue.png")
    run Show("theme_palette_chrome_probe", palette_id="default")
    pause 0.3
    assert renpy.screenshot(default_palette_path)
    run Show("theme_palette_chrome_probe", palette_id="muted_blue")
    pause 0.3
    assert renpy.screenshot(muted_blue_palette_path)
    python:
        with open(default_palette_path, "rb") as default_palette_file:
            default_palette_hash = hashlib.sha256(default_palette_file.read()).hexdigest()
        with open(muted_blue_palette_path, "rb") as muted_blue_palette_file:
            muted_blue_palette_hash = hashlib.sha256(muted_blue_palette_file.read()).hexdigest()
    assert default_palette_hash != muted_blue_palette_hash
    run Hide("theme_palette_chrome_probe")
    $ main_menu = previous_main_menu
    run Quit(confirm=False)
