#include <Arduino.h>

#define LIDAR_SERIAL   Serial2
#define LIDAR_BAUD     115200
#define LIDAR_RX_PIN   16
#define LIDAR_TX_PIN   17

#define DEBUG_SERIAL   Serial
#define DEBUG_BAUD     115200

static const uint8_t FRAME_HEADER = 0x59;
static const uint8_t FRAME_LEN    = 9;

struct TFLunaData {
  uint16_t distanceCm;
  uint16_t amplitude;
  float    tempCelsius;
  bool     valid;
};

bool readTFLunaFrame(TFLunaData &out) {
  static uint8_t buf[FRAME_LEN];
  static uint8_t idx = 0;

  while (LIDAR_SERIAL.available()) {
    uint8_t byte = LIDAR_SERIAL.read();

    if (idx == 0 && byte != FRAME_HEADER) continue;
    if (idx == 1 && byte != FRAME_HEADER) { idx = 0; continue; }

    buf[idx++] = byte;

    if (idx == FRAME_LEN) {
      idx = 0;

      uint8_t checksum = 0;
      for (uint8_t i = 0; i < FRAME_LEN - 1; i++) checksum += buf[i];
      if (checksum != buf[FRAME_LEN - 1]) {
        out.valid = false;
        return false;
      }

      out.distanceCm  = (uint16_t)(buf[3] << 8 | buf[2]);
      out.amplitude   = (uint16_t)(buf[5] << 8 | buf[4]);
      int16_t rawTemp = (int16_t)(buf[7] << 8 | buf[6]);
      out.tempCelsius = rawTemp / 100.0f;
      out.valid       = true;
      return true;
    }
  }
  return false;
}

void setup() {
  DEBUG_SERIAL.begin(DEBUG_BAUD);
  while (!DEBUG_SERIAL) delay(10);
  delay(2000);

  LIDAR_SERIAL.begin(LIDAR_BAUD, SERIAL_8N1, LIDAR_RX_PIN, LIDAR_TX_PIN);

  DEBUG_SERIAL.println("=================================");
  DEBUG_SERIAL.println("  ESP32 + TF-Luna LiDAR Ready   ");
  DEBUG_SERIAL.println("=================================");
  DEBUG_SERIAL.println("Distance(cm) | Amplitude | Temp(C)");
  DEBUG_SERIAL.println("-------------|-----------|-------");
}

void loop() {
  TFLunaData data;

  if (readTFLunaFrame(data)) {
    if (!data.valid) {
      DEBUG_SERIAL.println("[WARN] Checksum mismatch — frame skipped");
      return;
    }

    const char* status = "";
    if      (data.distanceCm < 10)       status = " [TOO CLOSE]";
    else if (data.distanceCm > 20)      status = " [OUT OF RANGE/TOO FAR]";
    else if (data.amplitude  < 100)      status = " [WEAK SIGNAL]";
    else if (data.amplitude  == 65535)   status = " [SATURATED]";

    char line[64];
    snprintf(line, sizeof(line),
             "%11u  | %9u | %7.2f%s",
             data.distanceCm,
             data.amplitude,
             data.tempCelsius,
             status);
    DEBUG_SERIAL.println(line);
  }
}