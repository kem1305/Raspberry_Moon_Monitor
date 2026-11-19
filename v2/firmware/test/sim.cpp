// PC simulator: renders the exact firmware screens to raw RGB888 files (converted to PNG by sim.py).
// usage: sim <frames_rgb565_dir> <out.rgb> <unix> <lat> <lon> <moon|info>
#include "../src/ui.h"
#include <stdlib.h>
#include <vector>
int main(int argc, char** argv) {
  if (argc < 7) return 2;
  double t = atof(argv[3]), lat = atof(argv[4]), lon = atof(argv[5]);
  ui::InfoData d = ui::computeInfo((time_t)t, lat, lon);
  int idx = ui::selectFrame(d.moon.elong);
  char path[512]; snprintf(path, sizeof path, "%s/%03d.565", argv[1], idx);
  std::vector<uint16_t> src(240 * 240), dst(240 * 240);
  FILE* f = fopen(path, "rb"); if (!f) return 3;
  if (fread(src.data(), 2, 240 * 240, f) != 240 * 240) return 4;
  fclose(f);
  if (argv[6][0] == 'i') ui::drawInfoScreen(src.data(), idx, dst.data(), d, (time_t)t);
  else ui::drawMoonScreen(src.data(), idx, dst.data(), d.moon);
  f = fopen(argv[2], "wb");
  for (uint16_t p : dst) { uint8_t c[3] = { (uint8_t)((p >> 11) * 255 / 31), (uint8_t)(((p >> 5) & 63) * 255 / 63), (uint8_t)((p & 31) * 255 / 31) }; fwrite(c, 1, 3, f); }
  fclose(f);
  printf("frame=%d elong=%.1f illum=%.1f%% az=%.1f alt=%.1f north=%.1f limb=%.1f rot=%.1f\n", idx, d.moon.elong, d.moon.illum * 100,
         d.moon.az, d.moon.alt, d.moon.northAngle, d.moon.limbAngle, ui::frameRotation(d.moon, idx));
}
