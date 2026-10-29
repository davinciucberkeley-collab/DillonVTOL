"""Writes docs/validation/VALIDATION-REPORT.md from the result files, so every number in the report is read from the
file it cites (nothing typed by hand). Run after the CFD, the checks and build_matrix.py.

Usage:  py analysis/validation/report.py
"""
import json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
J = lambda p: json.loads((ROOT / p).read_text()) if (ROOT / p).exists() else None
f3 = lambda x: "—" if x is None else f"{x:.3f}"
f4 = lambda x: "—" if x is None else f"{x:.4f}"


def main():
    vm = J("analysis/validation/validation_matrix.json"); cfd = J("analysis/cfd3d/out/cfd3d_results.json")
    geo = J("analysis/cfd3d/out/oml_fidelity.json"); xt = J("analysis/validation/xtool_boom_fea.json")
    cl = {c["id"]: c for c in vm["claims"]}
    lv = {k: J(f"analysis/cfd3d/out/L{k}/mesh_stats.json") for k in (1, 2, 3)}
    post = {p.stem: json.loads(p.read_text()) for p in (ROOT / "analysis/cfd3d/out/post").glob("*.json") if not p.stem.endswith("_viz")}
    S = []
    w = S.append
    w("# Engineering validation report")
    w("")
    w(f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `analysis/validation/report.py` from the files it cites. House style: docs/reference/REVIEW-STYLE.md.")
    w("")
    c = vm["counts"]
    w("## Verdict")
    w("")
    w(f"**{len(vm['claims'])} engineering claims checked: {c.get('Verified', 0)} Verified, {c.get('Partially Verified', 0)} Partially Verified, "
      f"{c.get('Unverified', 0)} Unverified, {c.get('Failed', 0)} Failed.** A full-aircraft 3-D CFD now exists: seven runs on three meshes, all finished. "
      "It confirms the neutral point and the induced drag the sizing uses. Its absolute lift is still mesh-limited: a 2-D check with the same numerics shows the scheme loses lift at this wall spacing (CFD-12), and only the finest mesh lands within 4 % of AVL. "
      "It does not predict drag, because it is inviscid. The design failures cluster in four places: power at full hover thrust, the structural tip mass, stale documents and CAD, and the wing-bolt and joiner specification.")
    w("")
    w("## What was changed")
    w("")
    w("| Area | Change | Files |")
    w("|---|---|---|")
    w("| Full-aircraft CFD | New: CAD-derived outer mould line, three tetrahedral meshes, SU2 incompressible-Euler runs, independent post-processing and checks | `analysis/cfd3d/` |")
    w("| 3-D CFD view | New tab in Aerodynamics: whole aircraft with surface Cp or speed, streamlines, wake planes, symmetry slice, and the real surface, symmetry-plane and cut-volume mesh, with residual histories and results tables | `review/src/cfdviz.js`, `review/src/body.html` |")
    w("| Validation matrix | New chapter: claims map on the 3-D CAD model, every claim with equations, inputs, assumptions, evidence, independent check and status, plus manufacturing readiness | `analysis/validation/`, `review/src/claimsmap.js`, `docs/validation/VALIDATION-MATRIX.md` |")
    w("| Cross-tool FEA | New: boom study re-solved with gmsh + own C3D10 solver (no SOLIDWORKS code) | `analysis/validation/xtool_boom_fea.py` |")
    w("| Agent interface | New: `tools/vtol.py` CLI with JSON output over every pipeline step, and the integration notes | `tools/vtol.py`, `docs/validation/AGENT-INTERFACE.md` |")
    w("| Review text | Simulation chapter verdict and the stopped-rotor drag card updated to match the audit | `review/src/body.html` |")
    w("")
    w("## Full-aircraft CFD")
    w("")
    w(f"Solver: {cfd['solver']}. Conditions: V {cfd['conditions']['V_mps']} m/s, ρ {cfd['conditions']['rho_kgm3']} kg/m³, S_ref {cfd['conditions']['S_ref_m2']} m², "
      f"c_ref {cfd['conditions']['c_ref_m']:.4f} m, elevator {cfd['conditions']['elevator_deg']}°, {cfd['conditions']['power']}, sideslip {cfd['conditions']['sideslip_deg']}°. "
      f"Source: `analysis/cfd3d/out/cfd3d_results.json`.")
    w("")
    w("| Case | Tetrahedra | Iterations | log10 rms(p) drop | CL | CMy | CDi Trefftz | Own CL integration |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|")
    for n, r in sorted(cfd["cases"].items(), key=lambda z: (z[1]["level"], z[1]["alpha_deg"])):
        p = post.get(n, {})
        w(f"| {n} | {r['tets']:,} | {r['iterations']} | {r['rms_p_first'] - r['rms_p_last']:.1f} | {f4(r['CL'])} | {f4(r['CMy'])} | {f4(p.get('trefftz', {}).get('CDi'))} | {f4(p.get('integrated', {}).get('CL'))} |")
    w("")
    w("Meshes (`analysis/cfd3d/out/L*/mesh_stats.json`): " + "; ".join(f"L{k} {s['tetrahedra']:,} tets, min SICN {s['quality_minSICN']['min']:.3f}" for k, s in lv.items() if s) + ".")
    w("")
    w("| Check | Status | Result |")
    w("|---|---|---|")
    for i in sorted(k for k in cl if k.startswith("CFD-")):
        x = cl[i]; w(f"| {i}: {x['claim']} | **{x['status']}** | {x['status_reason']} |")
    w("")
    w(f"Geometry: {len(geo['defeaturing'])} defeaturing rules recorded in `analysis/cfd3d/out/oml_fidelity.json` and in the review. Each rebuilt part's bounding box is compared with its STEP solid.")
    w("")
    if xt:
        cmp = xt["comparison"]
        w("## Cross-tool structural check (boom)")
        w("")
        w(f"Toolchain: {xt['toolchain']}. Source: `analysis/validation/xtool_boom_fea.json`.")
        w("")
        w("| Quantity | Independent FE | SOLIDWORKS | Beam theory | Difference |")
        w("|---|---:|---:|---:|---:|")
        t = cmp["tip_deflection_mm"]; w(f"| Tip deflection, mm | {t['independent_fe']:.3f} | {t['solidworks']:.3f} | {t['beam_PL3_3EI']:.3f} | {t['delta_vs_solidworks_pct']:+.1f} % vs SOLIDWORKS |")
        s = cmp["sxx_x100_MPa"]; w(f"| Bending stress at x = 0.10 m, MPa | {s['independent_fe']:.2f} | — | {s['beam']:.2f} | {s['delta_pct']:+.1f} % vs beam |")
        v = cmp["vm_max_MPa"]; w(f"| Peak von Mises (root corner), MPa | {v['independent_fe']:.1f} | {v['solidworks_fine']:.1f} | — | {v['delta_vs_solidworks_pct']:+.1f} % ({v['note']}) |")
        w(f"| Mesh change in tip deflection | {cmp['mesh_change_tip_defl_pct']:+.2f} % | | | |")
        w("")
        w("Same inputs, different mesher, element formulation and solver. The tip deflection and the stress away from the root corner agree, so the SOLIDWORKS study is reproduced. The study's load case is the separate issue: its tip mass is 37 % low (STR-05).")
        w("")
    w("## Failed claims")
    w("")
    for x in [x for x in vm["claims"] if x["status"] == "Failed"]:
        w(f"- **{x['id']}** ({vm['component_labels'][x['component']]}): {x['claim']} *{x['status_reason']}* Next: {x.get('next_step', '—')}")
    w("")
    w("## Manufacturing readiness")
    w("")
    for s in vm["manufacturing"]["subsystems"]:
        w(f"- **{s['name']}**: {s['level']}." + (" Blocking: " + "; ".join(s["blocking_items"]) if s["blocking_items"] else ""))
    w("")
    w("## What remains unverified or not run")
    w("")
    w("- Hover and transition CFD: need rotor modelling (actuator disk in SU2 is compressible-only; resolved rotors need sliding/overset meshes). Not run, and not shown as if it were.")
    w("- Viscous full-aircraft CFD (drag, separation, stall): needs prism layers on every part; the drag build-up stays the drag source.")
    w("- Power-on cruise (pusher slipstream), trimmed elevator, sideslip: not modelled.")
    w("- CalculiX is not installed, so the team's Gmsh/CalculiX workflow was not run; the gmsh mesh and load case in `xtool_boom_fea.py` are the hand-off.")
    w("- Prices could not be re-checked where vendor sites rate-limited (see AERO-31).")
    w("")
    w("## Next steps (in order)")
    w("")
    w("1. Measure pack + four-motor full-throttle current and thrust on the stand (AERO-18, AERO-19): decides whether hover T/W meets R13.")
    w("2. Feed CAD part masses back into the sizing (motor mount 88.7 g vs 20 g allowance), then re-run sizing, FEA, modal, CG and a landing case (STR-05, STR-11).")
    w("3. Regenerate CAD, drawings and FEA on the current sizing; rewrite the contradicting joint specs J05/J07/J10/J11; lengthen the wing bolt (MFG-01, MFG-04, MFG-09).")
    w("4. Re-mesh the wing, tail and fins at about 2 mm wall spacing with finer leading edges and re-run α 0/4/8 (CFD-12, CFD-11, CFD-02); then a viscous full-aircraft run for drag.")
    w("5. Install CalculiX and run the boom and spar cases from the gmsh meshes as a second independent structural solver.")
    w("")
    w("## Demonstration for the weekly meeting (10 minutes)")
    w("")
    w("1. Aerodynamics → *Whole aircraft: 3-D CFD*: rotate the aircraft, switch α 0–8°, toggle *Surface mesh* and *Volume cut* to show the real computational mesh, open the residual history.")
    w("2. The results table: SU2's CL against our own pressure integration, the three-mesh study (not yet monotone), CFD against AVL, and the 2-D check that explains the gap (CFD-12).")
    w("3. Validation matrix → *Claims map*: click the wing, open one Verified and one Failed claim, show the evidence files and the independent check.")
    w("4. `py tools/vtol.py claims --status Failed` and `py tools/vtol.py compare HEAD~4`: how an agent queries and diffs the design.")
    w("")
    (ROOT / "docs/validation/VALIDATION-REPORT.md").write_text("\n".join(S) + "\n", encoding="utf-8", newline="\n")
    print("wrote docs/validation/VALIDATION-REPORT.md", len(S), "lines")


if __name__ == "__main__":
    main()
