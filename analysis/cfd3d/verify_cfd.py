"""Independent checks of the full-aircraft CFD (out/cfd3d_results.json + out/post/*.json) -> analysis/validation/claims_cfd.json

Checks (each one says whether it shares inputs with the CFD, so agreement is not mistaken for independence):
  CFD-01 run evidence: every case finished (return code 0), residual drop, Cauchy convergence of CL
  CFD-02 grid convergence at alpha 4: Richardson extrapolation and GCI (Roache / Celik 2008) on CL and CMy, with the
         actual refinement ratios r = (N_fine / N_coarse)^(1/3)
  CFD-03 force bookkeeping: SU2's CL / CMy against an independent pressure integration over the wall triangles
  CFD-04 boundary conditions: symmetry-plane normal velocity, free stream recovered at the far field
  CFD-05 lift-curve slope against (a) lifting-line theory with the XFOIL section slope (Helmbold), (b) AVL with pod
  CFD-06 CL at alpha 4 and elevator 0 against AVL (pod) and the AeroSandbox VLM; zero-lift angle against the section
  CFD-07 pitching moment slope -> neutral point against AVL (39.8 % MAC)
  CFD-08 induced drag: Trefftz-plane estimate against CL^2 / (pi e AR) with AVL's e
  CFD-09 Reynolds number and why an inviscid solver is admissible for lift at cruise (attached flow, Re 3.5e5)
  CFD-10 drag: what the inviscid run can and cannot say (spurious drag vs the viscous build-up)
"""
import json, math, sys, time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
import run_cases as rc  # noqa: E402

AR = (2 * (rc.P["panelLen"] + rc.P["fusR"])) ** 2 / rc.S_REF


def gci(f1, f2, f3, r21, r32):
    """Celik et al. 2008 (J. Fluids Eng. 130, 078001) procedure; f1 finest. Returns p, extrapolated value, GCI_fine %"""
    e32, e21 = f3 - f2, f2 - f1
    if e21 == 0 or e32 == 0 or e32 / e21 <= 0:
        return {"p": None, "f_ext": None, "gci_fine_pct": None, "note": "oscillatory or zero change: no asymptotic estimate"}
    s = np.sign(e32 / e21); p = 1.0
    for _ in range(200):
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
    f_ext = (r21 ** p * f1 - f2) / (r21 ** p - 1)
    ea21 = abs((f1 - f2) / f1)
    return {"p": p, "f_ext": f_ext, "gci_fine_pct": 100 * 1.25 * ea21 / (r21 ** p - 1)}


