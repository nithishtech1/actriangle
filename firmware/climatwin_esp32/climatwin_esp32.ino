/*
 * ClimaTwin Unified ESP32 Firmware (Single 4.7 kOhm Resistor Edition)
 * ------------------------------------------------------------------
 * Matches ESP-32S NodeMCU 38-Pin + 840-pt Breadboard layout:
 *   - 2x DS18B20 Waterproof Probes -> BOTH shared on P27 (GPIO 27)
 *                                    with ONE 4.7 kOhm pull-up to 3V3
 *   - 1x DHT11 (3-pin PCB module)  -> P26 (GPIO 26), VCC=3V3, GND=GND
 *
 * Output CSV (115200 baud, ~5s/row):
 *   ms,probe0_C,probe1_C,room_C,room_RH
 *
 * Lines starting with '#' are diagnostic status lines automatically ignored
 * by ClimaTwin's Python logger (logger/log_serial.py).
 */

#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>

#define ONEWIRE_PIN 27   // P27: Both DS18B20 yellow wires + 4.7k resistor to 3V3
#define DHT_PIN     26   // P26: DHT11 DATA/OUT pin
#define DHT_TYPE    DHT11

OneWire oneWire(ONEWIRE_PIN);
DallasTemperature dsSensors(&oneWire);
DHT dht(DHT_PIN, DHT_TYPE);

static bool isValidTemp(float c) {
  return !isnan(c) && c > -10.0f && c < 60.0f && c != 85.0f;
}

void setup() {
  Serial.begin(115200);
  delay(600);
  dsSensors.begin();
  dsSensors.setResolution(12);
  dht.begin();
  Serial.println("# ClimaTwin ESP32 ready (115200 baud)");
  Serial.printf("# DS18B20 probes found on P27: %d / 2\n", dsSensors.getDeviceCount());
  Serial.println("# Format: ms,probe0_C,probe1_C,room_C,room_RH");
}

void loop() {
  unsigned long loopStart = millis();

  if (dsSensors.getDeviceCount() < 2) {
    dsSensors.begin();  // Auto-rediscover if a loose probe wire is pushed in live
    dsSensors.setResolution(12);
  }

  dsSensors.requestTemperatures();
  float probe0 = dsSensors.getTempCByIndex(0);
  float probe1 = dsSensors.getTempCByIndex(1);
  float roomT  = dht.readTemperature();
  float roomRH = dht.readHumidity();

  int found = dsSensors.getDeviceCount();
  bool okDS  = (found >= 2) && isValidTemp(probe0) && isValidTemp(probe1);
  bool okDHT = !isnan(roomT) && !isnan(roomRH) && roomT > -10.0f && roomT < 60.0f && roomRH >= 0.0f && roomRH <= 100.0f;

  if (okDS && okDHT) {
    Serial.printf("%lu,%.2f,%.2f,%.2f,%.2f\n", millis(), probe0, probe1, roomT, roomRH);
  } else {
    Serial.printf("# CHECK [%d/2 probes on P27]: P0=%.2f P1=%.2f | DHT(P26): T=%.2f RH=%.1f\n",
                  found, probe0, probe1, roomT, roomRH);
  }

  unsigned long elapsed = millis() - loopStart;
  if (elapsed < 5000UL) {
    delay(5000UL - elapsed);
  }
}
