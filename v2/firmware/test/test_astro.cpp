#include "../src/astro.h"
#include <stdio.h>
#include <stdlib.h>
int main() {
  // input lines: unix lat lon   -> output CSV
  double t, la, lo;
  while (scanf("%lf %lf %lf", &t, &la, &lo) == 3) {
    astro::MoonState s = astro::moonState(t, la, lo);
    astro::Event r = astro::nextRiseSet(t, la, lo, true), st = astro::nextRiseSet(t, la, lo, false);
    printf("%.0f,%.4f,%.4f,%.4f,%.4f,%.5f,%.3f,%.3f,%lld,%.2f,%lld,%.2f,%.3f\n", t, la, lo, s.az, s.altGeom, s.illum,
           s.limbAngle, s.northAngle, r.valid ? (long long)r.unixTime : -1LL, r.az,
           st.valid ? (long long)st.unixTime : -1LL, st.az, s.elong);
  }
}
