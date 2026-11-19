#!/usr/bin/env python3
"""Moon Monitor v2 — parametric 3D-printable enclosure (CadQuery).

    pip install cadquery
    python3 build_case.py            -> stl/*.stl (print orientation), moonmonitor-case.step (assembly)

Body frame used below: x = right (seen from the front), y = up, z = out of the display.
z = 0 is the front face; everything else is at negative z.  All dimensions in millimetres.
"""
import math, os, sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------------------------------------
# PARAMETERS — measure your display module with callipers and adjust the first block if needed
# ------------------------------------------------------------------------------------------------
MODULE_D = 36.0          # diameter of the round PCB of the GC9A01 module
MODULE_T = 3.2           # glass front to PCB back (LCD + tape + PCB), without the pin header
MODULE_TAB_W = 21.0      # width of the tab that carries the pin header
MODULE_TAB_R = 26.0      # distance display centre -> outer end of that tab
WINDOW_D = 33.0          # visible opening (the active area of the LCD is 32.4 mm)

R_OUT = 31.0             # outer sphere radius (body is a slice of a sphere, 62 mm across)
DEPTH = 20.0             # front face to back face
WALL = 2.0
FRONT_T = 1.2            # front wall (bezel) thickness
BACK_T = 1.6
FLAT_Y = -27.0           # bottom flat (distance from the centre)
PCB_Z = -7.5             # display-side face of the main PCB (= split plane between the two shells)
PCB_T = 1.6
PCB_R = 28.0
HOLES = [(9.5, 22.37), (-17.2, -17.2)]       # case screws (front-view x, y) = PCB holes H1, H2
POSTS = [(-9.5, 22.4), (8.0, -21.0)]         # extra PCB rests in the front shell
INSERT_D = 4.0           # hole for M3 heat-set inserts (OD 4.2-4.6 mm, 4 mm long); use 2.6 to self-tap
SCREW_CLEAR = 3.4
HEAD_D = 6.2
USB_POS = (0.0, -13.5)   # centre of the vertical USB-C connector
USB_SIZE = (9.7, 4.0)    # opening (connector shell is 8.94 x 3.2)
BTN_Z = PCB_Z - PCB_T - 3.6                  # axis of the tactile switch plunger
BTN_TIP_Y = 27.25        # top of the plunger
BTN_D = 6.0
TILT = 12.0              # stand: backwards tilt of the display, degrees
FIT = 0.2                # general clearance between printed parts

CZ = -DEPTH / 2          # sphere centre
R_IN = R_OUT - WALL


def slab(z0, z1, size=200):
    return cq.Workplane("XY").workplane(offset=z0).rect(size, size).extrude(z1 - z0)


def cyl_z(x, y, d, z0, z1):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(z1 - z0)


def cyl_y(x, z, d, y0, y1):
    return cq.Workplane("XZ").workplane(offset=-y0).center(x, z).circle(d / 2).extrude(-(y1 - y0))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def sector(r0, r1, a0, a1, z0, z1):
    """ring sector between radii r0..r1 and angles a0..a1 (degrees, CCW from +x)"""
    ring = cq.Workplane("XY").workplane(offset=z0).circle(r1).circle(r0).extrude(z1 - z0)
    pts = [(0, 0)] + [(2 * r1 * math.cos(math.radians(a)), 2 * r1 * math.sin(math.radians(a)))
                      for a in (a0, (a0 + a1) / 2, a1)]
    wedge = cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(z1 - z0)
    return ring.intersect(wedge)


# ------------------------------------------------------------------------------------------------
# body
# ------------------------------------------------------------------------------------------------
sphere_out = cq.Workplane("XY").sphere(R_OUT).translate((0, 0, CZ))
outer = sphere_out.intersect(slab(-DEPTH, 0)).intersect(box(-100, 100, FLAT_Y, 100, -100, 100))
outer = outer.faces(">Z").edges().chamfer(0.8).faces("<Z").edges().chamfer(0.8)
sphere_in = cq.Workplane("XY").sphere(R_IN).translate((0, 0, CZ))
cavity = sphere_in.intersect(slab(-DEPTH + BACK_T, -FRONT_T)).intersect(box(-100, 100, FLAT_Y + WALL, 100, -100, 100))
shell = outer.cut(cavity)

