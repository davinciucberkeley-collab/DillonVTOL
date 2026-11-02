"""One-off restructure of review/src/body.html: 22 chapters -> 11, three or four tabs each (2026-11-01).

Each new chapter keeps the id of its first old chapter. Every other old chapter becomes a sub-heading (h4) carrying
its old id, and every old tab heading (h3) becomes an h4 with its old id. Old deep links (#mass, #cg, #aero/ae-cfd3d)
still resolve, because the router finds any element by id and opens the tab that contains it. A tab built from a
single old tab keeps that tab's id. Content is moved, not rewritten.

Usage: py review/tools/restructure.py      (run once; it refuses to run on an already-restructured file)
"""
import re
from pathlib import Path

F = Path(__file__).resolve().parents[1] / "src" / "body.html"
src = F.read_text(encoding="utf-8")
if 'data-restructured="1"' in src:
    raise SystemExit("body.html is already restructured")

# ---- parse: chapters -> head, lead (before first h3), [ (h3 id, h3 title, body) ] ----
SEC = re.compile(r'<section class="sec" id="([^"]+)"([^>]*)>(.*?)</section>\n?', re.S)
chapters, order = {}, []
for m in SEC.finditer(src):
    sid, attrs, inner = m.group(1), m.group(2), m.group(3)
    head = re.search(r'\s*<div class="sechead">.*?</div>', inner, re.S)
    rest = inner[head.end():]
    parts = re.split(r'(?=\n[ \t]*<h3 id=")', rest)
    lead, tabs = parts[0], []
    for p in parts[1:]:
        h = re.match(r'\n([ \t]*)<h3 id="([^"]+)">(.*?)</h3>', p, re.S)
        tabs.append((h.group(2), h.group(3), p[h.end():]))
    title = re.search(r'data-title="([^"]+)"', attrs).group(1)
    chapters[sid] = {"attrs": attrs, "title": title, "lead": lead, "tabs": dict((t[0], t) for t in tabs)}
    order.append(sid)
first, last = src.find('<section class="sec"'), src.rfind("</section>") + len("</section>\n")

# ---- the new structure: (id, title, group, [ (tab title, [pieces]) ]) ; piece = h3 id, or ("lead", chapter id) ----
NEW = [
    ("docinfo", None, None, None),
    ("overview", "Overview", "home", [("Start here", ["ov-start"]), ("Status", ["ov-margins", "ov-lanes", "ov-change"])]),
    ("requirements", "Requirements", "home", [("Requirements", ["ov-reqs", "req-ready"]), ("Open items", ["ov-decisions", "ov-measure"])]),
    ("model3d", "CAD and drawings", "design", [("3-D model", ["m3-cad"]), ("Drawings", [("lead", "drawings"), "m3-drw"]),
                                               ("Parts and fits", ["m3-hw", "m3-parts", "m3-transport", "vm-mfg"])]),
    ("aero", "Aerodynamics", "design", [("Drag and stall", ["ae-drag", "ae-polar"]), ("2-D CFD", ["ae-cfd", "ae-flow"]), ("3-D CFD", ["ae-cfd3d"]),
                                        ("Stability", ["ae-stab", ("lead", "cg"), "cg-items", "cg-stab"])]),
    ("structures", "Structures and heat", "design", [("Loads", ["s-loads", "s-land"]), ("Spar, booms, joints", ["s-spar", "s-boom", "s-joints"]),
                                                     ("FEA and heat", [("lead", "simulation"), "sim-table", "sim-3d", "sim-heat"])]),
    ("mass", "Mass and power", "design", [("Mass", ["mp-roll", "mp-chain", "mp-sens"]), ("Propulsion", [("lead", "propulsion"), "p-lift", "p-batt", "p-current", "mp-calib"])]),
    ("validation", "Proof and validation", "verify", [("Claims map", ["vm-map"]), ("All claims", ["vm-table"]),
                                                     ("Benchmarks", [("lead", "benchmarks"), "bm-speed", "bm-aircraft", "bm-lit", "bm-decisions"])]),
    ("testing", "Testing", "verify", [("Ground tests", ["t-stand", "t-duty", "t-motorout"]), ("Flight tests", [("lead", "flighttest"), "ft-matrix", "ft-ops"]),
                                      ("Risks", ["t-weak", "t-fmea", "ft-risk"])]),
    ("budget", "Budget and schedule", "program", [("Budget", ["b-cap", "b-side", "b-bom", "b-risk"]), ("Schedule", [("lead", "schedule"), "sch-order", "sch-comp"]),
                                                  ("Design history", [("lead", "iterations"), "it-findings", "it-criteria", "c-dropped", "c-morph", "c-pugh"])]),
    ("build", "Build and software", "build", [("Build", ["bd-wp", "ft-fab"]), ("Flight software", [("lead", "controls"), "ctl-fc", "ctl-state", "ctl-trans", "ctl-pins", "ctl-sitl"])]),
    ("sources", "Sources and files", "doc", [("Sources", ["src-key", "src-all"]), ("Files", [("lead", "downloads"), "dl-files"]), ("Glossary", ["ov-terms"])]),
]

where = {tid: sid for sid, c in chapters.items() for tid in c["tabs"]}
used_tabs, used_secs = set(), set()
slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def piece_html(p):
    if isinstance(p, tuple):
        sid = p[1]; used_secs.add(sid); c = chapters[sid]
        return f'\n  <h4 id="{sid}">{c["title"]}</h4>' + c["lead"].rstrip() + "\n"
    sid = where[p]; used_tabs.add(p); tid, title, body = chapters[sid]["tabs"][p]
    return f'\n  <h4 id="{tid}">{title}</h4>' + body.rstrip() + "\n"


out = []
for sid, title, group, tabs in NEW:
    c = chapters[sid]; used_secs.add(sid)
    if tabs is None:
        out.append(f'<section class="sec" id="{sid}"{c["attrs"]}>' + src[src.find(f'id="{sid}"'):].split(">", 1)[1].split("</section>", 1)[0] + "</section>\n")
        continue
    attrs = f' data-title="{title}" data-group="{group}" data-n="0" data-tabs="1"'
    html = f'<section class="sec" id="{sid}"{attrs}>\n  <div class="sechead"><h2><span class="secno">0</span> {title}</h2></div>' + c["lead"].rstrip() + "\n"
    for ttitle, pieces in tabs:
        if len(pieces) == 1 and not isinstance(pieces[0], tuple):          # one old tab: keep its id, take the new title
            p = pieces[0]; s2 = where[p]; used_tabs.add(p); tid, _, body = chapters[s2]["tabs"][p]
            html += f'\n  <h3 id="{tid}">{ttitle}</h3>' + body.rstrip() + "\n"
        else:
            html += f'\n  <h3 id="{sid}-{slug(ttitle)}">{ttitle}</h3>' + "".join(piece_html(p) for p in pieces)
    out.append(html + "</section>\n")

missing_t = sorted(set(where) - used_tabs); missing_s = sorted(set(order) - used_secs)
if missing_t or missing_s:
    raise SystemExit(f"not placed: tabs {missing_t} chapters {missing_s}")
new = src[:first] + "\n".join(out) + src[last:]
new = new.replace("<body", '<body data-restructured="1"', 1) if "<body" in new else new.replace("<section", '<!-- data-restructured="1" -->\n<section', 1)
F.write_text(new, encoding="utf-8", newline="\n")
print("chapters", len(NEW), "tabs", sum(len(t) for _, _, _, t in NEW if t))
