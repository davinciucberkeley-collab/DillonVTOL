"""Places the step figures in the build manual and the test plan (idempotent: a figure already referenced is skipped).

Build manual: docs/build/img/b_<step>.svg (Blender step render) and wire_<step>.svg (wiring highlight) go at the end
of their step; a step with more than one figure labels them <step>a, <step>b ... in order.
Test plan: docs/test/figures/t_<id>.svg goes at the end of its test section; the flight diagrams f<nn>_*.svg get a
short heading each under the flight-test table, so the one-test-at-a-time reader covers the flight series too.
Usage: python docs/figures/place_figures.py
"""
import glob, io, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(path):
    s = io.open(path, encoding='utf-8', newline='').read(); nl = '\r\n' if '\r\n' in s else '\n'
    return s.split(nl), nl


def save(path, L, nl):
    io.open(path, 'w', encoding='utf-8', newline='').write(nl.join(L))


# ------------------------------------------------------------ build manual
def manual():
    p = os.path.join(ROOT, 'docs/build/BUILD-MANUAL.md'); L, nl = load(p)
    import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from make_figures import WIRE_STEPS
    text = nl.join(L)
    new = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'docs/build/img/b_*.svg'))) + sorted(glob.glob(os.path.join(ROOT, 'docs/build/img/wire_*.svg'))):
        base = os.path.basename(f)
        if f'img/{base})' in text: continue
        step = base.split('_', 1)[1][:-4].replace('_', '.')
        new.setdefault(step, []).append(base)
    added = 0
    def step_line(no):
        for i, l in enumerate(L):
            if re.match(r'\*\*' + re.escape(no) + r' ', l): return i
        return None
    for no in sorted(new, key=lambda n: -(step_line(n) or -1)):
        i = step_line(no)
        if i is None: print('no step', no); continue
        title = re.match(r'\*\*' + re.escape(no) + r' (.+?)\*\*', L[i]).group(1).rstrip('.')
        title = re.sub(r'\s*\((?:J\d|FT|C\d|sheet|review|hardware|thermal|`).*?\)', '', title).strip()
        j = i + 1
        while j < len(L) and not re.match(r'(\*\*\d|\*\*WP|#|---)', L[j]): j += 1
        while L[j - 1].strip() == '': j -= 1
        figs = [k for k in range(i + 1, j) if L[k].startswith('![**Figure ')]
        items = []
        for base in sorted(new[no], key=lambda b: (not b.startswith('b_'), b)):
            cap = (title + ': render from the CAD model (tools and shop items illustrative)') if base.startswith('b_') else ('Circuits for this step highlighted; ' + WIRE_STEPS.get(no, (None, ''))[1])
            items.append(['', f'![**Figure {no}.** {cap}.](img/{base})'])
        L[j:j] = [x for it in items for x in it]
        # relabel every figure of the step in order when there is more than one
        j2 = j + sum(len(it) for it in items); all_figs = [k for k in range(i + 1, j2) if L[k].startswith('![**Figure ')]
        if len(all_figs) > 1:
            for n, k in enumerate(all_figs):
                L[k] = re.sub(r'^!\[\*\*Figure [^*]+\.\*\*', f'![**Figure {no}{"abcdefgh"[n]}.**', L[k])
        added += len(items)
    save(p, L, nl); print('build manual: figures added', added)


# ------------------------------------------------------------ test plan
FLIGHT = [('f01_hops.svg', 'F01'), ('f02_hover_learn.svg', 'F02'), ('f03_loiter.svg', 'F03'), ('f04_low_speed_box.svg', 'F04'), ('f05_hover_failsafes.svg', 'F05'),
          ('f06_partial_transitions.svg', 'F06'), ('f07_transition_circuit.svg', 'F07'), ('f08_airspeed_legs.svg', 'F08'), ('f13_fairing_ab.svg', 'F13'),
          ('f10_fw_failsafes.svg', 'F10'), ('f11_rehearsal.svg', 'F11'), ('f12_full_mission.svg', 'F12')]
SECTION_EXTRA = {'E02': 'e02_motor_order.svg', 'E03': 'e03_servo_throws.svg', 'E04': 'e04_range_walk.svg', 'E05': 'e05_failsafes.svg', 'E07': 'e07_compass_cal.svg', 'G08': 'g08_field_layout.svg'}


def test_plan():
    p = os.path.join(ROOT, 'docs/test/TEST-PLAN.md'); L, nl = load(p); text = nl.join(L); added = 0
    rows = {}
    for l in L:
        m = re.match(r'\| (F\d\d) \| ([^|]+) \|', l)
        if m: rows[m.group(1)] = re.sub(r'\s*\((?:new|review|FTC)[^)]*\)', '', m.group(2)).strip()
    def section_end(tid):
        i = next((k for k, l in enumerate(L) if l.startswith('#### ' + tid + ' ')), None)
        if i is None: return None, None
        j = i + 1
        while j < len(L) and not L[j].startswith('#'): j += 1
        while L[j - 1].strip() == '': j -= 1
        return i, j
    todo = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'docs/test/figures/t_*.svg'))):
        base = os.path.basename(f); tid = base[2:-4].upper()
        if f'figures/{base})' not in text: todo.append((tid, base))
    for tid, base in SECTION_EXTRA.items():
        if os.path.exists(os.path.join(ROOT, 'docs/test/figures', base)) and f'figures/{base})' not in text: todo.append((tid, base))
    for tid, base in sorted(todo, key=lambda t: -(section_end(t[0])[0] or -1)):
        i, j = section_end(tid)
        if i is None: print('no section', tid); continue
        title = re.sub(r'^#### \S+ [—–-] ', '', L[i]); title = re.sub(r'\s*\((?:review|new|hardware|§|M\[).*?\)', '', title).strip()
        kind = 'set-up rendered from the CAD model (test gear illustrative)' if base.startswith('t_') else 'diagram'
        L[j:j] = ['', f'![**Figure {tid}.** {title}: {kind}.](figures/{base})']; added += 1
        figs = [k for k in range(i + 1, j + 2) if L[k].startswith('![**Figure ')]
        if len(figs) > 1:
            for n, k in enumerate(figs): L[k] = re.sub(r'^!\[\*\*Figure [^*]+\.\*\*', f'![**Figure {tid}{"abcdefgh"[n]}.**', L[k])
    # flight diagrams: a heading per flight under the table (after the stall profile figure)
    k = next(i for i, l in enumerate(L) if l.startswith('### 9.5 Series F'))
    end = next((i for i in range(k + 1, len(L)) if L[i].startswith('### ') or L[i].startswith('## ')), len(L))
    block = []
    for base, fid in FLIGHT:
        if not os.path.exists(os.path.join(ROOT, 'docs/test/figures', base)) or f'figures/{base})' in nl.join(L): continue
        block += ['', f'#### {fid} — {rows.get(fid, fid)}', '', f'See the {fid} row in the table above and its card in docs/test/cards/ for the full procedure.', '',
                  f'![**Figure {fid}.** {rows.get(fid, fid)}: plan view and profile.](figures/{base})']
    if block:
        while L[end - 1].strip() == '': end -= 1
        L[end:end] = block; added += len(FLIGHT)
    save(p, L, nl); print('test plan: figures added', added)


if __name__ == '__main__':
    manual(); test_plan()