# ---- front shell -------------------------------------------------------------------------------
front = shell.intersect(slab(PCB_Z, 1))
window = (cq.Workplane("XY").workplane(offset=-FRONT_T - 0.01).circle(WINDOW_D / 2)
          .workplane(offset=FRONT_T + 0.02).circle(WINDOW_D / 2 + 0.7).loft())
front = front.cut(window)
front = front.cut(cq.Workplane("XY").workplane(offset=-0.4).circle(22.5).circle(21.7).extrude(0.5))   # decorative ring
zm = -FRONT_T - MODULE_T                      # back of the display module
for a in (0, 90, 270):                        # locating arcs around the module (the header tab is at 180 deg)
    front = front.union(sector(MODULE_D / 2 + FIT, MODULE_D / 2 + FIT + 1.4, a - 22, a + 22, zm + 0.4, -FRONT_T + 0.01))
for (x, y) in HOLES:
    front = front.union(cyl_z(x, y, 7.5, PCB_Z, -FRONT_T + 0.01))
    front = front.cut(cyl_z(x, y, INSERT_D, PCB_Z - 0.01, PCB_Z + 5.2)).cut(cyl_z(x, y, 3.0, PCB_Z - 0.01, PCB_Z + 5.9))
for (x, y) in POSTS:
    front = front.union(cyl_z(x, y, 4.5, PCB_Z, -FRONT_T + 0.01))

# ---- rear shell --------------------------------------------------------------------------------
rear = shell.intersect(slab(-DEPTH - 1, PCB_Z))
pcb_back = PCB_Z - PCB_T
seat = pcb_back - 3.0                         # screw-head seat: 3 mm of plastic between head and PCB
for (x, y) in HOLES:
    rear = rear.union(cyl_z(x, y, 8.6, -DEPTH + BACK_T - 0.01, pcb_back).intersect(outer))
for (x, y) in HOLES:
    rear = rear.cut(cyl_z(x, y, SCREW_CLEAR, -DEPTH - 1, pcb_back + 1)).cut(cyl_z(x, y, HEAD_D, -DEPTH - 1, seat))
# USB-C opening
usb = (cq.Workplane("XY").workplane(offset=-DEPTH - 1).center(*USB_POS).rect(*USB_SIZE).extrude(BACK_T + 2)
       .edges("|Z").fillet(1.6))
rear = rear.cut(usb)
# push-button guide
rear = rear.cut(cyl_y(0, BTN_Z, BTN_D + 0.5, 24.0, 40.0))
# alignment tabs reaching into the front shell (placed where the PCB is cut away for the antenna)
tabs = None
for a in (-45, 0, 45):
    t = sector(R_IN - 1.9, R_IN, a - 9, a + 9, PCB_Z - 3.0, PCB_Z + 2.4)
    tabs = t if tabs is None else tabs.union(t)
tab_fit = cq.Workplane("XY").sphere(R_IN - FIT).translate((0, 0, CZ))
rear = rear.union(tabs.intersect(tab_fit.union(slab(-DEPTH, PCB_Z).intersect(sphere_in))))
# threaded boss for the stand screw (bottom)
BOSS_Z = -14.0
rear = rear.union(cyl_y(0, BOSS_Z, 8.0, FLAT_Y + 0.5, FLAT_Y + 6.5).intersect(outer))
rear = rear.cut(cyl_y(0, BOSS_Z, INSERT_D, FLAT_Y - 1, FLAT_Y + 5.5))

# ---- button cap --------------------------------------------------------------------------------
btn_top = math.sqrt(R_OUT ** 2 - (BTN_Z - CZ) ** 2) + 1.3
button = cyl_y(0, BTN_Z, BTN_D, BTN_TIP_Y + 0.1, btn_top)
button = button.faces(">Y").edges().fillet(1.0)
button = button.union(box(-5.5, 5.5, BTN_TIP_Y + 0.1, BTN_TIP_Y + 1.1, BTN_Z - 2.8, BTN_Z + 2.8))

