# ARK Dino Pathfinder
**by matt430**

A tool for ARK: Survival Evolved / Ascended players that reads your Dino Scanner screenshots, extracts all the coordinates automatically using OCR, solves the optimal visit route, and displays it on an interactive map — so you never waste time backtracking across the map again.

<img width="885" height="883" alt="route_map" src="https://github.com/user-attachments/assets/c19d3970-d835-49ce-ac4f-e008c7a54094" />

---

## Features

- Automatically reads Lat/Long coordinates from Dino Scanner screenshots using OCR
- Deduplicates coordinates across multiple screenshots
- Solves the shortest possible route using a nearest-neighbor + 2-opt TSP algorithm
- Renders an interactive route map with labeled waypoints
- Shows Fjordur's three special realms (Asgard, Jotunheim, Vanaheim) as overlays
- Grid lines every 10 units for easy coordinate reading
- Press **L** to toggle realm outlines and legend on/off
- Pan and zoom the map interactively
- Saves the map as a PNG file
- Simple GUI — add screenshots by file picker or paste directly from clipboard

---

## Installation

### Step 1 — Download

Go to the [Releases](../../releases) page and download the latest dist.zip.

### Step 2 — Extract

Right-click the zip → **Extract All** → choose where you want the program to live (e.g. `C:\Programs\ARK Dino Pathfinder\`).

Do not move `gui.exe` out of its folder — it needs all the files next to it to run.

### Step 3 — Run

Double-click `gui.exe` inside the extracted folder.

> **Windows SmartScreen warning:** Windows may show a "Windows protected your PC" popup the first time you run it. This is normal for unsigned apps. Try these options in order:
> 1. Click **"More info"** → **"Run anyway"**
> 2. Right-click `gui.exe` → **Run as administrator**
> 3. Right-click `gui.exe` → **Properties** → check **"Unblock"** at the bottom → click OK, then try again

### Step 4 — First launch (internet required)

On the very first run, the OCR engine will automatically download its language model (~100 MB). This only happens once. Make sure you have an internet connection for the first launch.

---

## How to Use

### 1. Take your Dino Scanner screenshots

In ARK, open the Dino Scanner and let it populate the list of nearby creatures. Take a screenshot (`Win + PrintScreen` or your preferred method) for each page of results. The tool reads the **Lat.** and **Long.** columns from the scanner table.

### 2. Add your screenshots

You have two options:

**Option A — File picker**
Click **Add Files** and select one or more screenshot images (PNG, JPG, BMP, TIFF supported). You can add screenshots from multiple scans and the tool will deduplicate any overlapping coordinates automatically.

**Option B — Paste from clipboard**
Take a screenshot and copy it to your clipboard (`Win + Shift + S`, then copy, or use your screenshot tool). Click anywhere inside the screenshots box, then press **Ctrl+V**. The pasted image will be added as `pasted_1.png`, `pasted_2.png`, etc.

You can mix both methods freely.

Your screenshot should look like this:
<img width="1018" height="794" alt="s1" src="https://github.com/user-attachments/assets/7cf02798-2465-466e-9bd1-d89cd2038758" />

### 3. Set your output path (optional)

The map is saved as `route_map.png` by default. Click **Browse** to choose a different save location and filename.

### 4. Click Run

Hit the **Run** button. The log panel will show live progress:
- OCR scanning each screenshot
- Coordinates found
- Optimal route steps in order

Once complete, the route map opens in a new window and is saved to your output path.

### 5. Follow the route

The map shows:
- A **green star** marking your starting point (step 1)
- **Cyan dots** for each waypoint
- A **blue line** connecting them in optimal order
- Each waypoint labeled with its step number and exact coordinates

Follow the steps in order from the log or map for the shortest possible route.

> **Note on verticality:** The Dino Scanner only provides Lat/Long coordinates — it has no concept of altitude. If you arrive at a waypoint and the dino isn't there, it has either been killed by something else or it is above or below you (inside a cave, on a cliff, underwater, etc.). Look up and down before moving on.

---

## Map Controls

| Action | How |
|---|---|
| Pan | Click the four-arrow icon in the toolbar, then click and drag |
| Reset view | Click the house icon in the toolbar |
| Toggle realm overlays + legend | Press **L** on your keyboard |

---

## Realm Overlays

Fjordur has three special sub-realms. The map shows their approximate boundaries:

| Realm | Color |
|---|---|
| Asgard | Red |
| Jotunheim | Blue |
| Vanaheim | Green |

Press **L** to hide/show these overlays if they clutter your view.

> **Note:** The boundaries shown on the map are NOT exact. They may extend further outward or inward in some areas. The exact boundaries of the three sub-realms are extremely difficult to measure, so they have been approximated by going as far out into the corners as possible.

---

## Supported Maps

The coordinate extraction and route solver will work on any ARK map — only the realm overlays are Fjordur-specific.

---

## Troubleshooting

**No coordinates found**
- Make sure your screenshot clearly shows the Dino Scanner table with the **Lat.** and **Long.** column headers visible
- Avoid cropping out the headers
- Try taking a higher resolution screenshot

**Some coordinates are missing**
- The OCR engine can occasionally misread blurry or small text — take screenshots at a higher resolution or zoom in on the scanner table before screenshotting
- If your scanner shows multiple pages, screenshot each page separately and add them all

**The map window doesn't open**
- Check the log panel for any error messages
- Make sure you have not moved `gui.exe` out of its folder

**Slow first run**
- The first time you click Run after launching, the OCR engine loads into memory. Subsequent runs in the same session are much faster.

**Windows blocked the app with no "Run anyway" option**
- Right-click `gui.exe` → **Properties** → check **"Unblock"** at the bottom → OK
- Or open PowerShell and run: `Unblock-File -Path "C:\path\to\gui.exe"`

---

## Credits

Built by **matt430**

Uses:
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) for coordinate extraction
- [matplotlib](https://matplotlib.org/) for map rendering
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for the GUI
- [scipy](https://scipy.org/) for the TSP route solver
