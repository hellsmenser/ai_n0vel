#!/usr/bin/env python3
"""Focused regressions for deterministic, antialiased theme generation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("generate_theme_assets.py")
SPEC = importlib.util.spec_from_file_location("generate_theme_assets", MODULE_PATH)
assert SPEC and SPEC.loader
theme_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(theme_assets)


def read_rgba_png(path: Path) -> tuple[int, int, bytearray]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    width = height = 0
    compressed = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, depth, colour_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            assert (depth, colour_type, compression, filtering, interlace) == (8, 6, 0, 0, 0)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(compressed)
    stride = width * 4
    pixels = bytearray()
    for y in range(height):
        row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        assert row[0] == 0
        pixels.extend(row[1:])
    return width, height, pixels


class ThemeAssetGenerationTests(unittest.TestCase):
    def test_asset_contract_and_antialiased_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            theme_assets.generate(root)
            for theme_id, theme in theme_assets.THEMES.items():
                manifest = json.loads((root / theme_id / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(set(manifest["assets"]), set(theme_assets.ASSETS))
                self.assertEqual(
                    (root / theme_id / "manifest.json").read_bytes(),
                    (theme_assets.OUTPUT_ROOT / theme_id / "manifest.json").read_bytes(),
                    f"checked-in {theme_id} manifest is stale",
                )
                for asset_name, (expected_size, expected_slice) in theme_assets.ASSETS.items():
                    metadata = manifest["assets"][asset_name]
                    self.assertEqual(metadata["size"], list(expected_size))
                    self.assertEqual(metadata["slice"], list(expected_slice))
                    generated_asset = root / theme_id / metadata["file"]
                    checked_in_asset = theme_assets.OUTPUT_ROOT / theme_id / metadata["file"]
                    self.assertEqual(
                        generated_asset.read_bytes(),
                        checked_in_asset.read_bytes(),
                        f"checked-in {theme_id}/{asset_name} is stale",
                    )
                    width, height, pixels = read_rgba_png(generated_asset)
                    self.assertEqual((width, height), expected_size)

                # The outside of the rounded dialogue panel must contain
                # coverage alpha introduced by supersampling, not a binary stair.
                _, _, dialogue = read_rgba_png(root / theme_id / "dialogue_frame.png")
                primitive_alphas = {
                    int(value.removeprefix("#")[-2:], 16)
                    for value in theme["colors"].values()
                    if len(value.removeprefix("#")) == 8
                }
                edge_alphas = set(dialogue[3::4]) - {0, 255} - primitive_alphas
                self.assertTrue(edge_alphas, f"{theme_id} has no antialiased edge coverage")

    def test_romantic_nav_uses_a_literal_heart_silhouette(self) -> None:
        width, _, pixels = read_rgba_png(
            theme_assets.OUTPUT_ROOT / "romantic" / "nav_idle.png"
        )

        def pixel(x: int, y: int) -> tuple[int, int, int, int]:
            start = (y * width + x) * 4
            return tuple(pixels[start:start + 4])  # type: ignore[return-value]

        secondary = theme_assets.rgba(
            theme_assets.THEMES["romantic"]["colors"]["accent_secondary"]
        )
        panel = theme_assets.rgba(theme_assets.THEMES["romantic"]["colors"]["panel"])

        # Two filled lobes, a background-coloured central notch and a filled
        # lower body distinguish the symbol from the former leaf cluster.
        self.assertEqual(pixel(20, 15), secondary)
        self.assertEqual(pixel(32, 15), secondary)
        self.assertEqual(pixel(26, 15), panel)
        self.assertEqual(pixel(26, 26), secondary)

    def test_romantic_pause_frame_and_heart_have_coverage_alpha(self) -> None:
        width, _, pixels = read_rgba_png(
            theme_assets.OUTPUT_ROOT / "romantic" / "pause_history_frame.png"
        )
        primitive_alphas = {
            int(value.removeprefix("#")[-2:], 16)
            for value in theme_assets.THEMES["romantic"]["colors"].values()
            if len(value.removeprefix("#")) == 8
        }

        def region_alphas(x0: int, y0: int, x1: int, y1: int) -> set[int]:
            return {
                pixels[(y * width + x) * 4 + 3]
                for y in range(y0, y1)
                for x in range(x0, x1)
            }

        frame_coverage = region_alphas(0, 0, 40, 40) - {0, 255} - primitive_alphas
        heart_coverage = region_alphas(25, 20, 65, 60) - {0, 255} - primitive_alphas
        self.assertTrue(frame_coverage, "pause frame corner is still binary/jagged")
        self.assertTrue(heart_coverage, "pause heart edge is still binary/jagged")

    def test_single_asset_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root / "first.png", root / "second.png"]
            for path in paths:
                theme_assets.render_asset("romantic", "nav_idle", (260, 70)).save(path)
            hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
            self.assertEqual(hashes[0], hashes[1])


if __name__ == "__main__":
    unittest.main()
