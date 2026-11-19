// Moon Monitor v2 — firmware for the ESP32-S3 + GC9A01 round display gadget.
//
//  * Moon picture: NASA phase frame matching the current illumination, rotated to the exact orientation
//    the Moon has in the sky at the configured location (zenith = top of the display).
//  * Short press: information screen (30 s).  Hold 5 s: Wi-Fi setup portal.
//  * First boot (or Wi-Fi failure): the gadget opens its own WPA2 access point with a captive setup page.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <LittleFS.h>
#include <esp_random.h>
#include <sys/time.h>
#define LGFX_USE_V1
#include <LovyanGFX.hpp>

#include "config.h"
#include "ui.h"
#include "portal_html.h"

// ------------------------------------------------------------------------------------------------
// Display
// ------------------------------------------------------------------------------------------------
class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_GC9A01 _panel;
  lgfx::Bus_SPI _bus;
 public:
  LGFX() {
    {
      auto cfg = _bus.config();
      cfg.spi_host = SPI2_HOST;
      cfg.spi_mode = 0;
      cfg.freq_write = 40000000;
      cfg.freq_read = 16000000;
      cfg.spi_3wire = true;
      cfg.use_lock = true;
      cfg.dma_channel = SPI_DMA_CH_AUTO;
      cfg.pin_sclk = PIN_LCD_SCL;
      cfg.pin_mosi = PIN_LCD_SDA;
      cfg.pin_miso = -1;
      cfg.pin_dc = PIN_LCD_DC;
      _bus.config(cfg);
      _panel.setBus(&_bus);
    }
    {
      auto cfg = _panel.config();
      cfg.pin_cs = PIN_LCD_CS;
      cfg.pin_rst = PIN_LCD_RST;
      cfg.pin_busy = -1;
      cfg.panel_width = 240;
      cfg.panel_height = 240;
      cfg.offset_rotation = 0;
      cfg.readable = false;
      cfg.invert = true;
      cfg.rgb_order = false;
      cfg.bus_shared = false;
      _panel.config(cfg);
    }
    setPanel(&_panel);
  }
};

static LGFX lcd;
static LGFX_Sprite decoder(&lcd);        // JPEG decode target (PSRAM)
static uint16_t* frameBuf = nullptr;     // decoded Moon frame, native RGB565
static uint16_t* canvas = nullptr;       // composed screen
static int loadedFrame = -1;
static bool lcdPowered = false;

// ------------------------------------------------------------------------------------------------
// Settings (NVS)
// ------------------------------------------------------------------------------------------------
struct Settings {
  String ssid, pass, tz, apPass;
  double lat = 0, lon = 0;
  bool configured = false;
  uint8_t rotation = DISPLAY_ROTATION;
  bool night = false;
  uint16_t nightStart = 23 * 60, nightEnd = 6 * 60;      // minutes of the day
} cfg;

static Preferences prefs;

static void loadSettings() {
  prefs.begin("moon", false);
  cfg.configured = prefs.getBool("ok", false);
  cfg.ssid = prefs.getString("ssid", "");
  cfg.pass = prefs.getString("pass", "");
  cfg.tz = prefs.getString("tz", "<-03>3");
  cfg.lat = prefs.getDouble("lat", 0);
  cfg.lon = prefs.getDouble("lon", 0);
  cfg.rotation = prefs.getUChar("rot", DISPLAY_ROTATION) & 3;
  cfg.night = prefs.getBool("night", false);
  cfg.nightStart = prefs.getUShort("n0", 23 * 60);
  cfg.nightEnd = prefs.getUShort("n1", 6 * 60);
  cfg.apPass = prefs.getString("appass", "");
  if (cfg.apPass.length() != 8) {                        // per-device random portal password
    static const char abc[] = "abcdefghjkmnpqrstuvwxyz23456789";
    cfg.apPass = "";
    for (int i = 0; i < 8; i++) cfg.apPass += abc[esp_random() % (sizeof(abc) - 1)];
    prefs.putString("appass", cfg.apPass);
  }
}

