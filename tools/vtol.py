"""vtol: one tool for running and checking the VTOL engineering work.

New to the command line? Double-click VTOL.bat in the project folder (or run `py tools/vtol.py`) and pick from the menu.

Every command runs the repository's own scripts (no engineering logic lives here). With --json a command prints one JSON
object, so an AI agent can act on the result. Exit code 0 = success, 1 = a step failed or a check found a problem,
2 = bad usage.

  Checking the claims
    py tools/vtol.py check                         re-run every check and every claim's arithmetic; summary of what changed
    py tools/vtol.py trace AERO-14                 one claim, step by step: equations, numbers, where each number comes from
    py tools/vtol.py prove AERO-14 | all           write a proof sheet (Markdown, renders on GitHub) to docs/validation/proofs/
    py tools/vtol.py claims [--status Failed] [--component wing]
    py tools/vtol.py strict                        fail (exit 1) if any claim does not re-run, any hand-off is stale, or any input has no source
    py tools/vtol.py sources [--recheck]           external sources checked against the repo; --recheck re-tests every URL
  CFD and structures
    py tools/vtol.py mesh-audit                    score the CFD meshes against published standards
    py tools/vtol.py geometry | mesh --level 2     CFD geometry from the CAD parameters; tetrahedral mesh (levels 1-4)
    py tools/vtol.py cfd run L2_a4.0 [--restart-from L2_a4.0] [--iters 2500]
    py tools/vtol.py cfd summary | post <case>... | pack | verify
    py tools/vtol.py xtool boom                    independent boom FEA (gmsh + own solver) against SOLIDWORKS
  Project
    py tools/vtol.py status                        what exists and how old it is
    py tools/vtol.py compare <git-ref>             key results now against another commit
    py tools/vtol.py report | open                 rebuild the review website | open it in your browser
"""
import argparse, json, math, os, re, subprocess, sys, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CFD = ROOT / "analysis" / "cfd3d"
VAL = ROOT / "analysis" / "validation"
SHEETS = ROOT / "docs" / "validation" / "proofs"
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
OK, BAD = "✓", "✗"
# key scalar results that define a design iteration: (file, JSON path with "/" separators, label)
KEYS = [("analysis/results.json", "concepts/C0/sized/m", "MTOW kg"), ("analysis/results.json", "concepts/C0/sized/S", "wing area m2"),
        ("analysis/results.json", "concepts/C0/sized/P_cruise", "cruise power W"), ("analysis/results.json", "concepts/C0/sized/P_hover", "hover power W"),
        ("analysis/results.json", "concepts/C0/sized/t_cruise_avail_min", "cruise time min"), ("analysis/results.json", "concepts/C0/sized/TW", "hover T/W"),
        ("analysis/results.json", "concepts/C0/cg/pct/np", "neutral point % MAC"), ("analysis/aero/aero_results.json", "trim_cruise/alpha_deg", "trim alpha deg"),
        ("analysis/cfd3d/out/cfd3d_results.json", "cases/L2_a4.0/CL", "3-D CFD CL at 4 deg"), ("analysis/validation/validation_matrix.json", "counts/Failed", "failed claims")]


def run(cmd, log=None, quiet=False):
    if not quiet:
        print("  running:", " ".join(str(c).replace(str(ROOT) + os.sep, "") for c in cmd), file=sys.stderr)
    if log:
        with open(log, "w", encoding="utf-8") as f:
            return subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT).returncode
    if quiet:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True).returncode
    return subprocess.run(cmd, cwd=ROOT).returncode


def load(p):
    p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def dig(d, path):
    for k in path.split("/"):
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def pct(d, k=2):
    t = f"{d:+.{k}f}"
    return t[1:] if float(t) == 0 else t


def num(x, n=4):
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        return str(x)
    if x == 0:
        return "0"
    a = abs(x)
    if a >= 1e5 or a < 1e-3:
        return f"{x:.3e}"
    return f"{x:.{n}g}"


