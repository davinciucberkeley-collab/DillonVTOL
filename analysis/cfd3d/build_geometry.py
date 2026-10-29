"""Full-aircraft CFD outer mould line (OML), rebuilt in gmsh/OpenCASCADE from the same single sources as the CAD.

Why a rebuild and not the STEP solids directly: cad/model/VTOL_Concept.STEP is the as-built assembly. Fusing it gives
0.1 mm annular gaps between the 25.4 mm booms and the 25.6 mm clamp bores, 1.2 mm split gaps between every clamp half,
2 % hinge gaps at every control surface, open fastener holes and hollow tube ends. Each of those becomes a fluid
pocket a tetrahedral mesh must resolve, and none of them matters to the external aerodynamics at cruise. So every
external part is rebuilt here from the parameters BuildVtol.cs uses (cad/params.txt scalars and the comp= placements),
with the defeaturing listed in DEFEATURING below, and check_fidelity() compares each rebuilt part with its STEP solid.

Frames. CAD/review frame: X forward from the wing leading edge, Y up, Z starboard, metres. SU2 frame (what the mesh is
written in): x = -X (aft, along the free stream at alpha = 0), y = Z (starboard), z = Y (up). Right-handed, so SU2's
lift (+z), drag (+x) and pitching moment (+y = nose up) need no sign fixes.

Usage:  py analysis/cfd3d/build_geometry.py            -> analysis/cfd3d/out/oml.brep, oml_fidelity.json
"""
import json, math, sys, time
from pathlib import Path

import gmsh
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import geom  # noqa: E402  single source: params.txt reader, NACA sections, pod profile

P = geom.PARAMS
OUT = HERE / "out"
STEP = ROOT / "cad" / "model" / "VTOL_Concept.STEP"

DEFEATURING = [
    ("Wing panels, saddle, ailerons", "One extrusion of the NACA 2415 section over the full 2.4 m span", "Ailerons at 0 deg with the 2 % tape-hinge gaps sealed; spar socket, pockets and saddle tabs removed; trailing edge closed (aero TE coefficient, as the 2-D SU2 meshes), CAD TE is 0.9 mm thick"),
    ("H_Tail + Elevator", "One NACA 0009 extrusion, chord hC, span hSpan", "Elevator at 0 deg, hinge gap sealed; the aft 30 % outboard of the elevator (inside the fin shoes in CAD) filled; crush-sleeve holes removed"),
    ("Fin + Rudder", "Ruled loft of the full NACA 0009 section, root vC to 65 % tip, 35 % c LE sweep", "Rudder at 0 deg, gap sealed; the 2 mm notch between shoe and rudder filled"),
    ("Fin_Shoe", "Thickened section extrusion + 32 x 46 flange", "Extended 2 mm down into the stabiliser so no crevice forms under the flat flange"),
    ("Fuselage_Pod + Canopy + Pusher_Cup", "Revolved pod profile (geom.pod_radius) + ellipsoid blister", "Wing-root slot, bays, hatch slots, insert and radial holes removed; tail-ring bore filled (the cup is flush)"),
    ("Boom_Front + Boom_Rear_Stub", "Solid 25.4 mm cylinders", "Tube bores and open tube ends capped; splice plug internal"),
    ("Motor mounts, boom/gear/tail clamps", "One rounded block per clamp pair (BlockBody: 46 mm wide, r 4 mm)", "1.2 mm split gap, bore clearance, counterbores, insert and nut pockets filled; boom-clamp and tail-clamp tops extended 3-4 mm into the wing/stabiliser so no wedge crevice forms at the bonded joint"),
    ("Lift_Motor x4, Pusher_Motor", "Revolved BuildVtol.Motor() profile", "Bolt holes and the 4 mm shaft stub removed"),
    ("Landing_Leg + Gear_Fairing", "Leg cylinder + dome foot; solid NACA 0033 fairing", "Fairing cavity filled; fairing top extended 1 mm to meet the gear clamp (taped joint)"),
    ("Servos on the tail and under the wing", "Boxes from the STEP bounding boxes", "Horns, pushrods and clevises omitted (2 mm rods)"),
    ("Lift_Prop x4, Pusher_Prop_14in, Prop_Plate, prop adapter/nut", "Omitted", "Lift props: the CAD blade is a notional 8 mm flat planform (BuildVtol LiftProp, 'planform EST') and the parked angle is not controlled (BLHeli_S cannot park); pusher: no actuator-disk model in the incompressible solver, so cruise runs are power-off"),
    ("Pitot tube + clamp, fasteners, inserts, horns, pushrods", "Omitted", "Sub-6 mm features; local effect only"),
]

