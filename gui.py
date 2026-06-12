"""ARK Dino Pathfinder v2.0 — PyQt6 GUI."""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import pyqtgraph as pg
pg.setConfigOptions(antialias=True)

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QPalette, QPainter, QBrush
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QPushButton, QListWidget, QTextEdit,
    QProgressBar, QFileDialog, QFrame, QSizePolicy, QMessageBox,
)

VERSION = "2.4"
_GITHUB_API = "https://api.github.com/repos/matt430x/ark_dino_pathfinder/releases/latest"

# ── Colour tokens ─────────────────────────────────────────────────────────────
BG    = "#0d1f2d"
CARD  = "#102030"
ACCENT= "#00ccdd"
TEXT  = "#aaccdd"
DIM   = "#445566"
BTN2  = "#1a3a4a"
HOVER = "#2a4a5a"

# ── Global stylesheet ─────────────────────────────────────────────────────────
_QSS = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI";
    font-size: 11px;
}}
QLabel {{ background-color: transparent; }}

QPushButton {{
    background-color: {BTN2};
    color: {TEXT};
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover    {{ background-color: {HOVER}; }}
QPushButton:pressed  {{ background-color: {BTN2}; }}
QPushButton:disabled {{ background-color: #0f2535; color: #334455; }}

QPushButton#accent {{
    background-color: {ACCENT};
    color: {BG};
    font-weight: bold;
    font-size: 13px;
    padding: 8px 12px;
}}
QPushButton#accent:hover    {{ background-color: #22ddef; }}
QPushButton#accent:disabled {{ background-color: #005566; color: #334455; }}

QPushButton#update-ready {{
    background-color: #1a5c1a;
    color: {TEXT};
}}
QPushButton#update-ready:hover {{ background-color: #237023; }}

