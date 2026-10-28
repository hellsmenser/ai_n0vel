default story_metadata = None


init -45 python:
    import builtins
    import copy
    import json
    import re

    STORY_METADATA_SCHEMA_VERSION = 1
    STORY_METADATA_MAX_CAST = 64
    STORY_METADATA_MAX_IDENTIFIER = 256
    STORY_METADATA_MAX_TITLE = 256
    STORY_METADATA_MAX_SYNOPSIS = 4000
    STORY_METADATA_MAX_UI_IDENTIFIER = 64
    STORY_METADATA_MAX_RAW_BYTES = 128 * 1024
    _STORY_METADATA_FIELDS = set([
        "schema_version", "story_id", "title", "synopsis", "cast", "ui",
    ])
    _STORY_CAST_FIELDS = set([
        "character_id", "display_name", "asset_id",
    ])
    _STORY_UI_FIELDS = set(["theme_id", "palette_id", "font_pack_id"])
    _STORY_UI_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[_-][a-z0-9]+)*$")


    class StoryMetadataError(Exception):
        def __init__(self, path, message):
            Exception.__init__(self, message)
            self.path = str(path)
            self.message = str(message)


    def _story_expect(condition, path, message):
        if not condition:
            raise StoryMetadataError(path, message)


    def _story_duplicate_key_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise StoryMetadataError("$", "duplicate metadata key: " + str(key))
            result[key] = value
        return result


    def validate_story_metadata(value):
        _story_expect(isinstance(value, builtins.dict), "$", "metadata root must be an object")
        unknown = set(value.keys()) - _STORY_METADATA_FIELDS
        _story_expect(not unknown, "$." + sorted(unknown)[0] if unknown else "$", "unknown metadata field")
        _story_expect(value.get("schema_version") == STORY_METADATA_SCHEMA_VERSION
                      and not isinstance(value.get("schema_version"), bool),
                      "$.schema_version", "unsupported metadata schema version")

        story_id = value.get("story_id")
        _story_expect(isinstance(story_id, str) and 0 < len(story_id) <= STORY_METADATA_MAX_IDENTIFIER,
                      "$.story_id", "story_id must be a non-empty bounded string")
        title = value.get("title")
        _story_expect(isinstance(title, str) and 0 < len(title) <= STORY_METADATA_MAX_TITLE,
                      "$.title", "title must be a non-empty bounded string")
        synopsis = value.get("synopsis")
        _story_expect(isinstance(synopsis, str) and len(synopsis) <= STORY_METADATA_MAX_SYNOPSIS,
                      "$.synopsis", "synopsis must be a bounded string")

        cast = value.get("cast")
        _story_expect(isinstance(cast, builtins.list) and 1 <= len(cast) <= STORY_METADATA_MAX_CAST,
                      "$.cast", "cast must be a non-empty bounded array")
        seen_ids = set()
        for index, member in enumerate(cast):
            path = "$.cast[{}]".format(index)
            _story_expect(isinstance(member, builtins.dict), path, "cast member must be an object")
            unknown_member = set(member.keys()) - _STORY_CAST_FIELDS
            _story_expect(not unknown_member,
                          path + "." + sorted(unknown_member)[0] if unknown_member else path,
                          "unknown cast field")
            for field in _STORY_CAST_FIELDS:
                field_value = member.get(field)
                _story_expect(isinstance(field_value, str)
                              and 0 < len(field_value) <= STORY_METADATA_MAX_IDENTIFIER,
                              path + "." + field, field + " must be a non-empty bounded string")
            character_id = member["character_id"]
            _story_expect(character_id not in seen_ids, path + ".character_id", "duplicate character_id")
            seen_ids.add(character_id)

        ui = value.get("ui")
        if ui is not None:
            _story_expect(isinstance(ui, builtins.dict), "$.ui", "ui must be an object")
            unknown_ui = set(ui.keys()) - _STORY_UI_FIELDS
            _story_expect(not unknown_ui,
                          "$.ui." + sorted(unknown_ui)[0] if unknown_ui else "$.ui",
                          "unknown ui field")
            for field, identifier in ui.items():
                _story_expect(isinstance(identifier, str)
                              and len(identifier) <= STORY_METADATA_MAX_UI_IDENTIFIER
                              and _STORY_UI_IDENTIFIER.fullmatch(identifier) is not None,
                              "$.ui." + field, field + " must be a lowercase bounded identifier")
        return copy.deepcopy(value)


    def load_story_metadata_file(relative_path):
        with renpy.open_file(relative_path, encoding=False) as metadata_file:
            raw = metadata_file.read(STORY_METADATA_MAX_RAW_BYTES + 1)
        if len(raw) > STORY_METADATA_MAX_RAW_BYTES:
            raise StoryMetadataError("$", "metadata exceeds byte limit")
        try:
            decoded = raw.decode("utf-8-sig")
            value = json.loads(decoded, object_pairs_hook=_story_duplicate_key_object)
        except StoryMetadataError:
            raise
        except Exception as error:
            raise StoryMetadataError("$", "metadata JSON could not be decoded: " + error.__class__.__name__)
        return validate_story_metadata(value)


    def apply_story_metadata(value):
        trusted = validate_story_metadata(value)
        renpy.store.story_metadata = trusted
        return trusted


    def verify_story_metadata(value):
        try:
            validate_story_metadata(value)
        except StoryMetadataError as error:
            return error
        return None
