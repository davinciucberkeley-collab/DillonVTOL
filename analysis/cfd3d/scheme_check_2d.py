"""Solver-and-resolution check for the full-aircraft CFD: the same SU2 INC_EULER numerics (run_cases.CFG) on the 2-D
wing section (NACA 2415, closed TE, the 3-D run's section) at the 3-D meshes' wall spacing and finer, against
XFOIL 6.99 in inviscid mode (panel method, an independent potential-flow answer for the same section).

Question it answers: is the 3-D wing's low lift slope a property of the scheme at this resolution (numerical
dissipation acting like viscous decambering), or of the 3-D set-up?

Usage:  py analysis/cfd3d/scheme_check_2d.py      -> out/scheme_check_2d.json
"""
import json, math, os, re, subprocess, sys, time
from pathlib import Path

import gmsh
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import geom  # noqa: E402
import run_cases as rc  # noqa: E402

OUT = HERE / "out" / "scheme2d"
XFOIL = Path(os.environ.get("XFOIL", r"C:\Users\dillo\tools\xfoil\xfoil.exe"))
C = rc.C_REF
ALPHAS = (0.0, 4.0)
# wall size (m) and TE size: the 3-D L1/L2/L3 wall sizes (8 mm x f, TE 2.5 mm x f) and two finer levels
LEVELS = {"3D-L1": (0.012, 0.00375), "3D-L2": (0.008, 0.0025), "3D-L3": (0.00576, 0.0018), "fine": (0.002, 0.0006), "finest": (0.001, 0.0003)}


def mesh(name, h, hte):
    gmsh.model.add(name); o = gmsh.model.occ
    pts = geom.naca4_outline(geom.WING_M, geom.WING_P, geom.PARAMS["tc"], 120, geom.TE_AERO) * C
    le = int(np.argmin(pts[:, 0])); pts[-1] = pts[0]
    up = [o.addPoint(x, y, 0) for x, y in pts[:le + 1]]
    lo = [up[-1]] + [o.addPoint(x, y, 0) for x, y in pts[le + 1:-1]] + [up[0]]
    foil = o.addCurveLoop([o.addSpline(up), o.addSpline(lo)])
    far = o.addCurveLoop([o.addCircle(0.5 * C, 0, 0, 50 * C)])
    s = o.addPlaneSurface([far, foil]); o.synchronize()
    curves = gmsh.model.getBoundary([(2, s)], oriented=False)
    wall = [c for _, c in curves if gmsh.model.getType(1, c) != "Circle"]; ff = [c for _, c in curves if gmsh.model.getType(1, c) == "Circle"]
    gmsh.model.addPhysicalGroup(1, wall, name="wall"); gmsh.model.addPhysicalGroup(1, ff, name="farfield"); gmsh.model.addPhysicalGroup(2, [s], name="fluid")
    f = gmsh.model.mesh.field
    d = f.add("Distance"); f.setNumbers(d, "CurvesList", wall); f.setNumber(d, "Sampling", 400)
    t = f.add("Threshold"); f.setNumber(t, "InField", d); f.setNumber(t, "SizeMin", h); f.setNumber(t, "SizeMax", 2.0); f.setNumber(t, "DistMin", 0.004); f.setNumber(t, "DistMax", 8.0)
    dp = f.add("Distance"); f.setNumbers(dp, "PointsList", [up[0]])
    tp = f.add("Threshold"); f.setNumber(tp, "InField", dp); f.setNumber(tp, "SizeMin", hte); f.setNumber(tp, "SizeMax", 2.0); f.setNumber(tp, "DistMin", 0.003); f.setNumber(tp, "DistMax", 0.25)
    m = f.add("Min"); f.setNumbers(m, "FieldsList", [t, tp]); f.setAsBackgroundMesh(m)
    for k, v in (("Mesh.MeshSizeExtendFromBoundary", 0), ("Mesh.MeshSizeFromPoints", 0), ("Mesh.MeshSizeFromCurvature", 24), ("Mesh.MeshSizeMin", hte), ("Mesh.Algorithm", 6)):
        gmsh.option.setNumber(k, v)
    gmsh.model.mesh.generate(2)
    d_ = OUT / name; d_.mkdir(parents=True, exist_ok=True)
    gmsh.option.setNumber("Mesh.SaveAll", 0); gmsh.write(str(d_ / "mesh.su2"))
    ntri = sum(len(e) for e in gmsh.model.mesh.getElements(2)[1])
    nwall = sum(len(gmsh.model.mesh.getElements(1, c)[1][0]) for c in wall)
    return d_, ntri, nwall


