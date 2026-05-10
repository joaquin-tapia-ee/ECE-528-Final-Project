import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import threading
from collections import deque

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT  = 'COM12'   # Change to your actual COM port
BAUD_RATE    = 115200
MAX_DIST     = 800       # Maximum TF-Luna range in cm
HISTORY      = 200       # Number of data points shown on waveform
PADDING      = 50        # of cm padding above and below waveform

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist  = 0
latest_amp   = 0
latest_temp  = 0.0
dist_history = deque([0] * HISTORY, maxlen=HISTORY)
lock         = threading.Lock()
dynamic_max  = [800]
dynamic_min  = [0]

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
fig.patch.set_facecolor('#0a0a0a')
ax.set_facecolor('#0a0a0a')
ax.tick_params(colors='#00ff41')
ax.spines['bottom'].set_color('#00ff41')
ax.spines['top'].set_color('#003300')
ax.spines['left'].set_color('#00ff41')
ax.spines['right'].set_color('#003300')
ax.set_xlabel('Time', color='#00ff41', fontsize=11)
ax.set_ylabel('Distance (cm)', color='#00ff41', fontsize=11)
ax.set_title('TF-Luna Oscilloscope',
             color='#00ff41', fontsize=14, fontweight='bold')
ax.grid(color='#003300', linestyle='-', linewidth=0.5)

# Horizontal grid lines for distance reference
for d in range(0, MAX_DIST + 1, 100):
    ax.axhline(y=d, color='#002200', linestyle='--', linewidth=0.5)

# Main waveform line
wave_line, = ax.plot([], [], color='#00ff41',
                      linewidth=2, zorder=5)

# Glow effect — thicker transparent line behind main line
glow_line, = ax.plot([], [], color='#00ff41',
                      linewidth=6, alpha=0.15, zorder=4)

# Current value vertical line
curr_line = ax.axvline(x=HISTORY - 1, color='#00ff41',
                        linewidth=1, linestyle='--', alpha=0.5)

# Current value dot
curr_dot, = ax.plot([], [], 'o', color='#00ff41',
                     markersize=10, zorder=6,
                     markeredgecolor='white', markeredgewidth=1)

# Fill under waveform
fill = [ax.fill_between(range(HISTORY),
                         [0] * HISTORY,
                         [0] * HISTORY,
                         color='#00ff41', alpha=0.05)]

# Distance label on right side
dist_label = ax.text(HISTORY + 2, 0, '',
                      ha='left', va='center',
                      fontsize=12, fontweight='bold',
                      color='#00ff41')

# Status and info text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='#00ff41', fontweight='bold')
info_text   = fig.text(0.5, 0.02, '',
                        ha='center', fontsize=10, color='#00aa30')

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        dist = latest_dist
        amp  = latest_amp
        temp = latest_temp
        hist = list(dist_history)

    # ── Dynamic Y axis ────────────────────────────────────────────────────
    target_max = max(dist + PADDING, 200)
    target_min = max(0, dist - PADDING)

    if target_max > dynamic_max[0]:
        dynamic_max[0] = target_max
    else:
        dynamic_max[0] = max(dynamic_max[0] - 2, target_max)

    if target_min < dynamic_min[0]:
        dynamic_min[0] = target_min
    else:
        dynamic_min[0] = min(dynamic_min[0] + 2, target_min)

    ax.set_ylim(dynamic_min[0], dynamic_max[0])
    ax.set_xlim(0, HISTORY + 10)

    x = list(range(HISTORY))

    # ── Update waveform ───────────────────────────────────────────────────
    wave_line.set_data(x, hist)
    glow_line.set_data(x, hist)

    # ── Update fill under waveform ────────────────────────────────────────
    fill[0].remove()
    fill[0] = ax.fill_between(x, dynamic_min[0], hist,
                               color='#00ff41', alpha=0.05)

    # ── Current value dot and label ───────────────────────────────────────
    curr_dot.set_data([HISTORY - 1], [dist])
    dist_label.set_position((HISTORY + 2, dist))
    dist_label.set_text(f'{dist} cm')

    # ── Status flags ──────────────────────────────────────────────────────
    if dist < 20:
        status = '⚠ TOO CLOSE'
    elif dist > 800:
        status = '⚠ OUT OF RANGE'
    elif amp < 100:
        status = '⚠ WEAK SIGNAL'
    elif amp == 65535:
        status = '⚠ SATURATED'
    else:
        status = '● OK'

    status_text.set_text(status)
    info_text.set_text(
        f'Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C  |  Range: {int(dynamic_min[0])} - {int(dynamic_max[0])} cm'
    )

    return wave_line, glow_line, curr_dot, dist_label, status_text, info_text

ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
