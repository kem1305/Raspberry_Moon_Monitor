// ui.h — screen composition (portable; shared by the firmware and the PC simulator).
#pragma once
#include <stdio.h>
#include <time.h>
#include "astro.h"
#include "render.h"
#include "moon_frames.h"

namespace ui {

static const char* const PHASE_NAMES[8] = {
  "Lua nova", "Crescente", "Quarto crescente", "Gibosa crescente",
  "Lua cheia", "Gibosa minguante", "Quarto minguante", "Minguante" };
static const char* const MONTHS[12] = { "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez" };
static const char* const WEEKDAYS[7] = { "dom", "seg", "ter", "qua", "qui", "sex", "sáb" };

// frame whose illumination best matches the real Moon
inline int selectFrame(double elongDeg) {
  int best = 0; double bestD = 1e9;
  for (int i = 0; i < MOON_FRAME_COUNT; i++) {
    double d = fabs(astro::norm180(MOON_FRAME_ELONG[i] / 100.0 - elongDeg));
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

// rotation (CCW, degrees) to apply to frame `idx` so it matches the sky orientation
inline float frameRotation(const astro::MoonState& s, int idx) {
  return (float)astro::norm180(s.northAngle - MOON_FRAME_NORTH[idx] / 10.0);
}

// Moon picture. `frame` is the decoded 240x240 RGB565 frame selectFrame() asked for.
inline void drawMoonScreen(const uint16_t* frame, int idx, uint16_t* dst, const astro::MoonState& s, float dim = 1.0f) {
  render::drawMoon(frame, dst, frameRotation(s, idx), render::scale(render::tintForAltitude(s.alt), dim));
}

struct InfoData {
  astro::MoonState moon;
  bool visible;
  astro::Event first, second;     // next two events in chronological order
  bool firstIsRise;
};

inline InfoData computeInfo(time_t now, double lat, double lon) {
  InfoData d;
  d.moon = astro::moonState((double)now, lat, lon);
  d.visible = d.moon.altGeom > astro::riseSetAltitude(d.moon);
  d.firstIsRise = !d.visible;      // hidden: next rise, then the following set (and vice-versa)
  d.first = astro::nextRiseSet((double)now, lat, lon, d.firstIsRise);
  d.second.valid = false;
  if (d.first.valid) d.second = astro::nextRiseSet((double)d.first.unixTime + 60, lat, lon, !d.firstIsRise);
  return d;
}

inline void formatEvent(char* out, size_t n, bool rise, const astro::Event& e, time_t now) {
  if (!e.valid) { snprintf(out, n, "%s  --:--", rise ? "↑ Nasce" : "↓ Põe"); return; }
  struct tm te, tn; time_t t = (time_t)e.unixTime;
  localtime_r(&t, &te); localtime_r(&now, &tn);
  const char* day = (te.tm_yday == tn.tm_yday) ? "" : WEEKDAYS[te.tm_wday];
  snprintf(out, n, "%s %s%s%02d:%02d · %d°", rise ? "↑" : "↓", day, *day ? " " : "", te.tm_hour, te.tm_min,
           (int)lround(e.az) % 360);
}

// Information screen drawn over the dimmed Moon.
inline void drawInfoScreen(const uint16_t* frame, int idx, uint16_t* dst, const InfoData& d, time_t now) {
  using namespace render;
  drawMoonScreen(frame, idx, dst, d.moon, 0.22f);
  const uint16_t cTitle = rgb(255, 255, 255), cDate = rgb(170, 180, 215), cPhase = rgb(255, 214, 140);
  const uint16_t cLabel = rgb(130, 142, 190), cValue = rgb(225, 230, 255), cHidden = rgb(150, 155, 175);
  const uint16_t cLine = rgb(70, 76, 110);
  char buf[64];
  struct tm tn; localtime_r(&now, &tn);

  snprintf(buf, sizeof buf, "%s, %d %s %d", WEEKDAYS[tn.tm_wday], tn.tm_mday, MONTHS[tn.tm_mon], tn.tm_year + 1900);
  drawCentered(dst, FONT_S, 17, buf, cDate);
  snprintf(buf, sizeof buf, "%02d:%02d", tn.tm_hour, tn.tm_min);
  drawCentered(dst, FONT_XL, 32, buf, cTitle);

  drawCentered(dst, FONT_B, 70, PHASE_NAMES[astro::phaseIndex(d.moon)], cPhase);
  snprintf(buf, sizeof buf, "%d%% iluminada", (int)lround(d.moon.illum * 100));
  drawCentered(dst, FONT_S, 93, buf, cValue);

  hline(dst, 30, 209, 115, cLine);
  drawCentered(dst, FONT_S, 120, d.visible ? "No céu agora" : "Abaixo do horizonte", cLabel);
  int alt = (int)lround(d.moon.alt);
  snprintf(buf, sizeof buf, "Az %d°   Alt %s%d°", (int)lround(d.moon.az) % 360, alt < 0 ? "-" : "", abs(alt));
  drawCentered(dst, FONT_B, 138, buf, d.visible ? cValue : cHidden);

  hline(dst, 38, 201, 164, cLine);
  formatEvent(buf, sizeof buf, d.firstIsRise, d.first, now);
  drawCentered(dst, FONT_M, 171, buf, cValue);
  formatEvent(buf, sizeof buf, !d.firstIsRise, d.second, now);
  drawCentered(dst, FONT_M, 194, buf, cDate);
}

// Simple centred message screen (boot, Wi-Fi, errors). Up to 6 lines; first line is the title.
inline void drawMessage(uint16_t* dst, const char* title, const char* const* lines, int count) {
  using namespace render;
  fill(dst, 0);
  int y = 120 - (26 + count * 22) / 2;
  drawCentered(dst, FONT_B, y, title, rgb(255, 214, 140));
  y += 30;
  for (int i = 0; i < count; i++, y += 22) drawCentered(dst, FONT_S, y, lines[i], rgb(225, 230, 255));
}

}  // namespace ui
