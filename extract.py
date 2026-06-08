"""OCR-based coordinate extraction from ARK Dino Scanner screenshots."""

import gc
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, Optional, List, Tuple

from PIL import Image

_SCALE = 2

_reader = None
_NUM = re.compile(r"^\d{1,3}\.\d{1,2}$")


def _bundled_model_dir() -> Optional[str]:
    """Return the path to the bundled EasyOCR models, or None to use the default."""
    import sys

    if getattr(sys, "frozen", False):
        # PyInstaller onedir: sys._MEIPASS == dist/gui/_internal/
        candidate = os.path.join(sys._MEIPASS, "easyocr_models")
    else:
        candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

    return candidate if os.path.isdir(candidate) else None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr

        model_dir = _bundled_model_dir()
        kwargs = {"model_storage_directory": model_dir} if model_dir else {}

        print("  Loading OCR engine...")
        try:
            _reader = easyocr.Reader(["en"], gpu=True, **kwargs)
            print("  OCR running on GPU.")
        except Exception:
            _reader = easyocr.Reader(["en"], gpu=False, **kwargs)
            print("  OCR running on CPU (no GPU available).")
    return _reader


def unload_reader():
    """Release the OCR engine from memory."""
    global _reader
    _reader = None
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def extract_coordinates(
    image_paths: List[str],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[Tuple[float, float]]:
    """Return deduplicated (lat, long) pairs from one or more screenshots."""
    reader = _get_reader()
    seen: set = set()
    coords: List[Tuple[float, float]] = []
    total = len(image_paths)
    for i, path in enumerate(image_paths):
        print(f"  Processing: {Path(path).name}")
        for pair in _parse_image(path, reader):
            key = (round(pair[0], 2), round(pair[1], 2))
            if key not in seen:
                seen.add(key)
                coords.append(pair)
        if progress_callback:
            progress_callback(i + 1, total)
    return coords


def _parse_image(path: str, reader) -> List[Tuple[float, float]]:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        img = Image.open(path)
        img = img.resize((img.width * _SCALE, img.height * _SCALE), Image.LANCZOS)
        img.save(tmp_path)
        results = reader.readtext(tmp_path, detail=1)
    finally:
        os.unlink(tmp_path)
    dets = _to_detections(results)

    lat_x = _header_x(dets, r"lat")
    lon_x = _header_x(dets, r"lon")

    if lat_x is None or lon_x is None:
        print(f"    Warning: Lat/Long column headers not found in {Path(path).name}")
        return []

    col_tol = abs(lon_x - lat_x) * 0.55

    pairs: List[Tuple[float, float]] = []
    for row in _group_rows(dets, threshold=14 * _SCALE):
        lat_str = _col_value(row, lat_x, col_tol)
        lon_str = _col_value(row, lon_x, col_tol)
        if lat_str and lon_str:
            lat = _to_float(lat_str)
            lon = _to_float(lon_str)
            if lat is not None and lon is not None and 0 <= lat <= 100 and 0 <= lon <= 100:
                pairs.append((lat, lon))
    return pairs


def _to_detections(results) -> List[Tuple[float, float, str]]:
    dets = []
    for bbox, text, conf in results:
        if conf < 0.25:
            continue
        cx = sum(p[0] for p in bbox) / 4
        cy = sum(p[1] for p in bbox) / 4
        dets.append((cx, cy, text.strip()))
    return dets


def _header_x(dets: List[Tuple[float, float, str]], pattern: str) -> Optional[float]:
    for cx, cy, text in dets:
        if re.search(pattern, text, re.IGNORECASE):
            return cx
    return None


def _group_rows(dets: List[Tuple[float, float, str]], threshold: int = 14) -> List[List[Tuple]]:
    rows: List[List] = []
    for det in sorted(dets, key=lambda d: d[1]):
        for row in rows:
            avg_y = sum(d[1] for d in row) / len(row)
            if abs(det[1] - avg_y) <= threshold:
                row.append(det)
                break
        else:
            rows.append([det])
    return rows


def _col_value(row: List[Tuple], col_x: float, tol: float) -> Optional[str]:
    candidates = [
        (abs(cx - col_x), text)
        for cx, cy, text in row
        if _NUM.match(text) and abs(cx - col_x) <= tol
    ]
    if not candidates:
        return None
    return min(candidates)[1]


def _to_float(text: str) -> Optional[float]:
    cleaned = text.replace(",", ".").replace("O", "0").replace("o", "0")
    try:
        return float(cleaned)
    except ValueError:
        return None