# ---------------------------------------------------------------- status, compare (unchanged behaviour)
def status():
    def info(p):
        p = ROOT / p
        return {"exists": p.exists(), "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)) if p.exists() else None}
    files = ["cad/params.txt", "cad/model/VTOL_Concept.STEP", "analysis/results.json", "analysis/aero/aero_results.json", "cad/sim/results.txt",
             "analysis/cfd3d/out/oml_half.brep", "analysis/cfd3d/out/L1/mesh.su2", "analysis/cfd3d/out/L2/mesh.su2", "analysis/cfd3d/out/L3/mesh.su2",
             "analysis/cfd3d/out/cfd3d_results.json", "analysis/cfd3d/out/viz/cfd3d_viz.json", "analysis/validation/validation_matrix.json",
             "analysis/validation/proofs.json", "analysis/cfd3d/out/mesh_audit.json", "analysis/validation/xtool_boom_fea.json", "review/vtol-review.html"]
    cases = {}
    for d in sorted((CFD / "out" / "cases").glob("*")) if (CFD / "out" / "cases").exists() else []:
        r = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else None
        cases[d.name] = {"finished": r is not None, "returncode": r and r.get("returncode"), "has_restart": (d / "restart_flow.csv").exists(),
                         "post": (CFD / "out" / "post" / f"{d.name}.json").exists()}
    vm = load("analysis/validation/validation_matrix.json") or {}
    return {"files": {f: info(f) for f in files}, "cfd_cases": cases, "claims": vm.get("counts")}


def compare(ref):
    out = []
    for f, path, label in KEYS:
        now = dig(load(f), path) if (ROOT / f).exists() else None
        p = subprocess.run(["git", "show", f"{ref}:{f}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        then = dig(json.loads(p.stdout), path) if p.returncode == 0 else None
        d = (now - then) / then * 100 if isinstance(now, (int, float)) and isinstance(then, (int, float)) and then else None
        out.append({"quantity": label, "file": f, ref: then, "now": now, "change_pct": d})
    return out


# ---------------------------------------------------------------- claims: check, trace, prove, strict
def check():
    """every independent check, the matrix, then the proof chains; returns a summary"""
    before = load("analysis/validation/proofs.json")
    rc = 0
    for s in (VAL / "check_aero.py", VAL / "check_struct.py", CFD / "verify_cfd.py", VAL / "build_matrix.py", VAL / "proofs.py"):
        if s.exists() and (s.name != "verify_cfd.py" or (CFD / "out" / "cfd3d_results.json").exists()):
            r = run([PY, s], quiet=True)
            print(f"  {OK if r == 0 else BAD} {s.relative_to(ROOT)}", file=sys.stderr)
            rc |= r
    vm, pr = load("analysis/validation/validation_matrix.json"), load("analysis/validation/proofs.json")
    changed = []
    if before:
        for cid, p in pr["claims"].items():
            b = before["claims"].get(cid, {}).get("result", {}).get("value"); a = p.get("result", {}).get("value")
            if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b and abs(a - b) / abs(b) > 1e-6:
                changed.append({"claim": cid, "before": b, "now": a})
    return rc, {"status_counts": vm["counts"], "proofs": pr["summary"], "changed_since_last_check": changed,
                "not_reproduced": [c for c, p in pr["claims"].items() if p.get("result", {}).get("reproduced") is False],
                "stale_links": [f"{c}: {v['sym']} from {v['from_claim']}" for c, p in pr["claims"].items() for v in p.get("vars", []) if v.get("link", {}).get("state") == "stale"],
                "failed": [c["id"] for c in vm["claims"] if c["status"] == "Failed"]}


def show_check(s):
    c = s["status_counts"]; p = s["proofs"]
    print(f"\n  Claims: {sum(c.values())}   Verified {c.get('Verified', 0)} · Partly verified {c.get('Partially Verified', 0)} · Unverified {c.get('Unverified', 0)} · Failed {c.get('Failed', 0)}")
    print(f"  Arithmetic re-run: {p['reproduced']} of {p['computed']} claims give the same number from their cited files")
    print(f"  Hand-offs between claims: {p['links_consistent']} of {p['links']} carry the same number")
    if s["not_reproduced"]:
        print(f"  {BAD} Does not re-run to the claimed number: {', '.join(s['not_reproduced'])}")
    if s["stale_links"]:
        print(f"  {BAD} Stale hand-off (uses an old number): {'; '.join(s['stale_links'])}")
    if s["changed_since_last_check"]:
        print("  Changed since the last check:")
        for r in s["changed_since_last_check"]:
            print(f"     {r['claim']}: {num(r['before'])} -> {num(r['now'])}")
    print(f"  Failed claims: {', '.join(s['failed']) or 'none'}")
    print("\n  Next: `py tools/vtol.py trace <ID>` explains any one of them.")


def claim_bundle(cid):
    vm, pr = load("analysis/validation/validation_matrix.json"), load("analysis/validation/proofs.json")
    if not vm or not pr:
        raise SystemExit("Run `py tools/vtol.py check` first.")
    cid = cid.upper()
    c = next((x for x in vm["claims"] if x["id"] == cid), None)
    if not c:
        close = [x["id"] for x in vm["claims"] if x["id"].startswith(cid.split("-")[0])][:12]
        raise SystemExit(f"No claim {cid}. Some IDs: {', '.join(close) or ', '.join(x['id'] for x in vm['claims'][:12])}")
    return c, pr["claims"][cid], pr


def where(v, pr):
    s = v.get("src", {}); out = []
    if v.get("from_claim"):
        l = v.get("link", {})
        out.append(f"result of {v['from_claim']}" + (f" ({BAD} stale: that claim now says {num(l.get('claim_value'))})" if l.get("state") == "stale" else ""))
    if s.get("kind") in ("file", "checker"):
        out.append(s["ref"])
    elif s.get("kind") == "constant":
        out.append(s["ref"])
    if s.get("src_id"):
        so = pr["sources"].get(s["src_id"], {})
        out.append(f"{s['src_id']} [{so.get('status', '?')}] {so.get('title', '')[:60]}")
    return "; ".join(out)


def trace(cid):
    c, p, pr = claim_bundle(cid)
    print(f"\n  {c['id']}  [{c['status']}]  {c['claim']}")
    print(f"  Why: {c['status_reason']}\n")
    if p["kind"] == "computed":
        for i, st in enumerate(p["steps"], 1):
            print(f"  Step {i}: {st['desc']}")
            print(f"     {st['expr'].replace('math.', '')}  =  {num(st['value'])} {st['unit']}")
        r = p["result"]
        mark = OK if r["reproduced"] else (BAD if r["reproduced"] is False else "-")
        d = r["delta_pct"]
        print(f"\n  {mark} Result {num(r['value'])} {r['unit']} against the claim's {num(r['claim_value'])} {r.get('claim_units') or ''}" + (f"  (difference {pct(d)} %)" if d is not None else ""))
        print("\n  Inputs and where each comes from:")
        for v in p["vars"]:
            val = f"{len(v['value'])} items" if isinstance(v["value"], list) else f"{num(v['value'])} {v['unit']}"
            print(f"     {v['sym']:8s} = {val:18s} {v['desc']}\n{'':14s}<- {where(v, pr)}")
        if p.get("note"):
            print(f"\n  Note: {p['note']}")
    else:
        print("  No closed-form arithmetic to re-run; the evidence is:")
        for e in p.get("evidence", []):
            print(f"     {e['file']}: {e['what']}")
        if p.get("equations"):
            print("  Equations used: " + "; ".join(p["equations"]))
    ic = p.get("check") or {}
    print(f"\n  Independent check: {ic.get('method', '-')}" + (f" ({ic['delta_pct']:+.1f} %)" if ic.get("delta_pct") is not None else ""))
    if p["upstream"] or p["downstream"]:
        print(f"  Uses: {', '.join(p['upstream']) or '-'}    Used by: {', '.join(p['downstream']) or '-'}")
    if p.get("external"):
        print("  External sources: " + "; ".join(f"{s} [{pr['sources'].get(s, {}).get('status', '?')}]" for s in p["external"]))
    print(f"\n  Proof sheet: py tools/vtol.py prove {c['id']}")


# ---- proof sheets: GitHub renders $$...$$ as math ----
def _bounded_sub(tex, items):
    """replace each variable's TeX with a numbered token, longest first, on symbol boundaries (same rule as the website)"""
    for t, k in sorted(items, key=lambda x: -len(x[0])):
        out, i = "", 0
        while True:
            j = tex.find(t, i)
            if j < 0:
                out += tex[i:]; break
            b = tex[j - 1] if j else " "; a = tex[j + len(t)] if j + len(t) < len(tex) else " "
            ok = not re.match(r"[A-Za-z\\_]", b) and not re.match(r"[A-Za-z0-9_{]", a)
            out += tex[i:j] + (f"\x00{k}\x00" if ok else t); i = j + len(t)
        tex = out
    return tex


def _tex_num(x):
    if not isinstance(x, (int, float)):
        return "\\ldots"
    if x != 0 and (abs(x) >= 1e5 or abs(x) < 1e-3):
        e = math.floor(math.log10(abs(x))); s = f"{x / 10 ** e:.3g}\\times 10^{{{e}}}"
    else:
        s = f"{x:.4g}"
    return f"({s})" if x < 0 else s


def substitute(tex, vals):
    tok = _bounded_sub(tex, [(v["tex"], i) for i, v in enumerate(vals) if v.get("tex")])
    out = ""
    for part in re.split(r"(\x00\d+\x00)", tok):
        m = re.fullmatch(r"\x00(\d+)\x00", part)
        if not m:
            out += part; continue
        prev = re.sub(r"(\\,|\\;|\s)+$", "", out)
        out += ("\\times " if prev and (prev[-1].isdigit() or prev[-1] == ")") else "") + _tex_num(vals[int(m.group(1))]["value"])
    return out


def sheet(cid):
    c, p, pr = claim_bundle(cid)
    L = [f"# {c['id']}: {c['claim']}", "", f"**Status: {c['status']}.** {c['status_reason']}", ""]
    if p["kind"] == "computed":
        r = p["result"]; d = r["delta_pct"]
        mark = "✓ re-runs to" if r["reproduced"] else ("✗ re-runs to" if r["reproduced"] is False else "Result:")
        L += [f"**{mark} {num(r['value'])} {r['unit']}** against the claim's {num(r['claim_value'])} {r.get('claim_units') or ''}" + (f" (difference {pct(d)} %)." if d is not None else "."), "", "## Calculation", ""]
        prev = []
        for i, st in enumerate(p["steps"], 1):
            lhs, rhs = st["tex"].split("=", 1)
            unit = "" if st["unit"] in ("-", "") else f"\\ \\text{{{st['unit']}}}"
            L += [f"{i}. {st['desc'] or 'Step'}", "", "$$" + st["tex"] + "$$", "",
                  "$$= " + substitute(rhs, p["vars"] + prev) + f" = {_tex_num(st['value'])}{unit}$$", ""]
            prev.append({"tex": lhs.strip(), "value": st["value"]})
        L += ["## Inputs", "", "| Symbol | Value | Meaning | Comes from |", "|---|---|---|---|"]
        for v in p["vars"]:
            val = f"{len(v['value'])} items" if isinstance(v["value"], list) else f"{num(v['value'])} {'' if v['unit'] == '-' else v['unit']}"
            src = where(v, pr).replace("|", "/")
            if v.get("from_claim"):
                src = src.replace(f"result of {v['from_claim']}", f"result of [{v['from_claim']}]({v['from_claim']}.md)")
            L.append(f"| ${v['tex']}$ | {val} | {v['desc']} | {src} |")
        if p.get("note"):
            L += ["", f"*{p['note']}*"]
    else:
        L += ["## Evidence", "", "No closed-form arithmetic to re-run; the proof is the evidence and the independent check.", ""]
        if p.get("equations"):
            L += ["Equations used: " + "; ".join(f"`{e}`" for e in p["equations"]), ""]
        L += [f"- `{e['file']}`: {e['what']}" for e in p.get("evidence", [])]
    ic = p.get("check") or {}
    L += ["", "## Independent check", "", f"{ic.get('method', '—')}" + (f" (difference {ic['delta_pct']:+.1f} %)" if ic.get("delta_pct") is not None else "") + (f", `{ic['script']}`" if ic.get("script") else "")]
    if p["upstream"] or p["downstream"]:
        L += ["", "## Links", "", "Uses: " + (", ".join(f"[{x}]({x}.md)" for x in p["upstream"]) or "—"), "", "Used by: " + (", ".join(f"[{x}]({x}.md)" for x in p["downstream"]) or "—")]
    if p.get("external"):
        L += ["", "## External sources", ""]
        for s in p["external"]:
            so = pr["sources"].get(s, {})
            L.append(f"- **{s}** [{so.get('status', '?')}]: " + (f"[{so.get('title', '')}]({so['url']})" if so.get("url") else so.get("title", "")) + (f", checked {so['checked']}" if so.get("checked") else ""))
    L += ["", "---", f"Generated by `py tools/vtol.py prove {c['id']}` from `analysis/validation/proofs.json` ({pr['generated']}) and `{c['source_file']}`. Every input is read from the file it names when `proofs.py` runs.", ""]
    SHEETS.mkdir(parents=True, exist_ok=True)
    f = SHEETS / f"{c['id']}.md"; f.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return f, c, p


def prove(what):
    if what.lower() != "all":
        f, _, _ = sheet(what); return [str(f.relative_to(ROOT))]
    vm = load("analysis/validation/validation_matrix.json"); rows = ["# Proof sheets", "", "One page per claim: the calculation re-run with its numbers, every input and where it comes from, the independent check, and the claims it feeds.", "",
                                                                  "| Claim | Status | Re-run | Statement |", "|---|---|---|---|"]
    out = []
    for c in vm["claims"]:
        f, c, p = sheet(c["id"]); out.append(str(f.relative_to(ROOT)))
        r = p.get("result", {}); rr = "evidence" if p["kind"] != "computed" else ("✓" if r.get("reproduced") else "✗" if r.get("reproduced") is False else "—")
        rows.append(f"| [{c['id']}]({c['id']}.md) | {c['status']} | {rr} | {c['claim'].replace('|', '/')} |")
    (SHEETS / "README.md").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return out


def strict():
    """problems that should block a release: arithmetic that does not re-run (for a claim not already marked Failed), stale hand-offs, unsourced inputs"""
    vm, pr = load("analysis/validation/validation_matrix.json"), load("analysis/validation/proofs.json")
    st = {c["id"]: c["status"] for c in vm["claims"]}; issues = []
    for cid, p in pr["claims"].items():
        r = p.get("result") or {}
        if r.get("reproduced") is False and st[cid] != "Failed":
            issues.append(f"{cid}: re-runs to {num(r['value'])}, claim says {num(r['claim_value'])}, but its status is {st[cid]}")
        for v in p.get("vars", []):
            if v.get("link", {}).get("state") == "stale":
                issues.append(f"{cid}: input {v['sym']} = {num(v['value'])} is stale; {v['from_claim']} now says {num(v['link']['claim_value'])}")
            if not v.get("src", {}).get("ref"):
                issues.append(f"{cid}: input {v['sym']} has no source")
    return issues


# ---------------------------------------------------------------- sources, mesh audit
def sources(recheck):
    rc = run([PY, VAL / "link_check.py"]) if recheck else 0
    if recheck:
        run([PY, VAL / "proofs.py"], quiet=True)
    pr = load("analysis/validation/proofs.json"); S = pr["sources"]; cnt = {}
    for s in S.values():
        cnt[s["status"]] = cnt.get(s["status"], 0) + 1
    rows = [{"id": k, "status": s["status"], "title": s.get("title"), "url": s.get("url")} for k, s in S.items()]
    return rc, {"counts": cnt, "sources": rows, "link_check": pr.get("link_check")}


def mesh_audit():
    rc = run([PY, CFD / "mesh_audit.py"])
    a = load("analysis/cfd3d/out/mesh_audit.json")
    return rc, {"summary": a["summary"], "scorecard": [{"criterion": r["metric"], "threshold": r["threshold_text"], **{L: (r.get(L) or {}).get("result") for L in ("L1", "L2", "L3", "L4")}} for r in a["scorecard"]]}


# ---------------------------------------------------------------- menu for people who do not use the command line
MENU = [("Open the review website", lambda: do(["open"])),
        ("Check every claim (re-run the arithmetic, show what changed)", lambda: do(["check"])),
        ("Explain one claim step by step", lambda: do(["trace", ask("Claim ID, for example AERO-14: ")])),
        ("Write proof sheets for every claim (docs/validation/proofs/)", lambda: do(["prove", "all"])),
        ("Show the external sources and re-test every link", lambda: do(["sources", "--recheck"] if ask("Re-test all 600+ links? It takes a few minutes. [y/N] ").lower().startswith("y") else ["sources"])),
        ("Score the CFD meshes against published standards", lambda: do(["mesh-audit"])),
        ("Rebuild the review website after a change", lambda: do(["report"])),
        ("Project status", lambda: do(["status"])),
        ("What does each step do? (help)", lambda: print(__doc__))]


def ask(prompt):
    try:
        return input("  " + prompt).strip()
    except EOFError:
        return ""


def do(args):
    subprocess.run([PY, str(Path(__file__).resolve())] + args, cwd=ROOT)


def menu():
    while True:
        print("\n  VTOL engineering tools\n  ----------------------")
        for i, (label, _) in enumerate(MENU, 1):
            print(f"   {i}. {label}")
        print("   0. Quit")
        ch = ask("Choose a number: ")
        if ch in ("0", "q", "quit", "exit", ""):
            return
        if ch.isdigit() and 1 <= int(ch) <= len(MENU):
            print(); MENU[int(ch) - 1][1](); ask("\nPress Enter to return to the menu.")
        else:
            print("  Please type one of the numbers shown.")


# ---------------------------------------------------------------- entry point
def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("menu",):
        menu(); return
    if argv[0] in ("help", "-h", "--help") and len(argv) == 1:
        print(__doc__); return
    ap = argparse.ArgumentParser(prog="vtol", description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "geometry", "validate", "check", "strict", "mesh-audit", "report", "open"):
        sub.add_parser(name)
    m = sub.add_parser("mesh"); m.add_argument("--level", type=int, choices=(1, 2, 3, 4), default=2)
    c = sub.add_parser("cfd"); c.add_argument("action", choices=("run", "summary", "post", "pack", "verify")); c.add_argument("cases", nargs="*")
    c.add_argument("--restart-from"); c.add_argument("--iters", type=int)
    x = sub.add_parser("xtool"); x.add_argument("what", choices=("boom",))
    q = sub.add_parser("claims"); q.add_argument("--component"); q.add_argument("--status"); q.add_argument("--discipline")
    k = sub.add_parser("compare"); k.add_argument("ref")
    t = sub.add_parser("trace"); t.add_argument("claim")
    pv = sub.add_parser("prove"); pv.add_argument("claim", help="claim ID or 'all'")
    so = sub.add_parser("sources"); so.add_argument("--recheck", action="store_true")
    as_json = "--json" in argv            # accepted anywhere on the line, so agents need not know argparse's ordering
    a = ap.parse_args([v for v in argv if v != "--json"]); a.json = as_json
    rc, payload, printed = 0, None, False
    if a.cmd == "status":
        payload = status()
        if not a.json:
            print("\n  Files (last changed):")
            for f, i in payload["files"].items():
                print(f"     {OK if i['exists'] else BAD} {i['modified'] or 'missing':16s}  {f}")
            print("\n  CFD cases: " + (", ".join(f"{n}{'' if c['finished'] else ' (not finished)'}" for n, c in payload["cfd_cases"].items()) or "none"))
            cl = payload["claims"] or {}
            print("  Claims: " + ", ".join(f"{k} {v}" for k, v in cl.items()))
            printed = True
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
    elif a.cmd in ("check", "validate"):
        rc, payload = check()
        if not a.json:
            show_check(payload); printed = True
    elif a.cmd == "trace":
        if a.json:
            c, p, _ = claim_bundle(a.claim); payload = {"claim": c, "proof": p}
        else:
            trace(a.claim); printed = True
    elif a.cmd == "prove":
        files = prove(a.claim); payload = {"written": files}
        if not a.json:
            print(f"  Wrote {len(files)} proof sheet(s)" + (f": {files[0]}" if len(files) == 1 else f" to {SHEETS.relative_to(ROOT)} (index: README.md)")); printed = True
    elif a.cmd == "strict":
        issues = strict(); payload = {"issues": issues}; rc = 1 if issues else 0
        if not a.json:
            print(f"  {OK} No blocking problems." if not issues else f"  {BAD} {len(issues)} problem(s):\n" + "\n".join("     " + i for i in issues)); printed = True
    elif a.cmd == "sources":
        rc, payload = sources(a.recheck)
        if not a.json:
            print("  External sources behind the claims: " + ", ".join(f"{k} {v}" for k, v in payload["counts"].items()))
            for s in payload["sources"]:
                print(f"     {s['id']}  [{s['status']}]  {(s['title'] or '')[:70]}")
            lc = payload["link_check"]
            if lc:
                print(f"  Every URL in the docs: {lc['ok']} of {lc['n']} load, {lc['dead']} dead, {lc['blocked']} block automated checks.")
                for u in lc.get("dead_urls", []):
                    print(f"     dead: {u}")
            printed = True
    elif a.cmd == "mesh-audit":
        rc, payload = mesh_audit()
        if not a.json:
            s = payload["summary"]; print(f"\n  Mesh scorecard: {s['passes']} pass, {s['fails']} fail, {s['not_applicable']} do not apply.\n  {s['verdict']}\n")
            for r in payload["scorecard"]:
                print(f"     {r['criterion']:34s} {r['threshold']:22s} L1 {r['L1'] or '-':5s} L2 {r['L2'] or '-':5s} L3 {r['L3'] or '-':5s} L4 {r['L4'] or '-'}")
            printed = True
    elif a.cmd == "xtool":
        rc = run([PY, VAL / "xtool_boom_fea.py"])
        payload = load("analysis/validation/xtool_boom_fea.json")["comparison"] if rc == 0 else None
    elif a.cmd == "claims":
        vm = load("analysis/validation/validation_matrix.json")
        payload = [{k: c.get(k) for k in ("id", "component", "discipline", "claim", "status", "status_reason", "next_step")} for c in vm["claims"]
                   if (not a.component or c["component"] == a.component) and (not a.status or c["status"] == a.status) and (not a.discipline or c["discipline"] == a.discipline)]
        if not a.json:
            for r in payload:
                print(f"  {r['id']:8s} [{r['status']}] {r['claim']}")
            printed = True
    elif a.cmd == "compare":
        payload = compare(a.ref)
    elif a.cmd == "report":
        rc = run(["node", ROOT / "review" / "build.mjs"])
        if rc == 0 and not a.json:
            print(f"  {OK} Website rebuilt: VTOL-Review.html (open it with `py tools/vtol.py open`)")
    elif a.cmd == "open":
        f = ROOT / "VTOL-Review.html"; webbrowser.open(f.as_uri()); print(f"  Opened {f.name} in your browser.")
    if payload is not None and (a.json or not printed):
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
