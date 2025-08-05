from tkinter import filedialog, messagebox
import tkinter as tk
from ttkbootstrap import Style
import ttkbootstrap as ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from geopy.distance import geodesic
import os
import sys
from PIL import Image, ImageTk

def resource_path(relative_path: str) -> str:
    """Return absolute path to resource for PyInstaller bundles."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def interpolate_pwm(grams, time_seconds, cal_points):
    """Interpolate PWM value based on required dispense rate and calibration points."""
    pwms = sorted(cal_points.keys())
    if not pwms:
        return 1000  # Default PWM if no calibration points
    # Calculate required dispense rate (grams per second)
    target_rate = grams / time_seconds if time_seconds > 0 else grams
    # Find the PWM value that achieves the closest flow rate to target_rate
    for i in range(len(pwms) - 1):
        pwm1, pwm2 = pwms[i], pwms[i + 1]
        rate1, rate2 = cal_points[pwm1], cal_points[pwm2]
        if rate1 <= target_rate <= rate2:
            # Linear interpolation
            slope = (pwm2 - pwm1) / (rate2 - rate1)
            return pwm1 + slope * (target_rate - rate1)
    # Clamp to min/max PWM if target_rate is outside calibration range
    min_pwm, max_pwm = min(pwms), max(pwms)
    if target_rate < cal_points[min_pwm]:
        return min_pwm
    return max_pwm

def load_calibration_csv(cal_csv):
    """Load calibration data from CSV with Valve and Avg quantity(g) columns."""
    try:
        df = pd.read_csv(cal_csv)
        if 'Valve' not in df.columns or 'Avg quantity(g)' not in df.columns:
            messagebox.showerror("Error", "CSV must contain 'Valve' and 'Avg quantity(g)' columns")
            return None
        cal_points = {float(row['Valve']): float(row['Avg quantity(g)']) for _, row in df.iterrows()}
        return cal_points
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read calibration CSV: {e}")
        return None

def generate_waypoints(input_csv, altitude, speed, cal_points, valve_servo_channel, disc_servo_channel, disc_pwm, include_takeoff):
    """Generate QGC WPL 110 waypoint lines from CSV input."""
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV: {e}")
        return []
    waypoints = ["QGC WPL 110"]
    seq = 0
    # Add home position (MAV_CMD_NAV_WAYPOINT, 16) at mission start
    home_lat, home_lon = 0.0, 0.0
    if not df.empty:
        first_coord = df.iloc[0]['Target Coordinates'].split(',')
        if len(first_coord) == 2:
            try:
                home_lat = float(first_coord[0].strip())
                home_lon = float(first_coord[1].strip())
            except ValueError:
                pass
    waypoints.append(f"{seq}\t1\t0\t16\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t{home_lat:.7f}\t{home_lon:.7f}\t{altitude:.6f}\t1")
    seq += 1
    if include_takeoff:
        # Add takeoff command (MAV_CMD_NAV_TAKEOFF, 22)
        waypoints.append(f"{seq}\t0\t3\t22\t20.00000000\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t{altitude:.6f}\t1")
        seq += 1
    # Initialize both servos to 1000 PWM before first waypoint
    waypoints.append(f"{seq}\t0\t3\t183\t{disc_servo_channel:.8f}\t1000.00000000\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
    seq += 1
    waypoints.append(f"{seq}\t0\t3\t183\t{valve_servo_channel:.8f}\t1000.00000000\t1.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
    seq += 1
    # Set disc speed PWM to user-specified value
    disc_pwm = max(1000, min(2000, int(disc_pwm)))  # Clamp to 1000-2000us
    waypoints.append(f"{seq}\t0\t3\t183\t{disc_servo_channel:.8f}\t{disc_pwm:.8f}\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
    seq += 1
    previous_coord = None
    for idx, row in df.iterrows():
        try:
            grams = float(row['Fertilizer'])
            latlon = row['Target Coordinates'].split(',')
            if len(latlon) != 2:
                continue
            lat = float(latlon[0].strip())
            lon = float(latlon[1].strip())
            current_coord = (lat, lon)
            time_seconds = 1.0  # Default time if no previous coord
            if previous_coord:
                distance_m = geodesic(previous_coord, current_coord).meters
                time_seconds = distance_m / speed if speed > 0 else 1.0
            pwm = interpolate_pwm(grams, time_seconds, cal_points)
            pwm = max(min(cal_points.keys(), default=1000), min(max(cal_points.keys(), default=2000), int(pwm)))
            # Add waypoint (MAV_CMD_NAV_WAYPOINT, 16)
            waypoints.append(f"{seq}\t0\t3\t16\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t{lat:.7f}\t{lon:.7f}\t{altitude:.6f}\t1")
            seq += 1
            # Add servo command (MAV_CMD_DO_SET_SERVO, 183)
            waypoints.append(f"{seq}\t0\t3\t183\t{valve_servo_channel:.8f}\t{pwm:.8f}\t1.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
            seq += 1
            previous_coord = current_coord
        except Exception as e:
            print(f"Skipping row {idx} due to error: {e}")
            continue
    # Set both servos back to 1000 PWM after last waypoint
    waypoints.append(f"{seq}\t0\t3\t183\t{valve_servo_channel:.8f}\t1000.00000000\t1.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
    seq += 1
    waypoints.append(f"{seq}\t0\t3\t183\t{disc_servo_channel:.8f}\t1000.00000000\t0.00000000\t0.00000000\t0.00000000\t0.00000000\t0.000000\t1")
    return waypoints

def browse_file():
    """Open file dialog to select waypoint CSV file."""
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, filepath)

def browse_cal_file():
    """Open file dialog to select calibration CSV file."""
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        cal_file_entry.delete(0, tk.END)
        cal_file_entry.insert(0, filepath)

def parse_coordinate(coord_str):
    """Parse 'lat,lon' string into coordinates."""
    try:
        lat, lon = map(float, coord_str.split(','))
        return (lon, lat)
    except:
        return None

def visualize_waypoints(save_path=None):
    """Visualize waypoints with color-coded fertilizer quantities and PWM annotations."""
    try:
        input_path = file_entry.get()
        if not input_path:
            messagebox.showerror("Error", "Please select a waypoint CSV file")
            return
        df = pd.read_csv(input_path)
        cal_path = cal_file_entry.get()
        cal_points = load_calibration_csv(cal_path) if cal_path else None
        speed = float(speed_entry.get())
        disc_pwm = float(disc_pwm_entry.get())
        altitude = float(alt_entry.get())  # Not used here but for consistency
        if cal_points is None:
            messagebox.showwarning("Warning", "Calibration file not loaded. PWMs will not be shown.")
            disc_pwm = max(1000, min(2000, int(disc_pwm)))
        fig, ax = plt.subplots(figsize=(10, 8))
        lons, lats, grams, pwms = [], [], [], []
        previous_coord = None
        for i, row in df.iterrows():
            coord = parse_coordinate(row['Target Coordinates'])
            if coord:
                lon, lat = coord
                lons.append(lon)
                lats.append(lat)
                gram = float(row['Fertilizer'])
                grams.append(gram)
                if cal_points:
                    current_coord = (lat, lon)
                    time_seconds = 1.0
                    if previous_coord:
                        distance_m = geodesic(previous_coord, current_coord).meters
                        time_seconds = distance_m / speed if speed > 0 else 1.0
                    pwm = interpolate_pwm(gram, time_seconds, cal_points)
                    pwm = max(min(cal_points.keys(), default=1000), min(max(cal_points.keys(), default=2000), int(pwm)))
                    pwms.append(pwm)
                    previous_coord = current_coord
                else:
                    pwms.append(None)
        if lons and lats and grams:
            norm = Normalize(vmin=min(grams), vmax=max(grams))
            cmap = plt.get_cmap('RdBu')
            scatter = ax.scatter(lons, lats, c=grams, cmap=cmap, norm=norm, s=100, edgecolors='black', linewidth=0.5)
            for i, (lon, lat, pwm) in enumerate(zip(lons, lats, pwms)):
                text = f"{i+1}"
                if pwm is not None:
                    text += f": {pwm}"
                ax.text(lon, lat, text, fontsize=10, ha='center', va='bottom', color='darkblue')
            cbar = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax)
            cbar.set_label('Fertilizer Quantity (g)', fontsize=12)
            ax.text(min(lons), max(lats), f"Disc PWM: {disc_pwm}", ha='left', va='top', fontsize=12, color='red')
        # Set tighter axis limits with padding
        if lons and lats:
            lon_range = max(lons) - min(lons)
            lat_range = max(lats) - min(lats)
            padding = 0.05 * max(lon_range, lat_range)
            ax.set_xlim(min(lons) - padding, max(lons) + padding)
            ax.set_ylim(min(lats) - padding, max(lats) + padding)
        ax.set_title("Fertilizer Waypoints with Quantity Coloring and PWMs", fontsize=16, weight='bold', color='navy')
        ax.set_xlabel("Longitude", fontsize=12)
        ax.set_ylabel("Latitude", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            messagebox.showinfo("Exported", f"Visualization saved to:\n{save_path}")
        else:
            plt.show()
    except Exception as e:
        messagebox.showerror("Plot Error", str(e))

def visualize_calibration():
    """Visualize calibration data from CSV as a line plot."""
    try:
        cal_csv = cal_file_entry.get()
        if not cal_csv:
            messagebox.showerror("Error", "Please select a calibration CSV file")
            return
        df = pd.read_csv(cal_csv)
        if 'Valve' not in df.columns or 'Avg quantity(g)' not in df.columns:
            messagebox.showerror("Error", "CSV must contain 'Valve' and 'Avg quantity(g)' columns")
            return
        fig, ax = plt.subplots(figsize=(10, 6))
        pwms = df['Valve']
        quantities = df['Avg quantity(g)']
        ax.plot(pwms, quantities, 'o-', color='navy', linewidth=2, markersize=8, markeredgecolor='black')
        ax.set_title("Valve PWM vs. Flow Rate", fontsize=16, weight='bold', color='navy')
        ax.set_xlabel("Valve PWM (us)", fontsize=12)
        ax.set_ylabel("Flow Rate (g/s)", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        # Set axis limits with padding
        pwm_range = max(pwms) - min(pwms)
        quantity_range = max(quantities) - min(quantities)
        ax.set_xlim(min(pwms) - 0.05 * pwm_range, max(pwms) + 0.05 * pwm_range)
        ax.set_ylim(min(quantities) - 0.05 * quantity_range, max(quantities) + 0.05 * quantity_range)
        plt.tight_layout()
        plt.show()
    except Exception as e:
        messagebox.showerror("Plot Error", str(e))

def plot_points():
    """Trigger waypoint visualization."""
    visualize_waypoints()

def export_visualization():
    """Export waypoint visualization as PNG or PDF."""
    file_path = filedialog.asksaveasfilename(defaultextension=".png",
                    filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf")])
    if file_path:
        visualize_waypoints(file_path)

def save_waypoints(content, output_path):
    with open(output_path, 'w') as outfile:
        outfile.write(content)
    messagebox.showinfo("Success", f"Waypoints saved to {output_path}")

def preview_waypoints(waypoints, output_path):
    preview_window = tk.Toplevel(root)
    preview_window.title("Waypoint Preview and Editor")
    preview_window.geometry("800x600")
    text = tk.Text(preview_window, wrap='none', font=('Courier', 10))
    text.insert(tk.END, '\n'.join(waypoints))
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll = tk.Scrollbar(preview_window, command=text.yview)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    text.config(yscrollcommand=yscroll.set)
    xscroll = tk.Scrollbar(preview_window, orient='horizontal', command=text.xview)
    xscroll.pack(side=tk.BOTTOM, fill=tk.X)
    text.config(xscrollcommand=xscroll.set)
    btn_frame = ttk.Frame(preview_window)
    btn_frame.pack(pady=10)
    save_btn = ttk.Button(btn_frame, text="Save", bootstyle="success", command=lambda: [save_waypoints(text.get("1.0", tk.END), output_path), preview_window.destroy()])
    save_btn.pack(side=tk.LEFT, padx=10)
    cancel_btn = ttk.Button(btn_frame, text="Cancel", bootstyle="danger", command=preview_window.destroy)
    cancel_btn.pack(side=tk.LEFT, padx=10)

def run():
    """Run waypoint generation with user inputs."""
    input_path = file_entry.get()
    cal_path = cal_file_entry.get()
    try:
        altitude = float(alt_entry.get())
        speed = float(speed_entry.get())
        valve_servo_channel = int(valve_servo_var.get())
        disc_servo_channel = int(disc_servo_var.get())
        disc_pwm = float(disc_pwm_entry.get())
        include_takeoff = include_takeoff_var.get()
        cal_points = load_calibration_csv(cal_path)
        if cal_points is None:
            return
    except ValueError:
        messagebox.showerror("Error", "Invalid input values")
        return
    output_path = filedialog.asksaveasfilename(defaultextension=".waypoints",
                    filetypes=[("Waypoint files", "*.waypoints")])
    if output_path:
        waypoints = generate_waypoints(input_path, altitude, speed, cal_points, valve_servo_channel, disc_servo_channel, disc_pwm, include_takeoff)
        preview_waypoints(waypoints, output_path)

# ------------------ Modern GUI ------------------ #
style = Style(theme='flatly')
root = style.master
root.title("RSSA Waypoint Gen V1.0")
root.geometry("900x600")
root.configure(bg='#FFFFFF')
# Set application icon
try:
    root.iconbitmap(resource_path("app_icon.ico"))
except Exception as e:
    print(f"Icon file not found; using default icon: {e}")
# Main frame with weight for resizing
frame = ttk.Frame(root, padding=30, style='primary.TFrame')
frame.grid(row=0, column=0, sticky='nsew')
frame.configure(bootstyle='light')
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
# Configure frame grid weights for internal resizing
frame.grid_columnconfigure(0, weight=1)
frame.grid_columnconfigure(1, weight=1)
frame.grid_columnconfigure(2, weight=1)
frame.grid_columnconfigure(3, weight=1)
frame.grid_columnconfigure(4, weight=1)
# Header frame for title and images
header_frame = ttk.Frame(frame, style='light.TFrame')
header_frame.grid(row=0, column=0, columnspan=5, pady=20, sticky='ew')
header_frame.grid_columnconfigure(0, weight=1)
header_frame.grid_columnconfigure(1, weight=0)
header_frame.grid_columnconfigure(2, weight=0)
header_frame.grid_columnconfigure(3, weight=1)
# Load header images
try:
    left_img = Image.open(resource_path("left_image.png"))
    left_img = left_img.resize((50, 50), Image.Resampling.LANCZOS)
    left_photo = ImageTk.PhotoImage(left_img)
    ttk.Label(header_frame, image=left_photo).grid(row=0, column=1, padx=5, sticky='e')
except Exception as e:
    print(f"Left image not found: {e}")
# Title (centered)
ttk.Label(header_frame, text="RSSA Waypoint Gen V1.0", font=('Helvetica', 18, 'bold'), foreground='#1E3A8A').grid(row=0, column=2, pady=10, sticky='')
try:
    right_img = Image.open(resource_path("right_image.png"))
    right_img = right_img.resize((50, 50), Image.Resampling.LANCZOS)
    right_photo = ImageTk.PhotoImage(right_img)
    ttk.Label(header_frame, image=right_photo).grid(row=0, column=3, padx=5, sticky='w')
except Exception as e:
    print(f"Right image not found: {e}")
# Waypoint CSV File Input
ttk.Label(frame, text="Waypoint CSV:", font=('Helvetica', 12, 'bold'), foreground='#1E3A8A').grid(row=1, column=0, sticky='e', pady=10)
file_entry = ttk.Entry(frame, width=40, font=('Helvetica', 11))
file_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky='ew')
ttk.Button(frame, text="Browse", bootstyle="light", command=browse_file).grid(row=1, column=3, padx=10, pady=10)
# Calibration CSV File Input
ttk.Label(frame, text="Calibration CSV:", font=('Helvetica', 12, 'bold'), foreground='#1E3A8A').grid(row=2, column=0, sticky='e', pady=10)
cal_file_entry = ttk.Entry(frame, width=40, font=('Helvetica', 11))
cal_file_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky='ew')
ttk.Button(frame, text="Browse", bootstyle="light", command=browse_cal_file).grid(row=2, column=3, padx=10, pady=10)
ttk.Button(frame, text="📈 Plot Calibration", bootstyle="light", command=visualize_calibration).grid(row=2, column=4, padx=10, pady=10)
# Altitude
ttk.Label(frame, text="Altitude (m):", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=3, column=0, sticky='e', pady=10)
alt_entry = ttk.Entry(frame, width=10, font=('Helvetica', 11))
alt_entry.insert(0, "10")
alt_entry.grid(row=3, column=1, sticky='w', padx=10)
# Speed
ttk.Label(frame, text="Speed (m/s):", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=4, column=0, sticky='e', pady=10)
speed_entry = ttk.Entry(frame, width=10, font=('Helvetica', 11))
speed_entry.insert(0, "3")
speed_entry.grid(row=4, column=1, sticky='w', padx=10)
# Valve Servo Channel
ttk.Label(frame, text="Valve Servo Channel (1–16):", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=5, column=0, sticky='e', pady=10)
valve_servo_var = tk.StringVar(value="9")
valve_servo_dropdown = ttk.Combobox(frame, textvariable=valve_servo_var, values=[str(i) for i in range(1, 17)], width=5, font=('Helvetica', 11))
valve_servo_dropdown.grid(row=5, column=1, sticky='w', padx=10)
# Disc Servo Channel
ttk.Label(frame, text="Disc Servo Channel (1–16):", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=6, column=0, sticky='e', pady=10)
disc_servo_var = tk.StringVar(value="10")
disc_servo_dropdown = ttk.Combobox(frame, textvariable=disc_servo_var, values=[str(i) for i in range(1, 17)], width=5, font=('Helvetica', 11))
disc_servo_dropdown.grid(row=6, column=1, sticky='w', padx=10)
# Disc PWM
ttk.Label(frame, text="Disc PWM (1000–2000):", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=7, column=0, sticky='e', pady=10)
disc_pwm_entry = ttk.Entry(frame, width=10, font=('Helvetica', 11))
disc_pwm_entry.insert(0, "1500")
disc_pwm_entry.grid(row=7, column=1, sticky='w', padx=10)
# Include Takeoff
ttk.Label(frame, text="Include Takeoff Command:", font=('Helvetica', 12), foreground='#1E3A8A').grid(row=8, column=0, sticky='e', pady=10)
include_takeoff_var = tk.BooleanVar(value=True)
ttk.Checkbutton(frame, variable=include_takeoff_var, bootstyle="round-toggle").grid(row=8, column=1, sticky='w', padx=10)
# Buttons (light blue)
btn_frame = ttk.Frame(frame, style='light.TFrame')
btn_frame.grid(row=100, column=0, columnspan=5, pady=30, sticky='ew')
btn_frame.grid_columnconfigure(0, weight=1)
btn_frame.grid_columnconfigure(1, weight=1)
btn_frame.grid_columnconfigure(2, weight=1)
ttk.Button(btn_frame, text="📊 Visualize Grid", bootstyle="light", width=18, command=plot_points).grid(row=0, column=0, padx=15, sticky='ew')
ttk.Button(btn_frame, text="💾 Export as Image/PDF", bootstyle="light", width=22, command=export_visualization).grid(row=0, column=1, padx=15, sticky='ew')
ttk.Button(btn_frame, text="✅ Generate Waypoints", bootstyle="light", width=20, command=run).grid(row=0, column=2, padx=15, sticky='ew')
# Keep photo references to prevent garbage collection
frame.left_photo = left_photo
frame.right_photo = right_photo
root.mainloop()
