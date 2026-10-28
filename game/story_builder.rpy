default persistent.ai_novel_story_draft = None
default story_launch_payload = None

init -65 python:
    import copy

    STORY_DRAFT_VERSION = 1
    STORY_WISHES_MAX = 4000
    STORY_SHORT_TEXT_MAX = 256

    STORY_GENRES = (
        ("adventure", "Приключения"),
        ("drama", "Драма"),
        ("fantasy", "Фэнтези"),
        ("science_fiction", "Научная фантастика"),
        ("mystery", "Мистика"),
        ("romance", "Романтика"),
        ("slice_of_life", "Повседневность"),
        ("horror", "Хоррор"),
    )
    STORY_TONES = (
        ("light", "Лёгкий"),
        ("balanced", "Сбалансированный"),
        ("melancholic", "Меланхоличный"),
        ("tense", "Напряжённый"),
        ("hopeful", "Обнадёживающий"),
    )
    STORY_LENGTHS = (
        ("short", "Короткая"),
        ("medium", "Средняя"),
        ("long", "Длинная"),
    )
    STORY_PACING = (
        ("dynamic", "Динамичный"),
        ("measured", "Размеренный"),
        ("slow_burn", "Медленное развитие"),
    )

    def _story_ids(options):
        return tuple(item[0] for item in options)

    def _story_draft_default(mode="basic"):
        return {
            "version": STORY_DRAFT_VERSION,
            "mode": mode if mode in ("basic", "advanced") else "basic",
            "genres": [],
            "wishes": "",
            "tone": "",
            "setting": "",
            "length": "",
            "pacing": "",
            "title_seed": "",
            "cast_asset_ids": [],
            "ui": {
                "theme_id": "",
                "palette_id": "",
                "font_pack_id": "",
            },
        }

    def _bounded_story_text(value, maximum):
        return value[:maximum] if isinstance(value, str) else ""

    def _story_draft_sanitize(value):
        result = _story_draft_default()
        if not isinstance(value, dict) or value.get("version") != STORY_DRAFT_VERSION:
            return result
        mode = value.get("mode")
        result["mode"] = mode if mode in ("basic", "advanced") else "basic"
        genres = value.get("genres")
        if isinstance(genres, (list, tuple)):
            allowed = _story_ids(STORY_GENRES)
            result["genres"] = [g for g in allowed if g in genres]
        result["wishes"] = _bounded_story_text(value.get("wishes"), STORY_WISHES_MAX)
        for field, allowed in (
                ("tone", _story_ids(STORY_TONES)),
                ("length", _story_ids(STORY_LENGTHS)),
                ("pacing", _story_ids(STORY_PACING))):
            candidate = value.get(field)
            result[field] = candidate if candidate in allowed else ""
        result["setting"] = _bounded_story_text(value.get("setting"), STORY_WISHES_MAX)
        result["title_seed"] = _bounded_story_text(value.get("title_seed"), STORY_SHORT_TEXT_MAX)
        cast_ids = value.get("cast_asset_ids")
        if isinstance(cast_ids, (list, tuple)):
            allowed_cast = tuple(
                item["id"] for item in asset_catalog_entries("characters", enabled_only=True)
            )
            result["cast_asset_ids"] = [asset_id for asset_id in allowed_cast if asset_id in cast_ids]
        ui_value = value.get("ui")
        if isinstance(ui_value, dict):
            for field in ("theme_id", "palette_id", "font_pack_id"):
                candidate = ui_value.get(field)
                if isinstance(candidate, str):
                    result["ui"][field] = candidate[:64]
        return result

    def story_draft_get():
        clean = _story_draft_sanitize(getattr(persistent, "ai_novel_story_draft", None))
        persistent.ai_novel_story_draft = clean
        return clean

    @renpy.pure
    class StoryDraftInputValue(InputValue, FieldEquality):
        """Stable InputValue identity across story-builder screen rebuilds."""

        equality_fields = ("field", "default", "returnable")

        def __init__(self, field, default=True, returnable=False):
            self.field = field
            self.default = default
            self.returnable = returnable

        def get_text(self):
            value = story_draft_get().get(self.field, "")
            return value if isinstance(value, str) else ""

        def set_text(self, value):
            story_draft_set(self.field, value)
            renpy.restart_interaction()

    def story_draft_reset(mode="basic"):
        persistent.ai_novel_story_draft = _story_draft_default(mode)
        renpy.restart_interaction()
        return persistent.ai_novel_story_draft

    def story_draft_set_mode(mode):
        draft = story_draft_get()
        draft["mode"] = mode if mode in ("basic", "advanced") else "basic"
        persistent.ai_novel_story_draft = draft
        renpy.restart_interaction()
        return draft["mode"]

    def story_draft_toggle_genre(genre_id):
        if genre_id not in _story_ids(STORY_GENRES):
            return False
        draft = story_draft_get()
        if genre_id in draft["genres"]:
            draft["genres"].remove(genre_id)
        else:
            draft["genres"].append(genre_id)
            draft["genres"] = [g for g in _story_ids(STORY_GENRES) if g in draft["genres"]]
        persistent.ai_novel_story_draft = draft
        renpy.restart_interaction()
        return genre_id in draft["genres"]

    def story_draft_set(field, value):
        draft = story_draft_get()
        if field == "wishes":
            draft[field] = _bounded_story_text(value, STORY_WISHES_MAX)
        elif field in ("setting",):
            draft[field] = _bounded_story_text(value, STORY_WISHES_MAX)
        elif field == "title_seed":
            draft[field] = _bounded_story_text(value, STORY_SHORT_TEXT_MAX)
        elif field == "tone":
            draft[field] = value if value in _story_ids(STORY_TONES) else ""
        elif field == "length":
            draft[field] = value if value in _story_ids(STORY_LENGTHS) else ""
        elif field == "pacing":
            draft[field] = value if value in _story_ids(STORY_PACING) else ""
        else:
            return False
        persistent.ai_novel_story_draft = draft
        return True

    def story_draft_toggle_cast(asset_id):
        asset = asset_catalog_get(asset_id)
        if asset is None or asset["category"] != "characters":
            return False
        draft = story_draft_get()
        if asset_id in draft["cast_asset_ids"]:
            draft["cast_asset_ids"].remove(asset_id)
        else:
            draft["cast_asset_ids"].append(asset_id)
        persistent.ai_novel_story_draft = draft
        renpy.restart_interaction()
        return asset_id in draft["cast_asset_ids"]

    def story_draft_set_ui(theme_id="", palette_id="", font_pack_id=""):
        draft = story_draft_get()
        values = (theme_id, palette_id, font_pack_id)
        if not all(isinstance(value, str) and len(value) <= 64 for value in values):
            return False
        draft["ui"] = {
            "theme_id": theme_id,
            "palette_id": palette_id,
            "font_pack_id": font_pack_id,
        }
        persistent.ai_novel_story_draft = draft
        renpy.restart_interaction()
        return True

    def story_draft_validate(draft=None):
        value = _story_draft_sanitize(story_draft_get() if draft is None else draft)
        if not value["genres"] and not value["wishes"].strip():
            return ["story_request_empty"]
        return []

    def story_draft_export_payload(draft=None):
        value = _story_draft_sanitize(story_draft_get() if draft is None else draft)
        story_request = {
            "version": STORY_DRAFT_VERSION,
            "mode": value["mode"],
            "genres": list(value["genres"]),
            "wishes": value["wishes"].strip(),
            "assets": asset_catalog_export_selection(),
        }
        if value["mode"] == "advanced":
            for field in ("tone", "setting", "length", "pacing", "title_seed"):
                if value[field]:
                    story_request[field] = value[field].strip() if isinstance(value[field], str) else value[field]
            if value["cast_asset_ids"]:
                story_request["cast_asset_ids"] = list(value["cast_asset_ids"])
        payload = {"story_request": story_request}
        ui_value = {key: item for key, item in value["ui"].items() if item}
        if ui_value:
            payload["ui"] = ui_value
        return copy.deepcopy(payload)

    def story_builder_commit():
        if story_draft_validate():
            return False
        renpy.store.story_launch_payload = story_draft_export_payload()
        return True