static void saveSettings() {
  prefs.putString("ssid", cfg.ssid);
  prefs.putString("pass", cfg.pass);
  prefs.putString("tz", cfg.tz);
  prefs.putDouble("lat", cfg.lat);
  prefs.putDouble("lon", cfg.lon);
  prefs.putUChar("rot", cfg.rotation);
  prefs.putBool("night", cfg.night);
  prefs.putUShort("n0", cfg.nightStart);
  prefs.putUShort("n1", cfg.nightEnd);
  prefs.putBool("ok", true);
}

// ------------------------------------------------------------------------------------------------
// Display helpers
// ------------------------------------------------------------------------------------------------
static const int LCD_PINS[] = { PIN_LCD_RST, PIN_LCD_CS, PIN_LCD_DC, PIN_LCD_SDA, PIN_LCD_SCL };

static void lcdPower(bool on) {
  if (on == lcdPowered) return;
  if (on) {
    digitalWrite(PIN_LCD_POWER, LOW);
    delay(60);
    lcd.init();
    lcd.setRotation(cfg.rotation);
    lcd.setSwapBytes(true);
    lcd.fillScreen(0);
  } else {
    lcd.releaseBus();
    for (int p : LCD_PINS) { pinMode(p, OUTPUT); digitalWrite(p, LOW); }   // do not back-feed the module
    digitalWrite(PIN_LCD_POWER, HIGH);
  }
  lcdPowered = on;
}

static void present() {
  if (lcdPowered) lcd.pushImage(0, 0, 240, 240, canvas);
}

static void showMessage(const char* title, const char* l1 = nullptr, const char* l2 = nullptr, const char* l3 = nullptr) {
  const char* lines[3]; int n = 0;
  if (l1) lines[n++] = l1;
  if (l2) lines[n++] = l2;
  if (l3) lines[n++] = l3;
  ui::drawMessage(canvas, title, lines, n);
  present();
}

static bool loadFrame(int idx) {
  if (idx == loadedFrame) return true;
  char path[24];
  snprintf(path, sizeof path, "/m/%03d.jpg", idx);
  decoder.fillSprite(0);
  if (!decoder.drawJpgFile(LittleFS, path, 0, 0)) { loadedFrame = -1; return false; }
  const uint16_t* s = (const uint16_t*)decoder.getBuffer();      // sprite pixels are byte-swapped RGB565
  for (int i = 0; i < 240 * 240; i++) frameBuf[i] = (uint16_t)((s[i] << 8) | (s[i] >> 8));
  loadedFrame = idx;
  return true;
}

// ------------------------------------------------------------------------------------------------
// Time / Wi-Fi
// ------------------------------------------------------------------------------------------------
static bool timeValid() { return time(nullptr) > 1700000000; }

static void startWifi() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("moonmonitor");
  WiFi.setAutoReconnect(true);
  WiFi.begin(cfg.ssid.c_str(), cfg.pass.c_str());
  configTzTime(cfg.tz.c_str(), "pool.ntp.org", "time.google.com", "time.cloudflare.com");
}

// ------------------------------------------------------------------------------------------------
// Setup portal
// ------------------------------------------------------------------------------------------------
static WebServer server(80);
static DNSServer dns;
static bool portalActive = false;
static uint32_t portalStarted = 0;
static bool rebootPending = false;
static uint32_t rebootAt = 0;
static String apSsid;

static String htmlEscape(const String& s) {
  String o;
  for (char c : s) {
    if (c == '&') o += F("&amp;"); else if (c == '<') o += F("&lt;"); else if (c == '>') o += F("&gt;");
    else if (c == '"') o += F("&quot;"); else o += c;
  }
  return o;
}

