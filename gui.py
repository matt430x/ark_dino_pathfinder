"""ARK Dino Pathfinder — GUI entry point (customtkinter)."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from extract import extract_coordinates
from route import solve_tsp
from visualize import plot_route

VERSION = "1.1"
_GITHUB_API = "https://api.github.com/repos/matt430x/ark_dino_pathfinder/releases/latest"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ARK Dino Pathfinder")
        self.geometry("640x700")
        self.resizable(False, False)
        self.configure(fg_color="#0d1f2d")
        self._selected_files: list[str] = []
        self._paste_dir = tempfile.mkdtemp()
        self._paste_count = 0
        self._cleanup_old_files()
        self._build_ui()
        threading.Thread(target=self._preload, daemon=True).start()

    def _cleanup_old_files(self):
        """Remove leftover temp files from a previous update."""
        if not getattr(sys, "frozen", False):
            return
        app_dir = Path(sys.executable).parent
        for leftover in app_dir.glob("gui.exe.old"):
            try:
                leftover.unlink()
            except Exception:
                pass

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="ARK Dino Pathfinder",
            font=("Arial", 22, "bold"), text_color="cyan",
        ).pack(pady=(20, 2))
        ctk.CTkLabel(
            self, text="by matt430",
            font=("Arial", 11), text_color="#aaccdd",
        ).pack(pady=(0, 8))
        ctk.CTkLabel(
            self, text=f"v{VERSION}",
            font=("Arial", 11), text_color="#445566",
        ).place(relx=1.0, x=-20, y=20, anchor="ne")

        # ── file selection ────────────────────────────────────────────────
        file_frame = ctk.CTkFrame(self, fg_color="#102030", corner_radius=8)
        file_frame.pack(fill="x", padx=20, pady=8)

        btn_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(btn_row, text="Screenshots", text_color="#aaccdd",
                     font=("Arial", 13)).pack(side="left")
        ctk.CTkButton(btn_row, text="Clear", width=70,
                      fg_color="#1a3a4a", hover_color="#2a4a5a",
                      command=self._clear_files).pack(side="right", padx=(4, 0))
        ctk.CTkButton(btn_row, text="Add Files", width=90,
                      command=self._add_files).pack(side="right")

        self._file_box = ctk.CTkTextbox(
            file_frame, height=110,
            fg_color="#0d1f2d", text_color="#aaccdd",
            state="disabled",
        )
        self._file_box.pack(fill="x", padx=12, pady=(0, 10))
        self._file_box.bind("<Button-1>", lambda e: self._file_box.focus_set())
        self._file_box.bind("<Control-v>", self._paste_image)

        # ── output path ───────────────────────────────────────────────────
        out_frame = ctk.CTkFrame(self, fg_color="#102030", corner_radius=8)
        out_frame.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(out_frame, text="Output", text_color="#aaccdd",
                     font=("Arial", 13)).pack(side="left", padx=12, pady=10)
        self._out_var = ctk.StringVar(value="route_map.png")
        ctk.CTkEntry(out_frame, textvariable=self._out_var,
                     fg_color="#0d1f2d", text_color="white").pack(
            side="left", fill="x", expand=True, pady=10)
        ctk.CTkButton(out_frame, text="Browse", width=80,
                      command=self._browse_output).pack(side="right", padx=12, pady=10)

        # ── run button ────────────────────────────────────────────────────
        self._run_btn = ctk.CTkButton(
            self, text="Run", height=42,
            font=("Arial", 15, "bold"),
            command=self._run,
        )
        self._run_btn.pack(padx=20, pady=(0, 8), fill="x")

        # ── log ───────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Log", text_color="#aaccdd",
                     font=("Arial", 13)).pack(anchor="w", padx=20)
        self._log = ctk.CTkTextbox(
            self, fg_color="#0d1f2d", text_color="#aaccdd", state="disabled",
        )
        self._log.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        # ── bottom bar ────────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(bottom, text=f"v{VERSION}", text_color="#445566",
                     font=("Arial", 11)).pack(side="left")
        self._update_btn = ctk.CTkButton(
            bottom, text="Check for Updates", width=150,
            fg_color="#1a3a4a", hover_color="#2a4a5a",
            font=("Arial", 11),
            command=self._check_for_updates,
        )
        self._update_btn.pack(side="left", padx=(8, 0))

    # ── file helpers ──────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Dino Scanner screenshots",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All files", "*.*")],
        )
        for p in paths:
            if p not in self._selected_files:
                self._selected_files.append(p)
        self._refresh_file_box()

    def _paste_image(self, event=None):
        from PIL import ImageGrab
        try:
            img = ImageGrab.grabclipboard()
        except Exception:
            return "break"
        if img is None:
            return "break"
        self._paste_count += 1
        path = str(Path(self._paste_dir) / f"pasted_{self._paste_count}.png")
        img.save(path, "PNG")
        if path not in self._selected_files:
            self._selected_files.append(path)
        self._refresh_file_box()
        return "break"

    def _clear_files(self):
        self._selected_files.clear()
        self._refresh_file_box()

    def _refresh_file_box(self):
        self._file_box.configure(state="normal")
        self._file_box.delete("1.0", "end")
        for p in self._selected_files:
            self._file_box.insert("end", Path(p).name + "\n")
        self._file_box.configure(state="disabled")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile="route_map.png",
        )
        if path:
            self._out_var.set(path)

    # ── log helpers ───────────────────────────────────────────────────────

    def _log_write(self, text: str):
        self.after(0, self._log_append, text)

    def _log_append(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ── preload ───────────────────────────────────────────────────────────

    def _preload(self):
        """Import EasyOCR/PyTorch in the background so Run fires instantly."""
        from extract import _get_reader
        try:
            _get_reader()
        except Exception:
            pass

    # ── update ────────────────────────────────────────────────────────────

    def _check_for_updates(self):
        self._update_btn.configure(state="disabled", text="Checking...")
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        try:
            req = urllib.request.Request(
                _GITHUB_API, headers={"User-Agent": "ark-dino-pathfinder"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            tag = data["tag_name"].lstrip("v")

            def ver(v):
                return tuple(int(x) for x in v.split("."))

            if ver(tag) <= ver(VERSION):
                self.after(0, lambda: self._on_up_to_date())
                return

            download_url = next(
                (a["browser_download_url"] for a in data.get("assets", [])
                 if a["name"].endswith(".zip")),
                None,
            )
            if not download_url:
                self.after(0, lambda: self._on_update_error("No zip asset found in release."))
                return

            self.after(0, lambda: self._on_update_found(tag, download_url))

        except Exception as exc:
            self.after(0, lambda: self._on_update_error(str(exc)))

    def _on_up_to_date(self):
        self._log_append(f"Already up to date (v{VERSION}).\n")
        self._update_btn.configure(state="normal", text="Check for Updates")

    def _on_update_error(self, msg: str):
        self._log_append(f"Update check failed: {msg}\n")
        self._update_btn.configure(state="normal", text="Check for Updates")

    def _on_update_found(self, tag: str, download_url: str):
        self._log_append(f"Update available: v{tag} — downloading...\n")
        self._update_btn.configure(text="Downloading...", state="disabled")
        threading.Thread(
            target=self._do_download, args=(tag, download_url), daemon=True
        ).start()

    def _do_download(self, tag: str, download_url: str):
        try:
            tmp_zip = tempfile.mktemp(suffix=".zip")
            urllib.request.urlretrieve(download_url, tmp_zip)

            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(tmp_dir)
            os.unlink(tmp_zip)

            src_dir = self._find_exe_dir(tmp_dir)
            if not src_dir:
                self.after(0, lambda: self._on_update_error(
                    "Could not find gui.exe in downloaded update."))
                return

            self.after(0, lambda: self._on_download_complete(src_dir))

        except Exception as exc:
            self.after(0, lambda: self._on_update_error(str(exc)))

    def _find_exe_dir(self, root: str) -> str | None:
        for dirpath, _, files in os.walk(root):
            if "gui.exe" in files:
                return dirpath
        return None

    def _on_download_complete(self, src_dir: str):
        self._log_append("Download complete! Click 'Relaunch to Update' to apply.\n")
        self._update_btn.configure(
            text="Relaunch to Update",
            state="normal",
            fg_color="#1a5c1a",
            hover_color="#237023",
            command=lambda: self._do_relaunch(src_dir),
        )

    def _do_relaunch(self, src_dir: str):
        if not getattr(sys, "frozen", False):
            self._log_append("Auto-update only works in the packaged exe.\n")
            return

        app_dir = str(Path(sys.executable).parent)

        # Write a hidden batch script that copies files and relaunches after we exit
        bat_path = os.path.join(tempfile.gettempdir(), "ark_update.bat")
        bat = (
            "@echo off\n"
            "timeout /t 2 /nobreak > nul\n"
            f'robocopy "{src_dir}" "{app_dir}" /E /IS /IT /NFL /NDL /NJH /NJS /NC /NS /NP\n'
            f'start "" "{app_dir}\\gui.exe"\n'
            f'rmdir /s /q "{src_dir}"\n'
            'del "%~f0"\n'
        )
        with open(bat_path, "w") as f:
            f.write(bat)

        subprocess.Popen(
            ["cmd", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        sys.exit()

    # ── pipeline ──────────────────────────────────────────────────────────

    def _run(self):
        if not self._selected_files:
            self._log_append("No screenshots selected.\n")
            return
        self._run_btn.configure(state="disabled")
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        threading.Thread(target=self._pipeline, daemon=True).start()

    def _pipeline(self):
        old_stdout = sys.stdout
        sys.stdout = _Redirect(self._log_write)
        try:
            coords = extract_coordinates(list(self._selected_files))
            if not coords:
                self._log_write("\nNo coordinates found.\n")
                return
            route = solve_tsp(coords)
            total = sum(
                ((coords[route[i]][0] - coords[route[i - 1]][0]) ** 2
                 + (coords[route[i]][1] - coords[route[i - 1]][1]) ** 2) ** 0.5
                for i in range(1, len(route))
            )
            self._log_write(f"\nOptimal route — {len(coords)} stops, distance {total:.1f}\n")
            for step, idx in enumerate(route, 1):
                lat, lon = coords[idx]
                self._log_write(f"  Step {step:3d}:  Lat {lat:6.2f}  Long {lon:6.2f}\n")
            out = self._out_var.get()
            self.after(0, plot_route, coords, route, out)
        except Exception as exc:
            self._log_write(f"\nError: {exc}\n")
        finally:
            sys.stdout = old_stdout
            self.after(0, lambda: self._run_btn.configure(state="normal"))


class _Redirect:
    """Pipe stdout writes to the log widget."""
    def __init__(self, write_fn):
        self._write = write_fn

    def write(self, text: str):
        if text:
            self._write(text)

    def flush(self):
        pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
