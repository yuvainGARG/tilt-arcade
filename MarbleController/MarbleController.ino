// ============================================================
//  Marble Race - tilt controller
//  Works on BOTH boards: ESP32-S3 and ESP32 38-pin (ESP32-S / WROOM)
//
//  Reads an ADXL345 over I2C and sends tilt to the Raspberry Pi 5
//  over Bluetooth Low Energy (BLE notifications, ~50 per second).
//
//  >>> Set PLAYER_ID to 1 on one board and 2 on the other! <<<
//
//  Hold the controller FLAT when it powers on (it calibrates).
//  Press the BOOT button any time to re-calibrate.
//
//  Arduino IDE: board "ESP32S3 Dev Module" or "ESP32 Dev Module".
//  No extra libraries needed (uses the ESP32 core's BLE + Wire).
// ============================================================

#include <Wire.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#ifndef PLAYER_ID
#define PLAYER_ID 1   // <-- 1 or 2 (or compile with -DPLAYER_ID=2)
#endif

// ---- pins (picked automatically per board) ----
#if CONFIG_IDF_TARGET_ESP32S3
  #define SDA_PIN 8
  #define SCL_PIN 9
  #define LED_PIN -1      // S3 devkits have an RGB LED, not a plain one
#else
  #define SDA_PIN 21
  #define SCL_PIN 22
  #define LED_PIN 2       // blue LED on most 38-pin devkits
#endif
#define BOOT_PIN 0

// Must match marble_race.py on the Pi
#define SERVICE_UUID "6e400001-7a3b-4c1d-9e8f-0123456789ab"
#define TILT_UUID    "6e400002-7a3b-4c1d-9e8f-0123456789ab"

const uint8_t ADXL_ADDR = 0x53;   // SDO pin to GND. If SDO is to 3.3V use 0x1D.

BLECharacteristic* tiltChar = nullptr;
volatile bool piConnected = false;
float offX = 0, offY = 0;         // calibration offsets (raw counts)
float smX = 0, smY = 0;           // smoothed values (milli-g)

// ---------------- ADXL345 ----------------
void adxlWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

int adxlReadReg(uint8_t reg) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(ADXL_ADDR, (uint8_t)1) != 1) return -1;
  return Wire.read();
}

bool adxlRead(int16_t &x, int16_t &y, int16_t &z) {
  Wire.beginTransmission(ADXL_ADDR);
  Wire.write(0x32);                         // DATAX0
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(ADXL_ADDR, (uint8_t)6) != 6) return false;
  uint8_t b[6];
  for (int i = 0; i < 6; i++) b[i] = Wire.read();
  x = (int16_t)(b[0] | (b[1] << 8));
  y = (int16_t)(b[2] | (b[3] << 8));
  z = (int16_t)(b[4] | (b[5] << 8));
  return true;
}

void calibrate() {
  Serial.println("Calibrating - keep it flat...");
  long sx = 0, sy = 0; int n = 0;
  for (int i = 0; i < 60; i++) {
    int16_t x, y, z;
    if (adxlRead(x, y, z)) { sx += x; sy += y; n++; }
    delay(10);
  }
  if (n > 0) { offX = (float)sx / n; offY = (float)sy / n; }
  smX = smY = 0;
  Serial.printf("Offsets: %.1f, %.1f\n", offX, offY);
}

void setLed(bool on) {
  if (LED_PIN >= 0) digitalWrite(LED_PIN, on ? HIGH : LOW);
}

// ---------------- BLE ----------------
class ServerCB : public BLEServerCallbacks {
  void onConnect(BLEServer* s) override {
    piConnected = true;
    Serial.println("Pi connected");
  }
  void onDisconnect(BLEServer* s) override {
    piConnected = false;
    Serial.println("Pi disconnected - advertising again");
    BLEDevice::startAdvertising();
  }
};

void setupBLE() {
  char name[16];
  snprintf(name, sizeof(name), "Marble-P%d", PLAYER_ID);
  BLEDevice::init(name);

  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new ServerCB());

  BLEService* svc = server->createService(SERVICE_UUID);
  tiltChar = svc->createCharacteristic(
      TILT_UUID, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  // Notify needs a 0x2902 descriptor (newer cores add it automatically)
  if (tiltChar->getDescriptorByUUID(BLEUUID((uint16_t)0x2902)) == nullptr) {
    tiltChar->addDescriptor(new BLE2902());
  }
  svc->start();

  BLEAdvertising* adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);          // name goes in the scan response
  BLEDevice::startAdvertising();
  Serial.printf("Advertising as %s\n", name);
}

// ---------------- main ----------------
void setup() {
  Serial.begin(115200);
  delay(300);
  if (LED_PIN >= 0) pinMode(LED_PIN, OUTPUT);
  pinMode(BOOT_PIN, INPUT_PULLUP);

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);

  int id = adxlReadReg(0x00);
  if (id != 0xE5) {
    Serial.printf("ADXL345 not found (got 0x%02X). Check wiring / address.\n", id);
    while (true) { setLed(true); delay(100); setLed(false); delay(100); }  // fast blink = error
  }
  adxlWrite(0x2C, 0x0A);   // BW_RATE: 100 Hz
  adxlWrite(0x31, 0x08);   // DATA_FORMAT: full resolution, +-2g (256 counts per g)
  adxlWrite(0x2D, 0x08);   // POWER_CTL: measure

  calibrate();
  setupBLE();
}

void loop() {
  static uint32_t lastSend = 0, lastBlink = 0;
  static bool blink = false;

  if (digitalRead(BOOT_PIN) == LOW) {
    delay(30);
    if (digitalRead(BOOT_PIN) == LOW) calibrate();
  }

  int16_t x, y, z;
  if (adxlRead(x, y, z)) {
    // raw counts -> milli-g, with calibration, then light smoothing
    float mx = (x - offX) * (1000.0f / 256.0f);
    float my = (y - offY) * (1000.0f / 256.0f);
    smX = smX * 0.6f + mx * 0.4f;
    smY = smY * 0.6f + my * 0.4f;
  }

  uint32_t now = millis();
  if (piConnected && now - lastSend >= 20) {   // 50 Hz
    lastSend = now;
    int16_t ox = (int16_t)constrain(smX, -2000.0f, 2000.0f);
    int16_t oy = (int16_t)constrain(smY, -2000.0f, 2000.0f);
    uint8_t pkt[4] = { (uint8_t)(ox & 0xFF), (uint8_t)(ox >> 8),
                       (uint8_t)(oy & 0xFF), (uint8_t)(oy >> 8) };
    tiltChar->setValue(pkt, 4);
    tiltChar->notify();
  }

  // LED: solid = connected, slow blink = waiting for the Pi
  if (piConnected) setLed(true);
  else if (now - lastBlink > 500) { lastBlink = now; blink = !blink; setLed(blink); }

  delay(5);
}