static String jsonEscape(const String& s) {
  String o;
  for (char c : s) {
    if (c == '"' || c == '\\') { o += '\\'; o += c; }
    else if ((uint8_t)c < 0x20) o += ' ';
    else o += c;
  }
  return o;
}

static String hhmm(uint16_t m) { char b[6]; snprintf(b, sizeof b, "%02u:%02u", (m / 60) % 24, m % 60); return b; }
static uint16_t parseHhmm(const String& s, uint16_t fallback) {
  int h, m;
  if (sscanf(s.c_str(), "%d:%d", &h, &m) == 2 && h >= 0 && h < 24 && m >= 0 && m < 60) return h * 60 + m;
  return fallback;
}

static void handleRoot() {
  String page = FPSTR(PORTAL_HTML);
  page.replace(F("%SSID%"), htmlEscape(cfg.ssid));
  page.replace(F("%PASSHINT%"), cfg.configured ? F("(manter a senha atual)") : F("Senha do Wi-Fi"));
  page.replace(F("%COORD%"), cfg.configured ? String(cfg.lat, 5) + ", " + String(cfg.lon, 5) : String());
  page.replace(F("%TZ%"), cfg.configured ? htmlEscape(cfg.tz) : String());
  page.replace(F("%ROT%"), String(cfg.rotation));
  page.replace(F("%NIGHT%"), cfg.night ? "1" : "0");
  page.replace(F("%N0%"), hhmm(cfg.nightStart));
  page.replace(F("%N1%"), hhmm(cfg.nightEnd));
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.send(200, F("text/html; charset=utf-8"), page);
}

static void handleScan() {
  int n = WiFi.scanNetworks();
  String out = "[";
  int listed = 0;
  for (int i = 0; i < n && listed < 20; i++) {
    String s = WiFi.SSID(i);
    if (!s.length()) continue;
    bool dup = false;
    for (int j = 0; j < i; j++) if (WiFi.SSID(j) == s) { dup = true; break; }
    if (dup) continue;
    if (listed++) out += ',';
    out += "{\"s\":\"" + jsonEscape(s) + "\",\"r\":" + String(WiFi.RSSI(i)) + ",\"o\":" +
           (WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "1" : "0") + "}";
  }
  out += "]";
  WiFi.scanDelete();
  server.sendHeader(F("Cache-Control"), F("no-store"));
  server.send(200, F("application/json"), out);
}

static void handleSave() {
  String ssid = server.arg("ssid"), pass = server.arg("pass"), tz = server.arg("tz"), coord = server.arg("coord");
  ssid.trim(); tz.trim();
  double lat = 1000, lon = 1000;
  coord.replace(';', ',');
  int comma = coord.indexOf(',');
  if (comma > 0) { lat = coord.substring(0, comma).toDouble(); lon = coord.substring(comma + 1).toDouble(); }
  bool ok = ssid.length() >= 1 && ssid.length() <= 32 && pass.length() <= 64 && tz.length() >= 3 && tz.length() <= 60 &&
            comma > 0 && fabs(lat) <= 90.0 && fabs(lon) <= 180.0;
  if (!ok) { server.send(400, F("text/plain; charset=utf-8"), F("Dados inválidos. Volte e confira os campos.")); return; }
  bool sameNet = cfg.configured && ssid == cfg.ssid;
  cfg.ssid = ssid;
  if (pass.length() || !sameNet) cfg.pass = pass;        // empty password keeps the stored one for the same network
  cfg.tz = tz; cfg.lat = lat; cfg.lon = lon;
  cfg.rotation = (uint8_t)(server.arg("rot").toInt() & 3);
  cfg.night = server.arg("night") == "1";
  cfg.nightStart = parseHhmm(server.arg("n0"), cfg.nightStart);
  cfg.nightEnd = parseHhmm(server.arg("n1"), cfg.nightEnd);
  cfg.configured = true;
  saveSettings();
  long long epoch = atoll(server.arg("epoch").c_str());    // clock of the phone: useful until NTP answers
  if (epoch > 1700000000LL) { timeval tv = { (time_t)epoch, 0 }; settimeofday(&tv, nullptr); }
  server.send(200, F("text/html; charset=utf-8"), FPSTR(SAVED_HTML));
  rebootPending = true;
  rebootAt = millis() + 1500;
}

