#!/usr/bin/env python3
"""Generate deterministic, text-free Ren'Py theme assets.

The generator deliberately uses only the Python standard library so the checked-in
assets can be reproduced without Pillow or a graphics toolchain.  Every output is
RGBA PNG, keeps its centre stretch-safe for Ren'Py ``Frame``/9-slice use, and uses
the same dimensions across all seven themes.  Geometry is rendered at a higher
resolution and downsampled with premultiplied-alpha averaging so curves and
diagonals remain clean without introducing dark fringes on transparent edges.
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
SUPERSAMPLE = 2

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


class _RasterCanvas:
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

    def clear(self, box: tuple[int, int, int, int]) -> None:
        """Replace a rectangular region with transparent pixels."""

        x0, y0, x1, y1 = box
        x0, x1 = max(0, x0), min(self.width, x1)
        if x1 <= x0:
            return
        transparent = bytes((0, 0, 0, 0)) * (x1 - x0)
        for y in range(max(0, y0), min(self.height, y1)):
            start = (y * self.width + x0) * 4
            self.pixels[start:start + len(transparent)] = transparent

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


class Canvas:
    """Logical-size drawing surface backed by a supersampled raster.

    Drawing code continues to use the final asset coordinates, which keeps all
    existing dimensions and 9-slice margins stable.  Only the private backing
    raster is larger.
    """

    def __init__(self, width: int, height: int, scale: int = SUPERSAMPLE):
        if scale < 1:
            raise ValueError("supersample scale must be at least 1")
        self.width = width
        self.height = height
        self.scale = scale
        self._raster = _RasterCanvas(width * scale, height * scale)

    def _point(self, point: tuple[int, int]) -> tuple[int, int]:
        return point[0] * self.scale, point[1] * self.scale

    def _box(self, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(value * self.scale for value in box)  # type: ignore[return-value]

    def blend(self, x: int, y: int, color: tuple[int, int, int, int]) -> None:
        # A logical point is a one-pixel mark, not a vanishing subpixel sample.
        self._raster.rect(
            (x * self.scale, y * self.scale, (x + 1) * self.scale, (y + 1) * self.scale),
            color,
        )

    def rect(self, box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
        self._raster.rect(self._box(box), color)

    def clear(self, box: tuple[int, int, int, int]) -> None:
        self._raster.clear(self._box(box))

    def rounded_rect(self, box: tuple[int, int, int, int], radius: int,
                     fill: tuple[int, int, int, int], border: tuple[int, int, int, int] | None = None,
                     border_width: int = 1) -> None:
        self._raster.rounded_rect(
            self._box(box), radius * self.scale, fill, border, border_width * self.scale
        )

    def rounded_outline(self, box: tuple[int, int, int, int], radius: int,
                        color: tuple[int, int, int, int]) -> None:
        self._raster.rounded_outline(self._box(box), radius * self.scale, color)

    def polygon(self, points: list[tuple[int, int]], color: tuple[int, int, int, int]) -> None:
        self._raster.polygon([self._point(point) for point in points], color)

    def line(self, start: tuple[int, int], end: tuple[int, int],
             color: tuple[int, int, int, int], width: int = 1) -> None:
        self._raster.line(
            self._point(start), self._point(end), color, max(1, width * self.scale)
        )

    def ellipse(self, box: tuple[int, int, int, int], color: tuple[int, int, int, int],
                outline: tuple[int, int, int, int] | None = None) -> None:
        self._raster.ellipse(self._box(box), color, outline)

    def _downsample(self) -> bytearray:
        if self.scale == 1:
            return bytearray(self._raster.pixels)

        source = self._raster.pixels
        source_width = self._raster.width
        sample_count = self.scale * self.scale
        output = bytearray(self.width * self.height * 4)

        # Average premultiplied colour, then return to straight-alpha PNG.  A
        # transparent sample therefore cannot contribute black/grey edge halos.
        for y in range(self.height):
            source_y = y * self.scale
            for x in range(self.width):
                source_x = x * self.scale
                alpha_sum = 0
                red_alpha = 0
                green_alpha = 0
                blue_alpha = 0
                for sample_y in range(self.scale):
                    offset = ((source_y + sample_y) * source_width + source_x) * 4
                    for _ in range(self.scale):
                        red, green, blue, alpha = source[offset:offset + 4]
                        alpha_sum += alpha
                        red_alpha += red * alpha
                        green_alpha += green * alpha
                        blue_alpha += blue * alpha
                        offset += 4

                target = (y * self.width + x) * 4
                output[target + 3] = (alpha_sum + sample_count // 2) // sample_count
                if alpha_sum:
                    output[target] = (red_alpha + alpha_sum // 2) // alpha_sum
                    output[target + 1] = (green_alpha + alpha_sum // 2) // alpha_sum
                    output[target + 2] = (blue_alpha + alpha_sum // 2) // alpha_sum
        return output

    def save(self, path: Path) -> None:
        output = _RasterCanvas(self.width, self.height)
        output.pixels = self._downsample()
        output.save(path)


def composite_canvas(destination: Canvas, source: Canvas, x: int = 0, y: int = 0) -> None:
    """Composite a rendered logical-size canvas onto another canvas."""

    if destination.scale != 1:
        raise ValueError("destination canvas must use native resolution")
    pixels = source._downsample()
    for source_y in range(source.height):
        for source_x in range(source.width):
            offset = (source_y * source.width + source_x) * 4
            alpha = pixels[offset + 3]
            if not alpha:
                continue
            destination._raster.blend(
                x + source_x,
                y + source_y,
                tuple(pixels[offset:offset + 4]),  # type: ignore[arg-type]
            )


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


def draw_heart(
    canvas: Canvas,
    center: tuple[int, int],
    size: tuple[int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
) -> None:
    """Draw a compact, unmistakable heart with a clean central notch.

    A parametric silhouette is more stable at compact navigation sizes than the
    former cluster of leaf ellipses, which only suggested a heart from a distance.
    The outline is drawn after the fill so both lobes and the lower point survive
    downsampling.
    """

    center_x, center_y = center
    width, height = size
    points: list[tuple[int, int]] = []
    for step in range(64):
        angle = 2 * math.pi * step / 64
        normalized_x = math.sin(angle) ** 3
        normalized_y = -(
            13 * math.cos(angle)
            - 5 * math.cos(2 * angle)
            - 2 * math.cos(3 * angle)
            - math.cos(4 * angle)
        ) / 17
        points.append((
            round(center_x + normalized_x * width / 2),
            round(center_y + normalized_y * height / 2),
        ))
    canvas.polygon(points, fill)
    for start, end in zip(points, points[1:] + points[:1]):
        canvas.line(start, end, outline, 1)


def decorate(
    canvas: Canvas,
    theme_id: str,
    inset: int = 18,
    *,
    nav: bool = False,
    logical_height: int | None = None,
) -> None:
    theme = THEMES[theme_id]
    accent = rgba(theme["colors"]["accent"])
    secondary = rgba(theme["colors"]["accent_secondary"])
    w = canvas.width
    h = canvas.height if logical_height is None else logical_height
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
        # Keep the symbol literal and restrained: one clean heart in each
        # stretch-safe corner.  The old vine-and-leaf cluster became an
        # unreadable pink blot at the navigation asset's final resolution.
        compact = h <= 100
        # Compact hearts must remain wholly inside the 28 px top 9-slice.
        # If any part enters the stretch band, short buttons compress the tip
        # and make the symbol look clipped.
        heart_width, heart_height = ((22, 18) if compact else (30, 27))
        heart_y = (16 if compact else max(inset + heart_height // 2 - 3, heart_height // 2 + 5))
        side_padding = 2 if compact else 0
        for heart_x in (
            inset + heart_width // 2 + side_padding,
            w - inset - heart_width // 2 - side_padding,
        ):
            draw_heart(
                canvas,
                (heart_x, heart_y),
                (heart_width, heart_height),
                secondary,
                accent,
            )
    elif theme_id == "lovecraft_biopunk":
        # Two restrained living fibres: deliberately no gears, brass, rivets,
        # circles-with-ticks, or mechanical/alchemical symbols.  The earlier
        # three-branch node read as a tiny insect on compact controls.
        for flip in (1, -1):
            x0 = inset if flip == 1 else w - inset
            previous = (x0, inset + 2)
            main_points = [previous]
            for step in range(1, 18):
                t = step / 17
                current = (
                    round(x0 + flip * span * t),
                    round(inset + 2 + math.sin(t * math.pi * 1.5) * 7),
                )
                canvas.line(previous, current, accent, 2)
                main_points.append(current)
                previous = current
            branch_start = main_points[8]
            branch_end = (branch_start[0] + flip * 8, branch_start[1] + 10)
            canvas.line(branch_start, branch_end, secondary, 1)
            canvas.ellipse(
                (branch_end[0] - 3, branch_end[1] - 3, branch_end[0] + 4, branch_end[1] + 4),
                secondary,
            )
    elif theme_id == "high_fantasy":
        # A clean crystal-and-rule motif keeps the centre safe for arbitrary
        # 9-slice stretch.  Avoid crossing branches: at navigation scale they
        # looked like accidental scratches rather than filigree.
        top_y = 7 if nav else inset
        if not nav:
            canvas.line((inset + span, inset), (w - inset - span, inset), secondary, 2)
        for x in (inset + 22, w - inset - 22):
            direction = 1 if x < w // 2 else -1
            d = min(6 if nav else 10, h // 5)
            canvas.polygon([(x, top_y - d), (x + d, top_y), (x, top_y + d), (x - d, top_y)], accent)
            canvas.line((x + direction * d, top_y), (x + direction * (38 if nav else 52), top_y), accent, 2)
            canvas.line((x + direction * 12, top_y + 5), (x + direction * (30 if nav else 38), top_y + 5), secondary, 1)
    elif theme_id == "science_fiction":
        for flip in (1, -1):
            x0 = inset if flip == 1 else w - inset
            x1 = x0 + flip * min(span, w // 5)
            canvas.line((x0, inset), (x1, inset), accent, 2)
            canvas.line((x1, inset), (x1 + flip * 18, inset + 18), secondary, 2)
            canvas.ellipse((x1 - 3, inset - 3, x1 + 4, inset + 4), secondary)


def render_pause_asset(theme_id: str, asset_name: str, size: tuple[int, int]) -> Canvas:
    """Render a large pause panel with supersampling limited to visible edges.

    The flat interior stays at native resolution.  Four small corner tiles and
    the ornament band are rendered at 2x, then downsampled and composited.  This
    gives rounded/chamfered edges and curved decorations coverage alpha without
    allocating a full 2560x2160 backing image for every pause panel.
    """

    theme = THEMES[theme_id]
    width, height = size
    pad = 3
    canvas = Canvas(width, height, scale=1)
    panel_box = (pad, pad, width - pad, height - pad)
    panel_shape(canvas, theme, panel_box)

    shape = theme["shape"]
    if shape == "chamfer":
        corner_extent = min(24, (height - pad * 2) // 4)
    elif shape == "organic":
        corner_extent = 26
    elif shape in {"book", "fantasy"}:
        corner_extent = 8
    else:
        corner_extent = 18
    tile_size = corner_extent + pad + 5

    for origin_x, origin_y in (
        (0, 0),
        (width - tile_size, 0),
        (0, height - tile_size),
        (width - tile_size, height - tile_size),
    ):
        canvas.clear((origin_x, origin_y, origin_x + tile_size, origin_y + tile_size))
        corner = Canvas(tile_size, tile_size, scale=SUPERSAMPLE)
        translated_box = (
            panel_box[0] - origin_x,
            panel_box[1] - origin_y,
            panel_box[2] - origin_x,
            panel_box[3] - origin_y,
        )
        panel_shape(corner, theme, translated_box)
        composite_canvas(canvas, corner, origin_x, origin_y)

    ornament_height = min(height, 96)
    ornament = Canvas(width, ornament_height, scale=SUPERSAMPLE)
    decorate(ornament, theme_id, 28, logical_height=height)
    composite_canvas(canvas, ornament)
    canvas.line(
        (28, height - 28),
        (min(width - 28, 220), height - 28),
        rgba(theme["colors"]["accent"]),
        2,
    )
    return canvas


def render_asset(theme_id: str, asset_name: str, size: tuple[int, int]) -> Canvas:
    theme = THEMES[theme_id]
    w, h = size
    if asset_name.startswith("pause_"):
        return render_pause_asset(theme_id, asset_name, size)
    canvas = Canvas(w, h, scale=SUPERSAMPLE)
    if asset_name.startswith("scrollbar"):
        if asset_name == "scrollbar_track":
            canvas.rounded_rect((4, 0, w - 4, h), 5, rgba(theme["colors"]["panel_alt"]), rgba(theme["colors"]["border"]), 1)
        else:
            canvas.rounded_rect((2, 0, w - 2, h), 7, rgba(theme["colors"]["accent"]), rgba(theme["colors"]["accent_secondary"]), 1)
        return canvas

    hover = asset_name.endswith("hover")
    pad = 2
    panel_shape(canvas, theme, (pad, pad, w - pad, h - pad), hover=hover)

    if asset_name in {"dialogue_frame", "namebox_frame", "choice_idle", "choice_hover", "nav_idle", "nav_hover"}:
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