# ---------------------------------------------------------------------------------------------------------------
def comps(name):
    """comp= placements (translation only for the parts used here; mirrored servos handled by the caller)"""
    out = []
    for r in geom.read_records("comp"):
        if r[0] == name:
            out.append((float(r[1]), float(r[2]), float(r[3])))
    return out


def occ():
    return gmsh.model.occ


def section_wire(pts_xy, to3d, closed_te=True):
    """closed wire through a TE->upper->LE->lower->TE outline (N,2), mapped to 3-D by to3d(x, y) -> (X, Y, Z):
    two interpolating splines (upper TE->LE, lower LE->TE) sharing the LE and TE points, so the TE stays sharp.
    Measured on the 120-point outlines used here (scratch check 2026-10-29): within 0.11 mm (wing) / 0.04 mm (tail)
    of the analytic NACA section, LE slope break 0.94 / 0.25 deg. Clamping a common LE tangent removes the break
    but makes OCC overshoot the TE by 1.4 mm, which is worse and breaks the TE mesh."""
    o = occ()
    pts = np.asarray(pts_xy, float).copy()
    le = int(np.argmin(pts[:, 0]))
    if closed_te:
        pts[-1] = pts[0]
    tags_up = [o.addPoint(*to3d(*p)) for p in pts[:le + 1]]
    tags_lo = [tags_up[-1]] + [o.addPoint(*to3d(*p)) for p in pts[le + 1:-1]] + [tags_up[0]]
    return o.addWire([o.addSpline(tags_up), o.addSpline(tags_lo)])


def naca_outline(code_m, code_p, t, n=60):
    return geom.naca4_outline(code_m, code_p, t, n, geom.TE_AERO)


def extrude_section(outline, chord, xle, yle, z0, z1, xoff=0.0):
    """section in the XY plane (X = xle - xoff - x c, Y = yle + y c) extruded along +Z from z0 to z1"""
    o = occ()
    w = section_wire(outline, lambda x, y: (xle - xoff - x * chord, yle + y * chord, z0))
    s = o.addPlaneSurface([w])
    ex = o.extrude([(2, s)], 0, 0, z1 - z0)
    return [e for e in ex if e[0] == 3]


def round_block(cx, cy, cz, lx, y0, y1, w=0.046, r=0.004):
    """BuildVtol.BlockBody envelope: rounded rectangle (w along Z, y0..y1) extruded lx along X, centred at cx"""
    o = occ()
    h = y1 - y0
    s = o.addRectangle(cz - w / 2, cy + y0, 0, w, h, roundedRadius=r)  # in its own XY, rotated below
    # rectangle lies in plane XY: (u along X -> world Z, v along Y -> world Y); extrude along Z then map Z -> -X
    ex = o.extrude([(2, s)], 0, 0, lx)
    vol = [e for e in ex if e[0] == 3]
    # rotate about Y so local +Z extrusion becomes world X, and local X becomes world Z
    o.rotate(vol, 0, 0, 0, 0, 1, 0, -math.pi / 2)       # (x, y, z) -> (-z ... ) see below
    # after rotating by -90 deg about Y: x' = -z, z' = x. So world Z = local X = cz +- w/2 (good), world X in [-lx, 0]
    o.translate(vol, cx + lx / 2, 0, 0)
    return vol


