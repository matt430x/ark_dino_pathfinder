"""
Run this once before building to pre-download EasyOCR models into ./models/.
PyInstaller then bundles that folder so the installed app needs no internet access.

Usage:
    python download_models.py
"""

import os
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "models"


def main():
    MODEL_DIR.mkdir(exist_ok=True)
    print(f"Downloading EasyOCR English models to: {MODEL_DIR}")
    import easyocr

    # GPU disabled here — we just want to download weights, not run inference
    easyocr.Reader(["en"], gpu=False, model_storage_directory=str(MODEL_DIR))

    models = sorted(MODEL_DIR.iterdir())
    print("\nBundled models:")
    for m in models:
        print(f"  {m.name}  ({m.stat().st_size / 1_048_576:.1f} MB)")
    print("\nDone. Run 'build.bat' (or 'pyinstaller gui.spec') to build the app.")


if __name__ == "__main__":
    main()
