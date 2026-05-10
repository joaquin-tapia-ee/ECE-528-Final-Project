import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from collections import deque
import threading
import sys

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT = 'COM12'      # Change to your actual COM port
BAUD_RATE   = 115200
MAX_POINTS  = 360         # One point per degree

# ── State ─────────────────────────────────────────────────────────────────────
recording     = False
sweep_angles  = []
sweep_dists   = []
sweep_amps    = []
current_angle = 0
latest_dist   = 0
latest_amp    = 0
latest_temp   = 0.0
lock          = threading.Lock()

# ── Open serial port ──────────────────────────────────────────────────────────
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
ser.reset_input_buffer()

# ── Parse serial line ─────────────────────────────────────────────────────────
def parse_line(line):
    if '=' in line or 'Distance' in line or '---' in line or 'Ready' in line:
        return None
    try:
        parts = line.strip().split('|')
        if len(parts) == 3:
            dist = int(parts[0].strip().split()[0])
            amp  = int(parts[1].strip().split()[0])
            temp = float(parts[2].strip().split()[0])
            return dist, amp, temp
    except:
        pass
    return None

# ── Serial reading thread ─────────────────────────────────────────────────────
def serial_thread():
    global latest_dist, latest_amp, latest_temp, current_angle

    while True:
        try:
            ser.reset_input_buffer()
            raw = ser.readline().decode('utf-8', errors='ignore').strip()
            parsed = parse_line(raw)

            if parsed:
                dist, amp, temp = parsed
                with lock:
                    latest_dist = dist
                    latest_amp  = amp
                    latest_temp = temp

                    if recording:
                        sweep_angles.append(np.radians(current_angle))
                        sweep_dists.append(dist)
                        sweep_amps.append(amp)
                        current_angle = (current_angle + 1) % 360

        except Exception as e:
            print(f"Serial error: {e}")

thread = threading.Thread(target=serial_thread, daemon=True)
thread.start()

# ── Setup polar plot ──────────────────────────────────────────────────────────
fig = plt.figure(figsize=(10, 10))
fig.patch.set_facecolor('#1a1a2e')

ax = fig.add_subplot(111, polar=True)
ax.set_facecolor('#16213e')
ax.tick_params(colors='white')
ax.yaxis.label.set_color('white')
ax.xaxis.label.set_color('white')
ax.spines['polar'].set_color('#444')
ax.grid(color='#333', linestyle='--', linewidth=0.5)

# Status text
status_text = fig.text(0.5, 0.97, 'Press S to Start Recording',
                        ha='center', fontsize=12,
                        color='white', fontweight='bold')

info_text = fig.text(0.5, 0.93, '',
                      ha='center', fontsize=10, color='#aaa')

scatter = ax.scatter([], [], c=[], cmap='plasma',
                     s=10, alpha=0.8, vmin=0, vmax=800)

# Colorbar
cbar = plt.colorbar(scatter, ax=ax, pad=0.1, fraction=0.03)
cbar.set_label('Distance (cm)', color='white')
cbar.ax.yaxis.set_tick_params(color='white')
plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

ax.set_ylim(0, 800)
ax.set_title('TF-Luna 2D Sweep Map', color='white',
             fontsize=14, fontweight='bold', pad=20)

# ── Keyboard handler ──────────────────────────────────────────────────────────
def on_key(event):
    global recording, current_angle

    if event.key == 's':
        recording = not recording
        if recording:
            current_angle = 0
            status_text.set_text('● RECORDING — Sweep the sensor 360°')
            status_text.set_color('#e94560')
        else:
            status_text.set_text('■ STOPPED — Press S to record again | C to clear | Q to quit')
            status_text.set_color('#0f9b8e')

    elif event.key == 'c':
        with lock:
            sweep_angles.clear()
            sweep_dists.clear()
            sweep_amps.clear()
            current_angle = 0
        status_text.set_text('Cleared — Press S to Start Recording')
        status_text.set_color('white')

    elif event.key == 'q':
        ser.close()
        plt.close()
        sys.exit()

fig.canvas.mpl_connect('key_press_event', on_key)

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        angles = list(sweep_angles)
        dists  = list(sweep_dists)
        amps   = list(sweep_amps)
        dist   = latest_dist
        amp    = latest_amp
        temp   = latest_temp

    if angles:
        scatter.set_offsets(np.c_[angles, dists])
        scatter.set_array(np.array(dists))

        # Dynamic radius limit
        max_dist = max(dists) + 50
        ax.set_ylim(0, max_dist)

    # Update info text
    info_text.set_text(
        f'Live — Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C  |  Points: {len(angles)}'
    )

    return scatter,

ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
plt.tight_layout()
plt.show()

ser.close()
