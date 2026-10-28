testcase gui_story_draft_basic_contract:
    $ story_draft_reset("basic")
    assert story_draft_get()["mode"] == "basic"
    assert story_draft_validate() == ["story_request_empty"]
    $ story_draft_toggle_genre("adventure")
    $ story_draft_set("wishes", "A quiet journey with a difficult choice.")
    assert story_draft_validate() == []
    $ exported = story_draft_export_payload()
    assert exported["story_request"]["mode"] == "basic"
    assert exported["story_request"]["genres"] == ["adventure"]
    assert exported["story_request"]["wishes"] == "A quiet journey with a difficult choice."
    assert "tone" not in exported["story_request"]
    run Quit(confirm=False)


testcase gui_story_draft_advanced_contract:
    $ story_draft_reset("advanced")
    $ story_draft_toggle_genre("drama")
    $ story_draft_set("tone", "melancholic")
    $ story_draft_set("setting", "A coastal city where memories are traded.")
    $ story_draft_set("length", "medium")
    $ story_draft_set("pacing", "measured")
    $ story_draft_set("title_seed", "Salt Memory")
    $ story_draft_toggle_cast("lira")
    $ story_draft_set_ui("literary", "warm_parchment", "literary_serif")
    $ exported = story_draft_export_payload()
    assert exported["story_request"]["mode"] == "advanced"
    assert exported["story_request"]["cast_asset_ids"] == ["lira"]
    assert exported["story_request"]["tone"] == "melancholic"
    assert exported["ui"]["theme_id"] == "literary"
    assert exported["ui"]["palette_id"] == "warm_parchment"
    assert exported["ui"]["font_pack_id"] == "literary_serif"
    run Quit(confirm=False)


testcase gui_story_draft_bounds_and_launch_seam:
    $ story_draft_reset("invalid")
    assert story_draft_get()["mode"] == "basic"
    $ story_draft_set("wishes", "x" * 5000)
    assert len(story_draft_get()["wishes"]) == STORY_WISHES_MAX
    $ story_draft_toggle_genre("not_a_genre")
    assert story_draft_get()["genres"] == []
    $ story_draft_toggle_genre("mystery")
    $ committed = story_builder_commit()
    assert committed is True
    assert story_launch_payload == story_draft_export_payload()
    assert story_launch_payload is not persistent.ai_novel_story_draft
    run Quit(confirm=False)


testcase gui_story_draft_excludes_disabled_cast:
    $ asset_catalog_reset_preferences()
    $ story_draft_reset("advanced")
    $ story_draft_toggle_genre("drama")
    $ story_draft_toggle_cast("lira")
    assert story_draft_get()["cast_asset_ids"] == ["lira"]
    $ asset_catalog_toggle("lira")
    $ exported = story_draft_export_payload()
    assert "cast_asset_ids" not in exported["story_request"]
    assert "lira" not in [item["asset_id"] for item in exported["story_request"]["assets"]]
    $ asset_catalog_reset_preferences()
    run Quit(confirm=False)
