"""Half-model tetrahedral CFD mesh of the full aircraft (gmsh 4.15, OpenCASCADE + HXT).

Reads analysis/cfd3d/out/oml.brep (build_geometry.py), cuts it from a box domain, moves it into the SU2 frame
(x = -X aft, y = Z starboard, z = Y up), sizes the mesh with curvature + distance + wake/tip-vortex boxes, tags the
wall by component, and writes out/L{n}/mesh.su2 plus mesh_stats.json (counts, quality histogram, sizes).

Levels share every rule; only the length scale f changes (L1 1.5, L2 1.0, L3 0.72 -> refinement ratio ~1.4 in h,
about 2.7x cells per level), which is what the grid-convergence study in run_cases.py needs.

Usage:  py analysis/cfd3d/build_mesh.py 2      (level 1, 2 or 3)
"""
import json, math, sys, time
from pathlib import Path

import gmsh
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_geometry as bg  # noqa: E402

LEVELS = {1: 1.5, 2: 1.0, 3: 0.72}
# half-model domain in the CAD frame (aircraft spans X -1.04..0.45, Y -0.25..0.20, Z 0..1.2 on the starboard side)
DOMAIN = dict(x0=-16.0, x1=8.0, y0=-8.0, y1=8.0, z0=0.0, z1=10.0)
# component groups (CAD-frame part names from build_geometry.build_parts) -> SU2 wall markers
GROUPS = {"wing": ["Wing", "Servo_3", "Servo_4"], "htail": ["H_Tail"], "fins": ["Fin_0", "Fin_1", "Fin_Shoe", "Servo_0", "Servo_1", "Servo_2"],
          "pod": ["Pod", "Canopy", "Pusher_Motor"], "booms": ["Boom", "Motor_Mount", "Tail_Clamp"],
          "motors": ["Lift_Motor"], "gear": ["Landing_Leg", "Gear_Fairing", "Gear_Clamp"]}
CAD_TO_SU2 = [-1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0]   # x = -X, y = Z, z = Y  (det +1)


def to_su2(dimtags):
    """CAD -> SU2 frame as a rigid rotation (180 deg about (0, 1, 1)): R = 2nn^T - I = CAD_TO_SU2. A rotation keeps
    planes planar; occ.affineTransform would turn every face into a B-spline and the flat wing-tip caps then fail
    to mesh at the trailing edge."""
    gmsh.model.occ.rotate(dimtags, 0, 0, 0, 0, 1, 1, math.pi)


def su2(p):
    X, Y, Z = p
    return (-X, Z, Y)


def su2_box(x0, x1, y0, y1, z0, z1):
    """CAD-frame box -> SU2-frame (xmin, xmax, ymin, ymax, zmin, zmax)"""
    a, b = su2((x0, y0, z0)), su2((x1, y1, z1))
    return (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1]), min(a[2], b[2]), max(a[2], b[2]))


def group_of(part):
    for g, names in GROUPS.items():
        for n in names:
            if part == n or part.startswith(n + "_") or part.startswith(n):
                return g
    raise KeyError(part)


