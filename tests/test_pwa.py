from __future__ import annotations

import json
import struct
from pathlib import Path

_PWA = Path(__file__).resolve().parent.parent / "src" / "should_we" / "pwa"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as f:
        f.read(16)
        width, height = struct.unpack(">II", f.read(8))
    return width, height


def test_manifest_is_valid_pwa_manifest():
    manifest = json.loads((_PWA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"]
    assert manifest["short_name"]
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert sizes == {"192x192", "512x512"}
    for icon in manifest["icons"]:
        path = _PWA / Path(icon["src"]).name
        assert path.is_file(), f"missing icon {icon['src']}"
        assert path.read_bytes().startswith(PNG_MAGIC)
        assert f"{_png_size(path)[0]}x{_png_size(path)[1]}" == icon["sizes"]


def test_service_worker_exists_with_fetch_handler():
    sw = (_PWA / "sw.js").read_text(encoding="utf-8")
    assert "addEventListener('fetch'" in sw


def test_apple_touch_icon_is_180px_png():
    path = _PWA / "icon-180.png"
    assert path.is_file()
    assert path.read_bytes().startswith(PNG_MAGIC)
    assert _png_size(path) == (180, 180)
