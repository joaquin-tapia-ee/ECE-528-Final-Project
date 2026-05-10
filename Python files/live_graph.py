import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import re

# ── Configuration ─────────────────────────────────────────────────────────────
SERIAL_PORT = 'COM12'    
BAUD_RATE   = 115200
MAX_POINTS  = 50        # Number of data points shown on graph

# ── Data buffers ──────────────────────────────────────────────────────────────
distances  = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
amplitudes = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
temps      = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)


# ── Open serial port ──────────────────────────────────────────────────────────
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
ser.reset_input_buffer()  # Clear any buffered data on startup

# ── Setup plot ────────────────────────────────────────────────────────────────
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))
fig.suptitle('TF-Luna LiDAR Live Graph', fontsize=14, fontweight='bold')
fig.patch.set_facecolor('#1a1a2e')

for ax in (ax1, ax2, ax3):
    ax.set_facecolor('#16213e')
    ax.tick_params(colors='white')
    ax.yaxis.label.set_color('white')
    ax.xaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#444')

line1, = ax1.plot([], [], color='#e94560', linewidth=2)
line2, = ax2.plot([], [], color='#0f9b8e', linewidth=2)
line3, = ax3.plot([], [], color='#f5a623', linewidth=2)

ax1.set_ylim(0, 200)
ax1.set_title('Distance (cm)')
ax1.set_ylabel('cm')

ax2.set_ylim(0, 20000)
ax2.set_title('Amplitude')
ax2.set_ylabel('value')

ax3.set_ylim(0, 40)
ax3.set_title('Temperature (°C)')
ax3.set_ylabel('°C')

plt.tight_layout(rect=[0, 0, 1, 0.95])

# ── Parse incoming serial line ────────────────────────────────────────────────
def parse_line(line):
    # Skip header lines
    if '=' in line or 'Distance' in line or '---' in line or 'Ready' in line:
        return None
    try:
        parts = line.strip().split('|')
        if len(parts) == 3:
            # Extract first number from each column
            dist_str = parts[0].strip().split()[0]
            amp_str  = parts[1].strip().split()[0]
            temp_str = parts[2].strip().split()[0]
            dist = int(dist_str)
            amp  = int(amp_str)
            temp = float(temp_str)
            return dist, amp, temp
    except:
        pass
    return None

# ── Animation update function ─────────────────────────────────────────────────
def update(frame):
    try:
        ser.reset_input_buffer()
        raw = ser.readline().decode('utf-8', errors='ignore').strip()
        parsed = parse_line(raw)

        if parsed:
            dist, amp, temp = parsed
            distances.append(dist)
            amplitudes.append(amp)
            temps.append(temp)

            x = list(range(len(distances)))

            line1.set_data(x, list(distances))
            line2.set_data(x, list(amplitudes))
            line3.set_data(x, list(temps))

            for ax in (ax1, ax2, ax3):
                ax.set_xlim(0, MAX_POINTS)

            # ── Dynamic Y axis for distance ───────────────────────────────
            if len(distances) > 0:
                min_dist = max(0, min(distances) - 20)
                max_dist = max(distances) + 20
                ax1.set_ylim(min_dist, max_dist)

            # ── Dynamic Y axis for amplitude ──────────────────────────────
            if len(amplitudes) > 0:
                min_amp = max(0, min(amplitudes) - 200)    # 200 units padding below
                max_amp = max(amplitudes) + 200            # 200 units padding above
                ax2.set_ylim(min_amp, max_amp)

            fig.suptitle(
                f'TF-Luna LiDAR  |  Dist: {dist} cm  |  Amp: {amp}  |  Temp: {temp:.2f}°C',
                fontsize=12, fontweight='bold', color='white'
            )

    except Exception as e:
        print(f"Error: {e}")

    return line1, line2, line3

# ── Run animation ─────────────────────────────────────────────────────────────
ani = animation.FuncAnimation(fig, update, interval=1, blit=False)
plt.show()

# ── Cleanup ───────────────────────────────────────────────────────────────────
ser.close()
