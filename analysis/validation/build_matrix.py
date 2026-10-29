"""Merge every claim file into the engineering validation matrix the review page shows.

Inputs (each written by its own checker; this script only merges and counts):
  claims_aero.json    aerodynamics, performance, propulsion, mass, stability, cost   (check_aero.py)
  claims_struct.json  structures, thermal, CAD, manufacturing                         (check_struct.py)
  claims_cfd.json     full-aircraft 3-D CFD                                           (analysis/cfd3d/verify_cfd.py)
  claims_xtool.json   cross-tool structural check (gmsh + own C3D10 vs SOLIDWORKS)   (xtool_boom_fea.py)
  manufacturing_readiness.json
Output: validation_matrix.json (claims sorted by component, counts by status / component / discipline) and
        VALIDATION-MATRIX.md (the same table for reading on GitHub).

Status definitions (applied by the checkers, repeated here so the page can show them):
  Verified            reproducible computation + an independent check agreeing within the stated tolerance
  Partially Verified  some evidence, important checks incomplete
  Unverified          not enough evidence to establish the result
  Failed              a calculation or independent check contradicts the claim
"""
import json, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATUSES = ["Verified", "Partially Verified", "Unverified", "Failed"]
COMPONENTS = ["aircraft", "wing", "fuselage", "tail", "booms", "lift_propulsion", "cruise_propulsion", "battery", "landing_gear", "avionics"]
LABEL = {"aircraft": "Whole aircraft", "wing": "Wing", "fuselage": "Fuselage pod", "tail": "Tail", "booms": "Booms and clamps",
         "lift_propulsion": "Lift propulsion", "cruise_propulsion": "Cruise propulsion", "battery": "Battery", "landing_gear": "Landing gear", "avionics": "Avionics"}
DEFS = {"Verified": "Reproducible calculation or simulation plus an independent check that agrees within its stated tolerance.",
        "Partially Verified": "Some evidence exists, but important checks are incomplete.",
        "Unverified": "Insufficient evidence to establish the result.",
        "Failed": "A calculation, simulation or independent check contradicts the claim."}
# review chapters that hold each component's evidence (body.html section ids)
CHAPTER = {"aircraft": "aero", "wing": "aero", "fuselage": "aero", "tail": "cg", "booms": "structures", "lift_propulsion": "propulsion",
           "cruise_propulsion": "propulsion", "battery": "mass", "landing_gear": "structures", "avionics": "controls"}


def main():
    claims, sources = [], {}
    for f in ("claims_aero.json", "claims_struct.json", "claims_cfd.json", "claims_xtool.json"):
        p = HERE / f
        if not p.exists():
            print("missing", f); continue
        d = json.loads(p.read_text())
        sources[f] = {"generated": d.get("generated"), "author": d.get("author"), "n": len(d["claims"])}
        for c in d["claims"]:
            c["source_file"] = "analysis/validation/" + f
            if c.get("status") not in STATUSES:
                raise SystemExit(f"{c['id']}: bad status {c.get('status')}")
            if c.get("component") not in COMPONENTS:
                raise SystemExit(f"{c['id']}: bad component {c.get('component')}")
            claims.append(c)
    order = {s: i for i, s in enumerate(["Failed", "Unverified", "Partially Verified", "Verified"])}
    claims.sort(key=lambda c: (COMPONENTS.index(c["component"]), order[c["status"]], c["id"]))
    mfg = json.loads((HERE / "manufacturing_readiness.json").read_text())
    by = lambda k: {v: dict(Counter(c["status"] for c in claims if c[k] == v)) for v in sorted({c[k] for c in claims})}
    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "script": "analysis/validation/build_matrix.py", "sources": sources,
           "status_definitions": DEFS, "component_labels": LABEL, "component_chapter": CHAPTER,
           "counts": dict(Counter(c["status"] for c in claims)), "by_component": by("component"), "by_discipline": by("discipline"),
           "claims": claims, "manufacturing": mfg}
    (HERE / "validation_matrix.json").write_text(json.dumps(out, indent=1, default=float))
    # Markdown twin
    lines = ["# Engineering validation matrix", "", f"Generated {out['generated']} by `analysis/validation/build_matrix.py` from " +
             ", ".join(f"`{k}` ({v['n']})" for k, v in sources.items()) + ".", "",
             "| Status | Meaning | Count |", "|---|---|---:|"] + [f"| {s} | {DEFS[s]} | {out['counts'].get(s, 0)} |" for s in STATUSES] + ["",
             "| ID | Component | Discipline | Claim | Status | Independent check | Why |", "|---|---|---|---|---|---|---|"]
    for c in claims:
        ic = c.get("independent_check") or {}
        chk = ic.get("method", "—")
        if ic.get("delta_pct") is not None:
            chk += f" ({ic['delta_pct']:+.1f} %)"
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {c['id']} | {LABEL[c['component']]} | {c['discipline']} | {cell(c['claim'])} | **{c['status']}** | {cell(chk)} | {cell(c.get('status_reason', ''))} |")
    lines += ["", "## Manufacturing readiness", "", "| Subsystem | Level | Blocking items |", "|---|---|---|"]
    for s in mfg["subsystems"]:
        lines.append(f"| {s['name']} | {s['level']} | " + "; ".join(str(b).replace("|", "/") for b in s["blocking_items"]) + " |")
    (HERE.parents[1] / "docs" / "validation").mkdir(parents=True, exist_ok=True)
    (HERE.parents[1] / "docs" / "validation" / "VALIDATION-MATRIX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"counts": out["counts"], "n": len(claims)}, indent=1))


if __name__ == "__main__":
    main()
