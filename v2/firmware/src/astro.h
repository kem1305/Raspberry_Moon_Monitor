// astro.h — Moon/Sun ephemeris for the Moon Monitor (portable C++11, no dependencies).
//
// Algorithms: Jean Meeus, "Astronomical Algorithms" 2nd ed. (ch. 12, 13, 22, 25, 40, 47, 48).
// Accuracy (validated against PyEphem/libastro, see firmware/test): position ~0.02°,
// illumination <0.1 %, rise/set times within ~1 minute.
#pragma once
#include <math.h>
#include <stdint.h>

namespace astro {

static const double PI = 3.14159265358979323846;
static const double D2R = PI / 180.0;
static const double R2D = 180.0 / PI;

inline double norm360(double x) { x = fmod(x, 360.0); return x < 0 ? x + 360.0 : x; }
inline double norm180(double x) { x = norm360(x); return x > 180.0 ? x - 360.0 : x; }
inline double sind(double x) { return sin(x * D2R); }
inline double cosd(double x) { return cos(x * D2R); }

struct MoonState {
  // topocentric, for the observer
  double az;          // azimuth, degrees from North through East (0..360)
  double alt;         // apparent altitude incl. refraction, degrees
  double altGeom;     // geometric (airless) altitude of the centre, degrees
  // phase
  double illum;       // illuminated fraction 0..1
  double elong;       // "phase elongation" 0..360: 0 new, 90 first quarter, 180 full, 270 last quarter
  bool waxing;
  // orientation as seen by the observer (zenith up):
  double limbAngle;   // direction of the bright limb midpoint, degrees counter-clockwise from "up"
  double northAngle;  // direction of the Moon's (ecliptic) north, degrees counter-clockwise from "up"
  double distanceKm;
  double semiDiam;    // topocentric-ish semidiameter, degrees
};

struct Event {
  bool valid;
  int64_t unixTime;   // UTC
  double az;          // azimuth at the event
};

namespace detail {

struct Ecl { double lon, lat, dist; };          // degrees, degrees, km (Moon) / AU (Sun)
struct Equ { double ra, dec; };                 // degrees

inline double julianDay(double unixTime) { return unixTime / 86400.0 + 2440587.5; }

struct LTerm { int8_t d, m, mp, f; int32_t l; int32_t r; };
struct BTerm { int8_t d, m, mp, f; int32_t b; };

static const LTerm LT[] = {
  {0,0,1,0,6288774,-20905355},{2,0,-1,0,1274027,-3699111},{2,0,0,0,658314,-2955968},
  {0,0,2,0,213618,-569925},{0,1,0,0,-185116,48888},{0,0,0,2,-114332,-3149},
  {2,0,-2,0,58793,246158},{2,-1,-1,0,57066,-152138},{2,0,1,0,53322,-170733},
  {2,-1,0,0,45758,-204586},{0,1,-1,0,-40923,-129620},{1,0,0,0,-34720,108743},
  {0,1,1,0,-30383,104755},{2,0,0,-2,15327,10321},{0,0,1,2,-12528,0},
  {0,0,1,-2,10980,79661},{4,0,-1,0,10675,-34782},{0,0,3,0,10034,-23210},
  {4,0,-2,0,8548,-21636},{2,1,-1,0,-7888,24208},{2,1,0,0,-6766,30824},
  {1,0,-1,0,-5163,-8379},{1,1,0,0,4987,-16675},{2,-1,1,0,4036,-12831},
  {2,0,2,0,3994,-10445},{4,0,0,0,3861,-11650},{2,0,-3,0,3665,14403},
  {0,1,-2,0,-2689,-7003},{2,0,-1,2,-2602,0},{2,-1,-2,0,2390,10056},
  {1,0,1,0,-2348,6322},{2,-2,0,0,2236,-9884},{0,1,2,0,-2120,5751},
  {0,2,0,0,-2069,0},{2,-2,-1,0,2048,-4950},{2,0,1,-2,-1773,4130},
  {2,0,0,2,-1595,0},{4,-1,-1,0,1215,-3958},{0,0,2,2,-1110,0},
  {3,0,-1,0,-892,3258},{2,1,1,0,-810,2616},{4,-1,-2,0,759,-1897},
  {0,2,-1,0,-713,-2117},{2,2,-1,0,-700,2354},{2,1,-2,0,691,0},
  {2,-1,0,-2,596,0},{4,0,1,0,549,-1423},{0,0,4,0,537,-1117},
  {4,-1,0,0,520,-1571},{1,0,-2,0,-487,-1739},
};
static const BTerm BT[] = {
  {0,0,0,1,5128122},{0,0,1,1,280602},{0,0,1,-1,277693},{2,0,0,-1,173237},
  {2,0,-1,1,55413},{2,0,-1,-1,46271},{2,0,0,1,32573},{0,0,2,1,17198},
  {2,0,1,-1,9266},{0,0,2,-1,8822},{2,-1,0,-1,8216},{2,0,-2,-1,4324},
  {2,0,1,1,4200},{2,1,0,-1,-3359},{2,-1,-1,1,2463},{2,-1,0,1,2211},
  {2,-1,-1,-1,2065},{0,1,-1,-1,-1870},{4,0,-1,-1,1828},{0,1,0,1,-1794},
  {0,0,0,3,-1749},{0,1,-1,1,-1565},{1,0,0,1,-1491},{0,1,1,1,-1475},
  {0,1,1,-1,-1410},{0,1,0,-1,-1344},{1,0,0,-1,-1335},{0,0,3,1,1107},
  {4,0,0,-1,1021},{4,0,-1,1,833},
};

struct Frame {            // quantities shared by Sun and Moon for one instant
  double T;               // Julian centuries TT from J2000
  double dpsi, eps;       // nutation in longitude, true obliquity (degrees)
  double gast;            // Greenwich apparent sidereal time (degrees)
  double sunLon;          // Sun apparent ecliptic longitude
  double sunR;            // AU
};

inline Frame makeFrame(double unixTime) {
  Frame f;
  const double deltaT = 69.2;                         // TT-UT, seconds (2020s)
  double jd = julianDay(unixTime);
  double T = (jd + deltaT / 86400.0 - 2451545.0) / 36525.0;
  f.T = T;
  double L0 = norm360(280.46646 + 36000.76983 * T + 0.0003032 * T * T);
  double M = norm360(357.52911 + 35999.05029 * T - 0.0001537 * T * T);
  double e = 0.016708634 - 0.000042037 * T;
  double C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * sind(M)
           + (0.019993 - 0.000101 * T) * sind(2 * M) + 0.000289 * sind(3 * M);
  double trueLon = L0 + C;
  double om = norm360(125.04452 - 1934.136261 * T);
  double Lm = norm360(218.3165 + 481267.8813 * T);
  f.dpsi = (-17.20 * sind(om) - 1.32 * sind(2 * L0) - 0.23 * sind(2 * Lm) + 0.21 * sind(2 * om)) / 3600.0;
  double deps = (9.20 * cosd(om) + 0.57 * cosd(2 * L0) + 0.10 * cosd(2 * Lm) - 0.09 * cosd(2 * om)) / 3600.0;
  f.eps = 23.4392911 - 0.0130042 * T - 1.64e-7 * T * T + deps;
  f.sunLon = norm360(trueLon - 0.00569 + f.dpsi);     // aberration + nutation
  f.sunR = 1.000001018 * (1 - e * e) / (1 + e * cosd(M + C));
  double Tu = (jd - 2451545.0) / 36525.0;
  double gmst = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * Tu * Tu;
  f.gast = norm360(gmst + f.dpsi * cosd(f.eps));
  return f;
}

inline Ecl moonEcl(const Frame& f) {
  double T = f.T, T2 = T * T, T3 = T2 * T, T4 = T3 * T;
  double Lp = norm360(218.3164477 + 481267.88123421 * T - 0.0015786 * T2 + T3 / 538841.0 - T4 / 65194000.0);
  double D  = norm360(297.8501921 + 445267.1114034 * T - 0.0018819 * T2 + T3 / 545868.0 - T4 / 113065000.0);
  double M  = norm360(357.5291092 + 35999.0502909 * T - 0.0001536 * T2 + T3 / 24490000.0);
  double Mp = norm360(134.9633964 + 477198.8675055 * T + 0.0087414 * T2 + T3 / 69699.0 - T4 / 14712000.0);
  double F  = norm360(93.2720950 + 483202.0175233 * T - 0.0036539 * T2 - T3 / 3526000.0 + T4 / 863310000.0);
  double A1 = norm360(119.75 + 131.849 * T);
  double A2 = norm360(53.09 + 479264.290 * T);
  double A3 = norm360(313.45 + 481266.484 * T);
  double E = 1 - 0.002516 * T - 0.0000074 * T2;
  double sl = 0, sr = 0, sb = 0;
  for (const LTerm& t : LT) {
    double arg = (t.d * D + t.m * M + t.mp * Mp + t.f * F) * D2R;
    double k = (t.m == 0) ? 1.0 : ((t.m == 1 || t.m == -1) ? E : E * E);
    sl += k * t.l * sin(arg);
    sr += k * t.r * cos(arg);
  }
  for (const BTerm& t : BT) {
    double arg = (t.d * D + t.m * M + t.mp * Mp + t.f * F) * D2R;
    double k = (t.m == 0) ? 1.0 : ((t.m == 1 || t.m == -1) ? E : E * E);
    sb += k * t.b * sin(arg);
  }
  sl += 3958 * sind(A1) + 1962 * sind(Lp - F) + 318 * sind(A2);
  sb += -2235 * sind(Lp) + 382 * sind(A3) + 175 * sind(A1 - F) + 175 * sind(A1 + F)
      + 127 * sind(Lp - Mp) - 115 * sind(Lp + Mp);
  Ecl r;
  r.lon = norm360(Lp + sl / 1e6 + f.dpsi);
  r.lat = sb / 1e6;
  r.dist = 385000.56 + sr / 1000.0;
  return r;
}

inline Equ eclToEqu(double lon, double lat, double eps) {
  Equ q;
  q.ra = norm360(atan2(sind(lon) * cosd(eps) - tan(lat * D2R) * sind(eps), cosd(lon)) * R2D);
  q.dec = asin(sind(lat) * cosd(eps) + cosd(lat) * sind(eps) * sind(lon)) * R2D;
  return q;
}

// position angle (N through E) of the direction from (ra,dec) towards (ra2,dec2)
inline double posAngle(double ra, double dec, double ra2, double dec2) {
  return atan2(cosd(dec2) * sind(ra2 - ra),
               sind(dec2) * cosd(dec) - cosd(dec2) * sind(dec) * cosd(ra2 - ra)) * R2D;
}

inline double refraction(double altGeom) {        // Saemundsson, degrees
  if (altGeom < -1.5) return 0.0;
  return 1.02 / tan((altGeom + 10.3 / (altGeom + 5.11)) * D2R) / 60.0;
}

}  // namespace detail

// Full Moon state for an observer. lat/lon in degrees (east positive).
inline MoonState moonState(double unixTime, double latDeg, double lonDeg) {
  using namespace detail;
  Frame f = makeFrame(unixTime);
  Ecl me = moonEcl(f);
  Equ mq = eclToEqu(me.lon, me.lat, f.eps);
  Equ sq = eclToEqu(f.sunLon, 0.0, f.eps);

  // --- phase (geocentric) ---
  double cospsi = cosd(me.lat) * cosd(me.lon - f.sunLon);
  double psi = acos(cospsi);
  double Rkm = f.sunR * 149597870.7;
  double i = atan2(Rkm * sin(psi), me.dist - Rkm * cospsi);
  MoonState s;
  s.illum = (1 + cos(i)) / 2;
  s.waxing = norm360(me.lon - f.sunLon) < 180.0;
  double e = acos(1 - 2 * s.illum) * R2D;           // 0..180
  s.elong = s.waxing ? e : 360.0 - e;
  s.distanceKm = me.dist;

  // --- topocentric place (Meeus ch. 40) ---
  double u = atan(0.99664719 * tan(latDeg * D2R));
  double rsin = 0.99664719 * sin(u);
  double rcos = cos(u);
  double sinpi = 6378.14 / me.dist;
  double H = norm180(f.gast + lonDeg - mq.ra);
  double dra = atan2(-rcos * sinpi * sind(H), cosd(mq.dec) - rcos * sinpi * cosd(H)) * R2D;
  double decT = atan2((sind(mq.dec) - rsin * sinpi) * cosd(dra),
                      cosd(mq.dec) - rcos * sinpi * cosd(H)) * R2D;
  double raT = mq.ra + dra;
  double Ht = H - dra;

  double sinh_ = sind(latDeg) * sind(decT) + cosd(latDeg) * cosd(decT) * cosd(Ht);
  s.altGeom = asin(sinh_) * R2D;
  s.alt = s.altGeom + refraction(s.altGeom);
  s.az = norm360(atan2(sind(Ht), cosd(Ht) * sind(latDeg) - tan(decT * D2R) * cosd(latDeg)) * R2D + 180.0);
  s.semiDiam = asin(1737.4 / me.dist) * R2D * (1 + sinh_ * sinpi);

  // --- orientation ---
  double q = atan2(sind(Ht), tan(latDeg * D2R) * cosd(decT) - sind(decT) * cosd(Ht)) * R2D;  // parallactic angle
  double chi = posAngle(raT, decT, sq.ra, sq.dec);                 // bright limb
  double pole = posAngle(raT, decT, 270.0, 90.0 - f.eps);          // ecliptic north pole
  // "north" implied by the bright limb (perpendicular to the Sun direction)
  double nLimb = s.waxing ? chi + 90.0 : chi - 90.0;
  // near new/full the limb direction is ill-defined: blend towards the ecliptic pole direction
  double w = (fabs(sind(s.elong)) - 0.25) / 0.25;
  w = w < 0 ? 0 : (w > 1 ? 1 : w);
  w = w * w * (3 - 2 * w);
  double north = pole + w * norm180(nLimb - pole);
  s.northAngle = norm180(north - q);
  s.limbAngle = norm180(chi - q);
  return s;
}

// Geometric altitude of the Moon's centre at which the upper limb touches the apparent horizon.
inline double riseSetAltitude(const MoonState& s) { return -(34.0 / 60.0) - s.semiDiam; }

// Search forward from `fromUnix` for the next moonrise (rising=true) or moonset.
inline Event nextRiseSet(double fromUnix, double latDeg, double lonDeg, bool rising, double maxHours = 50.0) {
  Event ev; ev.valid = false; ev.unixTime = 0; ev.az = 0;
  const double step = 600.0;
  MoonState s0 = moonState(fromUnix, latDeg, lonDeg);
  double f0 = s0.altGeom - riseSetAltitude(s0);
  for (double t = fromUnix; t < fromUnix + maxHours * 3600.0; t += step) {
    MoonState s1 = moonState(t + step, latDeg, lonDeg);
    double f1 = s1.altGeom - riseSetAltitude(s1);
    bool cross = rising ? (f0 < 0 && f1 >= 0) : (f0 >= 0 && f1 < 0);
    if (cross) {
      double a = t, b = t + step, fa = f0;
      for (int k = 0; k < 14; k++) {
        double m = 0.5 * (a + b);
        MoonState sm = moonState(m, latDeg, lonDeg);
        double fm = sm.altGeom - riseSetAltitude(sm);
        if ((fa < 0) == (fm < 0)) { a = m; fa = fm; } else { b = m; }
      }
      double tm = 0.5 * (a + b);
      ev.valid = true;
      ev.unixTime = (int64_t)(tm + 0.5);
      ev.az = moonState(tm, latDeg, lonDeg).az;
      return ev;
    }
    f0 = f1;
  }
  return ev;
}

// 0 Nova, 1 Crescente, 2 Quarto crescente, 3 Gibosa crescente, 4 Cheia,
// 5 Gibosa minguante, 6 Quarto minguante, 7 Minguante
inline int phaseIndex(const MoonState& s) {
  const double win = 9.0;                              // half-width of the 4 principal phases
  double e = s.elong;
  if (e < win || e > 360 - win) return 0;
  if (e < 90 - win) return 1;
  if (e <= 90 + win) return 2;
  if (e < 180 - win) return 3;
  if (e <= 180 + win) return 4;
  if (e < 270 - win) return 5;
  if (e <= 270 + win) return 6;
  return 7;
}

}  // namespace astro