def revolve_profile(prof, axis_pt, axis_dir, plane_map, angle=2 * math.pi):
    """revolve a closed (axial, radial) polyline 360 deg. plane_map(a, r) -> 3-D point in a plane containing the axis"""
    o = occ()
    pts = [o.addPoint(*plane_map(a, r)) for a, r in prof]
    lines = [o.addLine(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    s = o.addPlaneSurface([o.addCurveLoop(lines)])
    ex = o.revolve([(2, s)], *axis_pt, *axis_dir, angle)
    return [e for e in ex if e[0] == 3]


def box(x0, y0, z0, x1, y1, z1):
    return [(3, occ().addBox(x0, y0, z0, x1 - x0, y1 - y0, z1 - z0))]


# ---------------------------------------------------------------------------------------------------------------
def build_parts(half=False):
    """returns {name: [dimTags]} in the CAD frame (metres).
    half=True builds the starboard half (Z >= 0) for the symmetry-plane CFD model: parts on the centre line are
    extruded from Z = 0 or revolved through 180 deg, so the symmetry plane is an exact planar face. Cutting full-span
    parts at Z = 0 instead makes OpenCASCADE approximate the section curves, which overshoot the sharp trailing
    edges and break the surface mesh."""
    keep = (lambda z: z > 0) if half else (lambda z: True)
    rev = math.pi if half else 2 * math.pi
    o = occ()
    parts = {}
    half_model = half
    c = P["chord"]; half = P["panelLen"] + P["fusR"]
    wing_m, wing_p = geom.WING_M, geom.WING_P
    # wing: CAD sections are geom.naca4 at t/c = tc
    parts["Wing"] = extrude_section(naca_outline(wing_m, wing_p, P["tc"]), c, 0.0, 0.0, 0.0 if half_model else -half, half)

    # horizontal tail
    xle, yle, _ = comps("H_Tail")[0]
    parts["H_Tail"] = extrude_section(naca_outline(0, 0, geom.TAIL_T), P["hC"], xle, yle, 0.0 if half_model else -P["hSpan"] / 2, P["hSpan"] / 2)

    # fins: ruled loft root (y=0) -> tip (y=vH), chord vC (1 - 0.35 f), LE offset 0.35 vC f aft (BuildVtol.FinSketch)
    vC, vH = P["vC"], P["vH"]
    tail_out = naca_outline(0, 0, geom.TAIL_T)
    for i, (fx, fy, fz) in enumerate(comps("Fin")):
        if not keep(fz):
            continue
        wires = []
        for f in (0.0, 1.0):
            cl = vC * (1 - 0.35 * f); xoff = 0.35 * vC * f; yy = fy + f * vH
            wires.append(section_wire(tail_out, lambda x, y, cl=cl, xoff=xoff, yy=yy: (fx - xoff - x * cl, yy, fz + y * cl)))
        parts[f"Fin_{i}"] = o.addThruSections(wires, makeSolid=True, makeRuled=True)
        parts[f"Fin_{i}"] = [e for e in parts[f"Fin_{i}"] if e[0] == 3]

    # fin shoes: thickened section (c + 3.2, LE 1.6 ahead) floor+wall high, plus the 32 x 46 flange; 2 mm into the stab
    c2 = vC + 0.0032; k = (geom.TAIL_T * vC + 0.0032) / (geom.TAIL_T * c2)
    shoe_out = naca_outline(0, 0, geom.TAIL_T * k)
    xc = P["xTC"] - P["xFinLE"]
    for i, (sx, sy, sz) in enumerate(comps("Fin_Shoe")):
        if not keep(sz):
            continue
        y0 = sy - 0.002; y1 = sy + P["shoeFloor"] + P["shoeWall"]
        w = section_wire(shoe_out, lambda x, y: (sx + 0.0016 - x * c2, y0, sz + y * c2))
        s = o.addPlaneSurface([w])
        body = [e for e in o.extrude([(2, s)], 0, y1 - y0, 0) if e[0] == 3]
        fl = o.addRectangle(sx + xc - P["shoeFlangeX"] / 2, sz - 0.023, 0, P["shoeFlangeX"], 0.046, roundedRadius=0.003)
        # rectangle is in the z = 0 XY plane: +90 deg about X maps (x, y, 0) -> (x, 0, y), then lift it to y0
        o.rotate([(2, fl)], 0, 0, 0, 1, 0, 0, math.pi / 2)
        o.translate([(2, fl)], 0, y0, 0)
        flange = [e for e in o.extrude([(2, fl)], 0, P["shoeFloor"] + 0.002, 0) if e[0] == 3]
        parts[f"Fin_Shoe_{i}"] = body + flange

    # pod: revolve geom.pod_radius about the X axis through (noseX, yPod)
    nx, py, _ = comps("Fuselage_Pod")[0]
    L = geom.POD_L
    # nose: cosine-clustered so the elliptic nose (vertical tangent at s = 0) is followed closely
    s_pts = np.concatenate([(1 - np.cos(np.linspace(0, math.pi / 2, 31))) * geom.POD_NOSE_A, np.linspace(geom.POD_NOSE_A, L, 50)[1:]])
    prof = [(float(s), geom.pod_radius(float(s))) for s in s_pts]
    prof[0] = (0.0, 0.0)
    prof = prof + [(L, 0.0)]
    pts = [o.addPoint(nx - s, py + r, 0) for s, r in prof]
    sp = o.addSpline(pts[0:len(pts) - 1])  # nose -> tail rim (r > 0 except the nose point)
    l1 = o.addLine(pts[-2], pts[-1]); l2 = o.addLine(pts[-1], pts[0])
    surf = o.addPlaneSurface([o.addCurveLoop([sp, l1, l2])])
    parts["Pod"] = [e for e in o.revolve([(2, surf)], nx, py, 0, 1, 0, 0, rev) if e[0] == 3]

    # canopy blister: half-ellipsoid L 0.26, r 0.055 on y = canopyY (the lower half sits inside the pod)
    cx, cy, _ = comps("Canopy")[0]
    th = np.linspace(0, math.pi, 41)
    cprof = [(0.13 * (1 - math.cos(t)), 0.055 * math.sin(t)) for t in th]   # ellipse, nose (x = cx) to tail
    cpts = [o.addPoint(cx - a, cy + r, 0) for a, r in cprof]
    csp = o.addSpline(cpts); cax = o.addLine(cpts[-1], cpts[0])
    csurf = o.addPlaneSurface([o.addCurveLoop([csp, cax])])
    parts["Canopy"] = [e for e in o.revolve([(2, csurf)], cx, cy, 0, 1, 0, 0, rev) if e[0] == 3]

    # motors: BuildVtol.Motor profile without the shaft stub
    R, H = P["motorD"] / 2, P["motorH"]
    mprof = [(0, 0), (0, R * 0.92), (0.004, R * 0.92), (0.004, R * 0.70), (0.007, R * 0.70), (0.007, R), (H - 0.004, R), (H, R - 0.004), (H, 0)]
    for i, (mx, my, mz) in enumerate(comps("Lift_Motor")):
        if not keep(mz):
            continue
        parts[f"Lift_Motor_{i}"] = revolve_profile(mprof, (mx, my, mz), (0, 1, 0), lambda a, r, mx=mx, my=my, mz=mz: (mx + r, my + a, mz))
    px, pyy, pz = comps("Pusher_Motor")[0]
    parts["Pusher_Motor"] = revolve_profile(mprof, (px, pyy, pz), (1, 0, 0), lambda a, r: (px - a, pyy + r, pz), rev)

    # booms: solid 25.4 cylinders
    for name in ("Boom_Front", "Boom_Rear_Stub"):
        for i, (bx, by, bz) in enumerate(comps(name)):
            if not keep(bz):
                continue
            ln = 0.99098 if name == "Boom_Front" else 0.48590
            ln = P.get("boomFrontLen", ln) if name == "Boom_Front" else P.get("boomRearLen", ln)
            parts[f"{name}_{i}"] = [(3, o.addCylinder(bx, by, bz, ln, 0, 0, P["boomOD"] / 2))]

    # clamp-pair envelopes (BlockBody), tops extended into the wing / stab where they are bonded
    pairs = [("Motor_Mount_Upper", 0.070, -0.015, 0.021, 0.0),
             ("Boom_Clamp_F_Upper", 0.034, -0.0167, P["clampTopF"], 0.004),
             ("Boom_Clamp_R_Upper", 0.034, -0.0167, P["clampTopR"], 0.004),
             ("Gear_Clamp_Upper", 0.034, P["gearClampBot"], 0.0167, 0.0),
             ("Tail_Clamp_Upper", 0.050, -0.015, 0.0157, 0.003)]
    for name, lx, y0, y1, ext in pairs:
        for i, (bx, by, bz) in enumerate(comps(name)):
            if not keep(bz):
                continue
            parts[f"{name.replace('_Upper', '')}_{i}"] = round_block(bx, by, bz, lx, y0, y1 + ext)

    # legs (tube + dome foot) and solid fairings (NACA 0033 section, LE 0.30 c ahead of the leg axis)
    lr = P["legOD"] / 2
    for i, (lx_, ly, lz) in enumerate(comps("Landing_Leg")):
        if not keep(lz):
            continue
        cyl = (3, o.addCylinder(lx_, ly, lz, 0, P["legLen"], 0, lr))
        foot = revolve_profile([(0, 0), (0, 0.017), (0.004, 0.020), (0.0099, 0.020), (0.018, lr * 1.15), (0.018, 0)],
                               (lx_, ly, lz), (0, 1, 0), lambda a, r, lx_=lx_, ly=ly, lz=lz: (lx_ + r, ly + a, lz))
        parts[f"Landing_Leg_{i}"] = [cyl] + foot
    fc, fL = P["fairChord"], P["fairLen"]
    ft = (P["fairBore"] + 2 * P["fairWall"]) / fc
    fout = naca_outline(0, 0, ft)
    for i, (gx, gy, gz) in enumerate(comps("Gear_Fairing")):
        if not keep(gz):
            continue
        w = section_wire(fout, lambda x, y, gx=gx, gy=gy, gz=gz: (gx + 0.30 * fc - x * fc, gy, gz + y * fc))
        s = o.addPlaneSurface([w])
        parts[f"Gear_Fairing_{i}"] = [e for e in o.extrude([(2, s)], 0, fL + 0.0012, 0) if e[0] == 3]

    # servo boxes from the STEP bounding boxes (tail servos on the stab top, aileron servos under the wing)
    servo_boxes = [(-0.86878, -0.00700, 0.36060, -0.81518, 0.02874, 0.40150),
                   (-0.86878, -0.00700, -0.40150, -0.81518, 0.02874, -0.36060),
                   (-0.86878, -0.00700, -0.02100, -0.81518, 0.02874, 0.01990),
                   (-0.18310, -0.02026, 0.63650, -0.12950, -0.00500, 0.67740),
                   (-0.18310, -0.02026, -0.67740, -0.12950, -0.00500, -0.63650)]
    for i, b in enumerate(servo_boxes):
        if half:
            if b[5] <= 0:
                continue
            b = (b[0], b[1], max(b[2], 0.0), b[3], b[4], b[5])
        parts[f"Servo_{i}"] = box(*b)
    o.synchronize()
    return parts


# ---------------------------------------------------------------------------------------------------------------
STEP_MAP = {  # rebuilt part prefix -> STEP solid names it stands for
    "Wing": ["Wing_Panel_L", "Wing_Panel_R", "Aileron_L", "Aileron_R", ""],
    "H_Tail": ["H_Tail", "Elevator"], "Fin": ["Fin", "Rudder"], "Fin_Shoe": ["Fin_Shoe"],
    "Pod": ["Fuselage_Pod"], "Canopy": ["Canopy"], "Lift_Motor": ["Lift_Motor"], "Pusher_Motor": ["Pusher_Motor"],
    "Boom_Front": ["Boom_Front"], "Boom_Rear_Stub": ["Boom_Rear_Stub"], "Motor_Mount": ["Motor_Mount_Upper", "Motor_Mount_Cap"],
    "Boom_Clamp_F": ["Boom_Clamp_F_Upper", "Boom_Clamp_F_Lower"], "Boom_Clamp_R": ["Boom_Clamp_R_Upper", "Boom_Clamp_R_Lower"],
    "Gear_Clamp": ["Gear_Clamp_Upper", "Gear_Clamp_Lower"], "Tail_Clamp": ["Tail_Clamp_Upper", "Tail_Clamp_Cap"],
    "Landing_Leg": ["Landing_Leg"], "Gear_Fairing": ["Gear_Fairing"],
}


def bbox_of(dimtags):
    b = np.array([gmsh.model.occ.getBoundingBox(d, t) for d, t in dimtags])
    return np.concatenate([b[:, :3].min(0), b[:, 3:].max(0)])


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("oml")
    parts = build_parts()
    # fidelity: compare each rebuilt group's bounding box with the matching STEP solids (imported in metres)
    gmsh.option.setString("Geometry.OCCTargetUnit", "M")
    gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
    step = gmsh.model.occ.importShapes(str(STEP))
    gmsh.model.occ.synchronize()
    by_name = {}
    for d, t in gmsh.model.getEntities(3):
        if (d, t) not in step:
            continue
        n = gmsh.model.getEntityName(d, t).split("/")[-1]
        by_name.setdefault(n, []).append((d, t))
    fidelity = []
    for prefix, names in STEP_MAP.items():
        mine = [dt for k, v in parts.items() if k == prefix or k.startswith(prefix + "_") for dt in v]
        if prefix == "Fin":
            mine = [dt for k, v in parts.items() if k.startswith("Fin_") and not k.startswith("Fin_Shoe") for dt in v]
        theirs = [dt for n in names for dt in by_name.get(n, [])]
        if prefix == "Wing":   # unnamed STEP solid 30 is the saddle (root section across the pod)
            theirs += [dt for dt in by_name.get("", []) if abs(gmsh.model.occ.getBoundingBox(*dt)[2] + 0.08) < 1e-3]
        if not mine or not theirs:
            continue
        # compare on the starboard side only for paired parts so the two boxes describe the same instances
        bm, bt = bbox_of(mine), bbox_of(theirs)
        dev = np.abs(bm - bt)
        fidelity.append({"part": prefix, "step_solids": names, "n_step": len(theirs), "n_rebuilt": len(mine),
                         "bbox_rebuilt_mm": [round(1000 * v, 2) for v in bm], "bbox_step_mm": [round(1000 * v, 2) for v in bt],
                         "max_bbox_dev_mm": round(1000 * float(dev.max()), 2)})
    gmsh.model.occ.remove(step, recursive=True)
    gmsh.model.occ.synchronize()

    # fuse everything into one body
    allv = [dt for v in parts.values() for dt in v]
    fused, _ = gmsh.model.occ.fuse(allv[:1], allv[1:])
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    vols = gmsh.model.getEntities(3)
    gmsh.write(str(OUT / "oml.brep"))
    # starboard half for the symmetry-plane CFD model
    gmsh.model.add("half")
    hp = build_parts(half=True)
    hv = [dt for v in hp.values() for dt in v]
    gmsh.model.occ.fuse(hv[:1], hv[1:]); gmsh.model.occ.removeAllDuplicates(); gmsh.model.occ.synchronize()
    half_vols = len(gmsh.model.getEntities(3))
    gmsh.write(str(OUT / "oml_half.brep"))
    gmsh.model.setCurrent("oml")
    info = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/cfd3d/build_geometry.py",
            "gmsh": gmsh.__version__, "source_step": "cad/model/VTOL_Concept.STEP", "params": "cad/params.txt",
            "volumes_after_fuse": len(vols), "half_volumes_after_fuse": half_vols, "surfaces": len(gmsh.model.getEntities(2)),
            "bbox_m": [round(v, 5) for v in bbox_of(vols)], "defeaturing": [dict(zip(("cad_parts", "cfd_representation", "differences"), r)) for r in DEFEATURING],
            "fidelity": fidelity, "wall_s": round(time.time() - t0, 1)}
    (OUT / "oml_fidelity.json").write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k not in ("defeaturing",)}, indent=1))
    gmsh.finalize()


if __name__ == "__main__":
    main()
