# 🛰️ Waypoint Generator for ArduPilot

A user-friendly Python GUI application to generate `.waypoints` files for ArduPilot-based drones. Designed for agricultural field operations, it maps fertilizer dispense rates to PWM values (1000–2000 µs), assigns them to servo channels, and visualizes coordinates in a grid format.

---

## 📦 Features

- Load CSV files containing midpoint coordinates and fertilizer amounts
- Map dispense rates (in g/s) to PWM values from **1000 µs to 2000 µs** at **100 µs intervals**
- Assign servo output channel via dropdown (1–16)
- Visualize the grid points on a 2D plot
- Generate `.waypoints` file compatible with **Mission Planner** / **ArduPilot**

---

## 📁 Folder Structure

```

waypoint-generator/
│
├── waypoint\_generator.py      # Main GUI script
├── README.md                  # This file
├── sample.csv                 # Sample input CSV
└── preview\.png                # Optional screenshot of GUI

```

---

## 🧪 Input CSV Format

The tool expects a CSV file with the following columns:

| Grids | Fertilizer | Midpoint       |
|-------|----------------------|----------------|
| 1     | 7.2                  | 12.9321, 77.6215 |
| 2     | 5.6                  | 12.9322, 77.6216 |

- `Fertilizer` → fertilizer quantity (in grams)
- `Midpoint` → comma-separated latitude and longitude

---

## ✅ Output File

Generates a `.waypoints` file with entries like:

```

QGC WPL 110
0	0	3	16	0	0	0	0	12.9321000	77.6215000	10.00	1
1	0	3	183	9	1350	0	0	0	0	0	1

````

This can be imported directly into **Mission Planner**.

---

## 🔧 Installation Instructions

### ✅ Step 1: Install Python

If Python is not already installed:

- Download from: https://www.python.org/downloads/
- During installation, check ✅ "Add Python to PATH"

### ✅ Step 2: Clone or Download the Project

Download this repository as a ZIP and extract it, or clone via Git:

```bash
git clone https://github.com/your-username/waypoint-generator.git
cd waypoint-generator
````

### ✅ Step 3: Create a Virtual Environment (optional but recommended)

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

### ✅ Step 4: Install Required Packages

This project uses only two external libraries:

```bash
pip install pandas matplotlib
```

---

## ▶️ Running the Application

Once installed, simply run:

```bash
python waypoint_generator.py
```

A graphical user interface (GUI) will open where you can:

1. Browse and select your CSV file
2. Enter:

   * Altitude and speed
   * Flow rates for PWM values (1000–2000 µs at 100 µs steps)
   * Servo channel to use (dropdown)
3. Visualize the grid
4. Export the `.waypoints` file

---

## 🧊 Optional: Create a Standalone `.exe`

If you want to share the tool without requiring Python:

### Step 1: Install PyInstaller

```bash
pip install pyinstaller
```

### Step 2: Build the Executable

```bash
pyinstaller --noconfirm --windowed --onefile waypoint_generator.py
```

The `.exe` will be created in the `dist/` folder.

You can now share `dist/waypoint_generator.exe` with others.

---

## 🧾 Dependencies Summary

| Library      | Purpose                           |
| ------------ | --------------------------------- |
| `tkinter`    | Built-in GUI library (no install) |
| `pandas`     | Read CSV data                     |
| `matplotlib` | Plotting grid midpoints           |

Install required packages with:

```bash
pip install pandas matplotlib
```

---


## 👤 Author

**Mohammed Haneef**
Project Associate – UAV Systems
DGCA-Certified Remote Pilot
CSIR-NAL, India

---

## 💡 Future Improvements

* PDF/image export of grid visualization
* Import/export user profiles (servo & flow settings)
* Support for 3D flight profiles and curved path visualization

---

## ⭐️ Support

If you found this project helpful:

* Star ⭐ this repo
* Share it with UAV & agri-tech developers
* Feel free to contribute or open issues!

---