def su2(d, a):
    cfg = rc.CFG
    for k, v in {"{restart}": "RESTART_SOL= NO", "{cfl}": "5", "{cflmax}": "30", "{limiter}": "VENKATAKRISHNAN", "{cauchy}": "1E-6", "{iters}": "8000",
                 "{mesh}": "mesh.su2", "{markers}": "wall", "{xcg}": f"{0.25 * C:.6f}", "{cref}": f"{C:.6f}", "{sref_half}": f"{C:.6f}", "{rho}": str(rc.RHO),
                 "{alpha}": str(a), "{vx:.10f}": f"{rc.V * math.cos(math.radians(a)):.10f}", "{vz:.10f}": f"{rc.V * math.sin(math.radians(a)):.10f}"}.items():
        cfg = cfg.replace(k, v)
    cfg = cfg.replace("{xcg:.6f}", f"{0.25 * C:.6f}").replace("{cref:.6f}", f"{C:.6f}").replace("{sref_half:.6f}", f"{C:.6f}")
    # 2-D: the section lies in x-y with lift along +y; SU2 projects with AoA in the x-y plane for 2-D meshes
    cfg = cfg.replace(f"INC_VELOCITY_INIT= ( {rc.V * math.cos(math.radians(a)):.10f}, 0.0, {rc.V * math.sin(math.radians(a)):.10f} )",
                      f"INC_VELOCITY_INIT= ( {rc.V * math.cos(math.radians(a)):.10f}, {rc.V * math.sin(math.radians(a)):.10f}, 0.0 )")
    cfg = cfg.replace("MARKER_SYM= ( symmetry )\n", "").replace(", MOMENT_Y )", ", MOMENT_Z )")   # 2-D: pitching moment is about z (output lists only)
    cfg = re.sub(r"OUTPUT_FILES= .*", "OUTPUT_FILES= ( RESTART_ASCII )", cfg)
    # small 2-D problems settle quickly: start the Cauchy test late and tighten it so no case stops on a transient
    cfg = cfg.replace("CONV_STARTITER= 300", "CONV_STARTITER= 2000").replace("CONV_CAUCHY_EPS= 1E-6", "CONV_CAUCHY_EPS= 1E-7")
    w = d / f"a{a:.0f}"; w.mkdir(exist_ok=True); (w / "case.cfg").write_text(cfg.replace("MESH_FILENAME= mesh.su2", "MESH_FILENAME= ../mesh.su2"))
    with open(w / "su2.log", "w") as log:
        p = subprocess.run([str(rc.SU2), "-t", "4", "case.cfg"], cwd=w, stdout=log, stderr=subprocess.STDOUT)
    head, rows = rc.read_history_file(w / "history.csv"); col = {h: i for i, h in enumerate(head)}
    return {"rc": p.returncode, "iters": len(rows), "CL": rows[-1][col["CL"]], "CD": rows[-1][col["CD"]]}


def xfoil_inviscid(alphas):
    """XFOIL inviscid (panel) CL for the same section; graphics off (PLOP G) and a polar file, as analysis/aero/xfoil_polars.py"""
    pts = geom.naca4_outline(geom.WING_M, geom.WING_P, geom.PARAMS["tc"], 120, geom.TE_AERO)
    w = OUT / "xfoil"; w.mkdir(parents=True, exist_ok=True)
    NL = chr(10)
    (w / "foil.dat").write_text("NACA2415 closed TE" + NL + NL.join(f"{x:.6f} {y:.6f}" for x, y in pts))
    pol = w / "inviscid_polar.txt"; pol.unlink(missing_ok=True)
    cmd = NL.join(["PLOP", "G", "", "LOAD foil.dat", "PANE", "OPER", "PACC", "inviscid_polar.txt", ""] + [f"ALFA {a}" for a in alphas] + ["PACC", "", "QUIT", ""])
    subprocess.run([str(XFOIL)], input=cmd, cwd=w, capture_output=True, text=True, timeout=120)
    out = {}
    for line in pol.read_text().splitlines():
        parts = line.split()
        try:
            out[float(parts[0])] = float(parts[1])
        except (ValueError, IndexError):
            pass
    return {a: out.get(a) for a in alphas}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
    res = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/cfd3d/scheme_check_2d.py",
           "xfoil_inviscid": xfoil_inviscid(ALPHAS), "levels": {}}
    for name, (h, hte) in LEVELS.items():
        d, ntri, nwall = mesh(name, h, hte)
        res["levels"][name] = {"wall_size_m": h, "te_size_m": hte, "triangles": ntri, "wall_edges": nwall, "su2": {a: su2(d, a) for a in ALPHAS}}
        r = res["levels"][name]["su2"]
        print(name, ntri, nwall, {a: round(r[a]["CL"], 4) for a in ALPHAS}, flush=True)
    gmsh.finalize()
    xf = res["xfoil_inviscid"]
    for name, L in res["levels"].items():
        s = L["su2"]; L["cl_alpha_per_rad"] = (s[4.0]["CL"] - s[0.0]["CL"]) / math.radians(4)
        L["cl4_vs_xfoil_pct"] = 100 * (s[4.0]["CL"] - xf[4.0]) / xf[4.0] if xf[4.0] else None
    res["xfoil_cl_alpha_per_rad"] = (xf[4.0] - xf[0.0]) / math.radians(4) if xf[0.0] is not None and xf[4.0] is not None else None
    (HERE / "out" / "scheme_check_2d.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"xfoil": xf, "xfoil_slope": res["xfoil_cl_alpha_per_rad"], **{k: (round(v["cl_alpha_per_rad"], 3), v["cl4_vs_xfoil_pct"]) for k, v in res["levels"].items()}}, indent=1))


if __name__ == "__main__":
    main()
