#pragma once
#include <Arduino.h>
enum { WL_CONNECTED = 3 };
enum { WIFI_STA = 1, WIFI_AP_STA = 3 };
enum { WIFI_AUTH_OPEN = 0 };
struct IPAddress {};
struct WiFiStub {
  void persistent(bool) {} void mode(int) {} void setHostname(const char*) {} void setAutoReconnect(bool) {}
  void begin(const char*, const char*) {} int status() { return 0; } void disconnect(bool = false) {}
  bool softAP(const char*, const char*, int = 1, int = 0, int = 4) { return true; } IPAddress softAPIP() { return IPAddress(); }
  void macAddress(uint8_t*) {} int scanNetworks() { return 0; } String SSID(int) { return ""; } int RSSI(int) { return 0; }
  int encryptionType(int) { return 0; } void scanDelete() {}
};
static WiFiStub WiFi;
