// render.h — portable software renderer for the 240x240 round display (no Arduino dependencies,
// also compiled on the PC by firmware/test/sim.cpp to produce the screenshots in docs/).
#pragma once
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "font_data.h"

namespace render {

static const int W = 240, H = 240;

inline uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) { return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)); }

struct Tint { uint16_t r, g, b; };   // per-channel gain, 256 = 1.0

// Colour treatment that mimics what the eye sees:
//  * Moon below the horizon  -> dimmed, cold blue ("it is there, but you cannot see it now")
//  * Moon close to the horizon -> warm orange, fading out at ~12 degrees of altitude
inline Tint tintForAltitude(double altDeg) {
  float r = 1, g = 1, b = 1;
  if (altDeg > 0) {
    float i = 1.0f - (float)altDeg / 12.0f;
    if (i > 0) { g = 1 - 0.30f * i; b = 1 - 0.58f * i; }
  }
  float below = (float)(-altDeg) / 1.5f;                 // 0..1 across the horizon
  below = below < 0 ? 0 : (below > 1 ? 1 : below);
  // at the horizon itself the colour is the full orange; blend from there to the "hidden" look
  float hr = 0.36f, hg = 0.40f, hb = 0.52f;
  float orR = 1, orG = 0.70f, orB = 0.42f;
  if (altDeg <= 0) { r = orR + (hr - orR) * below; g = orG + (hg - orG) * below; b = orB + (hb - orB) * below; }
  Tint t = { (uint16_t)(r * 256), (uint16_t)(g * 256), (uint16_t)(b * 256) };
  return t;
}

inline Tint scale(Tint t, float k) { Tint o = { (uint16_t)(t.r * k), (uint16_t)(t.g * k), (uint16_t)(t.b * k) }; return o; }

// Rotate `src` (240x240 RGB565, Moon disc filling the frame) counter-clockwise by angleDeg around the
// centre with bilinear filtering, apply the tint and write to `dst`. Everything outside the disc is black.
inline void drawMoon(const uint16_t* src, uint16_t* dst, float angleDeg, Tint tint) {
  const float a = angleDeg * 0.017453292f;
  const int32_t c = (int32_t)lroundf(cosf(a) * 65536.0f), s = (int32_t)lroundf(sinf(a) * 65536.0f);
  const int32_t half = 119 * 65536 + 32768;              // 119.5 in 16.16
  const int32_t rmax2 = 120 * 120 * 4;                   // compare in half-pixel units
  for (int y = 0; y < H; y++) {
    int32_t Y2 = 239 - 2 * y;                            // 2*(119.5 - y)
    // source coords for X = -119.5: xs = X c + Yup s ; ys_up = -X s + Yup c
    int32_t xs = (int32_t)(((int64_t)-239 * c + (int64_t)Y2 * s) / 2) + half;
    int32_t ysu = (int32_t)(((int64_t)239 * s + (int64_t)Y2 * c) / 2);
    int32_t ys = half - ysu;                             // image y grows downwards
    uint16_t* o = dst + y * W;
    for (int x = 0; x < W; x++, xs += c, ys += s) {
      int32_t X2 = 2 * x - 239;
      if (X2 * X2 + Y2 * Y2 > rmax2) { o[x] = 0; continue; }
      int32_t fx = xs < 0 ? 0 : (xs > (239 << 16) ? (239 << 16) : xs);
      int32_t fy = ys < 0 ? 0 : (ys > (239 << 16) ? (239 << 16) : ys);
      int ix = fx >> 16, iy = fy >> 16;
      int wx = (fx >> 11) & 31, wy = (fy >> 11) & 31;    // 5-bit weights
      int ix1 = ix < 239 ? ix + 1 : ix, iy1 = iy < 239 ? iy + 1 : iy;
      uint16_t p00 = src[iy * W + ix], p01 = src[iy * W + ix1], p10 = src[iy1 * W + ix], p11 = src[iy1 * W + ix1];
      int w00 = (32 - wx) * (32 - wy), w01 = wx * (32 - wy), w10 = (32 - wx) * wy, w11 = wx * wy;   // sum 1024
      uint32_t r = ((p00 >> 11) * w00 + (p01 >> 11) * w01 + (p10 >> 11) * w10 + (p11 >> 11) * w11);          // 5+10 bits
      uint32_t g = (((p00 >> 5) & 63) * w00 + ((p01 >> 5) & 63) * w01 + ((p10 >> 5) & 63) * w10 + ((p11 >> 5) & 63) * w11);
      uint32_t b = ((p00 & 31) * w00 + (p01 & 31) * w01 + (p10 & 31) * w10 + (p11 & 31) * w11);
      r = (r * tint.r) >> 18; g = (g * tint.g) >> 18; b = (b * tint.b) >> 18;
      if (r > 31) r = 31;
      if (g > 63) g = 63;
      if (b > 31) b = 31;
      o[x] = (uint16_t)((r << 11) | (g << 5) | b);
    }
  }
}

