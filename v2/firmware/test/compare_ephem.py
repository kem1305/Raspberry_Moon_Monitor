"""Validate firmware/src/astro.h against PyEphem. Usage: python3 compare_ephem.py"""
import ephem, math, random, subprocess, os, sys
here = os.path.dirname(os.path.abspath(__file__))
exe = os.path.join(here, "test_astro")
subprocess.check_call(["g++", "-O2", "-std=c++11", "-Wall", "-Wextra", "-o", exe, os.path.join(here, "test_astro.cpp")])
random.seed(7)
sites = [(-25.563, -51.486), (-23.55, -46.63), (38.72, -9.14), (51.5, -0.12), (35.68, 139.69), (-33.87, 151.2), (64.15, -21.94), (0.0, 0.0)]
cases = []
for _ in range(600):
    t = random.uniform(1767225600, 1767225600 + 6 * 365.25 * 86400)   # 2026..2032
    la, lo = random.choice(sites)
    cases.append((t, la, lo))
out = subprocess.run([exe], input="".join("%f %f %f\n" % c for c in cases), capture_output=True, text=True, check=True).stdout
def wrap(d): return (d + 180) % 360 - 180
mx = dict(az=0, alt=0, ill=0, limb=0, rise=0, set=0, razi=0)
nrs = 0
for line, (t, la, lo) in zip(out.strip().split("\n"), cases):
    v = [float(x) for x in line.split(",")]
    az, alt, ill, limb, north, rise, raz, sett, saz = v[3:12]
    o = ephem.Observer(); o.lat = str(la); o.lon = str(lo); o.elevation = 0
    o.date = ephem.Date(t / 86400.0 + 25567.5)
    o.pressure = 0                     # compare airless (geometric) altitudes
    m = ephem.Moon(o); s = ephem.Sun(o)
    eaz, ealt = math.degrees(m.az), math.degrees(m.alt)
    mx['alt'] = max(mx['alt'], abs(alt - ealt))
    mx['az'] = max(mx['az'], abs(wrap(az - eaz)) * math.cos(math.radians(ealt)))
    mx['ill'] = max(mx['ill'], abs(ill * 100 - m.moon_phase * 100))
    # bright limb angle relative to zenith from ephem quantities
    H = o.sidereal_time() - m.ra
    q = math.atan2(math.sin(H), math.tan(o.lat) * math.cos(m.dec) - math.sin(m.dec) * math.cos(H))
    chi = math.atan2(math.cos(s.dec) * math.sin(s.ra - m.ra), math.sin(s.dec) * math.cos(m.dec) - math.cos(s.dec) * math.sin(m.dec) * math.cos(s.ra - m.ra))
    if 0.02 < m.moon_phase < 0.98 and ealt < 80:
        mx['limb'] = max(mx['limb'], abs(wrap(limb - math.degrees(chi - q))))
    o.horizon = '-0:34'                # USNO convention: 34' refraction, upper limb
    for name, mine, myaz, fn in (('rise', rise, raz, o.next_rising), ('set', sett, saz, o.next_setting)):
        try:
            e = fn(ephem.Moon())
        except ephem.CircumpolarError:
            continue
        et = (e - 25567.5) * 86400.0
        if mine < 0:
            if et - t < 49 * 3600: print("MISSED", name, t, la, lo)
            continue
        if abs(mine - et) > 600:
            print("MISMATCH", name, t, la, lo, (mine - et) / 60); continue
        nrs += 1
        mx[name] = max(mx[name], abs(mine - et))
        o2 = ephem.Observer(); o2.lat = str(la); o2.lon = str(lo); o2.elevation = 0; o2.pressure = 0; o2.date = e
        mx['razi'] = max(mx['razi'], abs(wrap(myaz - math.degrees(ephem.Moon(o2).az))))
print("max errors vs PyEphem over %d cases (%d rise/set events):" % (len(cases), nrs))
print("  azimuth (on-sky)   %.3f deg" % mx['az'])
print("  altitude           %.3f deg" % mx['alt'])
print("  illumination       %.3f %%" % mx['ill'])
print("  bright-limb angle  %.3f deg" % mx['limb'])
print("  moonrise / moonset %.0f s / %.0f s" % (mx['rise'], mx['set']))
print("  rise/set azimuth   %.3f deg" % mx['razi'])
ok = mx['az'] < 0.1 and mx['alt'] < 0.1 and mx['ill'] < 0.3 and mx['limb'] < 1.0 and mx['rise'] < 90 and mx['set'] < 90 and mx['razi'] < 0.5
print("PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
