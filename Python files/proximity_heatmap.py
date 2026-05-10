import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import threading
from collections import deque

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT  = 'COM12'    # Change to your actual COM port
BAUD_RATE    = 115200
MAX_DIST     = 800       # Maximum TF-Luna range in cm
HISTORY      = 100       # Number of readings shown in heatmap history

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist  = 0
latest_amp   = 0
latest_temp  = 0.0
dist_history = deque([MAX_DIST] * HISTORY, maxlen=HISTORY)
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

# ── Setup plot ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#16213e')
ax.set_xticks([])
ax.set_yticks([])
ax.set_title('TF-Luna Proximity Heatmap',
             color='white', fontsize=14, fontweight='bold')

# Initial heatmap data — 20 rows tall for visual thickness
heatmap_data = np.ones((20, HISTORY)) * MAX_DIST
img = ax.imshow(heatmap_data, aspect='auto',
                cmap='RdYlGn_r', vmin=0, vmax=MAX_DIST,
                interpolation='bilinear')

# Colorbar
cbar = plt.colorbar(img, ax=ax, orientation='vertical',
                     pad=0.02, fraction=0.03)
cbar.set_label('Distance (cm)', color='white', fontsize=10)
cbar.ax.yaxis.set_tick_params(color='white')
plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')

# Distance label in center
dist_label = ax.text(HISTORY / 2, 10, '',
                      ha='center', va='center',
                      fontsize=48, fontweight='bold',
                      color='white', alpha=0.85)

# Status and info text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='white', fontweight='bold')
info_text   = fig.text(0.5, 0.02, '',
                        ha='center', fontsize=10, color='#aaa')

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        dist = latest_dist
        amp  = latest_amp
        temp = latest_temp
        hist = list(dist_history)

    # Build heatmap — repeat history across all 20 rows
    heatmap_data = np.array([hist] * 20, dtype=float)
    img.set_data(heatmap_data)

    # Dynamic color scale based on current range
    min_d = max(0, min(hist) - 50)
    max_d = max(hist) + 50
    img.set_clim(vmin=min_d, vmax=max_d)

    # Update center distance label
    dist_label.set_text(f'{dist} cm')

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

    return img, dist_label, status_text, info_text

ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
