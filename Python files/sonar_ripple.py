import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import numpy as np
import threading

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT  = 'COM12'      # Change to your actual COM port
BAUD_RATE    = 115200
MAX_DIST     = 800          # Maximum TF-Luna range in cm
NUM_RIPPLES  = 5            # Number of ripple rings
PADDING      = 50           # of cm padding above current max distance

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist  = 0
latest_amp   = 0
latest_temp  = 0.0
lock         = threading.Lock()
dynamic_max  = [800]

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
fig, ax = plt.subplots(figsize=(8, 8))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#16213e')
ax.set_xlim(-1.1, 1.1)
ax.set_ylim(-1.1, 1.1)
ax.set_aspect('equal')
ax.set_xticks([])
ax.set_yticks([])
ax.set_title('TF-Luna Sonar Ripple Effect',
             color='white', fontsize=14, fontweight='bold')

for spine in ax.spines.values():
    spine.set_edgecolor('#333')

# Distance range rings (dynamic background)
range_rings  = []
range_labels = []
for r in np.linspace(0.2, 1.0, 5):
    ring = plt.Circle((0, 0), r, color='#333',
                       fill=False, linewidth=0.8, linestyle='--')
    ax.add_patch(ring)
    label = ax.text(0, r + 0.02, '',
                    ha='center', fontsize=7, color='#555')
    range_rings.append(r)
    range_labels.append(label)

# Center dot — represents the sensor
center_dot = plt.Circle((0, 0), 0.03, color='#0f9b8e', zorder=5)
ax.add_patch(center_dot)
ax.text(0, -0.08, 'SENSOR', ha='center',
        fontsize=8, color='#0f9b8e', fontweight='bold')

# Ripple rings
ripples = []
for i in range(NUM_RIPPLES):
    ripple = plt.Circle((0, 0), 0.0,
                         fill=False, linewidth=2, alpha=0.0)
    ax.add_patch(ripple)
    ripples.append(ripple)

# Target dot at detected distance
target_dot = plt.Circle((0, 0), 0.04, color='#e94560',
                          zorder=5, alpha=0.0)
ax.add_patch(target_dot)

# Distance label in center
dist_label = ax.text(0, 0.15, '',
                      ha='center', va='center',
                      fontsize=28, fontweight='bold',
                      color='white', alpha=0.9)

# Status and info text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='white', fontweight='bold')
info_text   = fig.text(0.5, 0.02, '',
                        ha='center', fontsize=10, color='#aaa')

# ── Color mapping based on distance ──────────────────────────────────────────
def dist_to_color(dist):
    ratio = min(dist / MAX_DIST, 1.0)
    if ratio < 0.25:   return '#e94560'
    elif ratio < 0.5:  return '#f5a623'
    elif ratio < 0.75: return '#a8e063'
    else:              return '#0f9b8e'

# ── Ripple animation state ────────────────────────────────────────────────────
ripple_offsets = [i / NUM_RIPPLES for i in range(NUM_RIPPLES)]

# ── Animation update ──────────────────────────────────────────────────────────
def update(frame):
    with lock:
        dist = latest_dist
        amp  = latest_amp
        temp = latest_temp

    # ── Dynamically adjust max range ──────────────────────────────────────
    target_max = max(dist + PADDING, 200)
    if target_max > dynamic_max[0]:
        dynamic_max[0] = target_max
    else:
        dynamic_max[0] = max(dynamic_max[0] - 2, target_max)

    current_max = dynamic_max[0]

    # Normalize distance
    dist_norm = min(dist / current_max, 1.0)
    color     = dist_to_color(dist)

    # ── Update background range ring labels ───────────────────────────────
    for r, label in zip(range_rings, range_labels):
        ring_dist = int(r * current_max)
        label.set_text(f'{ring_dist}cm')

    # ── Animate ripples ───────────────────────────────────────────────────
    for i, ripple in enumerate(ripples):
        offset = (ripple_offsets[i] + 0.02) % 1.0
        ripple_offsets[i] = offset

        radius = offset * dist_norm
        alpha  = (1.0 - offset) * 0.8

        ripple.set_radius(radius)
        ripple.set_alpha(alpha)
        ripple.set_edgecolor(color)
        ripple.set_linewidth(2.5 - offset * 1.5)

    # ── Target dot ────────────────────────────────────────────────────────
    target_dot.center = (0, dist_norm)
    target_dot.set_alpha(0.9)
    target_dot.set_color(color)

    # ── Distance label ────────────────────────────────────────────────────
    dist_label.set_text(f'{dist} cm')
    dist_label.set_color(color)

    # ── Status flags ──────────────────────────────────────────────────────
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
        f'Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C  |  Range: {int(current_max)} cm'
    )

    return ripples + [target_dot, dist_label, status_text, info_text]

ani = animation.FuncAnimation(fig, update, interval=50, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