def main(level):
    f = LEVELS[level]
    out = HERE / "out" / f"L{level}"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 1)
    gmsh.option.setNumber("General.NumThreads", 20)
    gmsh.option.setNumber("Geometry.OCCParallel", 1)

    # model "parts": the un-fused rebuilt parts, kept only to classify wall faces by component (isInside tests)
    gmsh.model.add("parts")
    parts = bg.build_parts(half=True)
    for name, dts in parts.items():
        to_su2(dts)
    gmsh.model.occ.synchronize()
    part_vols = {name: [t for d, t in dts] for name, dts in parts.items()}

    gmsh.model.add("fluid")
    body = gmsh.model.occ.importShapes(str(HERE / "out" / "oml_half.brep"))
    d = DOMAIN
    dom = gmsh.model.occ.addBox(d["x0"], d["y0"], d["z0"], d["x1"] - d["x0"], d["y1"] - d["y0"], d["z1"] - d["z0"])
    res, _ = gmsh.model.occ.cut([(3, dom)], [b for b in body if b[0] == 3])
    gmsh.model.occ.synchronize()
    vols = gmsh.model.getEntities(3)
    masses = [(gmsh.model.occ.getMass(*v), v) for v in vols]
    keep = max(masses)[1]
    drop = [v for m, v in masses if v != keep]
    if drop:
        gmsh.model.occ.remove(drop, recursive=True)
    if __import__("os").environ.get("HEAL", "0") == "1":
        healed = gmsh.model.occ.healShapes([keep], tolerance=1e-6, fixDegenerated=True, fixSmallEdges=True, fixSmallFaces=True, sewFaces=True, makeSolids=True)
        gmsh.model.occ.synchronize(); print("healed", healed[:5], gmsh.model.getEntities(3)); keep = gmsh.model.getEntities(3)[0]
    to_su2([keep])
    gmsh.model.occ.synchronize()

    # boundary classification by position (SU2 frame): farfield box faces, symmetry plane y = 0, wall = the rest
    xs = (-d["x1"], -d["x0"]); ys = (d["z0"], d["z1"]); zs = (d["y0"], d["y1"])
    far, sym, wall = [], [], []
    eps = 1e-6
    for _, s in gmsh.model.getBoundary([keep], oriented=False):
        b = gmsh.model.getBoundingBox(2, s)
        if abs(b[1]) < eps and abs(b[4]) < eps:
            sym.append(s)
        elif (abs(b[0] - b[3]) < eps and (abs(b[0] - xs[0]) < eps or abs(b[0] - xs[1]) < eps)) or \
             (abs(b[1] - b[4]) < eps and abs(b[1] - ys[1]) < eps) or \
             (abs(b[2] - b[5]) < eps and (abs(b[2] - zs[0]) < eps or abs(b[2] - zs[1]) < eps)):
            far.append(s)
        else:
            wall.append(s)

    # ---- size fields ------------------------------------------------------------------------------------------
    fld = gmsh.model.mesh.field
    dist = fld.add("Distance"); fld.setNumbers(dist, "SurfacesList", wall); fld.setNumber(dist, "Sampling", int(__import__("os").environ.get("SAMPLING", 40)))
    thr = fld.add("Threshold"); fld.setNumber(thr, "InField", dist)
    fld.setNumber(thr, "SizeMin", 0.008 * f); fld.setNumber(thr, "SizeMax", 0.9 * f)
    fld.setNumber(thr, "DistMin", 0.004); fld.setNumber(thr, "DistMax", 7.0)
    # sharp trailing edges (wing, tail, fins, fairings): curves that are straight and long in the span direction
    te = []
    for _, c in gmsh.model.getEntities(1):
        b = gmsh.model.getBoundingBox(1, c)
        near = abs(b[0]) < 1.2 and abs(b[3]) < 1.2 and b[4] < 1.3 and abs(b[2]) < 0.35 and abs(b[5]) < 0.35
        if near and gmsh.model.getType(1, c) == "Line" and math.dist(b[:3], b[3:]) > 0.05 and (b[3] - b[0]) < 1e-4:
            te.append(c)   # straight, long, constant-x edges: the sharp trailing edges of wing, tail, fins, fairings
    dte = fld.add("Distance"); fld.setNumbers(dte, "CurvesList", te); fld.setNumber(dte, "Sampling", 400)
    tte = fld.add("Threshold"); fld.setNumber(tte, "InField", dte)
    fld.setNumber(tte, "SizeMin", 0.0025 * f); fld.setNumber(tte, "SizeMax", 0.9 * f)
    fld.setNumber(tte, "DistMin", 0.003); fld.setNumber(tte, "DistMax", 0.25)
    # TE end points (tips, symmetry plane, fin root/tip): the section curves meet there at a 10-16 deg wedge and a
    # coarse 1-D spacing lets the upper and lower segments cross; 0.6 mm within ~5 mm keeps them apart
    tep = sorted({int(p) for c in te for _, p in gmsh.model.getBoundary([(1, c)], oriented=False)})
    dtp = fld.add("Distance"); fld.setNumbers(dtp, "PointsList", tep)
    ttp = fld.add("Threshold"); fld.setNumber(ttp, "InField", dtp)
    fld.setNumber(ttp, "SizeMin", 0.0006); fld.setNumber(ttp, "SizeMax", 0.9 * f)
    fld.setNumber(ttp, "DistMin", 0.004); fld.setNumber(ttp, "DistMax", 0.12)
    boxes = [ttp]
    def add_box(cad_box, size, thick):
        x0, x1, y0, y1, z0, z1 = su2_box(*cad_box)
        bx = fld.add("Box")
        for k, v in dict(VIn=size, VOut=1.0, XMin=x0, XMax=x1, YMin=y0, YMax=y1, ZMin=z0, ZMax=z1, Thickness=thick).items():
            fld.setNumber(bx, k, v)
        boxes.append(bx)
    add_box((-1.15, 0.55, -0.30, 0.25, 0.0, 1.30), 0.020 * f, 0.4)     # around the aircraft
    add_box((-4.0, -0.25, -0.30, 0.30, 0.0, 1.35), 0.030 * f, 0.6)     # wake of wing and tail
    add_box((-4.0, -0.20, -0.08, 0.10, 1.12, 1.30), 0.012 * f, 0.15)   # starboard tip-vortex path
    add_box((-0.40, 0.02, -0.08, 0.06, 1.15, 1.25), 0.006 * f, 0.05)   # wing tip
    mn = fld.add("Min"); fld.setNumbers(mn, "FieldsList", [thr, tte] + boxes)
    fld.setAsBackgroundMesh(mn)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 24)
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.0006)
    gmsh.option.setNumber("Mesh.MeshSizeMax", 0.9 * f)
    gmsh.option.setNumber("Mesh.Algorithm", int(__import__("os").environ.get("ALG2D", 5)))
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)

    if __import__("os").environ.get("DUMPC"):   # debugging aid: describe curves named in a failed run's log
        for c in map(int, __import__("os").environ["DUMPC"].split(",")):
            up, _ = gmsh.model.getAdjacencies(1, c)
            print("DUMP curve", c, gmsh.model.getType(1, c), [round(v, 4) for v in gmsh.model.getBoundingBox(1, c)],
                  [(int(q), gmsh.model.getType(2, q), [round(v, 4) for v in gmsh.model.getBoundingBox(2, q)]) for q in up])
        gmsh.model.mesh.generate(1)
        for c in map(int, __import__("os").environ["DUMPC"].split(",")):
            _, xyz, _ = gmsh.model.mesh.getNodes(1, c, includeBoundary=True)
            print("DUMP 1d", c, len(xyz) // 3, [round(v, 4) for v in xyz[:3]], [round(v, 4) for v in xyz[-3:]])
        print("DUMP te", len(te), [[round(v, 3) for v in gmsh.model.getBoundingBox(1, c)] for c in te][:12])
        gmsh.finalize(); return
    gmsh.model.mesh.generate(2)
    t2 = time.time()
    if __import__("os").environ.get("ONLY2D"):
        print("2D OK", len(gmsh.model.mesh.getNodes()[0])); gmsh.finalize(); return

    # ---- classify wall faces by component: offset a face node by +-0.4 mm along the normal, test the parts -----
    gmsh.model.setCurrent("parts")
    def part_at(p):
        for name, tags in part_vols.items():
            for t in tags:
                if gmsh.model.isInside(3, t, list(p)) > 0:
                    return name
        return None
    gmsh.model.setCurrent("fluid")
    probes = []
    for s in wall:
        tags, xyz, uv = gmsh.model.mesh.getNodes(2, s, includeBoundary=False, returnParametricCoord=True)
        if len(tags) == 0:
            tags, xyz, uv = gmsh.model.mesh.getNodes(2, s, includeBoundary=True, returnParametricCoord=False); uv = []
        xyz = np.array(xyz).reshape(-1, 3)
        k = len(xyz) // 2
        n = np.array(gmsh.model.getNormal(s, list(uv[2 * k:2 * k + 2]))) if len(uv) else np.zeros(3)
        probes.append((s, xyz[k], n))
    gmsh.model.setCurrent("parts")
    comp = {}
    for s, p, n in probes:
        name = None
        for sgn in (1, -1, 0.5, -0.5, 2, -2):
            name = part_at(p + sgn * 4e-4 * n)
            if name:
                break
        comp[s] = group_of(name) if name else "unclassified"
    gmsh.model.setCurrent("fluid")

    for g in list(GROUPS) + ["unclassified"]:
        tags = [s for s in wall if comp[s] == g]
        if tags:
            gmsh.model.addPhysicalGroup(2, tags, name=g)
    gmsh.model.addPhysicalGroup(2, sym, name="symmetry")
    gmsh.model.addPhysicalGroup(2, far, name="farfield")
    gmsh.model.addPhysicalGroup(3, [keep[1]], name="fluid")

    gmsh.model.mesh.generate(3)
    t3 = time.time()

    # ---- statistics ---------------------------------------------------------------------------------------------
    etypes, etags, _ = gmsh.model.mesh.getElements(3)
    tets = np.concatenate([t for ty, t in zip(etypes, etags) if ty == 4])
    q = np.array(gmsh.model.mesh.getElementQualities(tets.tolist(), "minSICN"))
    g = np.array(gmsh.model.mesh.getElementQualities(tets.tolist(), "gamma"))
    tri_counts = {}
    for dim, pg in gmsh.model.getPhysicalGroups(2):
        n = 0
        for tag in gmsh.model.getEntitiesForPhysicalGroup(dim, pg):
            ty, el, _ = gmsh.model.mesh.getElements(2, tag)
            n += sum(len(e) for e in el)
        tri_counts[gmsh.model.getPhysicalName(dim, pg)] = n
    nodes = gmsh.model.mesh.getNodes()[0]
    hist_edges = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    stats = {"level": level, "scale_f": f, "generated": time.strftime("%Y-%m-%d %H:%M"), "gmsh": gmsh.__version__,
             "script": "analysis/cfd3d/build_mesh.py", "frame": "SU2: x = -X_cad (aft), y = Z_cad (starboard), z = Y_cad (up), metres",
             "domain_cad_m": DOMAIN, "half_model": True,
             "nodes": int(len(nodes)), "tetrahedra": int(len(tets)), "surface_triangles": tri_counts,
             "quality_minSICN": {"min": float(q.min()), "p01": float(np.percentile(q, 1)), "mean": float(q.mean()),
                                 "hist_edges": hist_edges, "hist": np.histogram(q, hist_edges)[0].tolist()},
             "quality_gamma": {"min": float(g.min()), "p01": float(np.percentile(g, 1)), "mean": float(g.mean())},
             "sizes_m": {"wall_default": 0.008 * f, "trailing_edges": 0.0025 * f, "min": 0.0006, "te_points": 0.0006, "near_box": 0.020 * f,
                         "wake_box": 0.030 * f, "tip_vortex_box": 0.012 * f, "tip": 0.006 * f, "far": 0.9 * f, "curvature_per_2pi": 24},
             "elements": "linear tetrahedra (gmsh HXT), linear triangles on the walls; no prism layer (inviscid Euler)",
             "te_curves": len(te), "wall_faces": len(wall), "faces_by_group": {k: sum(1 for s in wall if comp[s] == k) for k in list(GROUPS) + ["unclassified"]},
             "time_s": {"surface": round(t2 - t0, 1), "volume": round(t3 - t2, 1)}}
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.write(str(out / "mesh.su2"))
    (out / "mesh_stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))
    gmsh.finalize()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