static void handleRedirect() {            // captive-portal detection requests land here
  server.sendHeader(F("Location"), F("http://192.168.4.1/"), true);
  server.send(302, F("text/plain"), "");
}

static void drawPortalScreen() {
  using namespace render;
  fill(canvas, 0);
  drawCentered(canvas, FONT_B, 12, "Configurar", rgb(255, 214, 140));
  fillRect(canvas, 59, 37, 122, 122, 0xFFFF);                     // quiet zone for the QR code
  drawCentered(canvas, FONT_S, 164, apSsid.c_str(), rgb(225, 230, 255));
  String p = "senha " + cfg.apPass;
  drawCentered(canvas, FONT_S, 184, p.c_str(), rgb(225, 230, 255));
  drawCentered(canvas, FONT_S, 204, "192.168.4.1", rgb(130, 142, 190));
  present();
  String qr = "WIFI:T:WPA;S:" + apSsid + ";P:" + cfg.apPass + ";;";
  if (lcdPowered) lcd.qrcode(qr.c_str(), 65, 43, 110, 3);
}

static void startPortal() {
  if (portalActive) return;
  lcdPower(true);
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char suffix[5];
  snprintf(suffix, sizeof suffix, "%02X%02X", mac[4], mac[5]);
  apSsid = String(AP_SSID_PREFIX) + suffix;
  WiFi.disconnect(true);
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(apSsid.c_str(), cfg.apPass.c_str(), 1, 0, 2);
  delay(150);
  dns.setErrorReplyCode(DNSReplyCode::NoError);
  dns.start(53, "*", WiFi.softAPIP());
  server.on("/", HTTP_GET, handleRoot);
  server.on("/scan", HTTP_GET, handleScan);
  server.on("/save", HTTP_POST, handleSave);
  server.onNotFound(handleRedirect);
  server.begin();
  portalActive = true;
  portalStarted = millis();
  drawPortalScreen();
}

// ------------------------------------------------------------------------------------------------
// Main state machine
// ------------------------------------------------------------------------------------------------
enum Screen { SCREEN_MOON, SCREEN_INFO };
static Screen screen = SCREEN_MOON;
static uint32_t infoSince = 0, lastDraw = 0, wakeUntil = 0, bootMs = 0;
static bool needDraw = true;
static int lastMinute = -1;

static bool nightNow() {
  if (!cfg.night || !timeValid() || cfg.nightStart == cfg.nightEnd) return false;
  time_t now = time(nullptr); struct tm t; localtime_r(&now, &t);
  int m = t.tm_hour * 60 + t.tm_min;
  return cfg.nightStart < cfg.nightEnd ? (m >= cfg.nightStart && m < cfg.nightEnd)
                                       : (m >= cfg.nightStart || m < cfg.nightEnd);
}

static void drawCurrent() {
  if (!timeValid()) {
    if (WiFi.status() == WL_CONNECTED) showMessage("Moon Monitor", "Wi-Fi conectado", "Sincronizando o relógio…");
    else showMessage("Moon Monitor", "Conectando ao Wi-Fi…", cfg.ssid.c_str());
    return;
  }
  time_t now = time(nullptr);
  ui::InfoData d = ui::computeInfo(now, cfg.lat, cfg.lon);
  int idx = ui::selectFrame(d.moon.elong);
  if (!loadFrame(idx)) {
    showMessage("Sem imagens", "Grave o sistema de", "arquivos: pio run -t uploadfs");
    return;
  }
  if (screen == SCREEN_INFO) ui::drawInfoScreen(frameBuf, idx, canvas, d, now);
  else ui::drawMoonScreen(frameBuf, idx, canvas, d.moon);
  present();
}

