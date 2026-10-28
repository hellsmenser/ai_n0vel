default persistent.ai_novel_asset_preferences = None

init -70 python:
    import builtins
    import copy
    import json

    ASSET_DESCRIPTION_MAX = 500
    ASSET_CATALOG_PATH = "asset_catalog.json"

    def _asset_catalog_read_document():
        with renpy.open_file(ASSET_CATALOG_PATH, encoding=False) as catalog_file:
            return json.loads(catalog_file.read().decode("utf-8"))

    def _asset_catalog_load():
        document = _asset_catalog_read_document()
        if not isinstance(document, builtins.dict) or document.get("version") != 1:
            raise ValueError("Asset catalog must be a version 1 object.")

        raw_categories = document.get("categories")
        raw_assets = document.get("assets")
        if not isinstance(raw_categories, builtins.list) or not raw_categories:
            raise ValueError("Asset catalog categories must be a non-empty list.")
        if not isinstance(raw_assets, builtins.list):
            raise ValueError("Asset catalog assets must be a list.")

        categories = []
        category_ids = set()
        for category in raw_categories:
            if not isinstance(category, builtins.dict):
                raise ValueError("Asset catalog category entries must be objects.")
            category_id = category.get("id")
            title = category.get("title")
            if (
                not isinstance(category_id, str)
                or not category_id
                or category_id in category_ids
                or not isinstance(title, str)
                or not title.strip()
            ):
                raise ValueError("Asset catalog category metadata is invalid.")
            categories.append((category_id, title.strip()))
            category_ids.add(category_id)

        assets = []
        asset_ids = set()
        for asset in raw_assets:
            if not isinstance(asset, builtins.dict):
                raise ValueError("Asset catalog entries must be objects.")
            asset_id = asset.get("id")
            variants = asset.get("variants")
            if (
                not isinstance(asset_id, str)
                or not asset_id
                or asset_id in asset_ids
                or asset.get("category") not in category_ids
                or not isinstance(asset.get("title"), str)
                or not asset["title"].strip()
                or not isinstance(asset.get("description"), str)
                or not isinstance(asset.get("tags"), builtins.list)
                or not isinstance(variants, builtins.list)
                or not variants
            ):
                raise ValueError("Asset catalog asset metadata is invalid.")

            variant_ids = set()
            for variant in variants:
                if not isinstance(variant, builtins.dict):
                    raise ValueError("Asset catalog variants must be objects.")
                variant_id = variant.get("id")
                if (
                    not isinstance(variant_id, str)
                    or not variant_id
                    or variant_id in variant_ids
                    or not isinstance(variant.get("title"), str)
                    or not variant["title"].strip()
                    or not isinstance(variant.get("preview"), str)
                    or not variant["preview"]
                    or not isinstance(variant.get("image_name"), str)
                    or not variant["image_name"]
                ):
                    raise ValueError("Asset catalog variant metadata is invalid.")
                variant_ids.add(variant_id)

            constructor = asset.get("constructor")
            if constructor is not None and (
                not isinstance(constructor, builtins.dict)
                or not isinstance(constructor.get("sprite_manifest"), str)
                or not constructor["sprite_manifest"]
                or constructor.get("preview_mode") not in ("whole_sprite", "layered_atlas")
                or not isinstance(constructor.get("defaults"), builtins.dict)
            ):
                raise ValueError("Asset catalog constructor metadata is invalid.")

            assets.append(copy.deepcopy(asset))
            asset_ids.add(asset_id)

        return tuple(categories), tuple(assets)

    ASSET_CATEGORIES, ASSET_CATALOG = _asset_catalog_load()

    def _asset_catalog_index():
        return {item["id"]: item for item in ASSET_CATALOG}

    def _asset_catalog_default_preferences():
        selected_components = {}
        for item in ASSET_CATALOG:
            if "constructor" not in item:
                continue
            constructor = asset_catalog_constructor(item["id"])
            if constructor is not None:
                selected_components[item["id"]] = dict(constructor["defaults"])
        return {
            "version": 1,
            "enabled": {
                item["id"]: item.get("enabled_by_default", True)
                for item in ASSET_CATALOG
            },
            "description_overrides": {},
            "selected_variants": {
                item["id"]: item["variants"][0]["id"] for item in ASSET_CATALOG
            },
            "selected_components": selected_components,
        }

    def _asset_catalog_sanitize_preferences(value):
        result = _asset_catalog_default_preferences()
        if not isinstance(value, dict) or value.get("version") != 1:
            return result
        index = _asset_catalog_index()
        enabled = value.get("enabled")
        if isinstance(enabled, dict):
            for asset_id in index:
                if isinstance(enabled.get(asset_id), bool):
                    result["enabled"][asset_id] = enabled[asset_id]
        descriptions = value.get("description_overrides")
        if isinstance(descriptions, dict):
            for asset_id, description in descriptions.items():
                if asset_id in index and isinstance(description, str):
                    cleaned = description.strip()[:ASSET_DESCRIPTION_MAX]
                    if cleaned:
                        result["description_overrides"][asset_id] = cleaned
        selected = value.get("selected_variants")
        if isinstance(selected, dict):
            for asset_id, variant_id in selected.items():
                item = index.get(asset_id)
                if item and any(v["id"] == variant_id for v in item["variants"]):
                    result["selected_variants"][asset_id] = variant_id
        selected_components = value.get("selected_components")
        if isinstance(selected_components, dict):
            for asset_id, selection in selected_components.items():
                item = index.get(asset_id)
                constructor = asset_catalog_constructor(asset_id) if item else None
                if not constructor or not isinstance(selection, dict):
                    continue
                for component, options_key in (
                        ("pose", "poses"),
                        ("outfit", "outfits"),
                        ("expression", "expressions")):
                    if options_key not in constructor:
                        continue
                    candidate = selection.get(component)
                    if any(option["id"] == candidate for option in constructor[options_key]):
                        result["selected_components"][asset_id][component] = candidate
        return result

    def asset_catalog_preferences():
        clean = _asset_catalog_sanitize_preferences(
            getattr(persistent, "ai_novel_asset_preferences", None)
        )
        persistent.ai_novel_asset_preferences = clean
        return clean

    def asset_catalog_reset_preferences():
        persistent.ai_novel_asset_preferences = _asset_catalog_default_preferences()
        return persistent.ai_novel_asset_preferences

    def asset_catalog_entries(category=None, enabled_only=False, include_hidden=True):
        preferences = asset_catalog_preferences()
        result = []
        for item in ASSET_CATALOG:
            if category is not None and item["category"] != category:
                continue
            if not include_hidden and item.get("library_hidden", False):
                continue
            if enabled_only and not preferences["enabled"].get(item["id"], True):
                continue
            result.append(item)
        return result

    def asset_catalog_get(asset_id):
        if not isinstance(asset_id, str):
            return None
        return _asset_catalog_index().get(asset_id)

    def asset_catalog_variants(asset_id):
        item = asset_catalog_get(asset_id)
        return list(item["variants"]) if item else []

    def asset_catalog_constructor(asset_id):
        item = asset_catalog_get(asset_id)
        if item is None or "constructor" not in item:
            return None
        constructor = copy.deepcopy(item["constructor"])
        manifest = _asset_catalog_constructor_manifest(constructor)
        poses = _asset_catalog_manifest_poses(manifest)
        outfits = _asset_catalog_manifest_outfits(manifest, poses)
        if not poses or not outfits:
            return None
        constructor["poses"] = poses
        constructor["outfits"] = outfits
        defaults = dict(constructor.get("defaults", {}))
        if not any(option["id"] == defaults.get("pose") for option in poses):
            defaults["pose"] = poses[0]["id"]
        if not any(option["id"] == defaults.get("outfit") for option in outfits):
            defaults["outfit"] = outfits[0]["id"]
        constructor["defaults"] = defaults
        return constructor

    def asset_catalog_selected_components(asset_id):
        if asset_catalog_constructor(asset_id) is None:
            return None
        return copy.deepcopy(
            asset_catalog_preferences()["selected_components"][asset_id]
        )

    def asset_catalog_select_component(asset_id, component, option_id):
        item = asset_catalog_get(asset_id)
        constructor = asset_catalog_constructor(asset_id) if item else None
        option_keys = {
            "pose": "poses",
            "outfit": "outfits",
            "expression": "expressions",
        }
        options_key = option_keys.get(component)
        if (
            constructor is None
            or options_key is None
            or options_key not in constructor
            or not isinstance(option_id, str)
        ):
            return False
        if not any(option["id"] == option_id for option in constructor[options_key]):
            return False
        preferences = asset_catalog_preferences()
        preferences["selected_components"][asset_id][component] = option_id
        persistent.ai_novel_asset_preferences = preferences
        renpy.save_persistent()
        renpy.restart_interaction()
        return True

    def asset_catalog_constructor_preview(asset_id):
        item = asset_catalog_get(asset_id)
        constructor = asset_catalog_constructor(asset_id) if item else None
        if constructor is None:
            variant = asset_catalog_selected_variant(asset_id)
            return variant["preview"] if variant else None
        metadata = asset_catalog_constructor_sprite_metadata(asset_id)
        if metadata is not None:
            return asset_catalog_constructor_composite(asset_id)
        variant = asset_catalog_selected_variant(asset_id)
        return variant["preview"] if variant else None

    def asset_catalog_expression_preview(asset_id):
        item = asset_catalog_get(asset_id)
        constructor = asset_catalog_constructor(asset_id) if item else None
        selected = asset_catalog_selected_components(asset_id)
        if constructor is None or selected is None or "expressions" not in constructor:
            return None
        for expression in constructor["expressions"]:
            if expression["id"] == selected["expression"]:
                return expression["layer"]
        return None

    def _asset_catalog_constructor_manifest(constructor):
        manifest_path = constructor.get("sprite_manifest")
        if not manifest_path:
            return None
        try:
            with renpy.open_file(manifest_path, encoding=False) as manifest_file:
                manifest = json.loads(manifest_file.read().decode("utf-8"))
        except Exception:
            return None
        if (
            not isinstance(manifest, builtins.dict)
            or manifest.get("version") != 8
            or manifest.get("canvas") != [1024, 1536]
            or manifest.get("render_mode") != "whole_sprite"
            or manifest.get("layer_order") != ["sprite"]
            or not isinstance(manifest.get("poses"), builtins.list)
            or not isinstance(manifest.get("sprites"), builtins.dict)
        ):
            return None
        return manifest

    def _asset_catalog_manifest_poses(manifest):
        if not isinstance(manifest, builtins.dict):
            return []
        raw_poses = manifest.get("poses")
        if not isinstance(raw_poses, builtins.list):
            return []
        result = []
        seen = set()
        for raw in raw_poses:
            if not isinstance(raw, builtins.dict):
                return []
            pose_id = raw.get("id")
            title = raw.get("title")
            filename = raw.get("file")
            if (
                not isinstance(pose_id, str)
                or not pose_id
                or pose_id in seen
                or not isinstance(title, str)
                or not title.strip()
                or not isinstance(filename, str)
                or not filename
            ):
                return []
            result.append({
                "id": pose_id,
                "title": title.strip(),
                "file": filename,
            })
            seen.add(pose_id)
        return result

    def _asset_catalog_manifest_outfits(manifest, poses):
        if not isinstance(manifest, builtins.dict):
            return []
        raw_outfits = manifest.get("outfits")
        if not isinstance(raw_outfits, builtins.list) or not isinstance(poses, (builtins.list, tuple)):
            return []
        result = []
        seen = set()
        sprites = manifest["sprites"]
        for raw in raw_outfits:
            if not isinstance(raw, builtins.dict):
                continue
            outfit_id = raw.get("id")
            title = raw.get("title")
            directory = raw.get("directory")
            if (
                not isinstance(outfit_id, str)
                or not outfit_id
                or outfit_id in seen
                or not isinstance(title, str)
                or not title.strip()
                or not isinstance(directory, str)
                or not directory
            ):
                continue
            complete = True
            for pose in poses:
                if not isinstance(pose, builtins.dict) or not isinstance(pose.get("file"), str):
                    complete = False
                    break
                sprite_id = "{}/{}".format(directory, pose["file"])
                metadata = sprites.get(sprite_id)
                if (
                    not isinstance(metadata, builtins.dict)
                    or metadata.get("sprite_id") != sprite_id
                    or not isinstance(metadata.get("sprite"), str)
                    or not renpy.loadable(metadata["sprite"])
                ):
                    complete = False
                    break
            if not complete:
                continue
            result.append({
                "id": outfit_id,
                "title": title.strip(),
                "directory": directory,
            })
            seen.add(outfit_id)
        return result

    def asset_catalog_constructor_sprite_metadata(asset_id, pose_id=None, outfit_id=None):
        item = asset_catalog_get(asset_id)
        constructor = asset_catalog_constructor(asset_id) if item else None
        selected = asset_catalog_selected_components(asset_id)
        if constructor is None or selected is None:
            return None
        selected_pose_id = pose_id if pose_id is not None else selected["pose"]
        selected_outfit_id = outfit_id if outfit_id is not None else selected["outfit"]
        pose = next((
            option for option in constructor["poses"]
            if option["id"] == selected_pose_id
        ), None)
        outfit = next((
            option for option in constructor["outfits"]
            if option["id"] == selected_outfit_id
        ), None)
        if pose is None or outfit is None:
            return None
        manifest = _asset_catalog_constructor_manifest(constructor)
        if manifest is None:
            return None
        sprite_id = "{}/{}".format(outfit["directory"], pose["file"])
        metadata = manifest["sprites"].get(sprite_id)
        if not isinstance(metadata, builtins.dict):
            return None
        if (
            metadata.get("sprite_id") != sprite_id
            or not isinstance(metadata.get("sprite"), str)
            or not renpy.loadable(metadata["sprite"])
            or not isinstance(metadata.get("root_anchor"), builtins.list)
            or len(metadata["root_anchor"]) != 2
            or "head" in metadata
            or "expression" in metadata
        ):
            return None
        return copy.deepcopy(metadata)

    def asset_catalog_constructor_layer_order(asset_id):
        metadata = asset_catalog_constructor_sprite_metadata(asset_id)
        if metadata is None:
            return None
        return ("sprite",)

    def asset_catalog_constructor_root_anchor(asset_id):
        """Return the per-sprite attachment point on the canonical canvas."""
        metadata = asset_catalog_constructor_sprite_metadata(asset_id)
        if metadata is None:
            return None
        return tuple(metadata["root_anchor"])

    def asset_catalog_constructor_composite(asset_id, pose_id=None, outfit_id=None):
        item = asset_catalog_get(asset_id)
        constructor = asset_catalog_constructor(asset_id) if item else None
        selected = asset_catalog_selected_components(asset_id)
        if constructor is None or selected is None:
            return None
        metadata = asset_catalog_constructor_sprite_metadata(asset_id, pose_id, outfit_id)
        if metadata is None:
            variant = asset_catalog_selected_variant(asset_id)
            return variant["preview"] if variant else None
        return Transform(metadata["sprite"])

    def asset_catalog_card_preview(asset_id):
        return asset_catalog_constructor_preview(asset_id)

    def asset_catalog_is_enabled(asset_id):
        item = asset_catalog_get(asset_id)
        if item is None:
            return False
        return bool(asset_catalog_preferences()["enabled"].get(asset_id, True))

    def asset_catalog_toggle(asset_id):
        if asset_catalog_get(asset_id) is None:
            return False
        preferences = asset_catalog_preferences()
        preferences["enabled"][asset_id] = not preferences["enabled"][asset_id]
        persistent.ai_novel_asset_preferences = preferences
        renpy.save_persistent()
        renpy.restart_interaction()
        return preferences["enabled"][asset_id]

    def asset_catalog_description(asset_id):
        item = asset_catalog_get(asset_id)
        if item is None:
            return ""
        return asset_catalog_preferences()["description_overrides"].get(
            asset_id, item["description"]
        )

    def asset_catalog_set_description(asset_id, description):
        if asset_catalog_get(asset_id) is None or not isinstance(description, str):
            return False
        preferences = asset_catalog_preferences()
        cleaned = description.strip()[:ASSET_DESCRIPTION_MAX]
        if cleaned:
            preferences["description_overrides"][asset_id] = cleaned
        else:
            preferences["description_overrides"].pop(asset_id, None)
        persistent.ai_novel_asset_preferences = preferences
        renpy.save_persistent()
        return True

    def asset_catalog_select_variant(asset_id, variant_id):
        item = asset_catalog_get(asset_id)
        if item is None or not isinstance(variant_id, str):
            return False
        if not any(v["id"] == variant_id for v in item["variants"]):
            return False
        preferences = asset_catalog_preferences()
        preferences["selected_variants"][asset_id] = variant_id
        persistent.ai_novel_asset_preferences = preferences
        renpy.save_persistent()
        renpy.restart_interaction()
        return True

    def asset_catalog_selected_variant(asset_id):
        item = asset_catalog_get(asset_id)
        if item is None:
            return None
        selected_id = asset_catalog_preferences()["selected_variants"].get(asset_id)
        for variant in item["variants"]:
            if variant["id"] == selected_id:
                return variant
        return item["variants"][0]

    def asset_catalog_export_selection():
        result = []
        for item in ASSET_CATALOG:
            if not asset_catalog_is_enabled(item["id"]):
                continue
            variant = asset_catalog_selected_variant(item["id"])
            result.append({
                "asset_id": item["id"],
                "category": item["category"],
                "variant_id": variant["id"],
                "resource": variant["image_name"],
                "description": asset_catalog_description(item["id"]),
            })
        return copy.deepcopy(result)
