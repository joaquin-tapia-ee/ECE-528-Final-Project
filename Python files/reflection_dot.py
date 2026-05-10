import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
import numpy as np
import threading

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT = 'COM12'    # Change to your actual COM port
BAUD_RATE   = 115200
MAX_DIST    = 800       # Maximum TF-Luna range in cm

# ── State ─────────────────────────────────────────────────────────────────────
latest_dist = 0
latest_amp  = 0
latest_temp = 0.0
lock        = threading.Lock()

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
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#16213e')
ax.set_xlim(0, MAX_DIST)
ax.set_ylim(-1.5, 1.5)
ax.set_yticks([])
ax.tick_params(colors='white')
ax.spines['bottom'].set_color('#444')
ax.spines['top'].set_color('#444')
ax.spines['left'].set_color('#444')
ax.spines['right'].set_color('#444')
ax.set_xlabel('Distance (cm)', color='white', fontsize=11)
ax.set_title('TF-Luna 2D Reflection Dot', color='white',
             fontsize=14, fontweight='bold')

# Distance range markers
for d in range(0, MAX_DIST + 1, 100):
    ax.axvline(x=d, color='#333', linestyle='--', linewidth=0.5)
    ax.text(d, -1.35, f'{d}cm', color='#666',
            fontsize=8, ha='center')

# Sensor icon on the left
sensor_rect = patches.FancyBboxPatch(
    (-30, -0.3), 25, 0.6,
    boxstyle="round,pad=0.02",
    linewidth=2, edgecolor='#0f9b8e',
    facecolor='#0f3460'
)
ax.add_patch(sensor_rect)
ax.text(-17, 0, 'SENSOR', color='#0f9b8e',
        fontsize=7, ha='center', va='center', fontweight='bold')

# Beam line from sensor to dot
beam_line, = ax.plot([], [], color='#0f9b8e',
                      linewidth=1, linestyle='--', alpha=0.4)

# Reflection dot
dot, = ax.plot([], [], 'o', markersize=20,
               color='#e94560', alpha=0.9,
               markeredgecolor='white', markeredgewidth=1.5)

# Ripple circles around dot
ripple1 = plt.Circle((0, 0), 0.1, color='#e94560',
                       fill=False, linewidth=1.5, alpha=0.6)
ripple2 = plt.Circle((0, 0), 0.1, color='#e94560',
                       fill=False, linewidth=1, alpha=0.3)
ax.add_patch(ripple1)
ax.add_patch(ripple2)

# Status text
status_text = fig.text(0.5, 0.97, '',
                        ha='center', fontsize=11,
                        color='white', fontweight='bold')

# Info text
info_text = fig.text(0.5, 0.02, '',
                      ha='center', fontsize=10, color='#aaa')

# ── Color mapping based on distance ──────────────────────────────────────────
def dist_to_color(dist):
    ratio = min(dist / MAX_DIST, 1.0)
    if ratio < 0.25:
        return '#e94560'   # Red   — very close
    elif ratio < 0.5:
        return '#f5a623'   # Orange — medium close
    elif ratio < 0.75:
        return '#a8e063'   # Green  — medium far
    else:
        return '#0f9b8e'   # Teal   — far

# ── Size mapping based on amplitude ──────────────────────────────────────────
def amp_to_size(amp):
    normalized = min(amp / 10000, 1.0)
    return 10 + normalized * 30   # Size range 10–40

# ── Animation update ──────────────────────────────────────────────────────────
ripple_scale = [0]

def update(frame):
    with lock:
        dist = latest_dist
        amp  = latest_amp
        temp = latest_temp

    # Clamp distance
    dist_clamped = max(1, min(dist, MAX_DIST))

    # Update dot position and appearance
    color = dist_to_color(dist_clamped)
    size  = amp_to_size(amp)
    dot.set_data([dist_clamped], [0])
    dot.set_color(color)
    dot.set_markersize(size)

    # Update beam line
    beam_line.set_data([0, dist_clamped], [0, 0])

    # ── Dynamic X axis ────────────────────────────────────────────────────
    padding = 25  # 25 cm padding on either side of the dot
    ax.set_xlim(0, max(dist_clamped + padding, 200))

    # Animate ripple circles
    ripple_scale[0] = (ripple_scale[0] + 0.05) % 1.0
    r1 = 0.1 + ripple_scale[0] * 0.4
    r2 = 0.1 + ((ripple_scale[0] + 0.5) % 1.0) * 0.4
    ripple1.center = (dist_clamped, 0)
    ripple1.set_radius(r1)
    ripple1.set_alpha(1.0 - ripple_scale[0])
    ripple1.set_edgecolor(color)
    ripple2.center = (dist_clamped, 0)
    ripple2.set_radius(r2)
    ripple2.set_alpha(1.0 - ((ripple_scale[0] + 0.5) % 1.0))
    ripple2.set_edgecolor(color)

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

    return dot, beam_line, ripple1, ripple2, status_text, info_text

ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.show()

ser.close()
