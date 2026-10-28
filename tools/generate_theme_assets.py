#!/usr/bin/env python3
"""Generate deterministic, text-free Ren'Py theme assets.

The generator deliberately uses only the Python standard library so the checked-in
assets can be reproduced without Pillow or a graphics toolchain.  Every output is
RGBA PNG, keeps its centre stretch-safe for Ren'Py ``Frame``/9-slice use, and uses
the same dimensions across all seven themes.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "game" / "gui" / "themes"

ASSETS = {
    # Slice margins intentionally contain every non-uniform corner ornament.
    "dialogue_frame": ((1728, 300), (160, 60, 160, 60)),
    "namebox_frame": ((420, 72), (80, 28, 80, 28)),
    "choice_idle": ((1100, 92), (150, 36, 150, 36)),
    "choice_hover": ((1100, 92), (150, 36, 150, 36)),
    "pause_history_frame": ((1280, 1080), (180, 80, 180, 80)),
    "pause_menu_frame": ((640, 1080), (180, 80, 180, 80)),
    "nav_idle": ((260, 70), (80, 28, 80, 28)),
    "nav_hover": ((260, 70), (80, 28, 80, 28)),
    "scrollbar_track": ((18, 700), (8, 18, 8, 18)),
    "scrollbar_thumb": ((18, 160), (8, 18, 8, 18)),
}


THEMES = {
    "default": {
        "display_name": "Default",
        "kind": "default",
        "shape": "round",
        "colors": {
            "panel": "#182129E8", "panel_alt": "#202C35EE", "border": "#78909CAA",
            "accent": "#5FB7B0FF", "accent_secondary": "#A7C9C6FF",
            "text": "#F1F4F5FF", "muted_text": "#B6C1C6FF",
            "heading_text": "#F1F4F5FF", "overlay_text": "#F1F4F5FF", "button_hover_text": "#F1F4F5FF",
            "hover": "#2D434CEB", "overlay": "#080B0DC4",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
            "dialogue": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
            "name": ["gui/themes/fonts/fira_sans/FiraSans-Bold.ttf"],
            "history": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
        },
    },
    "modern_muted": {
        "display_name": "Modern Muted",
        "kind": "modified",
        "shape": "soft",
        "colors": {
            "panel": "#C9C2B5E8", "panel_alt": "#B4B1A9EE", "border": "#625F5AA8",
            "accent": "#607B78FF", "accent_secondary": "#869894FF",
            "text": "#292B2BFF", "muted_text": "#555B5AFF",
            "heading_text": "#292B2BFF", "overlay_text": "#F1F4F5FF", "button_hover_text": "#292B2BFF",
            "hover": "#D9D2C5F2", "overlay": "#171817B8",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
            "dialogue": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
            "name": ["gui/themes/fonts/fira_sans/FiraSans-Bold.ttf"],
            "history": ["gui/themes/fonts/fira_sans/FiraSans-Regular.ttf"],
        },
    },
    "literary": {
        "display_name": "Literary",
        "kind": "modified",
        "shape": "book",
        "colors": {
            "panel": "#261B17F0", "panel_alt": "#35241DF2", "border": "#A47B49CC",
            "accent": "#C39A62FF", "accent_secondary": "#E1C99DFF",
            "text": "#F1E5CCFF", "muted_text": "#C8B99EFF",
            "heading_text": "#F1E5CCFF", "overlay_text": "#F1E5CCFF", "button_hover_text": "#F1E5CCFF",
            "hover": "#493326F2", "overlay": "#100B09C7",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/pt_serif/PTSerif-Bold.ttf"],
            "dialogue": ["gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"],
            "name": ["gui/themes/fonts/pt_serif/PTSerif-Bold.ttf"],
            "history": ["gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"],
        },
    },
    "romantic": {
        "display_name": "Romantic",
        "kind": "modified",
        "shape": "soft",
        "colors": {
            "panel": "#F1E5DDEB", "panel_alt": "#E8D4D0F0", "border": "#8D596EB8",
            "accent": "#A65E79FF", "accent_secondary": "#D19AACFF",
            "text": "#3D2733FF", "muted_text": "#725464FF",
            "heading_text": "#3D2733FF", "overlay_text": "#FFF6FAFF", "button_hover_text": "#3D2733FF",
            "hover": "#F6E9E2F4", "overlay": "#1D1118B8",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"],
            "dialogue": ["gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"],
            "name": ["gui/themes/fonts/pt_serif/PTSerif-Bold.ttf"],
            "history": ["gui/themes/fonts/pt_serif/PTSerif-Regular.ttf"],
        },
    },
    "lovecraft_biopunk": {
        "display_name": "Lovecraft Biopunk",
        "kind": "modified",
        "shape": "organic",
        "colors": {
            "panel": "#091B1CF2", "panel_alt": "#12272AF2", "border": "#55766FB8",
            "accent": "#72A69AFF", "accent_secondary": "#8A6F9BFF",
            "text": "#D7DFD5FF", "muted_text": "#8FA69CFF",
            "heading_text": "#D7DFD5FF", "overlay_text": "#D7DFD5FF", "button_hover_text": "#D7DFD5FF",
            "hover": "#173638F2", "overlay": "#020809D1",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/philosopher/Philosopher-Regular.ttf"],
            "dialogue": ["gui/themes/fonts/philosopher/Philosopher-Regular.ttf"],
            "name": ["gui/themes/fonts/philosopher/Philosopher-Bold.ttf"],
            "history": ["gui/themes/fonts/philosopher/Philosopher-Regular.ttf"],
        },
    },
    "high_fantasy": {
        "display_name": "High Fantasy",
        "kind": "modified",
        "shape": "fantasy",
        "colors": {
            "panel": "#0E1A35F0", "panel_alt": "#172747F2", "border": "#AAB7CEE0",
            "accent": "#7FA6E4FF", "accent_secondary": "#D4DCEAFF",
            "text": "#EDF1F8FF", "muted_text": "#B7C1D4FF",
            "heading_text": "#EDF1F8FF", "overlay_text": "#EDF1F8FF", "button_hover_text": "#EDF1F8FF",
            "hover": "#213967F2", "overlay": "#050914C9",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/philosopher/Philosopher-Bold.ttf"],
            "dialogue": ["gui/themes/fonts/philosopher/Philosopher-Regular.ttf"],
            "name": ["gui/themes/fonts/philosopher/Philosopher-Bold.ttf"],
            "history": ["gui/themes/fonts/philosopher/Philosopher-Regular.ttf"],
        },
    },
    "science_fiction": {
        "display_name": "Science Fiction",
        "kind": "modified",
        "shape": "chamfer",
        "colors": {
            "panel": "#10151DF2", "panel_alt": "#171E28F2", "border": "#3E6178CC",
            "accent": "#4BD5E8FF", "accent_secondary": "#9D6BFFFF",
            "text": "#E6F5F7FF", "muted_text": "#91AEB7FF",
            "heading_text": "#E6F5F7FF", "overlay_text": "#E6F5F7FF", "button_hover_text": "#E6F5F7FF",
            "hover": "#1C2D3AF2", "overlay": "#03070BCB",
        },
        "fonts": {
            "interface": ["gui/themes/fonts/play/Play-Regular.ttf"],
            "dialogue": ["gui/themes/fonts/play/Play-Regular.ttf"],
            "name": ["gui/themes/fonts/play/Play-Bold.ttf"],
            "history": ["gui/themes/fonts/play/Play-Regular.ttf"],
        },
    },
}


def rgba(value: str) -> tuple[int, int, int, int]:
    value = value.removeprefix("#")
    if len(value) == 6:
        value += "FF"
    return tuple(int(value[i:i + 2], 16) for i in range(0, 8, 2))  # type: ignore[return-value]


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pixels = bytearray(width * height * 4)

    def blend(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        i = (y * self.width + x) * 4
        sr, sg, sb, sa = color
        if sa == 255 or self.pixels[i + 3] == 0:
            self.pixels[i:i + 4] = bytes(color)
            return
        da = self.pixels[i + 3]
        out_a = sa + (da * (255 - sa) + 127) // 255
        if out_a == 0:
            return
        for offset, source in enumerate((sr, sg, sb)):
            dest = self.pixels[i + offset]
            self.pixels[i + offset] = (
                source * sa * 255 + dest * da * (255 - sa) + out_a * 127
            ) // (out_a * 255)
        self.pixels[i + 3] = out_a

    def span(self, y: int, x0: int, x1: int, color: tuple[int, int, int, int]) -> None:
        if not (0 <= y < self.height):
            return
        x0, x1 = max(0, x0), min(self.width, x1)
        if x1 <= x0:
            return
        if color[3] == 255:
            row = bytes(color) * (x1 - x0)
            start = (y * self.width + x0) * 4
            self.pixels[start:start + len(row)] = row
        else:
            for x in range(x0, x1):
                self.blend(x, y, color)

    def rect(self, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        for y in range(max(0, y0), min(self.height, y1)):
            self.span(y, x0, x1, color)

    def rounded_rect(self, box: tuple[int, int, int, int], radius: int,
                     fill: tuple[int, int, int, int], border: tuple[int, int, int, int] | None = None,
                     border_width: int = 1) -> None:
        x0, y0, x1, y1 = box
        radius = max(0, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
        for y in range(y0, y1):
            dy = min(y - y0, y1 - 1 - y)
            inset = 0 if dy >= radius else int(radius - math.sqrt(max(0, radius * radius - (radius - dy) ** 2)))
            self.span(y, x0 + inset, x1 - inset, fill)
        if border and border_width:
            for n in range(border_width):
                self.rounded_outline((x0 + n, y0 + n, x1 - n, y1 - n), max(0, radius - n), border)

    def rounded_outline(self, box: tuple[int, int, int, int], radius: int,
                        color: tuple[int, int, int, int]) -> None:
        x0, y0, x1, y1 = box
        self.line((x0 + radius, y0), (x1 - radius - 1, y0), color)
        self.line((x0 + radius, y1 - 1), (x1 - radius - 1, y1 - 1), color)
        self.line((x0, y0 + radius), (x0, y1 - radius - 1), color)
        self.line((x1 - 1, y0 + radius), (x1 - 1, y1 - radius - 1), color)
        for corner_x, corner_y, start in (
            (x0 + radius, y0 + radius, math.pi), (x1 - radius - 1, y0 + radius, -math.pi / 2),
            (x1 - radius - 1, y1 - radius - 1, 0), (x0 + radius, y1 - radius - 1, math.pi / 2),
        ):
            for step in range(max(6, radius * 2)):
                angle = start + (math.pi / 2) * step / max(1, radius * 2 - 1)
                self.blend(round(corner_x + math.cos(angle) * radius), round(corner_y + math.sin(angle) * radius), color)

    def polygon(self, points: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
        min_y = max(0, min(y for _, y in points))
        max_y = min(self.height - 1, max(y for _, y in points))
        for y in range(min_y, max_y + 1):
            intersections = []
            for i, (x1, y1) in enumerate(points):
                x2, y2 = points[(i + 1) % len(points)]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    intersections.append(round(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
            intersections.sort()
            for i in range(0, len(intersections) - 1, 2):
                self.span(y, intersections[i], intersections[i + 1] + 1, color)

    def line(self, start: tuple[int, int], end: tuple[int, int],
             color: tuple[int, int, int, int], width: int = 1) -> None:
        x0, y0 = start
        x1, y1 = end
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        radius = max(0, width // 2)
        for i in range(steps + 1):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            if radius == 0:
                self.blend(x, y, color)
            else:
                for oy in range(-radius, radius + 1):
                    span = int(math.sqrt(max(0, radius * radius - oy * oy)))
                    for ox in range(-span, span + 1):
                        self.blend(x + ox, y + oy, color)

    def ellipse(self, box: tuple[int, int, int, int], color: tuple[int, int, int, int],
                outline: tuple[int, int, int, int] | None = None) -> None:
        x0, y0, x1, y1 = box
        rx, ry = max(1.0, (x1 - x0) / 2), max(1.0, (y1 - y0) / 2)
        cx, cy = (x0 + x1 - 1) / 2, (y0 + y1 - 1) / 2
        for y in range(max(0, y0), min(self.height, y1)):
            norm = 1 - ((y - cy) / ry) ** 2
            if norm < 0:
                continue
            dx = int(rx * math.sqrt(norm))
            self.span(y, round(cx - dx), round(cx + dx + 1), color)
        if outline:
            for step in range(max(16, int(2 * math.pi * max(rx, ry)))):
                angle = step * 2 * math.pi / max(16, int(2 * math.pi * max(rx, ry)))
                self.blend(round(cx + rx * math.cos(angle)), round(cy + ry * math.sin(angle)), outline)

    def save(self, path: Path) -> None:
        raw = b"".join(
            b"\x00" + bytes(self.pixels[y * self.width * 4:(y + 1) * self.width * 4])
            for y in range(self.height)
        )
        def chunk(kind: bytes, payload: bytes) -> bytes:
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 6, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(raw, 9))
        png += chunk(b"IEND", b"")
        path.write_bytes(png)


def panel_shape(canvas: Canvas, theme: dict, box: tuple[int, int, int, int], *, hover: bool = False) -> None:
    colors = theme["colors"]
    fill = rgba(colors["hover"] if hover else colors["panel"])
    border = rgba(colors["accent"] if hover else colors["border"])
    x0, y0, x1, y1 = box
    shape = theme["shape"]
    if shape == "chamfer":
        c = min(24, (y1 - y0) // 4)
        canvas.polygon([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
                        (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)], fill)
        for a, b in zip([(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c),
                         (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)],
                        [(x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1),
                         (x0 + c, y1), (x0, y1 - c), (x0, y0 + c), (x0 + c, y0)]):
            canvas.line(a, b, border, 2)
    else:
        radius = 8 if shape in {"book", "fantasy"} else 18
        if shape == "organic":
            radius = 26
        canvas.rounded_rect(box, radius, fill, border, 2)


def decorate(canvas: Canvas, theme_id: str, inset: int = 18, *, nav: bool = False) -> None:
    theme = THEMES[theme_id]
    accent = rgba(theme["colors"]["accent"])
    secondary = rgba(theme["colors"]["accent_secondary"])
    w, h = canvas.width, canvas.height
    span = min(110, max(24, w // 8), max(24, h // 3))
    if theme_id == "default":
        for sx in (1, -1):
            x = inset if sx == 1 else w - inset - 1
            canvas.line((x, inset), (x + sx * span, inset), accent, 2)
            canvas.ellipse((x + sx * span - 3, inset - 3, x + sx * span + 4, inset + 4), accent)
    elif theme_id == "modern_muted":
        if nav:
            # Navigation captions live in the middle of this compact asset.
            # Keep the ornament on the top edge and leave a generous centre gap.
            top_y = 6
            canvas.line((inset + 8, top_y), (w // 2 - 52, top_y), accent, 2)
            canvas.line((w // 2 + 52, top_y), (w - inset - 8, top_y), accent, 2)
            canvas.line((inset + 18, top_y + 5), (w // 2 - 70, top_y + 5), secondary, 1)
            canvas.line((w // 2 + 70, top_y + 5), (w - inset - 18, top_y + 5), secondary, 1)
        else:
            canvas.line((inset + 20, inset), (w - inset - 20, inset), accent, 2)
            canvas.line((inset + 60, inset + 7), (w - inset - 60, inset + 7), secondary, 1)
    elif theme_id == "literary":
        for x in (inset + 12, w - inset - 12):
            direction = 1 if x < w // 2 else -1
            canvas.line((x, inset), (x + direction * span, inset), accent, 3)
            canvas.line((x, inset), (x, min(h - inset, inset + span // 2)), accent, 2)
            d = 8
            canvas.polygon([(x, inset - d), (x + d, inset), (x, inset + d), (x - d, inset)], secondary)
    elif theme_id == "romantic":
        for flip in (1, -1):
            x0 = inset if flip == 1 else w - inset
            points = []
            for step in range(25):
                t = step / 24
                points.append((round(x0 + flip * span * t), round(inset + 12 * math.sin(t * math.pi))))
            for a, b in zip(points, points[1:]):
                canvas.line(a, b, accent, 2)
            for t in (0.28, 0.55, 0.8):
                x = round(x0 + flip * span * t)
                y = round(inset + 12 * math.sin(t * math.pi))
                canvas.ellipse((x - 5, y - 9, x + 6, y + 2), secondary)
    elif theme_id == "lovecraft_biopunk":
        # Asymmetric organic fibres and membrane nodes: deliberately no gears,
        # brass, rivets, circles-with-ticks, or mechanical/alchemical symbols.
        for flip in (1, -1):
            x0 = inset if flip == 1 else w - inset
            for branch in range(3):
                prev = (x0, inset + branch * 7)
                for step in range(1, 18):
                    t = step / 17
                    cur = (round(x0 + flip * span * t), round(inset + branch * 7 + math.sin(t * 7 + branch) * (5 + branch * 2)))
                    canvas.line(prev, cur, accent if branch == 0 else secondary, 2 if branch == 0 else 1)
                    prev = cur
            node_x = round(x0 + flip * span * 0.62)
            canvas.ellipse((node_x - 8, inset - 5, node_x + 9, inset + 12), rgba(theme["colors"]["panel_alt"]), secondary)
            canvas.ellipse((node_x - 3, inset, node_x + 4, inset + 7), accent)
    elif theme_id == "high_fantasy":
        # Corner-only filigree keeps the centre safe for arbitrary 9-slice stretch.
        top_y = 7 if nav else inset
        if not nav:
            canvas.line((inset + span, inset), (w - inset - span, inset), secondary, 2)
        for x in (inset + 22, w - inset - 22):
            direction = 1 if x < w // 2 else -1
            d = min(6 if nav else 10, h // 5)
            canvas.polygon([(x, top_y - d), (x + d, top_y), (x, top_y + d), (x - d, top_y)], accent)
            canvas.line((x, top_y), (x + direction * (32 if nav else 42), top_y + (8 if nav else 22)), accent, 2)
            canvas.line((x + direction * 12, top_y + 3), (x + direction * 26, top_y - 1), secondary, 1)
    elif theme_id == "science_fiction":
        for flip in (1, -1):
            x0 = inset if flip == 1 else w - inset
            x1 = x0 + flip * min(span, w // 5)
            canvas.line((x0, inset), (x1, inset), accent, 2)
            canvas.line((x1, inset), (x1 + flip * 18, inset + 18), secondary, 2)
            canvas.ellipse((x1 - 3, inset - 3, x1 + 4, inset + 4), secondary)


def render_asset(theme_id: str, asset_name: str, size: tuple[int, int]) -> Canvas:
    theme = THEMES[theme_id]
    w, h = size
    canvas = Canvas(w, h)
    if asset_name.startswith("scrollbar"):
        if asset_name == "scrollbar_track":
            canvas.rounded_rect((4, 0, w - 4, h), 5, rgba(theme["colors"]["panel_alt"]), rgba(theme["colors"]["border"]), 1)
        else:
            canvas.rounded_rect((2, 0, w - 2, h), 7, rgba(theme["colors"]["accent"]), rgba(theme["colors"]["accent_secondary"]), 1)
        return canvas

    hover = asset_name.endswith("hover")
    pad = 3 if asset_name.startswith("pause_") else 2
    panel_shape(canvas, theme, (pad, pad, w - pad, h - pad), hover=hover)

    if asset_name.startswith("pause_"):
        # Keep the middle empty/stretch-safe; decoration is confined to edges.
        decorate(canvas, theme_id, 28)
        canvas.line((28, h - 28), (min(w - 28, 220), h - 28), rgba(theme["colors"]["accent"]), 2)
    elif asset_name in {"dialogue_frame", "namebox_frame", "choice_idle", "choice_hover", "nav_idle", "nav_hover"}:
        decorate(canvas, theme_id, 14, nav=asset_name.startswith("nav_"))
    return canvas


def manifest_for(theme_id: str) -> dict:
    theme = THEMES[theme_id]
    return {
        "schema_version": 1,
        "id": theme_id,
        "display_name": theme["display_name"],
        "kind": theme["kind"],
        "inherits": None if theme_id == "default" else "default",
        "target_resolution": [1920, 1080],
        "colors": theme["colors"],
        "fonts": theme["fonts"],
        "assets": {
            name: {"file": f"{name}.png", "size": list(size), "slice": list(slice_meta)}
            for name, (size, slice_meta) in ASSETS.items()
        },
        "pause_layout": {
            "history_fraction": 0.6666667,
            "menu_fraction": 0.3333333,
            "history_order": "oldest_to_newest",
            "show_separate_history_button": False,
            "background_dimming_color": theme["colors"]["overlay"],
        },
    }


def generate(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for theme_id in THEMES:
        theme_dir = output_root / theme_id
        theme_dir.mkdir(parents=True, exist_ok=True)
        for asset_name, (size, _) in ASSETS.items():
            render_asset(theme_id, asset_name, size).save(theme_dir / f"{asset_name}.png")
        (theme_dir / "manifest.json").write_text(
            json.dumps(manifest_for(theme_id), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT, help="Theme asset root")
    args = parser.parse_args()
    generate(args.output.resolve())
    print(f"Generated {len(THEMES)} themes in {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