inline void fill(uint16_t* dst, uint16_t color) { for (int i = 0; i < W * H; i++) dst[i] = color; }

inline void hline(uint16_t* dst, int x0, int x1, int y, uint16_t color) {
  if (y < 0 || y >= H) return;
  for (int x = x0 < 0 ? 0 : x0; x <= x1 && x < W; x++) dst[y * W + x] = color;
}

inline void fillRect(uint16_t* dst, int x, int y, int w, int h, uint16_t color) {
  for (int j = y; j < y + h; j++) hline(dst, x, x + w - 1, j, color);
}

// ---- text (UTF-8, anti-aliased) --------------------------------------------------------------
inline uint32_t nextCodepoint(const char*& p) {
  uint8_t c = (uint8_t)*p++;
  if (c < 0x80) return c;
  int extra = (c >= 0xF0) ? 3 : (c >= 0xE0) ? 2 : 1;
  uint32_t cp = c & (0x3F >> extra);
  while (extra-- && *p) cp = (cp << 6) | ((uint8_t)*p++ & 0x3F);
  return cp;
}

inline const Glyph* findGlyph(const Font& f, uint32_t cp) {
  int lo = 0, hi = f.count - 1;
  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (f.glyphs[mid].code == cp) return &f.glyphs[mid];
    if (f.glyphs[mid].code < cp) lo = mid + 1; else hi = mid - 1;
  }
  return cp == '?' ? nullptr : findGlyph(f, '?');
}

inline int textWidth(const Font& f, const char* s) {
  int w = 0;
  while (*s) { const Glyph* g = findGlyph(f, nextCodepoint(s)); if (g) w += g->adv; }
  return w;
}

inline void blendPixel(uint16_t* dst, int x, int y, uint16_t color, int a /*0..15*/) {
  if (x < 0 || y < 0 || x >= W || y >= H || a == 0) return;
  uint16_t d = dst[y * W + x];
  int r = ((d >> 11) * (15 - a) + (color >> 11) * a) / 15;
  int g = (((d >> 5) & 63) * (15 - a) + ((color >> 5) & 63) * a) / 15;
  int b = ((d & 31) * (15 - a) + (color & 31) * a) / 15;
  dst[y * W + x] = (uint16_t)((r << 11) | (g << 5) | b);
}

// draws with (x, y) = left / top of the line box; returns the advance
inline int drawText(uint16_t* dst, const Font& f, int x, int y, const char* s, uint16_t color) {
  int x0 = x;
  while (*s) {
    const Glyph* g = findGlyph(f, nextCodepoint(s));
    if (!g) continue;
    const uint8_t* d = f.data + g->offset;
    int n = 0;
    for (int j = 0; j < g->h; j++)
      for (int i = 0; i < g->w; i++, n++) {
        int a = (n & 1) ? (d[n >> 1] & 15) : (d[n >> 1] >> 4);
        blendPixel(dst, x + g->xoff + i, y + g->yoff + j, color, a);
      }
    x += g->adv;
  }
  return x - x0;
}

inline void drawCentered(uint16_t* dst, const Font& f, int y, const char* s, uint16_t color, int cx = W / 2) {
  drawText(dst, f, cx - textWidth(f, s) / 2, y, s, color);
}

}  // namespace render
