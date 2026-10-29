"""vtol: one command-line interface over the engineering pipeline, for team members and AI agents.

Every command runs the repository's own scripts (no logic is duplicated here) and, with --json, prints one JSON object
on stdout so an agent can act on the result without scraping text. Exit code 0 = success, 1 = a step failed,
2 = bad usage. Long runs (CFD) print where their logs are.

  py tools/vtol.py status [--json]                     what exists, how old it is, which CFD cases ran
  py tools/vtol.py geometry                            CFD outer mould line from cad/params.txt (+ STEP fidelity)
  py tools/vtol.py mesh --level 2                      tetrahedral CFD mesh (levels 1-3)
  py tools/vtol.py cfd run L2_a4.0 [--restart-from L2_a4.0] [--iters 2500]
  py tools/vtol.py cfd summary | post <case>... | pack | verify
  py tools/vtol.py validate                            re-run every independent check and rebuild the matrix
  py tools/vtol.py xtool boom                          gmsh + own C3D10 solver vs the SOLIDWORKS boom FEA
  py tools/vtol.py claims [--component wing] [--status Failed] [--json]
  py tools/vtol.py compare <git-ref> [--json]          key results now vs another commit (design iterations)
  py tools/vtol.py report                              rebuild the review page (node review/build.mjs)
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CFD = ROOT / "analysis" / "cfd3d"
VAL = ROOT / "analysis" / "validation"
# key scalar results that define a design iteration: (file, JSON path with "/" separators, label)
KEYS = [("analysis/results.json", "concepts/C0/sized/m", "MTOW kg"), ("analysis/results.json", "concepts/C0/sized/S", "wing area m2"),
        ("analysis/results.json", "concepts/C0/sized/P_cruise", "cruise power W"), ("analysis/results.json", "concepts/C0/sized/P_hover", "hover power W"),
        ("analysis/results.json", "concepts/C0/sized/t_cruise_avail_min", "cruise time min"), ("analysis/results.json", "concepts/C0/sized/TW", "hover T/W"),
        ("analysis/results.json", "concepts/C0/cg/pct/np", "neutral point % MAC"), ("analysis/aero/aero_results.json", "trim_cruise/alpha_deg", "trim alpha deg"),
        ("analysis/cfd3d/out/cfd3d_results.json", "cases/L2_a4.0/CL", "3-D CFD CL at 4 deg"), ("analysis/validation/validation_matrix.json", "counts/Failed", "failed claims")]


def run(cmd, log=None):
    print("$", " ".join(str(c) for c in cmd), file=sys.stderr)
    if log:
        with open(log, "w") as f:
            return subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    return subprocess.run(cmd, cwd=ROOT).returncode


def dig(d, path):
    for k in path.split("/"):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def status():
    def info(p):
        p = ROOT / p
        return {"exists": p.exists(), "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)) if p.exists() else None}
    files = ["cad/params.txt", "cad/model/VTOL_Concept.STEP", "analysis/results.json", "analysis/aero/aero_results.json", "cad/sim/results.txt",
             "analysis/cfd3d/out/oml_half.brep", "analysis/cfd3d/out/L1/mesh.su2", "analysis/cfd3d/out/L2/mesh.su2", "analysis/cfd3d/out/L3/mesh.su2",
             "analysis/cfd3d/out/cfd3d_results.json", "analysis/cfd3d/out/viz/cfd3d_viz.json", "analysis/validation/validation_matrix.json",
             "analysis/validation/xtool_boom_fea.json", "review/vtol-review.html"]
    cases = {}
    for d in sorted((CFD / "out" / "cases").glob("*")) if (CFD / "out" / "cases").exists() else []:
        r = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else None
        cases[d.name] = {"finished": r is not None, "returncode": r and r.get("returncode"), "has_restart": (d / "restart_flow.csv").exists(),
                         "post": (CFD / "out" / "post" / f"{d.name}.json").exists()}
    vm = json.loads((VAL / "validation_matrix.json").read_text()) if (VAL / "validation_matrix.json").exists() else {}
    return {"files": {f: info(f) for f in files}, "cfd_cases": cases, "claims": vm.get("counts")}


def compare(ref):
    out = []
    for f, path, label in KEYS:
        now = dig(json.loads((ROOT / f).read_text()), path) if (ROOT / f).exists() else None
        p = subprocess.run(["git", "show", f"{ref}:{f}"], cwd=ROOT, capture_output=True, text=True)
        then = dig(json.loads(p.stdout), path) if p.returncode == 0 else None
        d = (now - then) / then * 100 if isinstance(now, (int, float)) and isinstance(then, (int, float)) and then else None
        out.append({"quantity": label, "file": f, ref: then, "now": now, "change_pct": d})
    return out


def main():
    ap = argparse.ArgumentParser(prog="vtol", description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("geometry")
    m = sub.add_parser("mesh"); m.add_argument("--level", type=int, choices=(1, 2, 3), default=2)
    c = sub.add_parser("cfd"); c.add_argument("action", choices=("run", "summary", "post", "pack", "verify")); c.add_argument("cases", nargs="*")
    c.add_argument("--restart-from"); c.add_argument("--iters", type=int)
    sub.add_parser("validate")
    x = sub.add_parser("xtool"); x.add_argument("what", choices=("boom",))
    q = sub.add_parser("claims"); q.add_argument("--component"); q.add_argument("--status"); q.add_argument("--discipline")
    k = sub.add_parser("compare"); k.add_argument("ref")
    sub.add_parser("report")
    argv = sys.argv[1:]
    as_json = "--json" in argv            # accepted anywhere on the line, so agents need not know argparse's ordering
    a = ap.parse_args([v for v in argv if v != "--json"]); a.json = as_json
    rc, payload = 0, None
    if a.cmd == "status":
        payload = status()
    elif a.cmd == "geometry":
        rc = run([PY, CFD / "build_geometry.py"])
    elif a.cmd == "mesh":
        rc = run([PY, CFD / "build_mesh.py", str(a.level)], log=CFD / "out" / f"mesh_L{a.level}.log")
    elif a.cmd == "cfd":
        env_cmd = [PY, CFD / "run_cases.py"]
        if a.action == "run":
            if a.restart_from:
                os.environ["RESTART_FROM"] = a.restart_from
            if a.iters:
                os.environ["ITERS"] = str(a.iters)
            rc = run(env_cmd + ["run"] + a.cases)
            payload = {"logs": [str(CFD / "out" / "cases" / n / "su2.log") for n in a.cases]}
        elif a.action == "summary":
            rc = run(env_cmd + ["summary"])
        elif a.action == "post":
            rc = run([PY, CFD / "postprocess.py"] + a.cases)
        elif a.action == "pack":
            rc = run([PY, CFD / "postprocess.py", "pack"])
        else:
            rc = run([PY, CFD / "verify_cfd.py"])
    elif a.cmd == "validate":
        for s in (VAL / "check_aero.py", VAL / "check_struct.py", CFD / "verify_cfd.py", VAL / "build_matrix.py"):
            if s.exists() and (s.name != "verify_cfd.py" or (CFD / "out" / "cfd3d_results.json").exists()):
                rc |= run([PY, s])
        payload = json.loads((VAL / "validation_matrix.json").read_text())["counts"]
    elif a.cmd == "xtool":
        rc = run([PY, VAL / "xtool_boom_fea.py"])
        payload = json.loads((VAL / "xtool_boom_fea.json").read_text())["comparison"] if rc == 0 else None
    elif a.cmd == "claims":
        vm = json.loads((VAL / "validation_matrix.json").read_text())
        payload = [{k: c.get(k) for k in ("id", "component", "discipline", "claim", "status", "status_reason", "next_step")} for c in vm["claims"]
                   if (not a.component or c["component"] == a.component) and (not a.status or c["status"] == a.status) and (not a.discipline or c["discipline"] == a.discipline)]
    elif a.cmd == "compare":
        payload = compare(a.ref)
    elif a.cmd == "report":
        rc = run(["node", ROOT / "review" / "build.mjs"])
    if payload is not None:
        if a.json:
            print(json.dumps(payload, indent=1, default=str))
        elif isinstance(payload, list):
            for r in payload:
                print(" | ".join(f"{v}" for v in r.values()))
        else:
            print(json.dumps(payload, indent=1, default=str))
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
