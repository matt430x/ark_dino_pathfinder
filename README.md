# ARK Dino Pathfinder
**by matt430** · v2.1

A tool for ARK: Survival Evolved players that reads your Dino Scanner screenshots, extracts all GPS coordinates automatically using OCR, solves the optimal visit route, and displays it on an interactive embedded map — so you never waste time backtracking across the map again.

---

## Features

- Automatically reads Lat/Long coordinates from Dino Scanner screenshots using OCR
- Deduplicates coordinates across multiple screenshots
- Solves the shortest possible route using a nearest-neighbor + 2-opt TSP algorithm
- Embedded interactive map panel — no separate window needed
- Smart label placement with leader lines — every waypoint is labeled, overlapping labels are automatically pushed apart
- Shows Fjordur's three special realms (Asgard, Jotunheim, Vanaheim) as toggleable overlays
- Grid lines for easy coordinate reading
- Pan (left-drag), zoom (scroll wheel), and toolbar buttons for zoom in/out and reset view
- Download the map as a PNG, or pop it out into a separate interactive window
- All dependencies bundled — no internet connection required after install
- Add screenshots by file picker, drag-and-drop, or paste directly from clipboard (Ctrl+V)
- Check for updates and apply them in one click — no manual downloading

---

## Installation

### Step 1 — Download

Go to the [Releases](../../releases) page and download the latest `ARKDinoPathfinder_Setup_vX.X.exe`.

### Step 2 — Run the installer

Double-click the `.exe` and follow the setup wizard. The program installs to your user folder — no administrator password required.

> **Windows SmartScreen warning:** Windows may show a "Windows protected your PC" popup the first time you run the installer. This is normal for unsigned apps.
> 1. Click **"More info"** → **"Run anyway"**
> 2. If that option isn't available: right-click the installer → **Properties** → check **"Unblock"** → OK, then try again

### Step 3 — Run

Launch **ARK Dino Pathfinder** from the Start Menu or desktop shortcut.

All dependencies (including the OCR engine and language models) are fully bundled — no additional downloads happen on first launch.

---

## How to Use

### 1. Take your Dino Scanner screenshots

In ARK, open the Dino Scanner and let it populate the list of nearby creatures. Take a screenshot (`Win + PrintScreen` or your preferred method) for each page of results. The tool reads the **Lat.** and **Long.** columns from the scanner table.

Your screenshot should look like this:

<img width="1018" height="794" alt="dino scanner screenshot example" src="https://github.com/user-attachments/assets/7cf02798-2465-466e-9bd1-d89cd2038758" />

### 2. Add your screenshots

You have three options — mix and match freely:

**Option A — File picker**
Click **Add Files** and select one or more screenshot images (PNG, JPG, BMP, TIFF supported).

**Option B — Drag and drop**
Drag image files from Explorer directly onto the app window. They will be added instantly.

**Option C — Paste from clipboard**
Take a screenshot and copy it to your clipboard (`Win + Shift + S`, then copy, or use your screenshot tool). Click anywhere inside the screenshots list, then press **Ctrl+V**. The pasted image is added as `pasted_1.png`, `pasted_2.png`, etc.

You can add screenshots from multiple scans — duplicate coordinates are automatically removed.

### 3. Click Run

Hit the **Run** button. The log panel shows live progress:
- OCR engine loading
- Scanning each screenshot
- Coordinates found
- Optimal route steps in order

Once complete, the interactive map appears in the right panel.

The OCR engine is automatically unloaded after each run to free up GPU/CPU memory while you play.

### 4. Read the map

The map shows:
- A **green star** marking your starting point (step 1)
- **Cyan dots** for each waypoint
- A **blue line** connecting them in optimal order
- Each waypoint labeled with its step number and exact coordinates
- **Leader lines** connecting each label to its waypoint when labels would otherwise overlap

Follow the steps in order (also listed in the log) for the shortest possible route.

> **Note on verticality:** The Dino Scanner only provides Lat/Long — it has no altitude. If you arrive at a waypoint and the dino isn't there, check above and below you (caves, cliffs, underwater, etc.).

---

## Map Controls

| Action | How |
|---|---|
| Pan | Left-click and drag |
| Zoom | Scroll wheel |
| Zoom in / out | **+** / **−** buttons in the map toolbar |
| Toggle realm overlays | **◈** button in the map toolbar |
| Reset view | **⟳** button in the map toolbar |
| Download map as PNG | **↓ Download Map** button (bottom right) |
| Open map in a separate window | **⧉ Open in Window** button (bottom right) |

The "Open in Window" button opens a fully interactive copy of the map in its own resizable window with its own toolbar. You can open as many copies as you like and interact with each one independently.

The popup toolbar has the same `+`, `−`, `◈`, `⟳` controls as the main window, plus a `📌` always-on-top toggle to keep the map above ARK.

---

## Realm Overlays (Fjordur)

Fjordur has three special sub-realms. Enable them with the **◈** button in the map toolbar:

| Realm | Color |
|---|---|
| Asgard | Red (dashed) |
| Jotunheim | Blue (dashed) |
| Vanaheim | Green (dashed) |

> **Note:** The boundaries shown are approximations. The exact edges of each sub-realm are difficult to measure and may vary slightly in-game.

---

## Supported Maps

The coordinate extraction and route solver work on any ARK map. The realm overlays are Fjordur-specific and have no effect on other maps.

---

## Troubleshooting

**No coordinates found**
- Make sure your screenshot clearly shows the Dino Scanner table with the **Lat.** and **Long.** column headers visible — don't crop them out
- Try taking a higher resolution screenshot

**Some coordinates are missing**
- The OCR engine can occasionally misread blurry or small text — try screenshotting at higher resolution or zooming in on the scanner before screenshotting
- If your scanner spans multiple pages, screenshot each page separately and add them all

**Slow first run after launch**
- The OCR engine loads into memory the first time you click Run after opening the app. Subsequent runs in the same session are faster. The engine is unloaded after each run to keep memory free.

**Windows blocked the installer with no "Run anyway" option**
- Right-click the installer → **Properties** → check **"Unblock"** → OK
- Or open PowerShell: `Unblock-File -Path "C:\path\to\ARKDinoPathfinder_Setup_vX.X.exe"`

---

## Updating

Click **Check for Updates** in the bottom left of the app. It checks GitHub for the latest release and compares it to your installed version (shown in the top right).

- If you're up to date, the log will say so
- If an update is available, it downloads the new installer automatically — the button turns green and reads **Relaunch to Update**
- Click **Relaunch to Update** — the app closes and the new installer runs silently. The app relaunches automatically when done

An internet connection is required to check for and download updates.

---

## Building from Source

Requirements: Python 3.11+, the packages in `requirements.txt`, and [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in dev mode
python main.py

# Build the installer (downloads OCR models if needed, then builds exe + installer)
build.bat
```

The installer is written to `installer_output\ARKDinoPathfinder_Setup_v2.1.exe`.

---

## Credits

Built by **matt430**

Uses:
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) for coordinate extraction
- [PyQtGraph](https://www.pyqtgraph.org/) for interactive map rendering
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI
- [scipy](https://scipy.org/) for the TSP route solver
- [Pillow](https://python-pillow.org/) for image handling
