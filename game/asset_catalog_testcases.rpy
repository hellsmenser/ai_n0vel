testcase gui_asset_catalog_contract:
    $ asset_catalog_reset_preferences()
    $ catalog_document = _asset_catalog_read_document()
    $ characters = asset_catalog_entries("characters")
    $ locations = asset_catalog_entries("locations")
    assert ASSET_CATALOG_PATH == "asset_catalog.json"
    assert catalog_document["version"] == 1
    assert list(ASSET_CATEGORIES) == [(item["id"], item["title"]) for item in catalog_document["categories"]]
    assert [item["id"] for item in ASSET_CATALOG] == [item["id"] for item in catalog_document["assets"]]
    assert [item["id"] for item in characters] == ["lira", "kael", "akari", "ren"]
    assert [item["id"] for item in asset_catalog_entries("characters", include_hidden=False)] == ["akari", "ren"]
    assert [item["id"] for item in locations] == ["forest", "tavern_interior", "academy_corridor_evening", "academy_rooftop_blue_hour"]
    assert len(asset_catalog_variants("lira")) == 4
    assert asset_catalog_selected_variant("lira")["id"] == "neutral"
    assert [item["id"] for item in asset_catalog_variants("ren")] == ["constructed"]
    $ ren_constructor = asset_catalog_constructor("ren")
    assert ren_constructor is not None
    assert ren_constructor["defaults"] == {"pose": "neutral", "outfit": "school"}
    assert ren_constructor["preview_mode"] == "whole_sprite"
    assert [item["id"] for item in ren_constructor["outfits"]] == ["school"]
    assert [item["id"] for item in ren_constructor["poses"]] == ["neutral", "open", "concerned"]
    $ ren_manifest = _asset_catalog_constructor_manifest(ren_constructor)
    assert ren_manifest["version"] == 8
    assert ren_manifest["canvas"] == [1024, 1536]
    assert ren_manifest["render_mode"] == "whole_sprite"
    assert ren_manifest["layer_order"] == ["sprite"]
    python:
        for ren_pose in ren_constructor["poses"]:
            ren_sprite_id = "school/{}".format(ren_pose["file"])
            ren_sprite = ren_manifest["sprites"][ren_sprite_id]
            assert ren_sprite["sprite_id"] == ren_sprite_id
            assert ren_sprite["root_anchor"] == [512, 1500]
            assert renpy.loadable(ren_sprite["sprite"])
    assert asset_catalog_constructor_preview("ren") is not None
    assert renpy.has_image(asset_catalog_selected_variant("academy_corridor_evening")["image_name"], exact=True)
    assert renpy.has_image(asset_catalog_selected_variant("academy_rooftop_blue_hour")["image_name"], exact=True)
    assert asset_catalog_get("missing") is None
    assert asset_catalog_variants("missing") == []
    run Quit(confirm=False)


testcase gui_asset_catalog_preferences_and_export:
    $ asset_catalog_reset_preferences()
    assert asset_catalog_is_enabled("kael") is True
    $ asset_catalog_toggle("kael")
    assert asset_catalog_is_enabled("kael") is False
    $ asset_catalog_set_description("lira", "  A custom guide for the current draft.  ")
    $ asset_catalog_select_variant("lira", "smile")
    assert asset_catalog_description("lira") == "A custom guide for the current draft."
    assert asset_catalog_selected_variant("lira")["id"] == "smile"
    assert asset_catalog_card_preview("lira") == asset_catalog_selected_variant("lira")["preview"]
    $ exported = asset_catalog_export_selection()
    assert [item["asset_id"] for item in exported] == ["lira", "ren", "forest", "tavern_interior", "academy_corridor_evening", "academy_rooftop_blue_hour"]
    assert exported[0]["variant_id"] == "smile"
    assert exported[0]["description"] == "A custom guide for the current draft."
    run Quit(confirm=False)


