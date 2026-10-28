testcase character_slot_contract_and_transform:
    python:
        import copy

        expected_slots = {
            "far_left": 0.0,
            "left": 0.25,
            "center": 0.5,
            "right": 0.75,
            "far_right": 1.0,
        }
        for slot, expected_xalign in expected_slots.items():
            properties = show_transform_properties({"slot": slot, "flip": True})
            assert properties["xalign"] == expected_xalign
            assert properties["xzoom"] == -1.0

            scene = {
                "schema_version": 1,
                "scene_id": "slot-" + slot,
                "characters": {},
                "dialogue": [
                    {
                        "type": "show",
                        "target": "lira neutral",
                        "transform": {"slot": slot, "flip": True},
                    },
                ],
            }
            accepted = prepare_playback_bytes(
                json.dumps(scene).encode("utf-8"),
                expected_scene_id=scene["scene_id"],
            )
            assert accepted.phase == "ready"

        legacy = {
            "schema_version": 1,
            "scene_id": "legacy-xalign",
            "characters": {},
            "dialogue": [
                {
                    "type": "show",
                    "target": "lira neutral",
                    "transform": {"xalign": 0.37, "yalign": 0.8, "alpha": 0.6, "flip": False},
                },
                {"type": "show", "target": "kael serious", "transform": {}},
            ],
        }
        legacy_state = prepare_playback_bytes(json.dumps(legacy).encode("utf-8"))
        assert legacy_state.phase == "ready"
        assert show_transform_properties(legacy["dialogue"][0]["transform"])["xalign"] == 0.37
        assert show_transform_properties(legacy["dialogue"][0]["transform"])["xzoom"] == 1.0

        conflict = copy.deepcopy(legacy)
        conflict["scene_id"] = "slot-xalign-conflict"
        conflict["dialogue"][0]["transform"]["slot"] = "left"
        conflict_state = prepare_playback_bytes(json.dumps(conflict).encode("utf-8"))
        assert conflict_state.phase == "error"
        assert conflict_state.last_error.code == "contract_violation"
        assert conflict_state.last_error.path == "dialogue[0].transform"

        invalid = copy.deepcopy(legacy)
        invalid["scene_id"] = "invalid-slot"
        invalid["dialogue"][0]["transform"] = {"slot": "middle"}
        invalid_state = prepare_playback_bytes(json.dumps(invalid).encode("utf-8"))
        assert invalid_state.phase == "error"
        assert invalid_state.last_error.code == "contract_violation"
        assert invalid_state.last_error.path == "dialogue[0].transform.slot"

        invalid_type = copy.deepcopy(legacy)
        invalid_type["scene_id"] = "invalid-slot-type"
        invalid_type["dialogue"][0]["transform"] = {"slot": []}
        invalid_type_state = prepare_playback_bytes(json.dumps(invalid_type).encode("utf-8"))
        assert invalid_type_state.phase == "error"
        assert invalid_type_state.last_error.code == "contract_violation"
        assert invalid_type_state.last_error.path == "dialogue[0].transform.slot"
    run Quit(confirm=False)
