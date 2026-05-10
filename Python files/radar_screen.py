import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import numpy as np
import threading
from collections import deque

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT   = 'COM12'   # Change to your actual COM port
BAUD_RATE     = 115200
MAX_DIST      = 800       # Maximum TF-Luna range in cm
SWEEP_SPEED   = 2         # Degrees per frame
FADE_STEPS    = 180       # How many degrees before blip fades out
PADDING       = 50        # of cm padding above current max distance

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist   = 0
latest_amp    = 0
latest_temp   = 0.0
lock          = threading.Lock()
dynamic_max   = [800]

# Blip history — stores (angle, distance) pairs
blip_history  = deque(maxlen=FADE_STEPS)

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
        except Exception as e:
            print(f"Serial error: {e}")

thread = threading.Thread(target=serial_thread, daemon=True)
thread.start()

# ── Setup plot ────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
fig.patch.set_facecolor('#0a0a0a')
ax.set_facecolor('#0a1a0a')
ax.tick_params(colors='#00ff41')
ax.spines['polar'].set_color('#00ff41')
ax.grid(color='#003300', linestyle='-', linewidth=0.5)

# Green radar aesthetic
ax.set_title('TF-Luna Radar Screen',
             color='#00ff41', fontsize=14, fontweight='bold', pad=20)

# Set angle labels
ax.set_thetagrids(range(0, 360, 45),
                  ['0°', '45°', '90°', '135°', '180°',
                   '225°', '270°', '315°'],
                  color='#00ff41', fontsize=8)

ax.set_ylim(0, 1.0)
ax.set_yticks(np.linspace(0.2, 1.0, 5))
ax.set_yticklabels([])

# Range ring labels
range_labels = []
for r in np.linspace(0.2, 1.0, 5):
    label = ax.text(np.radians(80), r, '',
                    ha='center', fontsize=7, color='#00ff41')
    range_labels.append((r, label))

# Sweep line
sweep_line, = ax.plot([0, 0], [0, 1.0],
                       color='#00ff41', linewidth=2,
                       alpha=0.9, zorder=5)

# Sweep trail — fading green wedge
trail_lines = []
for i in range(30):
    trail, = ax.plot([0, 0], [0, 1.0],
                      color='#00ff41',
                      linewidth=1.5,
                      alpha=0.0)
    trail_lines.append(trail)

# Blip scatter
blip_scatter = ax.scatter([], [], c='#00ff41',
                           s=80, zorder=6, alpha=1.0)

# Center dot
ax.plot(0, 0, 'o', color='#00ff41', markersize=5, zorder=7)

# Status and info text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='#00ff41', fontweight='bold')
info_text   = fig.text(0.5, 0.02, '',
                        ha='center', fontsize=10, color='#00aa30')

# ── Sweep angle state ─────────────────────────────────────────────────────────
sweep_angle = [0]

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        dist = latest_dist
        amp  = latest_amp
        temp = latest_temp

    # ── Dynamic max range ─────────────────────────────────────────────────
    target_max = max(dist + PADDING, 200)
    if target_max > dynamic_max[0]:
        dynamic_max[0] = target_max
    else:
        dynamic_max[0] = max(dynamic_max[0] - 2, target_max)

    current_max = dynamic_max[0]

    # Normalize distance
    dist_norm = min(dist / current_max, 1.0)

    # ── Advance sweep angle ───────────────────────────────────────────────
    sweep_angle[0] = (sweep_angle[0] + SWEEP_SPEED) % 360
    angle_rad      = np.radians(sweep_angle[0])

    # ── Update sweep line ─────────────────────────────────────────────────
    sweep_line.set_data([angle_rad, angle_rad], [0, 1.0])

    # ── Update sweep trail ────────────────────────────────────────────────
    for i, trail in enumerate(trail_lines):
        trail_angle = np.radians(
            (sweep_angle[0] - (i + 1) * SWEEP_SPEED * 2) % 360
        )
        alpha = max(0, 0.4 - i * 0.015)
        trail.set_data([trail_angle, trail_angle], [0, 1.0])
        trail.set_alpha(alpha)

    # ── Record blip at current sweep angle ───────────────────────────────
    blip_history.append((angle_rad, dist_norm, sweep_angle[0]))

    # ── Draw blips with fade ──────────────────────────────────────────────
    if blip_history:
        angles  = []
        dists   = []
        colors  = []
        current = sweep_angle[0]

        for b_angle, b_dist, b_sweep in blip_history:
            age = (current - b_sweep) % 360
            alpha = max(0, 1.0 - age / FADE_STEPS)
            if alpha > 0.05:
                angles.append(b_angle)
                dists.append(b_dist)
                colors.append(alpha)

        if angles:
            blip_scatter.set_offsets(np.c_[angles, dists])
            blip_scatter.set_array(np.array(colors))
            blip_scatter.set_cmap('Greens')
            blip_scatter.set_clim(0, 1)

    # ── Update range ring labels ──────────────────────────────────────────
    for r, label in range_labels:
        label.set_text(f'{int(r * current_max)}cm')

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
        status = '● TRACKING'

    status_text.set_text(status)
    info_text.set_text(
        f'Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C  |  Range: {int(current_max)} cm'
    )

    return [sweep_line, blip_scatter, status_text, info_text] + trail_lines

ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
