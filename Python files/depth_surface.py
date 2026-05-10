import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import threading
from collections import deque
from mpl_toolkits.mplot3d import Axes3D

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT  = 'COM12'    # Change to your actual COM port
BAUD_RATE    = 115200
MAX_DIST     = 800       # Maximum TF-Luna range in cm
HISTORY      = 50        # Number of time steps shown on surface
WIDTH        = 20        # Width of the surface (spread across Y axis)

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist  = 0
latest_amp   = 0
latest_temp  = 0.0
dist_history = deque([0] * HISTORY, maxlen=HISTORY)
lock         = threading.Lock()

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
    global latest_dist, latest_amp, latest_temp
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
                    dist_history.append(dist)
        except Exception as e:
            print(f"Serial error: {e}")

thread = threading.Thread(target=serial_thread, daemon=True)
thread.start()

# ── Setup 3D plot ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(12, 7))
fig.patch.set_facecolor('#1a1a2e')

ax = fig.add_subplot(111, projection='3d')
ax.set_facecolor('#16213e')
ax.tick_params(colors='white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.zaxis.label.set_color('white')
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.xaxis.pane.set_edgecolor('#333')
ax.yaxis.pane.set_edgecolor('#333')
ax.zaxis.pane.set_edgecolor('#333')
ax.grid(color='#333', linestyle='--', linewidth=0.5)

ax.set_xlabel('Time', color='white', labelpad=10)
ax.set_ylabel('Width', color='white', labelpad=10)
ax.set_zlabel('Distance (cm)', color='white', labelpad=10)
ax.set_title('TF-Luna 3D Rolling Depth Surface',
             color='white', fontsize=14, fontweight='bold')

# Set initial viewing angle
ax.view_init(elev=30, azim=-60)

# Status and info text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='white', fontweight='bold')
info_text   = fig.text(0.5, 0.02, '',
                        ha='center', fontsize=10, color='#aaa')

# ── Build surface mesh ────────────────────────────────────────────────────────
x = np.linspace(0, HISTORY - 1, HISTORY)   # Time axis
y = np.linspace(-WIDTH / 2, WIDTH / 2, 10) # Width axis
X, Y = np.meshgrid(x, y)
Z    = np.zeros_like(X)

surf = [ax.plot_surface(X, Y, Z, cmap='plasma',
                         edgecolor='none', alpha=0.85)]

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        dist   = latest_dist
        amp    = latest_amp
        temp   = latest_temp
        hist   = list(dist_history)

    # Build Z surface — each column is the same distance value
    # giving a ribbon-like wave across the width
    Z = np.array([hist for _ in range(10)], dtype=float)

    # Dynamic Z axis
    min_z = max(0, min(hist) - 50)
    max_z = max(hist) + 50
    ax.set_zlim(min_z, max_z)

    # Remove old surface and redraw
    surf[0].remove()
    surf[0] = ax.plot_surface(X, Y, Z, cmap='plasma',
                               edgecolor='none', alpha=0.85,
                               vmin=min_z, vmax=max_z)

    # Status flags
    if dist < 20:
        status = '⚠ TOO CLOSE'
        status_color = '#e94560'
    elif dist > 800:
        status = '⚠ OUT OF RANGE'
        status_color = '#f5a623'
    elif amp < 100:
        status = '⚠ WEAK SIGNAL'
        status_color = '#f5a623'
    elif amp == 65535:
        status = '⚠ SATURATED'
        status_color = '#f5a623'
    else:
        status = '● OK'
        status_color = '#a8e063'

    status_text.set_text(status)
    status_text.set_color(status_color)

    info_text.set_text(
        f'Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C'
    )

    return surf

ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