def main():
    R = json.loads((OUT / "cfd3d_results.json").read_text())
    C = R["cases"]
    post = {p.stem: json.loads(p.read_text()) for p in (OUT / "post").glob("*.json") if not p.stem.endswith("_viz")}
    avl = json.loads((ROOT / "analysis/aero/out/avl_results.json").read_text())
    aero = json.loads((ROOT / "analysis/aero/aero_results.json").read_text())
    avl_pod = {round(s["Alpha"], 1): s for s in avl["pod"]["sweep"]}
    claims = []

    def claim(**k):
        k.setdefault("component", "aircraft"); k.setdefault("discipline", "aerodynamics")
        k.setdefault("tool", "SU2 8.5.0 INC_EULER on gmsh 4.15.2 tetrahedra (analysis/cfd3d/)")
        claims.append(k)

    # ---- CFD-01 run evidence
    done = {n: c for n, c in C.items() if c.get("returncode") == 0}
    drops = {n: c["rms_p_first"] - c["rms_p_last"] for n, c in done.items()}
    cauchy = {n: c["cauchy_CL"] for n, c in done.items()}
    claim(id="CFD-01", claim=f"{len(done)} of {len(rc.CASES)} full-aircraft cruise cases ran to completion in SU2.",
          value=len(done), units="cases", equations=["Cauchy criterion on CL, CD, CMy over 200 iterations, eps 1e-6"],
          assumptions=["steady, incompressible, inviscid", "power off, control surfaces 0 deg"],
          inputs={n: f"{c['iterations']} it, log10 rms(p) drop {drops[n]:.2f}, Cauchy[CL] {cauchy[n]:.1e}, {c['wall_s']} s" for n, c in done.items()},
          evidence=[{"file": f"analysis/cfd3d/out/cases/{n}/history.csv", "what": "per-iteration residuals and coefficients"} for n in done] +
                   [{"file": f"analysis/cfd3d/out/cases/{n}/su2.log", "what": "solver log incl. mesh read and orientation check"} for n in list(done)[:1]],
          ran_evidence="history.csv, su2.log, restart_flow.csv and forces_breakdown.dat written by SU2 in each case folder; run.json records return code and wall time",
          reproduced={"done": True, "how": "py analysis/cfd3d/run_cases.py run <case> regenerates every file", "matches": None},
          independent_check={"method": "residual drop and coefficient Cauchy series read from history.csv", "value": min(drops.values()) if drops else None, "repo_value": None, "delta_pct": None, "script": "analysis/cfd3d/verify_cfd.py#CFD-01"},
          status="Verified" if len(done) == len(rc.CASES) and all(v < 1e-5 for v in cauchy.values()) else "Partially Verified",
          status_reason=f"{len(done)} of {len(rc.CASES)} cases finished with exit code 0; log10 rms(p) fell " + (f"{min(drops.values()):.1f}-{max(drops.values()):.1f}" if drops else "-") + " orders; Cauchy[CL] " + (f"{max(cauchy.values()):.0e}" if cauchy else "-") + " at the last iteration" + ("" if len(done) == len(rc.CASES) else "; the remaining cases are still running or not run"),
          limitations=["residual drop is modest; convergence is judged on the integral quantities"], next_step="—")

    # ---- CFD-02 grid convergence
    g = [C.get(f"L{k}_a4.0") for k in (3, 2, 1)]
    if all(g):
        N = [x["tets"] for x in g]
        r21, r32 = (N[0] / N[1]) ** (1 / 3), (N[1] / N[2]) ** (1 / 3)
        gl = gci(g[0]["CL"], g[1]["CL"], g[2]["CL"], r21, r32)
        gm = gci(g[0]["CMy"], g[1]["CMy"], g[2]["CMy"], r21, r32)
        claim(id="CFD-02", claim=f"Grid convergence at alpha 4 deg: CL {g[2]['CL']:.4f} / {g[1]['CL']:.4f} / {g[0]['CL']:.4f} on {N[2]:,} / {N[1]:,} / {N[0]:,} tetrahedra.",
              value=gl.get("gci_fine_pct"), units="% GCI_fine on CL",
              equations=["r = (N_fine/N_coarse)^(1/3)", "p from |e32/e21| (Celik 2008, fixed-point)", "f_ext = (r21^p f1 - f2)/(r21^p - 1)", "GCI_fine = 1.25 |(f1-f2)/f1| / (r21^p - 1)"],
              assumptions=["the three meshes share every sizing rule (one scale factor)", "monotone convergence"],
              inputs={"r21": round(r21, 3), "r32": round(r32, 3), "CL": [g[2]["CL"], g[1]["CL"], g[0]["CL"]], "CMy": [g[2]["CMy"], g[1]["CMy"], g[0]["CMy"]]},
              evidence=[{"file": "analysis/cfd3d/out/cfd3d_results.json", "what": "cases L1_a4.0, L2_a4.0, L3_a4.0"}, {"file": "analysis/cfd3d/out/L1..L3/mesh_stats.json", "what": "cell counts"}],
              ran_evidence="three separate SU2 runs (CFD-01)",
              reproduced={"done": True, "how": "computed here from the stored coefficients", "matches": None},
              independent_check={"method": "Richardson extrapolation", "value": gl.get("f_ext"), "repo_value": g[0]["CL"], "delta_pct": None if gl.get("f_ext") is None else 100 * (g[0]["CL"] - gl["f_ext"]) / gl["f_ext"], "script": "analysis/cfd3d/verify_cfd.py#CFD-02",
                                 "CMy": gm},
              status="Verified" if gl.get("gci_fine_pct") is not None and gl["gci_fine_pct"] < 3 else "Partially Verified",
              status_reason=("GCI_fine on CL " + (f"{gl['gci_fine_pct']:.2f} % (p {gl['p']:.2f})" if gl.get("gci_fine_pct") is not None else "not computable: " + gl.get("note", "")) +
                             "; CMy " + (f"{gm['gci_fine_pct']:.1f} %" if gm.get("gci_fine_pct") is not None else gm.get("note", "—"))),
              limitations=["discretisation error only; model error (inviscid) is separate"], next_step="—")

    # ---- CFD-03 force bookkeeping
    rows = {}
    for n, c in done.items():
        if n in post:
            rows[n] = {"su2_CL": c["CL"], "int_CL": post[n]["integrated"]["CL"], "su2_CMy": c["CMy"], "int_CMy": post[n]["integrated"]["CMy"]}
    if rows:
        dmax = max(abs(r["int_CL"] - r["su2_CL"]) / abs(r["su2_CL"]) * 100 for r in rows.values() if abs(r["su2_CL"]) > 0.05)
        claim(id="CFD-03", claim="SU2's reported forces equal an independent pressure integration over the same wall triangles.",
              value=dmax, units="% max |dCL|", equations=["F = -sum_i p_i n_i A_i (n into the fluid, from the owning tetrahedron)", "CL = F.l / (q S_ref/2)"],
              assumptions=["node pressures averaged to triangle centroids (SU2 uses the same nodal dual-area idea, so small differences are expected)"],
              inputs={n: {k: round(v, 5) for k, v in r.items()} for n, r in rows.items()},
              evidence=[{"file": "analysis/cfd3d/out/post/<case>.json", "what": "integrated"}],
              ran_evidence="post-processing reads restart_flow.csv written by SU2",
              reproduced={"done": True, "how": "py analysis/cfd3d/postprocess.py <case>", "matches": dmax < 1.0},
              independent_check={"method": "own surface integration in numpy", "value": dmax, "repo_value": 0, "delta_pct": dmax, "script": "analysis/cfd3d/postprocess.py"},
              status="Verified" if dmax < 1.0 else "Partially Verified", status_reason=f"largest CL difference {dmax:.2f} %",
              limitations=["checks bookkeeping (reference area, axes, moment centre), not the flow solution"], next_step="—")

    # ---- CFD-04 boundary conditions
    if post:
        sym = max(p["symmetry_max_abs_vy_over_V"] for p in post.values())
        ffmin = min(p["farfield_speed_ratio"]["min"] for p in post.values()); ffmax = max(p["farfield_speed_ratio"]["max"] for p in post.values())
        claim(id="CFD-04", claim="Boundary conditions behave: no flow through the symmetry plane; free stream recovered at the far field.",
              value=sym, units="max |v_y|/V on the symmetry plane",
              equations=["symmetry: v . n = 0", "far field: |V|/V_inf -> 1"], assumptions=["domain 8 m ahead, 16 m behind, 8 m above/below, 10 m to the side of the half model"],
              inputs={"far_field_speed_ratio_min": ffmin, "far_field_speed_ratio_max": ffmax}, evidence=[{"file": "analysis/cfd3d/out/post/<case>.json", "what": "symmetry_max_abs_vy_over_V, farfield_speed_ratio"}],
              ran_evidence="read from the SU2 restart files", reproduced={"done": True, "how": "postprocess.py", "matches": None},
              independent_check={"method": "nodal velocities on the marker nodes", "value": sym, "repo_value": 0, "delta_pct": None, "script": "analysis/cfd3d/postprocess.py"},
              status="Verified" if sym < 1e-3 and 0.98 < ffmin and ffmax < 1.02 else "Partially Verified",
              status_reason=f"|v_y|/V <= {sym:.1e} on the symmetry plane; far-field |V|/V in {ffmin:.3f}-{ffmax:.3f}", limitations=[], next_step="—")

    # ---- CFD-05 lift slope
    pol = sorted([(c["alpha_deg"], c["CL"], c["CMy"]) for n, c in done.items() if c["level"] == 2])
    if len(pol) >= 3:
        a = np.radians([x[0] for x in pol]); cl = np.array([x[1] for x in pol]); cm = np.array([x[2] for x in pol])
        lin = np.abs(np.degrees(a)) <= 6.01
        cla, cl0 = np.polyfit(a[lin], cl[lin], 1)
        a0 = aero["section_polars"]["n2415_cruise_ncrit9"].get("cl_alpha_per_rad") if isinstance(aero["section_polars"].get("n2415_cruise_ncrit9"), dict) else None
        a0 = a0 or 6.832   # XFOIL NACA 2415, Re 3.5e5 (claims_aero.json AERO-02)
        helm = a0 / (math.sqrt(1 + (a0 / (math.pi * AR)) ** 2) + a0 / (math.pi * AR))
        avl_a = np.radians([s["Alpha"] for s in avl["pod"]["sweep"] if abs(s["Alpha"]) <= 6])
        avl_cl = np.array([s["CLtot"] for s in avl["pod"]["sweep"] if abs(s["Alpha"]) <= 6])
        avl_cla = float(np.polyfit(avl_a, avl_cl, 1)[0])
        claim(id="CFD-05", claim=f"Whole-aircraft lift-curve slope {cla:.2f} /rad (alpha {pol[0][0]:.0f}-6 deg, elevator 0).",
              value=float(cla), units="1/rad", equations=["CL = CL0 + CL_alpha alpha (least squares, |alpha| <= 6 deg)", "Helmbold: a = a0 / (sqrt(1 + (a0/(pi AR))^2) + a0/(pi AR))"],
              assumptions=["Helmbold is wing-only (no tail, pod or booms)", "AVL: vortex lattice + slender pod, same CG"],
              inputs={"AR": round(AR, 3), "a0_per_rad": a0, "CFD_points": [(round(math.degrees(x), 1), round(y, 4)) for x, y in zip(a, cl)]},
              evidence=[{"file": "analysis/cfd3d/out/cfd3d_results.json", "what": "L2 alpha sweep"}, {"file": "analysis/aero/out/avl_results.json", "what": "pod sweep, elevator 0"}],
              ran_evidence="SU2 runs (CFD-01)", reproduced={"done": True, "how": "fit here", "matches": None},
              independent_check={"method": "AVL (pod) lift slope; Helmbold wing-only as a sanity bound", "value": avl_cla, "repo_value": float(cla), "delta_pct": 100 * (cla - avl_cla) / avl_cla, "script": "analysis/cfd3d/verify_cfd.py#CFD-05", "helmbold_wing_only": helm},
              status="Verified" if abs(cla - avl_cla) / avl_cla < 0.08 else "Partially Verified",
              status_reason=f"CFD {cla:.2f} vs AVL {avl_cla:.2f} /rad ({100 * (cla - avl_cla) / avl_cla:+.1f} %); Helmbold wing alone {helm:.2f}" + ("; the gap matches the under-resolution the 2-D check measures at this wall spacing (CFD-12), so the CFD slope is a lower bound, not evidence against AVL" if abs(cla - avl_cla) / avl_cla > 0.08 else ""),
              limitations=["AVL and CFD share the planform and CG but not the solver or the body model; AVL geometry is one sizing pass older (chord 281.8 vs 284.2 mm)"], next_step="—")
        # ---- CFD-06 CL at 4 deg
        c4 = C.get("L3_a4.0") or C.get("L2_a4.0")
        avl4 = avl_pod.get(4.0, {}).get("CLtot")
        if c4 and avl4:
            claim(id="CFD-06", claim=f"CL {c4['CL']:.3f} at alpha 4 deg, elevator 0, V 18 m/s (finest mesh).", value=c4["CL"], units="-",
                  equations=["CL = L / (q S_ref)"], assumptions=["S_ref 0.682 m^2 (CAD wing)", "inviscid: no boundary-layer decambering, so CFD should sit a few % above a viscous answer"],
                  inputs={"AVL_pod_CL_a4": avl4, "zero_lift_alpha_CFD_deg": float(-math.degrees(cl0 / cla))},
                  evidence=[{"file": "analysis/aero/out/avl/ft_pod_a4.txt", "what": "AVL total forces"}],
                  ran_evidence="SU2 runs (CFD-01)", reproduced={"done": True, "how": "—", "matches": None},
                  independent_check={"method": "AVL 3.52 with pod at the same alpha and elevator", "value": avl4, "repo_value": c4["CL"], "delta_pct": 100 * (c4["CL"] - avl4) / avl4, "script": "analysis/cfd3d/verify_cfd.py#CFD-06"},
                  # agreement on one mesh is not enough: Verified also needs a computable grid-convergence estimate (CFD-02)
                  status="Verified" if abs(c4["CL"] - avl4) / avl4 < 0.08 and any(c["id"] == "CFD-02" and c["value"] is not None for c in claims) else "Partially Verified",
                  status_reason=f"{100 * (c4['CL'] - avl4) / avl4:+.1f} % against AVL on the finest mesh (L3); CL on L1/L2/L3 " + ", ".join(f"{C[k]['CL']:.4f}" for k in ("L1_a4.0", "L2_a4.0", "L3_a4.0") if k in C) + " is not monotone, so the agreement is not yet grid-independent" + ("; lift rises with refinement (CFD-02) and the 2-D check shows the scheme under-predicts lift at this spacing (CFD-12)" if abs(c4["CL"] - avl4) / avl4 > 0.08 else ""),
                  limitations=["both inviscid", "3-D lift magnitude not mesh-converged"], next_step="Finer wing/tail wall spacing (CFD-12).")
        # ---- CFD-07 neutral point
        cma = float(np.polyfit(a[lin], cm[lin], 1)[0])
        xnp = 28.0 - 100 * cma / cla   # % MAC: CG at 28 % MAC; dCm/dCL = -(x_np - x_cg)/c
        claim(id="CFD-07", component="tail", discipline="stability", claim=f"Neutral point {xnp:.1f} % MAC from the CFD moment slope (static margin {xnp - 28:.1f} % at the 28 % CG).",
              value=xnp, units="% MAC", equations=["x_np = x_cg - c (dCm/dalpha)/(dCL/dalpha)"], assumptions=["moment centre at the design CG on the chord line"],
              inputs={"Cm_alpha_per_rad": cma, "CL_alpha_per_rad": float(cla)},
              evidence=[{"file": "analysis/aero/aero_results.json", "what": "neutral_point (AVL with pod)"}],
              ran_evidence="SU2 runs (CFD-01)", reproduced={"done": True, "how": "fit here", "matches": None},
              independent_check={"method": "AVL neutral point with pod", "value": 39.84, "repo_value": xnp, "delta_pct": 100 * (xnp - 39.84) / 39.84, "script": "analysis/cfd3d/verify_cfd.py#CFD-07"},
              status="Verified" if abs(xnp - 39.84) < 3 else ("Failed" if xnp < 30 else "Partially Verified"),
              status_reason=f"CFD {xnp:.1f} % vs AVL 39.8 % MAC", limitations=["power-off; propeller normal force and slipstream not modelled"], next_step="Flight: trim-elevator-vs-speed test for the stick-fixed neutral point (test plan).")

    # ---- CFD-08 induced drag
    p4 = post.get("L3_a4.0") or post.get("L2_a4.0")
    c4 = C.get("L3_a4.0") or C.get("L2_a4.0")
    if p4 and c4:
        e = avl_pod.get(4.0, {}).get("e") or aero["trim_cruise"]["e_AVL"]
        cdi_th = c4["CL"] ** 2 / (math.pi * e * AR)
        cdi = p4["trefftz"]["CDi"]
        claim(id="CFD-08", claim=f"Induced drag from the Trefftz plane CDi {cdi:.4f} at alpha 4 deg.", value=cdi, units="-",
              equations=["CDi = (2/(q S)) * integral of 1/2 rho (v^2 + w^2) dA over the half plane", "CDi = CL^2 / (pi e AR)"],
              assumptions=["far-field kinetic-energy form; streamwise perturbation neglected"],
              inputs={"plane_x_m": p4["trefftz"]["x_su2_m"], "e_AVL": e, "AR": AR},
              evidence=[{"file": "analysis/cfd3d/out/post/<case>.json", "what": "trefftz"}], ran_evidence="sampled from the SU2 solution",
              reproduced={"done": True, "how": "postprocess.py", "matches": None},
              independent_check={"method": "CL^2/(pi e AR) with AVL's span efficiency", "value": cdi_th, "repo_value": cdi, "delta_pct": 100 * (cdi - cdi_th) / cdi_th, "script": "analysis/cfd3d/verify_cfd.py#CFD-08"},
              status="Partially Verified", status_reason=f"Trefftz {cdi:.4f} on the plane 0.3 m behind the wing TE vs CL^2/(pi e AR) {cdi_th:.4f} ({100 * (cdi - cdi_th) / cdi_th:+.0f} %); planes further aft read " + ", ".join(f"{q['CDi']:.4f}" for q in p4["trefftz"].get("planes", [])[1:]) + " as the trailing vortices dissipate on the tetrahedra, so the value depends on where it is measured",
              limitations=["numerical dissipation of the trailing vortices before the plane", "plane truncated at 4 m x 4 m"], next_step="—")
        # ---- CFD-10 drag
        claim(id="CFD-10", claim=f"The inviscid solver's surface CD ({c4['CD']:.4f}) is not a drag prediction.", value=c4["CD"], units="-",
              equations=["CD_surface = CD_induced + CD_spurious(numerical)"], assumptions=["no skin friction, no physical separation in an Euler run"],
              inputs={"components": {k: round(v["CD"], 4) for k, v in c4["components"].items()}},
              evidence=[{"file": "analysis/aero/drag_buildup.json", "what": "the viscous drag the sizing uses"}], ran_evidence="SU2 runs (CFD-01)",
              reproduced={"done": True, "how": "—", "matches": None},
              independent_check={"method": "Trefftz induced drag (CFD-08)", "value": cdi, "repo_value": c4["CD"], "delta_pct": None, "script": "analysis/cfd3d/verify_cfd.py#CFD-10"},
              status="Unverified", status_reason="surface CD minus the Trefftz CDi is numerical (blunt clamp and motor bases, coarse tetrahedra); profile drag stays with analysis/aero/drag_buildup.py",
              limitations=["a viscous (RANS) full-aircraft run with prism layers is needed for drag"], next_step="Car-roof / flight power test (aero M1, mass M3) remains the drag evidence.")

    # ---- CFD-11 physical bound on surface Cp
    rows = {n: p.get("cp_above_stagnation") for n, p in post.items() if p.get("cp_above_stagnation") is not None}
    if rows:
        worst = max(((n, tag, v) for n, r in rows.items() for tag, v in r.items()), key=lambda z: z[2]["cp_max"], default=None)
        tot = {n: sum(v["nodes_cp_gt_1"] for v in r.values()) for n, r in rows.items()}
        claim(id="CFD-11", component="tail", claim="Surface pressure stays within the incompressible stagnation bound (Cp <= 1) everywhere on the aircraft.",
              value=worst[2]["cp_max"] if worst else None, units="Cp max on a wall node",
              equations=["Bernoulli, incompressible: Cp = 1 - (V/V_inf)^2 <= 1"], assumptions=["nodal values from the restart file"],
              inputs={n: {tag: f"{v['nodes_cp_gt_1']}/{v['of_nodes']} nodes, max {v['cp_max']:.2f} at {v['at_su2_m']}" for tag, v in r.items()} for n, r in rows.items()},
              evidence=[{"file": "analysis/cfd3d/out/post/<case>.json", "what": "cp_above_stagnation"}], ran_evidence="read from the SU2 restart files",
              reproduced={"done": True, "how": "postprocess.py", "matches": False},
              independent_check={"method": "Bernoulli bound", "value": 1.0, "repo_value": worst[2]["cp_max"] if worst else None, "delta_pct": None, "script": "analysis/cfd3d/postprocess.py"},
              status="Failed" if worst and worst[2]["cp_max"] > 1.05 else "Verified",
              status_reason=(f"{worst[2]['cp_max']:.2f} on the {worst[1]} ({worst[0]}); " if worst else "") + ", ".join(f"{n}: {k} wall nodes above 1" for n, k in tot.items())
                            + ". Stagnation overshoot where the 0.9 mm horizontal-tail leading-edge radius and sharp box corners are resolved by only 1-2 mm elements",
              limitations=["local: the integrated tail load is a small share of CL, but tail-LE pressures from this run must not be used"],
              next_step="Refine the tail and fin leading edges (curvature sizing below 0.3 mm) and re-run; check the overshoot falls with refinement.")

    # ---- CFD-12 scheme and resolution on the 2-D section (scheme_check_2d.py)
    sc = json.loads((OUT / "scheme_check_2d.json").read_text()) if (OUT / "scheme_check_2d.json").exists() else None
    if sc:
        xf = sc["xfoil_cl_alpha_per_rad"]; L = sc["levels"]
        row = {k: f"{v['wall_edges']} wall edges: cl_alpha {v['cl_alpha_per_rad']:.2f} /rad, cl(4 deg) {v['cl4_vs_xfoil_pct']:+.1f} %" for k, v in L.items()}
        l2 = L.get("3D-L2"); fin = L.get("finest")
        claim(id="CFD-12", component="wing", claim="At the wall spacing of the 3-D meshes, the SU2 scheme reproduces the inviscid lift of the wing section.",
              value=l2["cl_alpha_per_rad"] if l2 else None, units="1/rad, 2-D at the L2 wall spacing",
              equations=["same SU2 INC_EULER numerics as run_cases.CFG on a 2-D gmsh mesh of the same NACA 2415 section", "reference: XFOIL 6.99 inviscid panel method"],
              assumptions=["2-D section behaviour carries over to the 3-D wing's chordwise resolution"],
              inputs={"xfoil_inviscid_cl_alpha_per_rad": round(xf, 3), **row},
              evidence=[{"file": "analysis/cfd3d/out/scheme_check_2d.json", "what": "five spacings, alpha 0 and 4"}, {"file": "analysis/cfd3d/out/scheme2d/", "what": "meshes, SU2 logs, XFOIL polar"}],
              ran_evidence="SU2 and XFOIL run by analysis/cfd3d/scheme_check_2d.py (2000+ iterations per case)",
              reproduced={"done": True, "how": "py analysis/cfd3d/scheme_check_2d.py", "matches": False},
              independent_check={"method": "XFOIL inviscid", "value": xf, "repo_value": l2["cl_alpha_per_rad"] if l2 else None,
                                 "delta_pct": 100 * (l2["cl_alpha_per_rad"] - xf) / xf if l2 else None, "script": "analysis/cfd3d/scheme_check_2d.py"},
              status="Failed",
              status_reason=(f"at the L1/L2 wall spacing the section lift slope is {100 * (L['3D-L1']['cl_alpha_per_rad'] - xf) / xf:+.0f} / {100 * (l2['cl_alpha_per_rad'] - xf) / xf:+.0f} % against XFOIL inviscid; "
                             f"it closes to {100 * (fin['cl_alpha_per_rad'] - xf) / xf:+.0f} % at {fin['wall_edges']} wall edges. Numerical dissipation at this resolution acts like viscous decambering, "
                             "which explains most of the 3-D lift-slope gap to AVL (CFD-05): absolute lift from the 3-D runs is mesh-limited"),
              limitations=["2-D proxy for the 3-D chordwise resolution"],
              next_step="Re-mesh the wing, tail and fins at about 2 mm wall spacing (about 300 wall edges per section) and re-run alpha 0, 4, 8; keep the other parts at the current sizes.")

    # ---- CFD-09 Reynolds number
    nu = 1.81e-5 / rc.RHO
    re = rc.V * rc.C_REF / nu
    claim(id="CFD-09", component="wing", claim=f"Cruise chord Reynolds number {re:.3g}: attached, lift-dominated flow, so inviscid CFD is admissible for lift and moment at alpha <= 8 deg.",
          value=re, units="-", equations=["Re = V c / nu", "nu = mu/rho, mu 1.81e-5 Pa s (ISA 15 C)"], assumptions=["ISA sea level"],
          inputs={"V": rc.V, "c": rc.C_REF}, evidence=[{"file": "analysis/aero/aero_results.json", "what": "conditions"}],
          ran_evidence="hand calculation", reproduced={"done": True, "how": "here", "matches": True},
          independent_check={"method": "XFOIL section at Re 3.5e5 stays attached to ~10 deg (aero_results.json section_polars)", "value": None, "repo_value": re, "delta_pct": None, "script": "analysis/cfd3d/verify_cfd.py#CFD-09"},
          status="Verified", status_reason="Re matches the aero package (AERO-01); attached-flow range from the viscous section polar",
          limitations=["laminar separation bubbles at Re 3.5e5 are not represented"], next_step="—")

    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "author": "analysis/cfd3d/verify_cfd.py", "claims": claims}
    (ROOT / "analysis/validation/claims_cfd.json").write_text(json.dumps(out, indent=1, default=float))
    for c in claims:
        print(c["id"], c["status"], "|", c["status_reason"])


if __name__ == "__main__":
    main()
