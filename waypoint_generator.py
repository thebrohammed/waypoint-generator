import tkinter as tk
from tkinter import filedialog, messagebox
from ttkbootstrap import Style
import ttkbootstrap as ttk
import csv
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

def interpolate_pwm(grams, cal_points):
    pwms = sorted(cal_points.keys())
    for i in range(len(pwms) - 1):
        pwm1, pwm2 = pwms[i], pwms[i+1]
        g1, g2 = cal_points[pwm1], cal_points[pwm2]
        if g1 <= grams <= g2:
            slope = (pwm2 - pwm1) / (g2 - g1)
            return pwm1 + slope * (grams - g1)
    return max(min(pwms), min(max(pwms), 1000))

def generate_waypoints(input_csv, output_waypoints, altitude, speed, cal_points, servo_channel):
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV: {e}")
        return

    waypoints = ["QGC WPL 110"]
    seq = 0

    for idx, row in df.iterrows():
        try:
            grams = float(row['Rajphos to apply(g)'])
            latlon = row['Midpoint'].split(',')
            if len(latlon) != 2:
                continue
            lat = float(latlon[0].strip())
            lon = float(latlon[1].strip())
            pwm = interpolate_pwm(grams, cal_points)
            pwm = max(1000, min(2000, int(pwm)))

            waypoints.append(f"{seq}\t0\t3\t16\t0\t0\t0\t0\t{lat:.7f}\t{lon:.7f}\t{altitude:.2f}\t1")
            seq += 1

            waypoints.append(f"{seq}\t0\t3\t183\t{servo_channel}\t{pwm}\t0\t0\t0\t0\t0\t1")
            seq += 1

        except Exception as e:
            print(f"Skipping row {idx} due to error: {e}")
            continue

    with open(output_waypoints, 'w') as outfile:
        for line in waypoints:
            outfile.write(line + '\n')

    messagebox.showinfo("Success", f"Waypoints saved to {output_waypoints}")

def browse_file():
    filepath = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if filepath:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, filepath)

def parse_coordinate(coord_str):
    try:
        lat, lon = map(float, coord_str.split(','))
        return (lon, lat)
    except:
        return None

def visualize_and_optionally_save(save_path=None):
    try:
        df = pd.read_csv(file_entry.get())
        fig, ax = plt.subplots(figsize=(8, 8))

        for i, row in df.iterrows():
            mid = parse_coordinate(row['Midpoint'])
            if mid:
                ax.plot(mid[0], mid[1], 'go')
                ax.text(mid[0], mid[1], str(i+1), fontsize=8, ha='center')

        for i, row in df.iterrows():
            ll = parse_coordinate(row.get('LL'))
            ul = parse_coordinate(row.get('UL'))
            ur = parse_coordinate(row.get('UR'))
            lr = parse_coordinate(row.get('LR'))

            if all([ll, ul, ur, lr]):
                polygon = Polygon([ll, ul, ur, lr], closed=True, edgecolor='blue',
                                  facecolor='skyblue', alpha=0.3, linewidth=1.5)
                ax.add_patch(polygon)

        ax.set_title("Fertilizer Grid & Midpoints", fontsize=14, weight='bold')
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True)

        if save_path:
            fig.savefig(save_path)
            plt.close(fig)
            messagebox.showinfo("Exported", f"Visualization saved to:\n{save_path}")
        else:
            plt.show()

    except Exception as e:
        messagebox.showerror("Plot Error", str(e))

def plot_points():
    visualize_and_optionally_save()

def export_visualization():
    file_path = filedialog.asksaveasfilename(defaultextension=".png",
                    filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf")])
    if file_path:
        visualize_and_optionally_save(file_path)

def run():
    input_path = file_entry.get()
    altitude = float(alt_entry.get())
    speed = float(speed_entry.get())
    pwm_1000 = float(flow_1000_entry.get())
    pwm_1500 = float(flow_1500_entry.get())
    pwm_2000 = float(flow_2000_entry.get())
    servo_channel = int(servo_var.get())

    cal_points = {
        1000: pwm_1000,
        1500: pwm_1500,
        2000: pwm_2000
    }

    output_path = filedialog.asksaveasfilename(defaultextension=".waypoints",
                    filetypes=[("Waypoint files", "*.waypoints")])
    if output_path:
        generate_waypoints(input_path, output_path, altitude, speed, cal_points, servo_channel)

# ------------------ Modern GUI ------------------ #
style = Style(theme='flatly')
root = style.master
root.title("📍 Fertilizer Waypoint Generator")
root.geometry("800x450")

frame = ttk.Frame(root, padding=20)
frame.pack(fill='both', expand=True)

ttk.Label(frame, text="CSV File:", font='Helvetica 10 bold').grid(row=0, column=0, sticky='e')
file_entry = ttk.Entry(frame, width=50)
file_entry.grid(row=0, column=1, padx=5)
ttk.Button(frame, text="Browse", bootstyle="primary", command=browse_file).grid(row=0, column=2)

ttk.Label(frame, text="Altitude (m):").grid(row=1, column=0, sticky='e')
alt_entry = ttk.Entry(frame)
alt_entry.insert(0, "10")
alt_entry.grid(row=1, column=1)

ttk.Label(frame, text="Speed (m/s):").grid(row=2, column=0, sticky='e')
speed_entry = ttk.Entry(frame)
speed_entry.insert(0, "3")
speed_entry.grid(row=2, column=1)

ttk.Label(frame, text="Servo Channel (1–16):").grid(row=3, column=0, sticky='e')
servo_var = tk.StringVar(value="9")
servo_dropdown = ttk.Combobox(frame, textvariable=servo_var, values=[str(i) for i in range(1, 17)], width=5)
servo_dropdown.grid(row=3, column=1, sticky='w')

ttk.Label(frame, text="Flow @ 1000us PWM (g/s):").grid(row=4, column=0, sticky='e')
flow_1000_entry = ttk.Entry(frame)
flow_1000_entry.insert(0, "0")
flow_1000_entry.grid(row=4, column=1)

ttk.Label(frame, text="Flow @ 1500us PWM (g/s):").grid(row=5, column=0, sticky='e')
flow_1500_entry = ttk.Entry(frame)
flow_1500_entry.insert(0, "5")
flow_1500_entry.grid(row=5, column=1)

ttk.Label(frame, text="Flow @ 2000us PWM (g/s):").grid(row=6, column=0, sticky='e')
flow_2000_entry = ttk.Entry(frame)
flow_2000_entry.insert(0, "10")
flow_2000_entry.grid(row=6, column=1)

btn_frame = ttk.Frame(frame)
btn_frame.grid(row=7, column=0, columnspan=3, pady=20)

ttk.Button(btn_frame, text="📊 Visualize Grid", bootstyle="info", width=18, command=plot_points).grid(row=0, column=0, padx=10)
ttk.Button(btn_frame, text="💾 Export as Image/PDF", bootstyle="warning", width=22, command=export_visualization).grid(row=0, column=1, padx=10)
ttk.Button(btn_frame, text="✅ Generate Waypoints", bootstyle="success", width=20, command=run).grid(row=0, column=2, padx=10)

root.mainloop()
