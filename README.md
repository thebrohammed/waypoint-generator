# 🛰️ RSSA Waypoint Generator

A modern Python GUI for building `.waypoints` files for ArduPilot missions.  The
app converts fertilizer application data into servo PWM commands and provides
rich visualisation tools for calibration and swath width tuning.

---

## 📦 Features

* Load a CSV of target points (`Fertilizer` and `Target Coordinates` columns)
* Load valve calibration data (`Valve`, `Avg quantity(g)`)
* Load disc swath width calibration (`PWM`, `Swath Width(m)`)
* Interpolate valve and disc PWM values automatically
* Optional take‑off command at mission start
* Colour‑coded waypoint visualisation with PWM annotations
* Export plots as PNG/PDF
* Edit and save generated QGroundControl `.waypoints` files

---

## 🧪 Input CSV Formats

### Waypoints
| Column | Description |
|--------|-------------|
| `Fertilizer` | Fertiliser quantity in grams |
| `Target Coordinates` | `lat, lon` pair |

### Valve Calibration
| Column | Description |
|--------|-------------|
| `Valve` | PWM microseconds |
| `Avg quantity(g)` | Flow rate in g/s |

### Disc Swath Calibration
| Column | Description |
|--------|-------------|
| `PWM` | Disc servo PWM |
| `Swath Width(m)` | Resulting swath width |

A sample `sample.csv` is included in the repository.

---

## ▶️ Running

```bash
python waypoint/waypoint_generator.py
```

---

## 🧾 Dependencies

```
pip install pandas matplotlib ttkbootstrap geopy pillow numpy
```

`tkinter` comes with Python.

---

## 🧊 Build a Stand‑alone Executable

1. Install PyInstaller
   ```bash
   pip install pyinstaller
   ```
2. From the repository root run
   ```bash
   pyinstaller --noconfirm --windowed --onefile waypoint/waypoint_generator.py \
       --add-data "waypoint/app_icon.ico;." \
       --add-data "waypoint/left_image.png;." \
       --add-data "waypoint/right_image.png;."
   ```
   *Use `:` instead of `;` on macOS/Linux.*

The helper `resource_path` function in the script locates these bundled assets,
and the resulting executable will appear in the `dist/` folder.

---

## 👤 Author

**Mohammed Haneef**  
Project Associate – UAV Systems  
DGCA‑Certified Remote Pilot  
CSIR‑NAL, India

---
