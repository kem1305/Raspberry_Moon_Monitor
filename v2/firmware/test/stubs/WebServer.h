#pragma once
#include <Arduino.h>
enum { HTTP_GET, HTTP_POST };
struct WebServer {
  WebServer(int) {}
  void on(const char*, int, void (*)()) {} void onNotFound(void (*)()) {} void begin() {} void handleClient() {}
  String arg(const char*) { return ""; } void sendHeader(const String&, const String&, bool = false) {}
  void send(int, const String&, const String&) {}
};