# ---- stand (wedge-shaped pedestal) --------------------------------------------------------------
# Built in the "ground frame": X right, Y towards the viewer, Z up.  The body is tilted back by TILT.
def body_to_ground(obj):
    # (x, y, z)_body -> (x, z, y)_ground would be a mirror; use the proper rotation (x, y, z) -> (-x, -z, y)
    # (the body is symmetric enough: the stand only needs its bottom flat), then tilt back about X.
    o = obj.rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 180)
    return o.rotate((0, 0, 0), (1, 0, 0), TILT)


MIN_T = 5.0                                    # stand thickness under the rear edge of the body
POCKET = 1.0                                   # how deep the body sits in the stand
g_outer = body_to_ground(outer)
zmin = g_outer.val().BoundingBox().zmin
lift = MIN_T - POCKET - zmin
g_outer = g_outer.translate((0, 0, lift))
bbg = g_outer.val().BoundingBox()
yc = (bbg.ymin + bbg.ymax) / 2
stand = (cq.Workplane("XY").center(0, yc).ellipse(29, 21).extrude(30))
# top surface: parallel to the body's flat, POCKET above it
n = (0, -math.sin(math.radians(TILT)), math.cos(math.radians(TILT)))      # flat normal in the ground frame
flat_pt = body_to_ground(cq.Workplane("XY").sphere(0.01).translate((0, FLAT_Y, CZ))).translate((0, 0, lift)).val().Center()
top_pt = (flat_pt.x + n[0] * POCKET, flat_pt.y + n[1] * POCKET, flat_pt.z + n[2] * POCKET)
keep = (cq.Workplane(cq.Plane(origin=top_pt, xDir=(1, 0, 0), normal=n)).rect(300, 300).extrude(-100))
stand = stand.intersect(keep)
stand = stand.edges("<Z").chamfer(0.6)
for dx, dy in ((0, 0), (FIT, 0), (-FIT, 0), (0, FIT), (0, -FIT)):
    stand = stand.cut(g_outer.translate((dx, dy, 0)))
# screw through the stand into the body's bottom boss
boss_pt = body_to_ground(cq.Workplane("XY").sphere(0.01).translate((0, FLAT_Y, BOSS_Z))).translate((0, 0, lift)).val().Center()
axis = cq.Plane(origin=(boss_pt.x, boss_pt.y, boss_pt.z), xDir=(1, 0, 0), normal=n)
stand = stand.cut(cq.Workplane(axis).circle(SCREW_CLEAR / 2).extrude(-40))
stand = stand.cut(cq.Workplane(axis).workplane(offset=-3.0).circle(HEAD_D / 2).extrude(-40))

# ------------------------------------------------------------------------------------------------
# checks + export
# ------------------------------------------------------------------------------------------------
def vol(o):
    return o.val().Volume()


parts = {"front_shell": front, "rear_shell": rear, "button": button, "stand": stand}
print("volumes (cm3):", {k: round(vol(v) / 1000, 2) for k, v in parts.items()})

