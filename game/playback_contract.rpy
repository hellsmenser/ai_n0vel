init python:
    import builtins
    import hashlib
    import json
    import math
    import re

    SCENE_SCHEMA_VERSION = 1
    # Limits keep untrusted AI output bounded before semantic validation.
    MAX_SCENE_RAW_BYTES = 1024 * 1024
    MAX_SCENE_DEPTH = 20
    MAX_SCENE_NODES = 10000
    MAX_DIALOGUE_ACTIONS = 500
    MAX_CHARACTERS = 64
    MAX_GENERIC_STRING_LENGTH = 4096
    MAX_IDENTIFIER_LENGTH = 256
    MAX_UI_IDENTIFIER_LENGTH = 64
    MAX_LINE_TEXT_LENGTH = 4000
    PRODUCTION_JSON_JUMP_TARGETS = set(["next_scene"])
    TEST_JSON_JUMP_TARGETS = set([
        "stage0_jump_target",
        "stage1_contract_jump_target",
        "stage2_jump_control_target",
    ])
    _ROOT_FIELDS = set(["schema_version", "scene_id", "characters", "dialogue", "name", "metadata", "ui"])
    _UI_FIELDS = set(["theme_id", "palette_id", "font_pack_id"])
    _UI_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")
    _CHARACTER_SLOTS = set(["far_left", "left", "center", "right", "far_right"])
    _ACTION_FIELDS = {
        "scene": set(["type", "target", "metadata"]),
        "show": set(["type", "target", "transform", "metadata"]),
        "line": set(["type", "speaker", "text", "metadata"]),
        "pause": set(["type", "duration", "metadata"]),
        "transition": set(["type", "effect", "metadata"]),
        "animate": set(["type", "target", "effect", "metadata"]),
        "jump": set(["type", "target", "metadata"]),
        "return": set(["type", "metadata"]),
    }

    def _contract_error(code, path, message, scene_id=None, schema_version=None,
                        snapshot=None, migrated_from_schema=None):
        return PlaybackState(
            scene_id=scene_id,
            schema_version=schema_version,
            content_hash=None,
            snapshot=snapshot,
            phase="error",
            last_error=PlaybackError(code, path, message),
            migrated_from_schema=migrated_from_schema,
        )

    def _duplicate_key_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key:" + str(key))
            result[key] = value
        return result

    def _is_number(value):
        return (not isinstance(value, bool) and isinstance(value, (int, float))
                and math.isfinite(value))

    def _scan_json_limits(root):
        """Iteratively enforce structural limits without recursive traversal."""
        stack = [(root, "$", 1)]
        nodes = 0
        while stack:
            value, path, depth = stack.pop()
            nodes += 1
            if nodes > MAX_SCENE_NODES:
                raise _ContractViolation("$", "scene exceeds node limit")
            if depth > MAX_SCENE_DEPTH:
                raise _ContractViolation("$", "scene exceeds nesting depth")
            if isinstance(value, str):
                if len(value) > MAX_GENERIC_STRING_LENGTH:
                    raise _ContractViolation(path, "string exceeds length limit")
            elif isinstance(value, builtins.list):
                for index in range(len(value) - 1, -1, -1):
                    stack.append((value[index], "{}[{}]".format(path, index), depth + 1))
            elif isinstance(value, builtins.dict):
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise _ContractViolation(path, "JSON object key must be a string")
                    if len(key) > MAX_GENERIC_STRING_LENGTH:
                        raise _ContractViolation(path, "object key exceeds length limit")
                    stack.append((item, "{}.{}".format(path, key), depth + 1))

    def _expect(condition, path, message):
        if not condition:
            raise _ContractViolation(path, message)

    class _ContractViolation(Exception):
        def __init__(self, path, message, code="contract_violation"):
            Exception.__init__(self, message)
            self.path = path
            self.code = code

    def _validate_metadata(value, path):
        _expect(isinstance(value, builtins.dict), path, "metadata must be an object")

    def _validate_ui(value, path="ui"):
        _expect(isinstance(value, builtins.dict), path, "ui must be an object")
        unknown = set(value.keys()) - _UI_FIELDS
        if unknown:
            raise _ContractViolation(path + "." + sorted(unknown)[0], "unknown ui field")
        for field, identifier in value.items():
            _expect(
                isinstance(identifier, str)
                and len(identifier) <= MAX_UI_IDENTIFIER_LENGTH
                and _UI_IDENTIFIER_PATTERN.fullmatch(identifier) is not None,
                path + "." + field,
                field + " must be a lowercase bounded identifier",
            )

    def _require_image(target, path):
        _expect(isinstance(target, str) and 0 < len(target) <= MAX_IDENTIFIER_LENGTH, path, "target must be a non-empty bounded string")
        if not renpy.has_image(target, exact=True):
            raise _ContractViolation(path, "image is not declared: " + target, "missing_resource")

    def _validate_action(action, index, characters):
        path = "dialogue[{}]".format(index)
        _expect(isinstance(action, builtins.dict), path, "action must be an object")
        action_type = action.get("type")
        _expect(isinstance(action_type, str) and action_type != "", path + ".type", "type must be a non-empty string")
        if action_type not in _ACTION_FIELDS:
            raise _ContractViolation(path + ".type", "unsupported action: " + action_type, "unsupported_action")
        unknown = set(action.keys()) - _ACTION_FIELDS[action_type]
        if unknown:
            raise _ContractViolation(path + "." + sorted(unknown)[0], "unknown action field")
        if "metadata" in action:
            _validate_metadata(action["metadata"], path + ".metadata")

        if action_type == "scene":
            _expect("target" in action, path + ".target", "scene target is required")
            _require_image(action["target"], path + ".target")
        elif action_type == "show":
            _expect("target" in action, path + ".target", "show target is required")
            _require_image(action["target"], path + ".target")
            if "transform" in action:
                transform = action["transform"]
                _expect(isinstance(transform, builtins.dict), path + ".transform", "transform must be an object")
                allowed = set(["slot", "xalign", "yalign", "alpha", "flip"])
                unknown_transform = set(transform.keys()) - allowed
                if unknown_transform:
                    raise _ContractViolation(path + ".transform." + sorted(unknown_transform)[0], "unknown transform field")
                _expect(not ("slot" in transform and "xalign" in transform),
                        path + ".transform", "slot and xalign are mutually exclusive")
                if "slot" in transform:
                    _expect(isinstance(transform["slot"], str) and transform["slot"] in _CHARACTER_SLOTS,
                            path + ".transform.slot", "slot must be a supported character slot")
                for field in ("xalign", "yalign", "alpha"):
                    if field in transform:
                        _expect(_is_number(transform[field]), path + ".transform." + field, field + " must be finite numeric")
                if "flip" in transform:
                    _expect(isinstance(transform["flip"], bool), path + ".transform.flip", "flip must be bool")
        elif action_type == "line":
            _expect(isinstance(action.get("speaker"), str) and 0 < len(action["speaker"]) <= MAX_IDENTIFIER_LENGTH and action["speaker"] in characters,
                    path + ".speaker", "speaker must name a declared character")
            _expect(isinstance(action.get("text"), str) and len(action["text"]) <= MAX_LINE_TEXT_LENGTH,
                    path + ".text", "text must be a bounded string")
        elif action_type == "pause":
            duration = action.get("duration")
            _expect(_is_number(duration) and 0 <= duration <= 60, path + ".duration", "duration must be finite and in 0..60")
        elif action_type == "transition":
            _expect(action.get("effect") in ("fade", "dissolve"), path + ".effect", "effect must be fade or dissolve")
        elif action_type == "animate":
            _expect("target" in action, path + ".target", "animate target is required")
            _require_image(action["target"], path + ".target")
            effect = action.get("effect")
            _expect(isinstance(effect, builtins.dict), path + ".effect", "effect must be an object")
            allowed = set(["type", "xoffset", "duration", "repeat"])
            unknown_effect = set(effect.keys()) - allowed
            if unknown_effect:
                raise _ContractViolation(path + ".effect." + sorted(unknown_effect)[0], "unknown effect field")
            _expect(effect.get("type") == "shake", path + ".effect.type", "only shake animation is supported")
            if "xoffset" in effect:
                _expect(_is_number(effect["xoffset"]) and 1 <= effect["xoffset"] <= 200,
                        path + ".effect.xoffset", "xoffset must be in 1..200")
            if "duration" in effect:
                _expect(_is_number(effect["duration"]) and 0 < effect["duration"] <= 2,
                        path + ".effect.duration", "duration must be in (0..2]")
            if "repeat" in effect:
                repeat = effect["repeat"]
                _expect(not isinstance(repeat, bool) and isinstance(repeat, int) and 1 <= repeat <= 20,
                        path + ".effect.repeat", "repeat must be an integer in 1..20")
        elif action_type == "jump":
            target = action.get("target")
            _expect(isinstance(target, str) and 0 < len(target) <= MAX_IDENTIFIER_LENGTH, path + ".target", "jump target is required")
            allowed_targets = set(PRODUCTION_JSON_JUMP_TARGETS)
            if renpy.game.args.command == "test":
                allowed_targets.update(TEST_JSON_JUMP_TARGETS)
            _expect(target in allowed_targets, path + ".target", "jump target is not approved")
            if not renpy.has_label(target):
                raise _ContractViolation(path + ".target", "approved label is not declared: " + target, "missing_resource")

    def _migrate_v0(raw, expected_scene_id):
        _expect(isinstance(raw, builtins.dict), "$", "root must be an object")
        allowed = set(["id", "scene", "characters", "dialogue", "name", "metadata", "ui", "test_probe"])
        unknown = set(raw.keys()) - allowed
        if unknown:
            raise _ContractViolation("$." + sorted(unknown)[0], "unknown v0 root field")
        scene_id = raw.get("id") or expected_scene_id
        _expect(isinstance(scene_id, str) and 0 < len(scene_id) <= MAX_IDENTIFIER_LENGTH, "scene_id", "legacy scene needs id or expected_scene_id")
        _expect(isinstance(raw.get("characters", {}), builtins.dict), "characters", "legacy characters must be an object")
        _expect(isinstance(raw.get("dialogue", []), builtins.list), "dialogue", "legacy dialogue must be an array")
        if "metadata" in raw:
            _validate_metadata(raw["metadata"], "metadata")
        migrated = {
            "schema_version": SCENE_SCHEMA_VERSION,
            "scene_id": scene_id,
            "characters": raw.get("characters", {}),
            "dialogue": copy.deepcopy(raw.get("dialogue", [])),
        }
        if "name" in raw:
            migrated["name"] = raw["name"]
        if "ui" in raw:
            migrated["ui"] = copy.deepcopy(raw["ui"])
        metadata = copy.deepcopy(raw.get("metadata", {}))
        if "test_probe" in raw:
            metadata["test_probe"] = raw["test_probe"]
        if metadata:
            migrated["metadata"] = metadata
        if "scene" in raw:
            migrated["dialogue"].insert(0, {"type": "scene", "target": raw["scene"]})
        for action in migrated["dialogue"]:
            if not isinstance(action, builtins.dict):
                continue
            # v0 probes lived alongside the action fields. v1 reserves that
            # namespace for the action contract, so move them before strict
            # validation while preserving all existing metadata.
            if "test_probe" in action:
                metadata = copy.deepcopy(action.get("metadata", {}))
                metadata["test_probe"] = action.pop("test_probe")
                action["metadata"] = metadata
            if action.get("type") == "animate" and action.get("effect") == "shake":
                action["effect"] = {"type": "shake"}
        return migrated

    def _validate_v1(snapshot, expected_scene_id):
        _expect(isinstance(snapshot, builtins.dict), "$", "root must be an object")
        unknown = set(snapshot.keys()) - _ROOT_FIELDS
        if unknown:
            raise _ContractViolation("$." + sorted(unknown)[0], "unknown root field")
        for field in ("schema_version", "scene_id", "characters", "dialogue"):
            _expect(field in snapshot, field, "required root field is missing")
        _expect(not isinstance(snapshot["schema_version"], bool) and isinstance(snapshot["schema_version"], int)
                and snapshot["schema_version"] == SCENE_SCHEMA_VERSION,
                "schema_version", "schema version must be integer 1")
        _expect(isinstance(snapshot["scene_id"], str) and 0 < len(snapshot["scene_id"]) <= MAX_IDENTIFIER_LENGTH, "scene_id", "scene_id must be a non-empty bounded string")
        if expected_scene_id is not None:
            _expect(snapshot["scene_id"] == expected_scene_id, "scene_id", "scene_id does not match expected_scene_id")
        _expect(isinstance(snapshot["characters"], builtins.dict), "characters", "characters must be an object")
        _expect(len(snapshot["characters"]) <= MAX_CHARACTERS, "characters", "character count exceeds limit")
        for key, value in snapshot["characters"].items():
            _expect(isinstance(key, str) and 0 < len(key) <= MAX_IDENTIFIER_LENGTH, "characters", "character key must be non-empty and bounded")
            _expect(isinstance(value, str) and 0 < len(value) <= MAX_IDENTIFIER_LENGTH, "characters." + key, "character name must be non-empty and bounded")
        _expect(isinstance(snapshot["dialogue"], builtins.list), "dialogue", "dialogue must be an array")
        _expect(len(snapshot["dialogue"]) <= MAX_DIALOGUE_ACTIONS, "dialogue", "dialogue action count exceeds limit")
        if "name" in snapshot:
            _expect(isinstance(snapshot["name"], str), "name", "name must be a string")
        if "metadata" in snapshot:
            _validate_metadata(snapshot["metadata"], "metadata")
        if "ui" in snapshot:
            _validate_ui(snapshot["ui"])
        for index, action in enumerate(snapshot["dialogue"]):
            _validate_action(action, index, snapshot["characters"])

    def compute_scene_hash(snapshot):
        canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def prepare_playback_bytes(raw_bytes, source="<memory>", expected_scene_id=None):
        """Prepare bounded UTF-8 JSON bytes; exposed for native contract tests."""
        if not isinstance(raw_bytes, bytes):
            return _contract_error("scene_read_error", source, "scene source is not bytes")
        if len(raw_bytes) > MAX_SCENE_RAW_BYTES:
            return _contract_error("contract_violation", "$", "scene exceeds raw byte limit")
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            return _contract_error("scene_read_error", source, str(error))
        try:
            raw = json.loads(raw_text, object_pairs_hook=_duplicate_key_object)
        except RecursionError as error:
            return _contract_error("contract_violation", "$", "scene nesting exceeds parser limit: " + str(error))
        except ValueError as error:
            text = str(error)
            if text.startswith("duplicate_json_key:"):
                return _contract_error("duplicate_json_key", text.split(":", 1)[1], text)
            return _contract_error("invalid_json", "$", text)

        try:
            _scan_json_limits(raw)
        except _ContractViolation as error:
            return _contract_error(error.code, error.path, str(error))

        version = None
        try:
            if not isinstance(raw, builtins.dict):
                raise _ContractViolation("$", "root must be an object")
            version = raw.get("schema_version")
            migrated_from_schema = None
            if version is None:
                raw = _migrate_v0(raw, expected_scene_id)
                migrated_from_schema = 0
            elif isinstance(version, bool) or not isinstance(version, int):
                raise _ContractViolation("schema_version", "schema version must be an integer")
            elif version != SCENE_SCHEMA_VERSION:
                raise _ContractViolation("schema_version", "unsupported schema version", "unsupported_schema_version")
            _validate_v1(raw, expected_scene_id)
            return PlaybackState(
                scene_id=raw["scene_id"],
                schema_version=SCENE_SCHEMA_VERSION,
                content_hash=compute_scene_hash(raw),
                snapshot=raw,
                phase="ready",
                migrated_from_schema=migrated_from_schema,
            )
        except _ContractViolation as error:
            return _contract_error(error.code, error.path, str(error),
                                   scene_id=raw.get("scene_id") if isinstance(raw, builtins.dict) else None,
                                   schema_version=raw.get("schema_version") if isinstance(raw, builtins.dict) else None,
                                   snapshot=raw if isinstance(raw, builtins.dict) else None,
                                   migrated_from_schema=0 if version is None else None)
        except (TypeError, ValueError) as error:
            return _contract_error("contract_violation", "$", str(error))

    def prepare_playback(relative_path, expected_scene_id=None):
        """Load, normalize and validate a scene without executing any action."""
        try:
            with renpy.open_file(relative_path, encoding=False) as scene_file:
                raw_bytes = scene_file.read(MAX_SCENE_RAW_BYTES + 1)
        except (IOError, OSError) as error:
            return _contract_error("scene_not_found", relative_path, str(error))
        except Exception as error:
            return _contract_error("scene_read_error", relative_path, str(error))
        return prepare_playback_bytes(raw_bytes, source=relative_path, expected_scene_id=expected_scene_id)

    def verify_playback_state(state):
        if not isinstance(state, PlaybackState):
            return PlaybackError("state_integrity_error", "state", "not a PlaybackState")
        if state.phase not in ("ready", "playing", "completed", "error"):
            return PlaybackError("state_integrity_error", "phase", "unsupported state phase")
        if isinstance(state.state_version, bool) or not isinstance(state.state_version, int) or state.state_version != 2:
            return PlaybackError("state_integrity_error", "state_version", "unsupported state version")
        if state.phase == "error":
            if state.scene_id is not None and not isinstance(state.scene_id, str):
                return PlaybackError("state_integrity_error", "scene_id", "error state scene_id must be string or None")
            if state.schema_version is not None and (isinstance(state.schema_version, bool) or not isinstance(state.schema_version, int)):
                return PlaybackError("state_integrity_error", "schema_version", "error state schema_version must be integer or None")
            if state.snapshot is not None:
                invalid_snapshot = _first_non_json_value(state.snapshot, "snapshot")
                if invalid_snapshot is not None:
                    return PlaybackError("state_integrity_error", invalid_snapshot, "error state snapshot must be JSON-save-safe")
            if not isinstance(state.last_error, PlaybackError):
                return PlaybackError("state_integrity_error", "last_error", "error state requires PlaybackError")
            if not all(isinstance(value, str) for value in (state.last_error.code, state.last_error.path, state.last_error.message)):
                return PlaybackError("state_integrity_error", "last_error", "error details must be strings")
            # Contract/read failures have no trusted hash. Runtime failures do,
            # and retain the verified snapshot plus the cursor of the action
            # that failed so save/load can diagnose the exact boundary.
            if state.content_hash is None:
                return None
        if isinstance(state.schema_version, bool) or not isinstance(state.schema_version, int) or state.schema_version != SCENE_SCHEMA_VERSION:
            return PlaybackError("state_integrity_error", "schema_version", "invalid state schema version")
        if state.phase != "error" and state.last_error is not None:
            return PlaybackError("state_integrity_error", "last_error", "non-error state cannot contain an error")
        if isinstance(state.step_index, bool) or not isinstance(state.step_index, int) or state.step_index < 0:
            return PlaybackError("state_integrity_error", "step_index", "invalid step index")
        if not isinstance(state.scene_variables, builtins.dict):
            return PlaybackError("state_integrity_error", "scene_variables", "scene variables must be an object")
        invalid_variables = _first_non_json_value(state.scene_variables, "scene_variables")
        if invalid_variables is not None:
            return PlaybackError("state_integrity_error", invalid_variables, "scene variables must be JSON-save-safe")
        if not isinstance(state.branch_trace, builtins.list):
            return PlaybackError("state_integrity_error", "branch_trace", "branch trace must be an array")
        invalid_trace = _first_non_json_value(state.branch_trace, "branch_trace")
        if invalid_trace is not None:
            return PlaybackError("state_integrity_error", invalid_trace, "branch trace must be JSON-save-safe")
        snapshot = state.snapshot
        try:
            _validate_v1(snapshot, state.scene_id)
        except _ContractViolation as error:
            return PlaybackError("state_integrity_error", error.path, str(error))
        if state.step_index > len(snapshot["dialogue"]):
            return PlaybackError("state_integrity_error", "step_index", "step index exceeds dialogue length")
        if state.phase == "ready" and state.step_index != 0:
            return PlaybackError("state_integrity_error", "step_index", "ready state must start at step zero")
        if state.phase == "playing" and state.step_index >= len(snapshot["dialogue"]):
            return PlaybackError("state_integrity_error", "step_index", "playing state requires a current action")
        if state.phase == "completed" and state.step_index < len(snapshot["dialogue"]):
            if state.step_index == 0 or snapshot["dialogue"][state.step_index - 1].get("type") not in ("return", "jump"):
                return PlaybackError("state_integrity_error", "step_index", "early completed state requires return or jump")
        if state.content_hash != compute_scene_hash(snapshot):
            return PlaybackError("state_integrity_error", "content_hash", "snapshot hash mismatch")
        return None

    def _first_non_json_value(value, path):
        """Return the first non-JSON/save-safe path, or None for inert data."""
        if value is None or isinstance(value, (str, bool, int)):
            return None
        if isinstance(value, float):
            return None if math.isfinite(value) else path
        if isinstance(value, builtins.list):
            for index, item in enumerate(value):
                invalid = _first_non_json_value(item, "{}[{}]".format(path, index))
                if invalid is not None:
                    return invalid
            return None
        if isinstance(value, builtins.dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    return path
                invalid = _first_non_json_value(item, "{}.{}".format(path, key))
                if invalid is not None:
                    return invalid
            return None
        return path
