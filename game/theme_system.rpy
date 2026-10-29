################################################################################
## Runtime UI themes
################################################################################

default persistent.ai_novel_theme_preference = "auto"

define config.game_menu_action = ShowMenu("pause_menu")

init -2 python:

    import colorsys
    import hashlib

    THEME_IDS = (
        "default",
        "modern_muted",
        "literary",
        "romantic",
        "lovecraft_biopunk",
        "high_fantasy",
        "science_fiction",
    )
    THEME_PREFERENCE_IDS = ("auto",) + THEME_IDS

    THEME_ASSET_NAMES = (
        "dialogue_frame.png",
        "namebox_frame.png",
        "choice_idle.png",
        "choice_hover.png",
        "pause_history_frame.png",
        "pause_menu_frame.png",
        "nav_idle.png",
        "nav_hover.png",
        "scrollbar_track.png",
        "scrollbar_thumb.png",
    )

    _THEME_BASE = {
        "default": {
            "label": "Default",
            "default_palette_id": "default",
            "palette_ids": ("default", "graphite_sage", "warm_parchment", "muted_blue", "subdued_plum"),
            "default_font_pack_id": "interface",
            "font_pack_ids": ("interface",),
            "colors": {"panel": "#182129E8", "panel_alt": "#202C35EE", "border": "#78909CAA", "text": "#F1F4F5FF", "muted": "#B6C1C6FF", "accent": "#5FB7B0FF", "hover": "#2D434CEB", "heading_text": "#F1F4F5FF", "overlay_text": "#F1F4F5FF", "button_hover_text": "#F1F4F5FF", "veil": "#080B0DC4"},
        },
        "modern_muted": {
            "label": "Modern Muted",
            "default_palette_id": "stone",
            "palette_ids": ("stone",),
            "default_font_pack_id": "editorial_sans",
            "font_pack_ids": ("editorial_sans",),
            "colors": {"panel": "#C9C2B5E8", "panel_alt": "#B4B1A9EE", "border": "#625F5AA8", "text": "#292B2BFF", "muted": "#555B5AFF", "accent": "#607B78FF", "hover": "#D9D2C5F2", "heading_text": "#292B2BFF", "overlay_text": "#F1F4F5FF", "button_hover_text": "#292B2BFF", "veil": "#171817B8"},
        },
        "literary": {
            "label": "Literary",
            "default_palette_id": "sepia",
            "palette_ids": ("sepia",),
            "default_font_pack_id": "literary_serif",
            "font_pack_ids": ("literary_serif",),
            "colors": {"panel": "#261B17F0", "panel_alt": "#35241DF2", "border": "#A47B49CC", "text": "#F1E5CCFF", "muted": "#C8B99EFF", "accent": "#C39A62FF", "hover": "#493326F2", "heading_text": "#F1E5CCFF", "overlay_text": "#F1E5CCFF", "button_hover_text": "#F1E5CCFF", "veil": "#100B09C7"},
        },
        "romantic": {
            "label": "Romantic",
            "default_palette_id": "rose",
            "palette_ids": ("rose",),
            "default_font_pack_id": "romantic_serif",
            "font_pack_ids": ("romantic_serif",),
            "colors": {"panel": "#F1E5DDEB", "panel_alt": "#E8D4D0F0", "border": "#8D596EB8", "text": "#3D2733FF", "muted": "#725464FF", "accent": "#A65E79FF", "hover": "#F6E9E2F4", "heading_text": "#3D2733FF", "overlay_text": "#FFF6FAFF", "button_hover_text": "#3D2733FF", "veil": "#1D1118B8"},
        },
        "lovecraft_biopunk": {
            "label": "Lovecraft Biopunk",
            "default_palette_id": "abyssal",
            "palette_ids": ("abyssal",),
            "default_font_pack_id": "organic_serif",
            "font_pack_ids": ("organic_serif",),
            "colors": {"panel": "#091B1CF2", "panel_alt": "#12272AF2", "border": "#55766FB8", "text": "#D7DFD5FF", "muted": "#8FA69CFF", "accent": "#72A69AFF", "hover": "#173638F2", "heading_text": "#D7DFD5FF", "overlay_text": "#D7DFD5FF", "button_hover_text": "#D7DFD5FF", "veil": "#020809D1"},
        },
        "high_fantasy": {
            "label": "High Fantasy",
            "default_palette_id": "midnight_silver",
            "palette_ids": ("midnight_silver",),
            "default_font_pack_id": "fantasy_serif",
            "font_pack_ids": ("fantasy_serif",),
            "colors": {"panel": "#0E1A35F0", "panel_alt": "#172747F2", "border": "#AAB7CEE0", "text": "#EDF1F8FF", "muted": "#B7C1D4FF", "accent": "#7FA6E4FF", "hover": "#213967F2", "heading_text": "#EDF1F8FF", "overlay_text": "#EDF1F8FF", "button_hover_text": "#EDF1F8FF", "veil": "#050914C9"},
        },
        "science_fiction": {
            "label": "Science Fiction",
            "default_palette_id": "cyan_violet",
            "palette_ids": ("cyan_violet",),
            "default_font_pack_id": "scifi_sans",
            "font_pack_ids": ("scifi_sans",),
            "colors": {"panel": "#10151DF2", "panel_alt": "#171E28F2", "border": "#3E6178CC", "text": "#E6F5F7FF", "muted": "#91AEB7FF", "accent": "#4BD5E8FF", "hover": "#1C2D3AF2", "heading_text": "#E6F5F7FF", "overlay_text": "#E6F5F7FF", "button_hover_text": "#E6F5F7FF", "veil": "#03070BCB"},
        },
    }

    THEME_REGISTRY = dict((theme_id, dict(value)) for theme_id, value in _THEME_BASE.items())

    # Generated package contract mirrored from tools/generate_theme_assets.py.
    # A native test compares this table against all checked-in manifests.
    THEME_ASSET_SLICES = {
        "dialogue_frame": (160, 60, 160, 60),
        "namebox_frame": (80, 28, 80, 28),
        "choice_idle": (150, 36, 150, 36),
        "choice_hover": (150, 36, 150, 36),
        "pause_history_frame": (180, 80, 180, 80),
        "pause_menu_frame": (180, 80, 180, 80),
        "nav_idle": (80, 28, 80, 28),
        "nav_hover": (80, 28, 80, 28),
        "scrollbar_track": (8, 18, 8, 18),
        "scrollbar_thumb": (8, 18, 8, 18),
    }

    THEME_FONT_CANDIDATES = {
        "interface": {
            "interface": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
            "dialogue": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
            "name": ("gui/themes/fonts/fira_sans/FiraSans-Bold.ttf",),
            "history": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
        },
        "editorial_sans": {
            "interface": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
            "dialogue": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
            "name": ("gui/themes/fonts/fira_sans/FiraSans-Bold.ttf",),
            "history": ("gui/themes/fonts/fira_sans/FiraSans-Regular.ttf",),
        },
        "literary_serif": {
            "interface": ("gui/themes/fonts/pt_serif/PTSerif-Bold.ttf",),
            "dialogue": ("gui/themes/fonts/pt_serif/PTSerif-Regular.ttf",),
            "name": ("gui/themes/fonts/pt_serif/PTSerif-Bold.ttf",),
            "history": ("gui/themes/fonts/pt_serif/PTSerif-Regular.ttf",),
        },
        "romantic_serif": {
            "interface": ("gui/themes/fonts/pt_serif/PTSerif-Regular.ttf",),
            "dialogue": ("gui/themes/fonts/pt_serif/PTSerif-Regular.ttf",),
            "name": ("gui/themes/fonts/pt_serif/PTSerif-Bold.ttf",),
            "history": ("gui/themes/fonts/pt_serif/PTSerif-Regular.ttf",),
        },
        "organic_serif": {
            "interface": ("gui/themes/fonts/philosopher/Philosopher-Regular.ttf",),
            "dialogue": ("gui/themes/fonts/philosopher/Philosopher-Regular.ttf",),
            "name": ("gui/themes/fonts/philosopher/Philosopher-Bold.ttf",),
            "history": ("gui/themes/fonts/philosopher/Philosopher-Regular.ttf",),
        },
        "fantasy_serif": {
            "interface": ("gui/themes/fonts/philosopher/Philosopher-Bold.ttf",),
            "dialogue": ("gui/themes/fonts/philosopher/Philosopher-Regular.ttf",),
            "name": ("gui/themes/fonts/philosopher/Philosopher-Bold.ttf",),
            "history": ("gui/themes/fonts/philosopher/Philosopher-Regular.ttf",),
        },
        "scifi_sans": {
            "interface": ("gui/themes/fonts/play/Play-Regular.ttf",),
            "dialogue": ("gui/themes/fonts/play/Play-Regular.ttf",),
            "name": ("gui/themes/fonts/play/Play-Bold.ttf",),
            "history": ("gui/themes/fonts/play/Play-Regular.ttf",),
        },
    }

    # Palette variants deliberately change runtime color tokens only. Structural
    # PNGs stay shared with the default pack, avoiding duplicated sprite sets.
    THEME_PALETTE_OVERRIDES = {
        ("default", "graphite_sage"): {"accent": "#7eb39f", "hover": "#b4d4c8", "button_hover_text": "#101419", "muted": "#aab8b1", "veil": "#0a0d0dde"},
        ("default", "warm_parchment"): {"text": "#f0e6d0", "accent": "#b99b6b", "hover": "#dec394", "button_hover_text": "#101419", "muted": "#b8aa91", "veil": "#100d09dc"},
        ("default", "muted_blue"): {"text": "#e6edf2", "accent": "#779db4", "hover": "#a8c3d2", "button_hover_text": "#101419", "muted": "#a4b0b9", "veil": "#080d13df"},
        ("default", "subdued_plum"): {"text": "#eee7ed", "accent": "#a583a0", "hover": "#c9abc4", "button_hover_text": "#101419", "muted": "#b3a4b0", "veil": "#100a10df"},
    }

    def _safe_theme_id(value):
        return value if isinstance(value, str) and value in THEME_REGISTRY else "default"

    def _safe_preference(value):
        return value if isinstance(value, str) and value in THEME_PREFERENCE_IDS else "auto"

    def _scene_ui(playback=None):
        state = playback if playback is not None else getattr(renpy.store, "playback_state", None)
        snapshot = getattr(state, "snapshot", None)
        if isinstance(snapshot, dict):
            ui = snapshot.get("ui", {})
            if isinstance(ui, dict):
                return ui
        metadata = getattr(renpy.store, "story_metadata", None)
        if not isinstance(metadata, dict):
            return {}
        ui = metadata.get("ui", {})
        return ui if isinstance(ui, dict) else {}

    def resolve_theme_selection(preference=None, playback=None):
        """Resolve a trusted runtime theme without making scene playback fail."""
        raw_preference = (getattr(persistent, "ai_novel_theme_preference", "auto")
                          if preference is None else preference)
        preference_id = _safe_preference(raw_preference)

        if raw_preference not in THEME_PREFERENCE_IDS:
            theme_id = "default"
            source = "fallback"
            scene_ui = {}
        elif preference_id != "auto":
            theme_id = preference_id
            source = "preference"
            scene_ui = {}
        else:
            scene_ui = _scene_ui(playback)
            requested_theme = scene_ui.get("theme_id", "default")
            theme_id = _safe_theme_id(requested_theme)
            source = "scene" if requested_theme in THEME_REGISTRY else "fallback"

        spec = THEME_REGISTRY[theme_id]
        palette_id = spec["default_palette_id"]
        font_pack_id = spec["default_font_pack_id"]
        if source == "scene":
            requested_palette = scene_ui.get("palette_id")
            requested_font = scene_ui.get("font_pack_id")
            if requested_palette in spec["palette_ids"]:
                palette_id = requested_palette
            if requested_font in spec["font_pack_ids"]:
                font_pack_id = requested_font

        return {
            "theme_id": theme_id,
            "palette_id": palette_id,
            "font_pack_id": font_pack_id,
            "source": source,
        }

    def set_theme_preference(value):
        persistent.ai_novel_theme_preference = _safe_preference(value)
        renpy.save_persistent()
        try:
            renpy.restart_interaction()
        except Exception:
            pass

    def _neutral_shell_active(neutral_shell=False):
        return bool(neutral_shell or getattr(renpy.store, "main_menu", False))

    def active_theme_id(neutral_shell=False):
        if _neutral_shell_active(neutral_shell):
            return "default"
        return resolve_theme_selection()["theme_id"]

    def _resolved_palette_id(selected, palette_id=None, neutral_shell=False):
        spec = THEME_REGISTRY[selected]
        if _neutral_shell_active(neutral_shell):
            return spec["default_palette_id"]
        if palette_id in spec["palette_ids"]:
            return palette_id
        if palette_id is None and not neutral_shell:
            resolved = resolve_theme_selection()
            if resolved["theme_id"] == selected:
                return resolved["palette_id"]
        return spec["default_palette_id"]

    def theme_color(role, theme_id=None, palette_id=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        palette_id = _resolved_palette_id(selected, palette_id=palette_id, neutral_shell=neutral_shell)
        palette = THEME_PALETTE_OVERRIDES.get((selected, palette_id), {})
        if role in palette:
            return palette[role]
        return THEME_REGISTRY[selected]["colors"].get(role, THEME_REGISTRY["default"]["colors"].get(role, "#ffffff"))

    def _theme_relative_luminance(color):
        value = str(color).lstrip("#")[:6]
        if len(value) != 6:
            return 0.0
        channels = []
        for index in (0, 2, 4):
            channel = int(value[index:index + 2], 16) / 255.0
            channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def _theme_contrast_ratio(foreground, background):
        first = _theme_relative_luminance(foreground)
        second = _theme_relative_luminance(background)
        return (max(first, second) + 0.05) / (min(first, second) + 0.05)

    def _trusted_story_cast_ids():
        metadata = getattr(renpy.store, "story_metadata", None)
        if not isinstance(metadata, dict) or verify_story_metadata(metadata) is not None:
            return None
        result = [member["character_id"] for member in metadata["cast"]]
        if "narrator" not in result:
            result.append("narrator")
        return tuple(result)

    def _speaker_color_index(speaker_id):
        identity = str(speaker_id or "narrator")
        cast_ids = _trusted_story_cast_ids()
        if cast_ids is not None and identity in cast_ids:
            return cast_ids.index(identity)
        return int(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12], 16)

    def _speaker_color_for_index(index, light_background):
        # The irrational hue step prevents repeated hues across the maximum
        # supported cast; alternating saturation/lightness keeps exact RGB
        # values collision-free after rounding.
        hue = (index * 0.38196601125) % 1.0
        saturation = (0.62, 0.72, 0.82)[index % 3]
        if light_background:
            lightness = (0.14, 0.17)[(index // 3) % 2]
        else:
            lightness = (0.82, 0.87)[(index // 3) % 2]
        red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
        return "#{:02X}{:02X}{:02X}".format(
            int(round(red * 255)),
            int(round(green * 255)),
            int(round(blue * 255)),
        )

    def speaker_name_color(speaker_id, theme_id=None, palette_id=None):
        """Return a cast-stable speaker accent readable on namebox_frame."""
        selected = active_theme_id() if theme_id is None else _safe_theme_id(theme_id)
        # generate_theme_assets.panel_shape uses the panel token for
        # namebox_frame; contrast must be checked against that actual fill.
        background = theme_color("panel", theme_id=selected, palette_id=palette_id)
        light_background = _theme_relative_luminance(background) > 0.35
        candidate = _speaker_color_for_index(_speaker_color_index(speaker_id), light_background)
        if _theme_contrast_ratio(candidate, background) >= 4.5:
            return candidate
        return "#101419" if light_background else "#FFFFFF"

    def ai_shell_hover_text_color():
        return theme_color("button_hover_text", theme_id="default", neutral_shell=True)

    def theme_palette_chrome_tint(theme_id=None, palette_id=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        selected_palette = _resolved_palette_id(selected, palette_id=palette_id, neutral_shell=neutral_shell)
        if selected != "default" or selected_palette == THEME_REGISTRY["default"]["default_palette_id"]:
            return None
        return theme_color("accent", theme_id=selected, palette_id=selected_palette, neutral_shell=neutral_shell)

    def theme_asset(name, theme_id=None, legacy=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        for candidate_theme in (selected, "default"):
            candidate = "gui/themes/{}/{}".format(candidate_theme, name)
            if renpy.loadable(candidate):
                return candidate
        if legacy and renpy.loadable(legacy):
            return legacy
        return legacy or "gui/frame.png"

    def theme_asset_slice(name, theme_id=None, fallback=(24, 24, 24, 24), neutral_shell=False):
        asset_id = name[:-4] if name.endswith(".png") else name
        return THEME_ASSET_SLICES.get(asset_id, tuple(fallback))

    def theme_frame(name, theme_id=None, legacy=None, fallback=(24, 24, 24, 24), neutral_shell=False, palette_id=None):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        path = theme_asset(name, theme_id=theme_id, legacy=legacy, neutral_shell=neutral_shell)
        borders = theme_asset_slice(name, theme_id=theme_id, fallback=fallback, neutral_shell=neutral_shell)
        framed = Frame(path, Borders(*borders))
        tint = theme_palette_chrome_tint(selected, palette_id=palette_id, neutral_shell=neutral_shell)
        if tint is not None:
            return Transform(framed, matrixcolor=ColorizeMatrix("#101419", tint))
        return framed

    def theme_font(role="body", theme_id=None, font_pack_id=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        spec = THEME_REGISTRY[selected]
        if _neutral_shell_active(neutral_shell):
            font_pack_id = spec["default_font_pack_id"]
        elif font_pack_id not in spec["font_pack_ids"]:
            if font_pack_id is None:
                resolved = resolve_theme_selection()
                if resolved["theme_id"] == selected:
                    font_pack_id = resolved["font_pack_id"]
            if font_pack_id not in spec["font_pack_ids"]:
                font_pack_id = spec["default_font_pack_id"]
        manifest_role = {"body": "dialogue", "title": "interface"}.get(role, role)
        candidates = THEME_FONT_CANDIDATES.get(font_pack_id, {}).get(manifest_role, ())
        for candidate in candidates:
            if renpy.loadable(candidate):
                return candidate
        if role in ("title", "name"):
            return gui.name_text_font
        return gui.text_font

    def theme_button_idle(theme_id=None, palette_id=None):
        return theme_frame("nav_idle.png", theme_id=theme_id, palette_id=palette_id, legacy="gui/button/idle_background.png")

    def theme_button_hover(theme_id=None, palette_id=None):
        return theme_frame("nav_hover.png", theme_id=theme_id, palette_id=palette_id, legacy="gui/button/hover_background.png")

    def _theme_color_with_alpha(color, alpha):
        if isinstance(color, str) and color.startswith("#") and len(color) >= 7:
            return color[:7] + alpha
        return color

    def theme_compact_button_idle(theme_id=None, palette_id=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        return Solid(theme_color("panel_alt", theme_id=selected, palette_id=palette_id, neutral_shell=neutral_shell))

    def theme_compact_button_hover(theme_id=None, palette_id=None, neutral_shell=False):
        selected = active_theme_id(neutral_shell=neutral_shell) if theme_id is None else _safe_theme_id(theme_id)
        return Solid(theme_color("hover", theme_id=selected, palette_id=palette_id, neutral_shell=neutral_shell))

    def theme_touch_button_idle(theme_id=None, palette_id=None):
        return theme_compact_button_idle(theme_id=theme_id, palette_id=palette_id)

    def theme_touch_button_hover(theme_id=None, palette_id=None):
        return theme_compact_button_hover(theme_id=theme_id, palette_id=palette_id)

    def theme_choice_idle(theme_id=None):
        return theme_frame("choice_idle.png", theme_id=theme_id, legacy="gui/button/choice_idle_background.png")

    def theme_choice_hover(theme_id=None):
        return theme_frame("choice_hover.png", theme_id=theme_id, legacy="gui/button/choice_hover_background.png")