pcb_step = os.path.join(HERE, "..", "hardware", "fab", "moonmonitor-pcb.step")
pcb = None
if os.path.exists(pcb_step) and "--no-pcb" not in sys.argv:
    pcb = cq.importers.importStep(pcb_step)
    # KiCad STEP: X = 100 + u, Y = -100 + v, Z = 0 (display side) .. 1.6 (component side), parts above.
    pcb = pcb.translate((-100, 100, 0)).rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, PCB_Z))
    keepouts = []
    for s in pcb.solids().vals():
        b = s.BoundingBox()
        if b.xmin < -20 and b.zmax > PCB_Z - 0.1 and b.ylen > 15 and b.xlen < 4:
            continue                               # KiCad's pin-header model (the real pins belong to the display)
        keepouts.append(s)
    # vertical USB-C receptacle (no 3D model in the KiCad library): 8.94 x 3.2 x 10.5 mm
    usb_body = box(USB_POS[0] - 4.47, USB_POS[0] + 4.47, USB_POS[1] - 1.6, USB_POS[1] + 1.6, pcb_back - 10.5, pcb_back)
    module = (cyl_z(0, 0, MODULE_D, zm, -FRONT_T)
              .union(box(-MODULE_TAB_R, 0, -MODULE_TAB_W / 2, MODULE_TAB_W / 2, zm, zm + 1.6))
              .union(box(-25.0, -22.0, -8.9, 8.9, PCB_Z - PCB_T - 3.0, zm)))          # header pins
    bad = 0.0
    for name in ("front_shell", "rear_shell", "button"):
        solid = parts[name].val()
        inter = sum(solid.intersect(s).Volume() for s in keepouts)
        inter_usb = vol(parts[name].intersect(usb_body))
        inter_mod = vol(parts[name].intersect(module))
        print("interference %-12s pcb+parts %.2f mm3, usb %.2f mm3, display %.2f mm3" % (name, inter, inter_usb, inter_mod))
        bad += inter + inter_usb + inter_mod
    print("usb mouth recess: %.2f mm" % ((pcb_back - 10.5) - (-DEPTH)))
    print("CLEARANCE CHECK:", "PASS" if bad < 0.5 else "FAIL")

os.makedirs(os.path.join(HERE, "stl"), exist_ok=True)
# print orientation: front shell face down, rear shell back down, button flange down, stand as it stands
prints = {
    "front_shell": front.rotate((0, 0, 0), (1, 0, 0), 180),
    "rear_shell": rear.translate((0, 0, DEPTH)),
    "button": button.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, 0)),
    "stand": stand,
}
for name, obj in prints.items():
    bb = obj.val().BoundingBox()
    obj = obj.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    cq.exporters.export(obj, os.path.join(HERE, "stl", name + ".stl"), tolerance=0.02, angularTolerance=0.1)
    bb = obj.val().BoundingBox()
    print("%-12s %.1f x %.1f x %.1f mm" % (name, bb.xlen, bb.ylen, bb.zlen))

# assembly (ground frame) for STEP / renders
asm = cq.Assembly(name="moonmonitor")
dark, light = cq.Color(0.13, 0.13, 0.15), cq.Color(0.75, 0.75, 0.78)
for name, col in (("front_shell", dark), ("rear_shell", dark), ("button", light)):
    asm.add(body_to_ground(parts[name]).translate((0, 0, lift)), name=name, color=col)
asm.add(stand, name="stand", color=dark)
asm.save(os.path.join(HERE, "moonmonitor-case.step"))
if "--render-stl" in sys.argv:                  # extra meshes used by tools/render (not needed for printing)
    out = os.path.join(HERE, "render"); os.makedirs(out, exist_ok=True)
    for name in ("front_shell", "rear_shell", "button"):
        cq.exporters.export(body_to_ground(parts[name]).translate((0, 0, lift)), os.path.join(out, name + ".stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(stand, os.path.join(out, "stand.stl"), tolerance=0.02, angularTolerance=0.1)
    screen = body_to_ground(cyl_z(0, 0, WINDOW_D + 1.0, -FRONT_T - 0.2, -FRONT_T)).translate((0, 0, lift))
    cq.exporters.export(screen, os.path.join(out, "screen.stl"), tolerance=0.02, angularTolerance=0.1)
    if pcb is not None:
        comp = cq.Compound.makeCompound(keepouts + [usb_body.val()])
        cq.exporters.export(cq.Workplane(obj=comp), os.path.join(out, "pcb.stl"), tolerance=0.05, angularTolerance=0.2)
        for name in ("front_shell", "rear_shell", "button"):
            cq.exporters.export(parts[name], os.path.join(out, "body_" + name + ".stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(module, os.path.join(out, "body_module.stl"), tolerance=0.05, angularTolerance=0.2)