testcase gui_asset_catalog_rejects_invalid_preferences:
    $ asset_catalog_reset_preferences()
    $ asset_catalog_select_variant("lira", "missing")
    assert asset_catalog_selected_variant("lira")["id"] == "neutral"
    $ asset_catalog_toggle("missing")
    $ asset_catalog_set_description("missing", "ignored")
    assert "missing" not in persistent.ai_novel_asset_preferences["enabled"]
    $ asset_catalog_set_description("lira", "x" * 2000)
    assert len(asset_catalog_description("lira")) == ASSET_DESCRIPTION_MAX
    $ persistent.ai_novel_asset_preferences = {"version": 1, "enabled": {"removed_asset": False}, "description_overrides": {"removed_asset": "stale"}, "selected_variants": {"removed_asset": "stale"}, "selected_components": {"removed_asset": {"pose": "stale"}}}
    $ sanitized = asset_catalog_preferences()
    assert "removed_asset" not in sanitized["enabled"]
    assert "removed_asset" not in sanitized["description_overrides"]
    assert "removed_asset" not in sanitized["selected_variants"]
    assert "removed_asset" not in sanitized["selected_components"]
    run Quit(confirm=False)


testcase gui_asset_constructor_contract:
    $ asset_catalog_reset_preferences()
    $ akari = asset_catalog_get("akari")
    assert akari is not None
    assert akari["category"] == "characters"
    assert asset_catalog_is_enabled("akari") is False
    $ constructor = asset_catalog_constructor("akari")
    assert [item["id"] for item in constructor["poses"]] == ["neutral", "open", "closed", "confident", "ready", "embarrassed", "determined"]
    $ stale_manifest_cache_key = "ai_novel_asset_manifest:" + constructor["sprite_manifest"]
    $ renpy.session[stale_manifest_cache_key] = {"version": 6, "outfits": [{"id": "school", "title": "stale", "directory": "school"}], "sprites": {}}
    $ constructor_manifest = _asset_catalog_constructor_manifest(constructor)
    assert constructor_manifest["sprites"]
    assert constructor_manifest["outfits"] != renpy.session[stale_manifest_cache_key]["outfits"]
    $ renpy.session.pop(stale_manifest_cache_key, None)
    assert constructor["outfits"] == _asset_catalog_manifest_outfits(constructor_manifest, constructor["poses"])
    assert [item["id"] for item in constructor["outfits"]] == ["casual", "school", "scifi"]
    $ current_outfit = constructor["outfits"][0]
    $ current_outfit_id = current_outfit["id"]
    $ default_pose = next(item for item in constructor["poses"] if item["id"] == constructor["defaults"]["pose"])
    $ expected_sprite_id = "{}/{}".format(current_outfit["directory"], default_pose["file"])
    $ expected_sprite_path = constructor_manifest["sprites"][expected_sprite_id]["sprite"]
    assert constructor["poses"] == constructor_manifest["poses"]
    assert len(constructor_manifest["poses"]) == 7
    assert "expressions" not in constructor
    assert constructor["preview_mode"] == "whole_sprite"
    assert asset_catalog_selected_components("akari") == {"pose": constructor["defaults"]["pose"], "outfit": current_outfit_id}
    assert asset_catalog_constructor_preview("akari") is not None
    assert asset_catalog_card_preview("akari") is not None
    assert asset_catalog_expression_preview("akari") is None
    $ sprite_meta = asset_catalog_constructor_sprite_metadata("akari")
    assert sprite_meta["sprite_id"] == expected_sprite_id
    assert len(sprite_meta["root_anchor"]) == 2
    assert asset_catalog_constructor_root_anchor("akari") == tuple(sprite_meta["root_anchor"])
    assert sprite_meta["sprite"] == expected_sprite_path
    assert "head" not in sprite_meta
    assert "expression" not in sprite_meta
    assert asset_catalog_constructor_layer_order("akari") == ("sprite",)
    $ constructor_displayable = asset_catalog_constructor_composite("akari")
    assert constructor_displayable is not None
    $ constructor_render = renpy.render(constructor_displayable, 1024, 1536, 0.0, 0.0)
    assert constructor_render.get_size() == (1024, 1536)
    python:
        assert constructor_manifest["version"] == 8
        assert constructor_manifest["render_mode"] == "whole_sprite"
        assert constructor_manifest["layer_order"] == ["sprite"]
        assert len(constructor_manifest["sprites"]) == 21
        for constructor_sprite_id, constructor_sprite in constructor_manifest["sprites"].items():
            assert constructor_sprite["sprite_id"] == constructor_sprite_id
            assert 0 <= constructor_sprite["root_anchor"][0] < 1024
            assert 0 <= constructor_sprite["root_anchor"][1] < 1536
            assert renpy.loadable(constructor_sprite["sprite"])
            assert "head" not in constructor_sprite
            assert "expression" not in constructor_sprite
    run Quit(confirm=False)