// button: returns 1 on short click (release), 2 once when held for LONG_PRESS_MS
static int pollButton() {
  static bool stable = false, lastRaw = false, longFired = false;
  static uint32_t changedAt = 0, pressedAt = 0;
  bool raw = digitalRead(PIN_BUTTON) == LOW;
  uint32_t now = millis();
  if (raw != lastRaw) { lastRaw = raw; changedAt = now; }
  if (now - changedAt > 30 && raw != stable) {
    stable = raw;
    if (stable) { pressedAt = now; longFired = false; }
    else if (!longFired) return 1;
  }
  if (stable && !longFired && now - pressedAt >= LONG_PRESS_MS) { longFired = true; return 2; }
  return 0;
}

void setup() {
  pinMode(PIN_LCD_POWER, OUTPUT);
  digitalWrite(PIN_LCD_POWER, HIGH);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  Serial.begin(115200);
  loadSettings();

  frameBuf = (uint16_t*)ps_malloc(240 * 240 * 2);
  canvas = (uint16_t*)ps_malloc(240 * 240 * 2);
  decoder.setPsram(true);
  decoder.setColorDepth(16);
  bool mem = frameBuf && canvas && decoder.createSprite(240, 240);
  lcdPower(true);
  if (!mem) { lcd.setTextColor(0xFFFF); lcd.drawCenterString("PSRAM?", 120, 112); for (;;) delay(1000); }
  if (!LittleFS.begin(false)) Serial.println("LittleFS mount failed (run: pio run -t uploadfs)");

  setenv("TZ", cfg.tz.c_str(), 1);
  tzset();
  bootMs = millis();
  if (cfg.configured) { startWifi(); drawCurrent(); }
  else startPortal();
}

void loop() {
  uint32_t ms = millis();
  int btn = pollButton();

  if (portalActive) {
    dns.processNextRequest();
    server.handleClient();
    if (rebootPending && (int32_t)(ms - rebootAt) >= 0) { delay(100); ESP.restart(); }
    // leave the portal: short click, or timeout (only when there is a configuration to fall back to)
    if (cfg.configured && !rebootPending && (btn == 1 || ms - portalStarted > PORTAL_TIMEOUT_MS)) ESP.restart();
    delay(2);
    return;
  }

  if (btn == 2) { startPortal(); return; }

  // no network after 90 s and the clock was never set -> the credentials are probably wrong: open the portal
  if (!timeValid() && WiFi.status() != WL_CONNECTED && ms - bootMs > 90000) { startPortal(); return; }

  bool night = nightNow() && (int32_t)(wakeUntil - ms) <= 0;
  if (btn == 1) {
    if (!lcdPowered) {                                     // wake the dark display for a while
      wakeUntil = ms + INFO_TIMEOUT_MS;
      night = false;
      screen = SCREEN_MOON;
    } else {
      screen = (screen == SCREEN_MOON) ? SCREEN_INFO : SCREEN_MOON;
      if (nightNow()) wakeUntil = ms + INFO_TIMEOUT_MS;
    }
    infoSince = ms;
    needDraw = true;
  }
  if (screen == SCREEN_INFO && ms - infoSince >= INFO_TIMEOUT_MS) { screen = SCREEN_MOON; needDraw = true; }

  if (night) { lcdPower(false); delay(20); return; }
  if (!lcdPowered) { lcdPower(true); needDraw = true; }

  // redraw: on demand, when the minute changes (info screen clock) and at least once a minute
  time_t now = time(nullptr); struct tm t; localtime_r(&now, &t);
  bool tick = timeValid() ? (t.tm_min != lastMinute) : (ms - lastDraw > 2000);
  if (needDraw || tick || ms - lastDraw > MOON_REFRESH_MS) {
    lastMinute = t.tm_min;
    lastDraw = ms;
    needDraw = false;
    drawCurrent();
  }
  delay(10);
}