QListWidget {{
    background-color: {BG};
    border: 1px solid {BTN2};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item           {{ padding: 3px 6px; }}
QListWidget::item:selected  {{ background-color: {BTN2}; color: {ACCENT}; }}
QListWidget::item:hover     {{ background-color: #0f2535; }}

QTextEdit {{
    background-color: {BG};
    border: 1px solid {BTN2};
    border-radius: 4px;
    color: {TEXT};
    font-family: "Consolas";
    font-size: 10px;
    padding: 4px;
}}

QLineEdit {{
    background-color: {BG};
    border: 1px solid {BTN2};
    border-radius: 4px;
    color: {TEXT};
    padding: 4px 8px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}

QProgressBar {{
    background-color: {BG};
    border: 1px solid {BTN2};
    border-radius: 3px;
    max-height: 8px;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}

QSplitter::handle:horizontal {{
    background-color: {BTN2};
    width: 2px;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {BTN2};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover   {{ background-color: {HOVER}; }}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical       {{ height: 0px; }}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical       {{ background: none; }}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {BTN2};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {HOVER}; }}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal     {{ width: 0px; }}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal     {{ background: none; }}
"""

_MAP_BTN_QSS = f"""
QPushButton {{
    background-color: #152535;
    color: {TEXT};
    font-size: 14px;
    border: 1px solid {BTN2};
    border-radius: 4px;
    padding: 0px;
}}
QPushButton:hover   {{ background-color: {BTN2}; color: {ACCENT}; }}
QPushButton:checked {{ background-color: {BTN2}; color: {ACCENT}; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #334455; border-color: #0f2535; }}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ver(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


class _Redirect:
    def __init__(self, fn):
        self._fn = fn
    def write(self, text: str):
        if text:
            self._fn(text)
    def flush(self):
        pass


# ── Workers ───────────────────────────────────────────────────────────────────

class PipelineWorker(QThread):
    log_message  = pyqtSignal(str)
    progress_set = pyqtSignal(float)        # –1 = indeterminate, 0–1 = determinate
    finished_ok  = pyqtSignal(list, list)   # coords, route  (plain data — no Qt objects)
    finished_err = pyqtSignal(str)

    def __init__(self, files: list, parent=None):
        super().__init__(parent)
        self._files = files

    def run(self):
        from extract import unload_reader
        old_stdout = sys.stdout
        sys.stdout = _Redirect(self.log_message.emit)
        try:
            from extract import _get_reader, extract_coordinates
            from route import solve_tsp

            self.log_message.emit("Loading OCR engine...\n")
            self.progress_set.emit(-1.0)
            _get_reader()

            def on_progress(current, total):
                self.progress_set.emit(current / total)

            coords = extract_coordinates(self._files, progress_callback=on_progress)

            if not coords:
                self.log_message.emit("\nNo coordinates found.\n")
                self.finished_err.emit("No coordinates found.")
                return

            route = solve_tsp(coords)
            total_dist = sum(
                ((coords[route[i]][0] - coords[route[i - 1]][0]) ** 2 +
                 (coords[route[i]][1] - coords[route[i - 1]][1]) ** 2) ** 0.5
                for i in range(1, len(route))
            )
            self.log_message.emit(
                f"\nOptimal route — {len(coords)} stops, distance {total_dist:.1f}\n"
            )
            for step, idx in enumerate(route, 1):
                lat, lon = coords[idx]
                self.log_message.emit(f"  Step {step:3d}:  Lat {lat:6.2f}  Long {lon:6.2f}\n")

            # Emit raw data only — PlotWidget must be created on the main thread
            self.finished_ok.emit(coords, route)

        except Exception as exc:
            import traceback
            self.finished_err.emit(str(exc) + "\n" + traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            unload_reader()
            self.log_message.emit("OCR engine unloaded.\n")


class UpdateWorker(QThread):
    up_to_date   = pyqtSignal()
    update_found = pyqtSignal(str, str, str)   # tag, zip_url, exe_url
    error        = pyqtSignal(str)

    def run(self):
        try:
            req = urllib.request.Request(
                _GITHUB_API, headers={"User-Agent": "ark-dino-pathfinder"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            tag = data["tag_name"].lstrip("v")
            if _ver(tag) <= _ver(VERSION):
                self.up_to_date.emit()
                return
            assets = data.get("assets", [])
            zip_url = next(
                (a["browser_download_url"] for a in assets
                 if a["name"].lower().endswith(".zip")),
                "",
            )
            exe_url = next(
                (a["browser_download_url"] for a in assets
                 if a["name"].lower().endswith(".exe")),
                "",
            )
            if not zip_url and not exe_url:
                self.error.emit("No update assets found in release.")
                return
            self.update_found.emit(tag, zip_url, exe_url)
        except Exception as exc:
            self.error.emit(str(exc))


class DownloadWorker(QThread):
    done     = pyqtSignal(str, bool)   # path, is_staged (True=staging dir, False=installer exe)
    error    = pyqtSignal(str)
    progress = pyqtSignal(int)         # 0-100

    def __init__(self, url: str, is_zip: bool = False, parent=None):
        super().__init__(parent)
        self._url    = url
        self._is_zip = is_zip

    def _reporthook(self, block_num, block_size, total_size):
        if total_size > 0:
            self.progress.emit(min(99, int(block_num * block_size * 100 / total_size)))

    def run(self):
        try:
            if self._is_zip:
                tmp = Path(tempfile.mktemp(suffix=".zip"))
                urllib.request.urlretrieve(self._url, str(tmp), reporthook=self._reporthook)
                staging = Path(tempfile.mkdtemp(prefix="ARKUpdate_"))
                with zipfile.ZipFile(tmp) as zf:
                    zf.extractall(staging)
                tmp.unlink()
                self.progress.emit(100)
                self.done.emit(str(staging), True)
            else:
                tmp = Path(tempfile.mktemp(suffix=".exe"))
                urllib.request.urlretrieve(self._url, str(tmp), reporthook=self._reporthook)
                self.progress.emit(100)
                self.done.emit(str(tmp), False)
        except Exception as exc:
            self.error.emit(str(exc))


# ── Card widget ───────────────────────────────────────────────────────────────

class Card(QFrame):
    """Rounded dark-navy panel painted directly to avoid stylesheet cascade."""

    def __init__(self, parent=None, radius: int = 8):
        super().__init__(parent)
        self._radius = radius
        self._color = QColor(CARD)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self._color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), self._radius, self._radius)


# ── Standalone map window ─────────────────────────────────────────────────────

class MapWindow(QMainWindow):
    """Popup map window opened via 'Open in Window'."""

    def __init__(self, coords, route, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ARK Dino Pathfinder — Map")
        self.resize(1000, 750)
        self.setStyleSheet(_QSS)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        from visualize import plot_route
        self._plot_widget, self._toggle_realms_fn = plot_route(coords, route)

        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet(f"background-color: {CARD};")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(6, 4, 6, 4)
        tb_lay.setSpacing(4)

        self._btns: dict = {}
        for sym, tip, name, checkable in [
            ("+", "Zoom in",        "zoom_in",  False),
            ("−", "Zoom out",       "zoom_out", False),
            ("◈", "Realm overlays", "realms",   True),
            ("⟳", "Reset view",     "reset",    False),
        ]:
            btn = QPushButton(sym)
            btn.setFixedSize(30, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet(_MAP_BTN_QSS)
            btn.setCheckable(checkable)
            self._btns[name] = btn
            tb_lay.addWidget(btn)

        lay.addWidget(toolbar)
        lay.addWidget(self._plot_widget, 1)

        self._btns["zoom_in"].clicked.connect(lambda: self._zoom(0.75))
        self._btns["zoom_out"].clicked.connect(lambda: self._zoom(1.33))
        self._btns["realms"].toggled.connect(lambda _: self._toggle_realms_fn())
        self._btns["reset"].clicked.connect(self._plot_widget.autoRange)

    def _zoom(self, factor: float):
        self._plot_widget.getViewBox().scaleBy((factor, factor))

    def _apply_overlay(self):
        """Auto-called when the window is opened. Enables always-on-top + click-through."""
        pos = self.pos()
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.move(pos)
        self.show()   # re-creates native window; winId() must be called after this

        # WS_EX_LAYERED + WS_EX_TRANSPARENT: all mouse input passes through to
        # whatever window is underneath, so ARK receives all clicks and scrolls.
        try:
            import ctypes
            _GWL_EXSTYLE       = -20
            _WS_EX_LAYERED     = 0x00080000
            _WS_EX_TRANSPARENT = 0x00000020
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, _GWL_EXSTYLE, style | _WS_EX_LAYERED | _WS_EX_TRANSPARENT
            )
        except Exception:
            pass

        self.setWindowOpacity(0.6)
        self.setWindowTitle("ARK Dino Pathfinder — Map  ▶  OVERLAY")

    def _remove_overlay(self):
        try:
            import ctypes
            _GWL_EXSTYLE       = -20
            _WS_EX_TRANSPARENT = 0x00000020
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, _GWL_EXSTYLE, style & ~_WS_EX_TRANSPARENT
            )
        except Exception:
            pass
        pos = self.pos()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.move(pos)
        self.show()
        self.setWindowOpacity(1.0)
        self.setWindowTitle("ARK Dino Pathfinder — Map")


# ── Main window ───────────────────────────────────────────────────────────────

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARK Dino Pathfinder")
        self.resize(1140, 720)
        self.setMinimumSize(820, 560)

        self._selected_files: list = []
        self._paste_dir = tempfile.mkdtemp()
        self._paste_count = 0
        self._plot_widget: QWidget | None = None
        self._toggle_realms_fn = None
        self._pipeline: PipelineWorker | None = None
        self._update_worker: UpdateWorker | None = None
        self._dl_worker: DownloadWorker | None = None
        self._coords: list | None = None
        self._route: list | None = None
        self._map_windows: list = []   # keep references so windows aren't GC'd

        self.setAcceptDrops(True)
        self._cleanup_old_files()
        self._build_ui()

    def _cleanup_old_files(self):
        if not getattr(sys, "frozen", False):
            return
        for f in Path(sys.executable).parent.glob("*.exe.old"):
            try:
                f.unlink()
            except Exception:
                pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 800])
        outer.addWidget(splitter)

    def _build_left(self) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(260)
        w.setMaximumWidth(440)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(8)

        # Title
        title = QLabel("ARK Dino Pathfinder")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {ACCENT};")
        sub = QLabel("by matt430")
        sub.setStyleSheet(f"font-size: 10px; color: {TEXT};")
        ver = QLabel(f"v{VERSION}")
        ver.setStyleSheet(f"font-size: 10px; color: {DIM};")
        ver.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.addWidget(title)
        title_col.addWidget(sub)
        title_row = QHBoxLayout()
        title_row.addLayout(title_col)
        title_row.addWidget(ver, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        lay.addLayout(title_row)

        # Screenshots card
        sc = Card()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(10, 10, 10, 10)
        sc_lay.setSpacing(6)
        sc_hdr = QHBoxLayout()
        sc_lbl = QLabel("Screenshots")
        sc_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        add_btn = QPushButton("Add Files")
        add_btn.setFixedHeight(26)
        add_btn.clicked.connect(self._add_files)
        clr_btn = QPushButton("Clear")
        clr_btn.setFixedHeight(26)
        clr_btn.clicked.connect(self._clear_files)
        sc_hdr.addWidget(sc_lbl)
        sc_hdr.addStretch()
        sc_hdr.addWidget(add_btn)
        sc_hdr.addWidget(clr_btn)
        sc_lay.addLayout(sc_hdr)
        self._file_list = QListWidget()
        self._file_list.setFixedHeight(100)
        self._file_list.installEventFilter(self)
        sc_lay.addWidget(self._file_list)
        lay.addWidget(sc)

        # Run button
        self._run_btn = QPushButton("▶   Run")
        self._run_btn.setObjectName("accent")
        self._run_btn.setFixedHeight(42)
        self._run_btn.clicked.connect(self._run)
        lay.addWidget(self._run_btn)

        # Progress bar (hidden until pipeline)
        self._progress = QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(8)
        self._progress.setRange(0, 100)
        self._progress.hide()
        lay.addWidget(self._progress)

        # Log card
        lc = Card()
        lc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lc_lay = QVBoxLayout(lc)
        lc_lay.setContentsMargins(10, 8, 10, 8)
        lc_lay.setSpacing(4)
        log_lbl = QLabel("Log")
        log_lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
        lc_lay.addWidget(log_lbl)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lc_lay.addWidget(self._log)
        lay.addWidget(lc, 1)

        # Updates button
        self._upd_btn = QPushButton("Check for Updates")
        self._upd_btn.setFixedHeight(28)
        self._upd_btn.clicked.connect(self._check_for_updates)
        lay.addWidget(self._upd_btn)

        return w

    def _build_right(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(8)

        # Map card
        mc = Card()
        mc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        mc_lay = QVBoxLayout(mc)
        mc_lay.setContentsMargins(10, 10, 10, 10)
        mc_lay.setSpacing(6)

        # Card header
        hdr = QHBoxLayout()
        hdr.addWidget(_bold_label("Map Preview"))
        hdr.addStretch()

        # Toolbar buttons: zoom in/out, realms toggle, reset view
        # Pan is always-on (left-drag) so no pan button needed
        self._map_btns: dict = {}
        for sym, tip, name, checkable in [
            ("+", "Zoom in",    "zoom_in",  False),
            ("−", "Zoom out",   "zoom_out", False),
            ("◈", "Realms",     "realms",   True),
            ("⟳", "Reset view", "reset",    False),
        ]:
            btn = QPushButton(sym)
            btn.setFixedSize(30, 26)
            btn.setToolTip(tip)
            btn.setStyleSheet(_MAP_BTN_QSS)
            btn.setEnabled(False)
            btn.setCheckable(checkable)
            self._map_btns[name] = btn
            hdr.addWidget(btn)

        mc_lay.addLayout(hdr)

        # Container that holds either the placeholder or the PlotWidget
        self._map_container = QWidget()
        self._map_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._map_lay = QVBoxLayout(self._map_container)
        self._map_lay.setContentsMargins(0, 0, 0, 0)
        self._show_placeholder()
        mc_lay.addWidget(self._map_container, 1)
        lay.addWidget(mc, 1)

        # Download / open row
        dl_row = QHBoxLayout()
        dl_row.addStretch()
        self._popup_overlay_btn = QPushButton("🎮   Game Overlay")
        self._popup_overlay_btn.setFixedHeight(32)
        self._popup_overlay_btn.setCheckable(True)
        self._popup_overlay_btn.setEnabled(False)
        self._popup_overlay_btn.setToolTip("Toggle click-through overlay on the popup map window")
        self._popup_overlay_btn.toggled.connect(self._toggle_popup_overlay)
        dl_row.addWidget(self._popup_overlay_btn)
        self._open_btn = QPushButton("⧉   Open in Window")
        self._open_btn.setFixedHeight(32)
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_in_window)
        dl_row.addWidget(self._open_btn)
        self._dl_btn = QPushButton("↓   Download Map")
        self._dl_btn.setFixedHeight(32)
        self._dl_btn.setEnabled(False)
        self._dl_btn.clicked.connect(self._download_map)
        dl_row.addWidget(self._dl_btn)
        lay.addLayout(dl_row)

        self._map_btns["zoom_in"].clicked.connect(lambda: self._zoom(0.75))
        self._map_btns["zoom_out"].clicked.connect(lambda: self._zoom(1.33))
        self._map_btns["realms"].toggled.connect(self._on_realms_toggled)
        self._map_btns["reset"].clicked.connect(self._reset_view)

        return w

    # ── Map helpers ───────────────────────────────────────────────────────────

    def _show_placeholder(self):
        ph = QWidget()
        ph.setStyleSheet(f"background-color: {CARD};")
        ph_lay = QVBoxLayout(ph)
        lbl = QLabel("Run to generate map")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {DIM}; font-size: 13px; background: transparent;")
        ph_lay.addWidget(lbl)
        self._set_plot_widget(ph)

    def _set_plot_widget(self, widget: QWidget):
        if self._plot_widget is not None:
            self._map_lay.removeWidget(self._plot_widget)
            self._plot_widget.deleteLater()
        self._plot_widget = widget
        self._plot_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._map_lay.addWidget(self._plot_widget)

    def _zoom(self, factor: float):
        if isinstance(self._plot_widget, pg.PlotWidget):
            self._plot_widget.getViewBox().scaleBy((factor, factor))

    def _on_realms_toggled(self, _checked: bool):
        if self._toggle_realms_fn:
            self._toggle_realms_fn()

    def _reset_view(self):
        if isinstance(self._plot_widget, pg.PlotWidget):
            self._plot_widget.autoRange()

    def _open_in_window(self):
        if self._coords is None or self._route is None:
            return
        win = MapWindow(self._coords, self._route, parent=None)
        win.destroyed.connect(lambda: self._on_popup_closed(win))
        self._map_windows.append(win)
        win.show()
        self._popup_overlay_btn.setEnabled(True)
        if self._popup_overlay_btn.isChecked():
            win._apply_overlay()

    def _download_map(self):
        if not isinstance(self._plot_widget, pg.PlotWidget):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Map Image", "route_map.png", "PNG Image (*.png)"
        )
        if path:
            pixmap = self._plot_widget.grab()
            pixmap.save(path, "PNG")
            self._log_append(f"Map saved: {path}\n")

    def _set_map_btns_enabled(self, enabled: bool):
        for btn in self._map_btns.values():
            btn.setEnabled(enabled)

    def _toggle_popup_overlay(self, checked: bool):
        for win in self._map_windows:
            if checked:
                win._apply_overlay()
            else:
                win._remove_overlay()

    def _on_popup_closed(self, win):
        if win in self._map_windows:
            self._map_windows.remove(win)
        if not self._map_windows:
            self._popup_overlay_btn.blockSignals(True)
            self._popup_overlay_btn.setChecked(False)
            self._popup_overlay_btn.blockSignals(False)
            self._popup_overlay_btn.setEnabled(False)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            for win in self._map_windows:
                if win.isMinimized():
                    win.showNormal()
        super().changeEvent(event)

    def closeEvent(self, event):
        for win in list(self._map_windows):
            win.close()
        event.accept()

    # ── Drag and drop ─────────────────────────────────────────────────────────

    _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(
            Path(u.toLocalFile()).suffix.lower() in self._IMAGE_EXTS
            for u in event.mimeData().urls() if u.isLocalFile()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        added = False
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in self._IMAGE_EXTS and path not in self._selected_files:
                self._selected_files.append(path)
                added = True
        if added:
            self._refresh_file_list()
        event.acceptProposedAction()

    # ── File helpers ──────────────────────────────────────────────────────────

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Dino Scanner screenshots",
            filter="Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All files (*.*)",
        )
        for p in paths:
            if p not in self._selected_files:
                self._selected_files.append(p)
        self._refresh_file_list()

    def eventFilter(self, obj, event):
        if obj is self._file_list and event.type() == QEvent.Type.KeyPress:
            if (event.key() == Qt.Key.Key_V and
                    event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self._paste_image()
                return True
        return super().eventFilter(obj, event)

    def _paste_image(self):
        from PIL import ImageGrab
        try:
            img = ImageGrab.grabclipboard()
        except Exception:
            return
        if img is None:
            return
        self._paste_count += 1
        path = str(Path(self._paste_dir) / f"pasted_{self._paste_count}.png")
        img.save(path, "PNG")
        if path not in self._selected_files:
            self._selected_files.append(path)
        self._refresh_file_list()

    def _clear_files(self):
        self._selected_files.clear()
        self._refresh_file_list()

    def _refresh_file_list(self):
        self._file_list.clear()
        for p in self._selected_files:
            self._file_list.addItem(Path(p).name)

    # ── Log ───────────────────────────────────────────────────────────────────

    def _log_append(self, text: str):
        self._log.moveCursor(self._log.textCursor().MoveOperation.End)
        self._log.insertPlainText(text)
        self._log.ensureCursorVisible()

    # ── Progress ──────────────────────────────────────────────────────────────

    def _on_progress(self, value: float):
        if self._progress.isHidden():
            self._progress.show()
        if value < 0:
            self._progress.setRange(0, 0)       # indeterminate (OCR loading)
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(int(value * 100))

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _run(self):
        if not self._selected_files:
            self._log_append("No screenshots selected.\n")
            return
        self._log.clear()
        self._run_btn.setEnabled(False)
        self._pipeline = PipelineWorker(list(self._selected_files))
        self._pipeline.log_message.connect(self._log_append)
        self._pipeline.progress_set.connect(self._on_progress)
        self._pipeline.finished_ok.connect(self._on_pipeline_done)
        self._pipeline.finished_err.connect(self._on_pipeline_error)
        self._pipeline.start()

    def _on_pipeline_done(self, coords: list, route: list):
        # PlotWidget must be created on the main thread — do it here
        from visualize import plot_route
        plot_widget, toggle_fn = plot_route(coords, route)

        # Reset realms button without triggering the old toggle fn
        self._map_btns["realms"].blockSignals(True)
        self._map_btns["realms"].setChecked(False)
        self._map_btns["realms"].blockSignals(False)

        self._toggle_realms_fn = toggle_fn
        self._set_plot_widget(plot_widget)
        self._set_map_btns_enabled(True)
        self._dl_btn.setEnabled(True)
        self._open_btn.setEnabled(True)
        self._progress.hide()
        self._run_btn.setEnabled(True)
        self._coords = coords
        self._route = route

    def _on_pipeline_error(self, msg: str):
        self._log_append(f"\nError: {msg}\n")
        self._progress.hide()
        self._run_btn.setEnabled(True)

    # ── Auto-updater ──────────────────────────────────────────────────────────

    def _check_for_updates(self):
        self._upd_btn.setEnabled(False)
        self._upd_btn.setText("Checking...")
        self._update_worker = UpdateWorker()
        self._update_worker.up_to_date.connect(self._on_up_to_date)
        self._update_worker.update_found.connect(self._on_update_found)
        self._update_worker.error.connect(self._on_update_error)
        self._update_worker.start()

    def _on_up_to_date(self):
        self._log_append(f"Already up to date (v{VERSION}).\n")
        self._upd_btn.setText("Check for Updates")
        self._upd_btn.setEnabled(True)

    def _on_update_error(self, msg: str):
        self._log_append(f"Update check failed: {msg}\n")
        self._upd_btn.setText("Check for Updates")
        self._upd_btn.setEnabled(True)

    def _on_update_found(self, tag: str, zip_url: str, exe_url: str):
        if zip_url:
            self._log_append(f"Update available: v{tag} — downloading in background...\n")
            self._dl_worker = DownloadWorker(zip_url, is_zip=True)
        else:
            self._log_append(f"Update available: v{tag} — downloading installer...\n")
            self._dl_worker = DownloadWorker(exe_url, is_zip=False)
        self._upd_btn.setText("Downloading... 0%")
        self._dl_worker.progress.connect(lambda pct: self._upd_btn.setText(f"Downloading... {pct}%"))
        self._dl_worker.done.connect(self._on_download_done)
        self._dl_worker.error.connect(self._on_update_error)
        self._dl_worker.start()

    def _on_download_done(self, path: str, is_staged: bool):
        self._update_path     = path
        self._update_is_staged = is_staged
        if is_staged:
            self._log_append("Ready! Click 'Relaunch to Update' — swap will be instant.\n")
        else:
            self._log_append("Download complete! Click 'Relaunch to Update' to apply.\n")
        self._upd_btn.setObjectName("update-ready")
        self._upd_btn.setStyle(self._upd_btn.style())
        self._upd_btn.setText("Relaunch to Update")
        self._upd_btn.setEnabled(True)
        self._upd_btn.clicked.disconnect()
        self._upd_btn.clicked.connect(self._relaunch)

    def _relaunch(self):
        if getattr(self, "_update_is_staged", False):
            self._relaunch_from_staging()
        else:
            self._relaunch_from_installer()

    def _relaunch_from_installer(self):
        subprocess.Popen(
            [self._update_path, "/VERYSILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sys.exit()

    def _relaunch_from_staging(self):
        if not getattr(sys, "frozen", False):
            self._log_append("Staging update not supported in dev mode.\n")
            return
        install_dir = Path(sys.executable).parent
        staging_dir = self._update_path
        new_exe     = install_dir / "gui.exe"
        pid         = os.getpid()
        ps = (
            f'try {{ Wait-Process -Id {pid} -ErrorAction SilentlyContinue }} catch {{}}\n'
            f'Start-Sleep -Milliseconds 500\n'
            f'Copy-Item -Path "{staging_dir}\\*" -Destination "{install_dir}" -Recurse -Force\n'
            f'Start-Process "{new_exe}"\n'
            f'Remove-Item -Path "{staging_dir}" -Recurse -Force -ErrorAction SilentlyContinue\n'
        )
        script = Path(tempfile.mktemp(suffix=".ps1"))
        script.write_text(ps, encoding="utf-8")
        subprocess.Popen(
            ["powershell.exe", "-NonInteractive", "-WindowStyle", "Hidden",
             "-ExecutionPolicy", "Bypass", "-File", str(script)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sys.exit()


# ── Utility ───────────────────────────────────────────────────────────────────

def _bold_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
    return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_QSS)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base,            QColor(BG))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(CARD))
    palette.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button,          QColor(BTN2))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(BG))
    app.setPalette(palette)

    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