testcase gui_asset_constructor_preferences_and_legacy_compatibility:
    $ constructor = asset_catalog_constructor("akari")
    $ current_outfit_id = constructor["outfits"][0]["id"]
    $ default_pose_id = constructor["defaults"]["pose"]
    $ persistent.ai_novel_asset_preferences = {"version": 1, "enabled": {"lira": False}, "description_overrides": {}, "selected_variants": {"lira": "smile"}}
    $ legacy = asset_catalog_preferences()
    assert legacy["enabled"]["lira"] is False
    assert legacy["selected_variants"]["lira"] == "smile"
    assert legacy["selected_components"]["akari"] == {"pose": default_pose_id, "outfit": current_outfit_id}
    $ persistent.ai_novel_asset_preferences = {"version": 1, "enabled": {}, "description_overrides": {}, "selected_variants": {}, "selected_components": {"akari": {"pose": "determined", "outfit": "removed"}}}
    $ stale = asset_catalog_preferences()
    assert stale["selected_components"]["akari"] == {"pose": "determined", "outfit": current_outfit_id}
    $ persistent.ai_novel_asset_preferences = {"version": 1, "enabled": {}, "description_overrides": {}, "selected_variants": {}, "selected_components": {"akari": ["malformed"]}}
    $ malformed = asset_catalog_preferences()
    assert malformed["selected_components"]["akari"] == {"pose": default_pose_id, "outfit": current_outfit_id}
    assert asset_catalog_select_component("akari", "pose", "determined") is True
    assert asset_catalog_select_component("akari", "outfit", "missing") is False
    assert asset_catalog_select_component("akari", "expression", "angry") is False
    assert asset_catalog_selected_components("akari") == {"pose": "determined", "outfit": current_outfit_id}
    assert asset_catalog_constructor_preview("akari") is not None
    assert asset_catalog_expression_preview("akari") is None
    assert asset_catalog_select_component("akari", "pose", "missing") is False
    assert asset_catalog_select_component("lira", "pose", "neutral") is False
    assert asset_catalog_variants("lira")[0]["id"] == "neutral"
    run Quit(confirm=False)


screen akari_layer_matrix():
    modal True
    add Solid("#15181D")
    $ matrix_constructor = asset_catalog_constructor("akari")
    grid 7 3:
        xalign 0.5
        yalign 0.5
        spacing 8
        for matrix_outfit in matrix_constructor["outfits"]:
            for matrix_pose in matrix_constructor["poses"]:
                $ matrix_label = "{} / {}".format(matrix_outfit["title"], matrix_pose["title"])
                frame:
                    xsize 250
                    ysize 340
                    background Solid("#242A32")
                    padding (6, 6)
                    vbox:
                        xalign 0.5
                        spacing 2
                        text matrix_label xalign 0.5 textalign 0.5 size 15 color "#FFFFFF"
                        add asset_catalog_constructor_composite("akari", matrix_pose["id"], matrix_outfit["id"]) xalign 0.5 xysize (225, 300) fit "contain"


testcase gui_asset_constructor_layer_matrix:
    $ asset_catalog_reset_preferences()
    run Show("akari_layer_matrix")
    pause 0.8
    $ matrix_path = stage0_artifact_path("gui-akari-layer-matrix.png")
    assert renpy.screenshot(matrix_path)
    run Quit(confirm=False)
