"""Flight-test and bench-test diagrams for the C0 test plan (SVG, generated so the numbers stay in step with the sources).

Writes docs/test/figures/f01_hops.svg ... f12_full_mission.svg, g08_field_layout.svg and e02-e07 diagrams.
Every number on a sheet comes from docs/test/cards/FTC-*.md, docs/test/test-matrix.csv (the "Pass:" lines are read
from its "Pass criterion" column), docs/test/TEST-PLAN.md, firmware/vtol_c0.param (read below), firmware/README.md,
analysis/results.json or cad/params.txt (read below). Values the sources do not give are drawn without a number
or marked "—". Cruise legs are drawn at the cruise speed AIRSPEED_CRUISE (18 m/s, = results.json C0 params.Vc).

Style and helpers come from make_figures.py (Svg, palette, FONT, legend): white sheet, dark line work, orange = the
aircraft and the path under test, blue = instruments, measurements and wind, grey = ground and fixtures, red = limits.

Usage: python docs/figures/flight_diagrams.py      (from the repository root)
"""
import json, csv, math, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_figures import Svg, INK, MUTED, LINE, GROUND, ORANGE, BLUE, PAPER, FONT, legend, ROOT, TEST_OUT, C0  # noqa: E402

RED = '#ad2a1f'                       # limit lines (as in stall_profile.svg)
OL, BL, GL = '#fbeadb', '#e6eefb', '#eef1f4'   # light orange / blue / grey fills
W, MG = 780, 24                       # sheet width, text margin

# ------------------------------------------------------------------ sources
PARAM = {}
for ln in open(os.path.join(ROOT, 'firmware/vtol_c0.param'), encoding='utf-8'):
    m = re.match(r'([A-Z0-9_]+),([-\d.]+)', ln)
    if m:
        PARAM[m.group(1)] = float(m.group(2))
P = lambda k: f'{PARAM[k]:g}'
VC = PARAM['AIRSPEED_CRUISE']                         # 18 m/s
assert VC == C0['params']['Vc'], 'AIRSPEED_CRUISE and results.json Vc disagree'
STOP = VC ** 2 / (2 * PARAM['Q_TRANS_DECEL'])          # back-transition stop distance, v^2 / 2a (vtol_c0.param comment)
CRUISE = f'cruise ({VC:g} m/s)'

MATRIX = {r['ID']: r for r in csv.DictReader(open(os.path.join(ROOT, 'docs/test/test-matrix.csv'), encoding='utf-8'))}

CAD = {}
for ln in open(os.path.join(ROOT, 'cad/params.txt'), encoding='utf-8'):
    m = re.match(r'([A-Za-z0-9_]+)=([-\d.]+)$', ln.strip())
    if m:
        CAD[m.group(1)] = float(m.group(2))
COMP = {}
for ln in open(os.path.join(ROOT, 'cad/params.txt'), encoding='utf-8'):
    if ln.startswith('comp='):
        f = ln[5:].split('|')
        COMP.setdefault(f[0], []).append((float(f[1]), float(f[2]), float(f[3])))


def typo(t):
    """typeset a source string without changing its words"""
    for a, b in (('>=', '≥'), ('<=', '≤'), ('+-', '±'), (' degC', ' °C'), (' deg', '°'), (' -> ', ' → '), ('m/s2', 'm/s²')):
        t = t.replace(a, b)
    return t


def pass_line(tid):
    return 'Pass (test-matrix.csv): ' + typo(MATRIX[tid]['Pass criterion'])


# ------------------------------------------------------------------ text metrics and the sheet class
def tw(t, size):
    w = 0
    for ch in t:
        if ch in 'iljtfI1.,:;!|()[]\'" ':
            w += 0.30
        elif ch in 'mwMW%':
            w += 0.86
        elif ch.isupper() or ch.isdigit() or ch in '≤≥±→°×–—':
            w += 0.62
        else:
            w += 0.53
    return w * size


def wrap(t, width, size):
    out, cur = [], ''
    for word in t.split(' '):
        test = (cur + ' ' + word).strip()
        if tw(test, size) <= width or not cur:
            cur = test
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    return out


MARK = {INK: 'arr', BLUE: 'arrB', ORANGE: 'arrO', MUTED: 'arrM', LINE: 'arrM', RED: 'arrR'}


class D(Svg):
    """make_figures.Svg plus coloured arrowheads of one fixed size, dashed circles and a text-collision check"""

    def __init__(self, w, h, title):
        super().__init__(w, h, title)
        self.boxes = []

    def text(self, x, y, s, size=13, c=INK, anchor='start', weight=400, check=True):
        w = tw(s, size) * (1.05 if weight >= 600 else 1.0)
        x0 = x if anchor == 'start' else x - w / 2 if anchor == 'middle' else x - w
        if check:
            self.boxes.append((x0, y - size * 0.76, x0 + w, y + size * 0.22, s))
        super().text(x, y, s, size, c, anchor, weight)

    def vtext(self, x, y, s, size=13, c=MUTED):
        s = s.replace('&', '&amp;')
        self.add(f"<text transform='rotate(-90 {x:.1f} {y:.1f})' x='{x:.1f}' y='{y:.1f}' {FONT} font-size='{size}' "
                 f"fill='{c}' text-anchor='middle'>{s}</text>")

    def line(self, x1, y1, x2, y2, c=INK, w=2, dash=None, arrow=False, start=False):
        d = f" stroke-dasharray='{dash}'" if dash else ''
        mk = MARK.get(c, 'arr')
        m = (f" marker-end='url(#{mk})'" if arrow else '') + (f" marker-start='url(#{mk})'" if start else '')
        self.add(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{c}' stroke-width='{w}'{d}{m}/>")

    def circ(self, x, y, r, fill='none', c=INK, sw=1.5, dash=None):
        d = f" stroke-dasharray='{dash}'" if dash else ''
        self.add(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r:.1f}' fill='{fill}' stroke='{c}' stroke-width='{sw}'{d}/>")

    def apath(self, d, c=ORANGE, sw=2.5, dash=None, arrow=False, fill='none'):
        dd = f" stroke-dasharray='{dash}'" if dash else ''
        m = f" marker-end='url(#{MARK.get(c, 'arr')})'" if arrow else ''
        self.add(f"<path d='{d}' fill='{fill}' stroke='{c}' stroke-width='{sw}'{dd}{m} stroke-linejoin='round' stroke-linecap='round'/>")

    def para(self, x, y, t, width, size=13, c=MUTED, lh=None, weight=400, anchor='start'):
        lh = lh or size + 5
        lines = wrap(t, width, size)
        for i, l in enumerate(lines):
            self.text(x, y + i * lh, l, size, c, anchor, weight)
        return y + len(lines) * lh

    def save(self, path):
        mk = ''.join(f"<marker id='{i}' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='userSpaceOnUse' markerWidth='10' "
                     f"markerHeight='10' orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' fill='{c}'/></marker>"
                     for c, i in ((INK, 'arr'), (BLUE, 'arrB'), (ORANGE, 'arrO'), (MUTED, 'arrM'), (RED, 'arrR')))
        head = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' width='{self.w}' height='{self.h}' role='img'>"
                f"<title>{self.title}</title><defs>{mk}</defs><rect width='100%' height='100%' fill='{PAPER}'/>")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(head + ''.join(self.parts) + '</svg>\n')
        bad = 0
        for i, a in enumerate(self.boxes):
            if a[0] < MG - 1 or a[2] > self.w - MG + 1 or a[1] < 4 or a[3] > self.h - 4:
                print(f'   OUTSIDE MARGIN: {a[4]!r}'); bad += 1
            for b in self.boxes[i + 1:]:
                if a[0] < b[2] - 1 and b[0] < a[2] - 1 and a[1] < b[3] - 1 and b[1] < a[3] - 1:
                    print(f'   OVERLAP: {a[4]!r} / {b[4]!r}'); bad += 1
        print('wrote', os.path.relpath(path, ROOT), '' if not bad else f'({bad} text warnings)')


# ------------------------------------------------------------------ drawing helpers
def header(s, tid, title, proc):
    s.text(MG, 30, f'{tid} · {title}', 15, INK, weight=600)
    return s.para(MG, 52, proc, W - 2 * MG, 13, MUTED) + 4


def footer(s, y, tid, extra=None):
    s.line(MG, y, W - MG, y, c=GROUND, w=1)
    y = s.para(MG, y + 20, pass_line(tid), W - 2 * MG, 13, INK)
    if extra:
        y = s.para(MG, y + 2, extra, W - 2 * MG, 12, MUTED, lh=16)
    s.h = int(y + 10)
    return y


def panel(s, x, y, w, h, title=None):
    s.rect(x, y, w, h, fill='none', c=GROUND, sw=1, rx=4)
    if title:
        s.text(x + 12, y + 20, title, 13, INK, weight=600)


def num(s, x, y, n, c=ORANGE):
    s.circ(x, y, 9.5, fill=PAPER, c=c, sw=2)
    s.text(x, y + 4, str(n), 11, INK, 'middle', 700, check=False)


def pill(s, x, y, t, c=INK, fill=PAPER, size=12):
    w = tw(t, size) * 1.05 + 14
    s.rect(x - w / 2, y - 9.5, w, 19, fill=fill, c=c, sw=1.2, rx=9.5)
    s.text(x, y + 4, t, size, c, 'middle', 600)
    return w


def wind(s, x, y, lines, L=44):
    s.line(x, y, x, y + L, c=BLUE, w=2.5, arrow=True)
    for i, t in enumerate(lines):
        s.text(x + 12, y + 12 + i * 16, t, 12, BLUE)


def scalebar(s, x, y, ppm, L, steps=4, label='m'):
    seg = L / steps * ppm
    for i in range(steps):
        s.rect(x + i * seg, y, seg, 5, fill=INK if i % 2 == 0 else PAPER, c=INK, sw=1, rx=0)
    for v in (0, L / 2, L):
        t = f'{v:g}' + (f' {label}' if v == L else '')
        s.text(x + v * ppm, y + 19, t, 11, MUTED, 'middle')


def dim_v(s, x, y1, y2, label, side='left', c=MUTED, size=12):
    s.line(x, y1, x, y2, c=c, w=1, arrow=True, start=True)
    ym = (y1 + y2) / 2 + 4
    s.text(x - 6 if side == 'left' else x + 6, ym, label, size, c, 'end' if side == 'left' else 'start')


def dim_h(s, x1, x2, y, label, c=MUTED, size=12, above=True):
    s.line(x1, y, x2, y, c=c, w=1, arrow=True, start=True)
    s.text((x1 + x2) / 2, y - 6 if above else y + 15, label, size, c, 'middle')


def chevron(s, x, y, ang, c=ORANGE, sz=6):
    ca, sa = math.cos(ang), math.sin(ang)
    p = [(x + sz * ca, y + sz * sa), (x - sz * ca - sz * 0.8 * sa, y - sz * sa + sz * 0.8 * ca),
         (x - sz * ca + sz * 0.8 * sa, y - sz * sa - sz * 0.8 * ca)]
    s.add(f"<path d='M{p[0][0]:.1f} {p[0][1]:.1f} L{p[1][0]:.1f} {p[1][1]:.1f} L{p[2][0]:.1f} {p[2][1]:.1f} Z' fill='{c}'/>")


def rounded(pts, r=14):
    """polyline with rounded corners (fixed-wing turns)"""
    d = f'M{pts[0][0]:.1f} {pts[0][1]:.1f}'
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = math.hypot(x1 - x0, y1 - y0), math.hypot(x2 - x1, y2 - y1)
        rr = min(r, l1 / 2, l2 / 2)
        a = (x1 - (x1 - x0) / l1 * rr, y1 - (y1 - y0) / l1 * rr)
        b = (x1 + (x2 - x1) / l2 * rr, y1 + (y2 - y1) / l2 * rr)
        d += f' L{a[0]:.1f} {a[1]:.1f} Q{x1:.1f} {y1:.1f} {b[0]:.1f} {b[1]:.1f}'
    d += f' L{pts[-1][0]:.1f} {pts[-1][1]:.1f}'
    return d


def chevrons_on(s, pts, c=ORANGE, minlen=50):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if math.hypot(x2 - x1, y2 - y1) >= minlen:
            chevron(s, (x1 + x2) / 2, (y1 + y2) / 2, math.atan2(y2 - y1, x2 - x1), c)


def pad(s, x, y, half=7, label=True):
    s.rect(x - half, y - half, 2 * half, 2 * half, fill=GL, c=INK, sw=1.5, rx=1)
    s.line(x - half * 0.55, y, x + half * 0.55, y, c=INK, w=1)
    s.line(x, y - half * 0.55, x, y + half * 0.55, c=INK, w=1)


def kit(s, x, y):
    """fire bag + extinguisher + first aid marker (red cross)"""
    s.rect(x - 8, y - 8, 16, 16, fill=PAPER, c=RED, sw=1.5, rx=2)
    s.rect(x - 1.8, y - 5.5, 3.6, 11, fill=RED, c=RED, sw=0, rx=0)
    s.rect(x - 5.5, y - 1.8, 11, 3.6, fill=RED, c=RED, sw=0, rx=0)


def plane_icon(s, x, y, sc=1.0, ang=0.0, c=ORANGE, fill=None):
    """small top-view C0 silhouette (nose toward ang; 0 = up the sheet)"""
    pts = [(0, -16), (3, -10), (3, -2), (24, -2), (24, 3), (3, 3), (3, 10), (9, 13), (9, 16), (-9, 16), (-9, 13),
           (-3, 10), (-3, 3), (-24, 3), (-24, -2), (-3, -2), (-3, -10)]
    ca, sa = math.cos(ang), math.sin(ang)
    q = [(x + sc * (px * ca - py * sa), y + sc * (px * sa + py * ca)) for px, py in pts]
    s.path('M' + ' L'.join(f'{a:.1f} {b:.1f}' for a, b in q) + ' Z', fill=fill or c, c=c, sw=1)


class Chart:
    def __init__(self, s, x, y, w, h, xr, yr):
        self.s, self.x, self.y, self.w, self.h = s, x, y, w, h
        self.x0, self.x1 = xr
        self.y0, self.y1 = yr

    def X(self, v):
        return self.x + self.w * (v - self.x0) / (self.x1 - self.x0)

    def Y(self, v):
        return self.y + self.h - self.h * (v - self.y0) / (self.y1 - self.y0)

    def axes(self, xticks, yticks, xlabel, ylabel, xfmt=lambda v: f'{v:g}', yfmt=lambda v: f'{v:g}', grid=True, ylx=None):
        s = self.s
        for v in yticks:
            if grid:
                s.line(self.x, self.Y(v), self.x + self.w, self.Y(v), c=GROUND, w=1)
            s.text(self.x - 7, self.Y(v) + 4, yfmt(v), 12, MUTED, 'end')
        for v in xticks:
            s.line(self.X(v), self.y + self.h, self.X(v), self.y + self.h + 5, c=INK, w=1)
            s.text(self.X(v), self.y + self.h + 19, xfmt(v), 12, MUTED, 'middle')
        s.line(self.x, self.y, self.x, self.y + self.h, c=INK, w=1.5)
        s.line(self.x, self.y + self.h, self.x + self.w, self.y + self.h, c=INK, w=1.5)
        if xlabel:
            s.text(self.x + self.w / 2, self.y + self.h + 38, xlabel, 13, MUTED, 'middle')
        if ylabel:
            s.vtext(ylx if ylx is not None else self.x - 40, self.y + self.h / 2, ylabel, 13)

    def poly(self, pts, c=ORANGE, w=3, dash=None):
        self.s.apath(' '.join(('M' if i == 0 else 'L') + f'{self.X(a):.1f} {self.Y(b):.1f}' for i, (a, b) in enumerate(pts)),
                     c=c, sw=w, dash=dash)

    def hline(self, v, label, c=RED, dash='6 4', side='right', dy=-6, lx=None):
        s = self.s
        s.line(self.x, self.Y(v), self.x + self.w, self.Y(v), c=c, w=1.5, dash=dash)
        if label:
            if lx is not None:
                s.text(lx, self.Y(v) + dy, label, 12, c, 'start')
            elif side == 'right':
                s.text(self.x + self.w - 4, self.Y(v) + dy, label, 12, c, 'end')
            else:
                s.text(self.x + 6, self.Y(v) + dy, label, 12, c, 'start')

    def brk(self, xv):
        """axis break mark on the time axis"""
        s, X, yb = self.s, self.X(xv), self.y + self.h
        s.rect(X - 5, yb - 6, 10, 12, fill=PAPER, c=PAPER, sw=0, rx=0)
        s.line(X - 7, yb + 6, X - 1, yb - 6, c=INK, w=1.2)
        s.line(X + 1, yb + 6, X + 7, yb - 6, c=INK, w=1.2)


# ------------------------------------------------------------------ hover-site plan (F01-F05)
PPM_H = 5.0      # px per metre on hover plans


def hover_plan(s, x, y, w, h, title='Plan view', wind_txt=None, drift=None, touch=None, extra_circles=()):
    """pad, 20 m clear radius, crew line 30 m upwind (TEST-PLAN.md §7; card 'Range' line); returns pad centre"""
    panel(s, x, y, w, h, title)
    px, py = x + w / 2 + 20, y + h - 20 * PPM_H - 34
    s.circ(px, py, 20 * PPM_H, c=LINE, sw=1, dash='5 4')
    s.text(px, py + 20 * PPM_H + 17, 'clear 20 m radius', 12, MUTED, 'middle')
    yc = py - 30 * PPM_H
    s.line(x + 64, yc, x + w - 16, yc, c=INK, w=1.5, dash='8 5')
    s.text(x + w - 16, yc + 24, 'crew line', 12, INK, 'end')
    s.text(px - 30, yc - 22, 'spectators behind the crew line', 12, MUTED, 'middle')
    for i, r in enumerate(['TD', 'SO / VO', 'PIC', 'GCS']):
        pill(s, px - 120 + i * 68, yc, r)
    kit(s, px + 150, yc)
    dim_v(s, x + 16, py, yc, '30 m', 'right')
    s.line(x + 10, py, px - 12, py, c=LINE, w=1, dash='2 3')
    for rr, lab, col in extra_circles:
        s.circ(px, py, rr * PPM_H, c=col, sw=1.5, dash='4 3')
    pad(s, px, py, 1.5 * PPM_H)
    if wind_txt:
        s.line(x + w - 24, y + 14, x + w - 24, y + 56, c=BLUE, w=2.5, arrow=True)
        s.text(x + w - 34, y + 20, 'wind', 12, BLUE, 'end', 600)
        for i, t in enumerate(wind_txt):
            s.text(x + w - 34, y + 36 + i * 15, t, 12, BLUE, 'end')
    scalebar(s, x + 18, y + h - 28, PPM_H, 10)
    return px, py


def crew_note(s, x, y, width):
    y = s.para(x, y, 'Crew (card): TD test director, SO safety officer and visual observer, PIC pilot, GCS ground station '
               '(TEST-PLAN.md §3).', width, 12, MUTED, lh=16)
    s.text(x, y + 2, '', 12)
    kit(s, x + 8, y + 8)
    return s.para(x + 22, y + 12, 'fire bag, extinguisher and first aid at the crew line', width - 22, 12, MUTED, lh=16)


# ================================================================== F01
def f01():
    s = D(W, 900, 'F01 first lift-off: QSTABILIZE hops to 0.5 m and 1 m over the pad, crew line 30 m upwind (card FTC-F01)')
    y = header(s, 'F01', 'First lift-off and QSTABILIZE hops',
               'QSTABILIZE, props on, no tether, 0.5 kg ballast. Arm and disarm; lift until the gear goes light; '
               '0.5 m for 5 s; 1 m for 10 s; ± 5° roll and pitch inputs at 1 m. Cool motors below 45 °C between points.')
    px, py = hover_plan(s, MG, y, 500, 400, wind_txt=['steady ≤ 3 m/s EST', 'gusts ≤ 5 m/s EST'],
                        extra_circles=[(3, 'drift', RED)])
    s.label(px + 3 * PPM_H * 0.7, py - 3 * PPM_H * 0.7, 'abort: drift > 3 m', px + 110, py - 24, anchor='start')
    s.label(px - 7, py + 7, 'pad 3 × 3 m (home)', px - 108, py + 24, anchor='end')
    # right column
    cx = MG + 516
    s.text(cx, y + 20, 'Hover limits on this aircraft', 13, INK, weight=600)
    yy = s.para(cx, y + 40, 'Hover-only flights ≤ 5 m AGL and ≤ 60 s per hover; total hover time this flight ≤ 60 s. '
                'C0 cannot survive a lift-motor failure in hover (R14).', W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'Abort (card)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'Any oscillation at lift-off: throttle down at once. Attitude error > 15°; drift > 3 m '
                'from the pad; lift output > 70 % to hold 1 m (expected ~52 %).', W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'Predicted (card)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'Hover throttle ~0.52 = 1,638 g / 3,130 g; hover current 41.2 A at 22.2 V.', W - MG - cx, 12, MUTED, lh=16)
    crew_note(s, cx, yy + 12, W - MG - cx)
    # profile
    y0 = y + 420
    panel(s, MG, y0, W - 2 * MG, 300, 'Height above the pad, by build-up point')
    ch = Chart(s, MG + 70, y0 + 46, W - 2 * MG - 100, 170, (0, 62), (0, 1.5))
    ch.axes([], [0, 0.5, 1.0, 1.5], None, 'height AGL, m', yfmt=lambda v: f'{v:.1f}')
    prof = [(0, 0), (12, 0), (13.5, 0.5), (18.5, 0.5), (20, 0), (26, 0), (27.5, 1), (37.5, 1), (39, 0), (46, 0), (47.5, 1),
            (57.5, 1), (59, 0), (62, 0)]
    ch.poly(prof)
    ch.brk(23); ch.brk(43)
    marks = [(2, 0, 1, 'arm, disarm'), (9, 0, 2, 'gear light'), (16, 0.5, 3, '0.5 m, 5 s'), (32.5, 1, 4, '1 m, 10 s'),
             (52.5, 1, 5, '± 5° roll, pitch')]
    for xv, hv, n, lab in marks:
        num(s, ch.X(xv), ch.Y(hv) - 20, n)
        s.text(ch.X(xv), ch.Y(0) + 22, lab, 12, INK, 'middle')
    s.text(ch.X(23), ch.Y(0) + 40, 'land', 11, MUTED, 'middle')
    s.text(ch.X(43), ch.Y(0) + 40, 'cool < 45 °C', 11, MUTED, 'middle')
    dim_h(s, ch.X(13.5), ch.X(18.5), ch.Y(0.5) + 16, '5 s', above=False)
    dim_h(s, ch.X(27.5), ch.X(37.5), ch.Y(1) + 16, '10 s', above=False)
    s.text(MG + 70, y0 + 282, 'Holds drawn to time scale; climbs, pauses and cooling (axis breaks) are not. '
           'Hover limit 5 m AGL is off this scale.', 12, MUTED)
    footer(s, y0 + 318, 'F01')
    s.save(os.path.join(TEST_OUT, 'f01_hops.svg'))


# ================================================================== F02
def f02():
    s = D(W, 900, 'F02 QHOVER hover-throttle learn: two 60 s hands-off hovers at 2-3 m over the pad (card FTC-F02)')
    y = header(s, 'F02', 'QHOVER hover-throttle learn and notch-filter log',
               'Take off in QSTABILIZE to 2 m, switch to QHOVER; hover hands-off 60 s at 2–3 m AGL (learning and FFT batch '
               'log); land and cool below 45 °C; second 60 s hover at 2–3 m; land; read and save the learned Q_M_THST_HOVER.')
    px, py = hover_plan(s, MG, y, 500, 400, wind_txt=['steady ≤ 3 m/s EST', 'gusts ≤ 5 m/s EST'])
    s.label(px - 7, py + 7, 'pad (home)', px - 108, py + 24, anchor='end')
    cx = MG + 516
    s.text(cx, y + 20, 'Configuration (card)', 13, INK, weight=600)
    yy = s.para(cx, y + 40, 'Q_M_HOVER_LEARN 2; INS_LOG_BAT_MASK 1, INS_LOG_BAT_OPT 4 (pre- and post-filter). '
                'Mode slots 1 QSTABILIZE, 2 QHOVER.', W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'Abort (card)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'Altitude excursion > 1 m in QHOVER; any oscillation; learned value climbing above 0.60.',
                W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'Predicted (card)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'Learned hover throttle ~0.52; front/rear split ~0 (CG at the thrust centroid, '
                'x = −0.0796 m from the LE).', W - MG - cx, 12, MUTED, lh=16)
    crew_note(s, cx, yy + 12, W - MG - cx)
    y0 = y + 420
    panel(s, MG, y0, W - 2 * MG, 300, 'Height above the pad against time')
    ch = Chart(s, MG + 70, y0 + 46, W - 2 * MG - 100, 170, (0, 170), (0, 4))
    # hover 1: t 0-8 climb (not to scale), 10-70 hold, landing; break 80; hover 2: 90-170
    ch.axes([], [0, 1, 2, 3, 4], None, 'height AGL, m')
    s.add(f"<rect x='{ch.X(0):.1f}' y='{ch.Y(3):.1f}' width='{ch.X(170) - ch.X(0):.1f}' height='{ch.Y(2) - ch.Y(3):.1f}' fill='{BL}' stroke='none'/>")
    s.text(ch.X(170) - 4, ch.Y(3) - 6, '2–3 m AGL band (card)', 12, BLUE, 'end')
    ch.poly([(0, 0), (6, 2), (12, 2), (14, 2.5), (72, 2.5), (78, 0), (84, 0)])
    ch.poly([(92, 0), (98, 2.5), (156, 2.5), (162, 0), (170, 0)])
    ch.brk(88)
    for t0, lab in ((14, '0'), (44, '30'), (72, '60 s')):
        s.line(ch.X(t0), ch.Y(0), ch.X(t0), ch.Y(0) + 5, c=INK, w=1)
        s.text(ch.X(t0), ch.Y(0) + 19, lab, 12, MUTED, 'middle')
    for t0, lab in ((98, '0'), (127, '30'), (156, '60 s')):
        s.line(ch.X(t0), ch.Y(0), ch.X(t0), ch.Y(0) + 5, c=INK, w=1)
        s.text(ch.X(t0), ch.Y(0) + 19, lab, 12, MUTED, 'middle')
    num(s, ch.X(6), ch.Y(2) - 22, 1); s.text(ch.X(6) + 14, ch.Y(3.5), 'QSTABILIZE to 2 m, then QHOVER', 12, INK)
    num(s, ch.X(43) - 92, ch.Y(1.2) - 4, 2); num(s, ch.X(127) - 92, ch.Y(1.2) - 4, 3)
    s.text(ch.X(43), ch.Y(1.2), 'hover 1: hands off, 60 s', 12, INK, 'middle')
    s.text(ch.X(127), ch.Y(1.2), 'hover 2: hands off, 60 s', 12, INK, 'middle')
    num(s, ch.X(166), ch.Y(0) - 22, 4)
    s.text(ch.X(88), ch.Y(0) + 38, 'land, cool < 45 °C', 11, MUTED, 'middle')
    s.text(ch.X(166), ch.Y(0) + 38, 'read Q_M_THST_HOVER', 11, MUTED, 'end')
    s.text(MG + 70, y0 + 282, 'Hovers drawn to time scale (60 s each); climbs, landings and cooling are not. Hover line at '
           'mid-band is schematic.', 12, MUTED)
    footer(s, y0 + 318, 'F02')
    s.save(os.path.join(TEST_OUT, 'f02_hover_learn.svg'))


# ================================================================== F03
def f03():
    s = D(W, 900, 'F03 QLOITER free hover: three 60 s hovers at no more than 5 m with cooling between (card FTC-F03)')
    y = header(s, 'F03', 'QLOITER free hover, 3 × 60 s, thermal and endurance point',
               'QHOVER take-off to 3 m, QLOITER hands off 60 s; second 60 s hover ≤ 5 m with 1 m/s translations fore/aft and '
               'left/right; third 60 s hover with 90° yaw left and right. IR on the motors within 30 s after each hover; '
               'cool below 45 °C between (IR every 30 s).')
    px, py = hover_plan(s, MG, y, 500, 400, wind_txt=['steady ≤ 3 m/s EST', 'gusts ≤ 5 m/s EST'],
                        extra_circles=[(2, 'hold', BLUE), (3, 'drift', RED)])
    L = 7 * PPM_H
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        s.line(px + dx * 17, py + dy * 17, px + dx * (17 + L), py + dy * (17 + L), c=ORANGE, w=2, arrow=True)
    s.apath(f'M{px - 26:.1f} {py + 26:.1f} A 37 37 0 0 1 {px - 26:.1f} {py - 26:.1f}', c=ORANGE, sw=1.8, arrow=True)
    num(s, px + 62, py - 16, 2); num(s, px - 50, py + 42, 3)
    s.label(px - 2 * PPM_H * 0.7, py - 2 * PPM_H * 0.7, 'pass: within 2 m EST', px - 108, py - 24, anchor='end')
    s.label(px + 3 * PPM_H * 0.7, py + 3 * PPM_H * 0.7, 'abort: drift > 3 m', px + 108, py + 30, anchor='start')
    s.text(px + 108, py - 48, '2: 1 m/s translations', 12, INK)
    s.text(px + 108, py - 33, '(distance not set)', 11, MUTED)
    s.text(px - 108, py + 50, '3: yaw 90° left', 12, INK, 'end')
    s.text(px - 108, py + 65, 'and right', 12, INK, 'end')
    cx = MG + 516
    s.text(cx, y + 20, 'Abort (card)', 13, INK, weight=600)
    yy = s.para(cx, y + 40, 'Position drift > 3 m in QLOITER; toilet-bowling (compass); motor > 80 °C after any hover.',
                W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'Predicted (card, thermal.md 6.1)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'Hover power 916 W. Motor can +28 K and ESC +21 K over ambient after a 60 s hover '
                '(63 / 56 °C on a 35 °C day). Hot day (≥ 25 °C EST): TEST-PLAN.md §6 rules; the 60 s limit stays.',
                W - MG - cx, 12, MUTED, lh=16)
    crew_note(s, cx, yy + 12, W - MG - cx)
    y0 = y + 420
    panel(s, MG, y0, W - 2 * MG, 300, 'Height above the pad against time')
    ch = Chart(s, MG + 70, y0 + 46, W - 2 * MG - 100, 170, (0, 250), (0, 6))
    ch.axes([], [0, 1, 2, 3, 4, 5, 6], None, 'height AGL, m')
    ch.hline(5, 'hover limit 5 m AGL', dy=-6)
    segs = [(4, 'hover 1, QLOITER 3 m'), (92, 'hover 2, translations'), (180, 'hover 3, yaw ± 90°')]
    ch.poly([(0, 0), (4, 3), (64, 3), (70, 0), (76, 0)])
    for i, (t0, lab) in enumerate(segs):
        if i:
            s.add(f"<rect x='{ch.X(t0):.1f}' y='{ch.Y(5):.1f}' width='{ch.X(t0 + 60) - ch.X(t0):.1f}' height='{ch.Y(0) - ch.Y(5):.1f}' "
                  f"fill='{OL}' stroke='{ORANGE}' stroke-width='1.5' stroke-dasharray='5 3'/>")
            s.text(ch.X(t0 + 30), ch.Y(1.4), 'height ≤ 5 m', 11, MUTED, 'middle')
            s.text(ch.X(t0 + 30), ch.Y(1.4) + 14, '(not set)', 11, MUTED, 'middle')
        num(s, ch.X(t0 + 30), ch.Y(3.9) if i == 0 else ch.Y(3.2), i + 1)
        s.text(ch.X(t0 + 30), ch.Y(0) + 22, lab, 12, INK, 'middle')
        for dt, tl in ((0, '0'), (60, '60 s')):
            s.line(ch.X(t0 + dt), ch.Y(0), ch.X(t0 + dt), ch.Y(0) + 5, c=INK, w=1)
    for xb in (80, 168):
        ch.brk(xb)
        s.text(ch.X(xb), ch.Y(0) + 40, 'cool < 45 °C, IR every 30 s', 11, MUTED, 'middle')
    s.text(MG + 70, y0 + 282, 'Each hover box spans 60 s to scale; climbs and cooling breaks are not to scale.', 12, MUTED)
    footer(s, y0 + 318, 'F03')
    s.save(os.path.join(TEST_OUT, 'f03_loiter.svg'))


# ================================================================== F04
def f04():
    s = D(W, 900, 'F04 Q-mode handling: 30 m box at 3 m/s at 5 m, then box at 5-8 m/s at 8-10 m with long legs into and down wind (card FTC-F04)')
    y = header(s, 'F04', 'Q-mode handling at low forward speed',
               'QLOITER at 5 m: 30 m box at 3 m/s groundspeed; land, cool. QLOITER at 8–10 m AGL: box at 5–8 m/s with the '
               'long legs into and down wind; note the airspeed on the upwind leg. QHOVER at 8–10 m: same box by stick. '
               'Hover time ≤ 60 s per climb.')
    px, py = hover_plan(s, MG, y, 500, 400, title='Plan view: box 1 to scale',
                        wind_txt=['steady ≤ 4 m/s EST', 'gusts ≤ 6 m/s EST'])
    b = 15 * PPM_H
    pts = [(px, py + b), (px + b, py + b), (px + b, py - b), (px - b, py - b), (px - b, py + b), (px, py + b)]
    s.apath(rounded(pts, 6), c=ORANGE, sw=2.5)
    chevrons_on(s, pts, minlen=60)
    num(s, px + b + 16, py - b + 18, 1)
    s.line(px - b, py - b - 14, px + b, py - b - 14, c=MUTED, w=1, arrow=True, start=True)
    s.text(px - b - 6, py - b - 10, '30 m (card)', 12, MUTED, 'end')
    s.label(px - 7, py + 7, 'pad', px - 40, py + 34, anchor='end')
    s.text(px, py - b + 20, 'QLOITER, 5 m, 3 m/s', 12, INK, 'middle')
    # right column: box 2/3 schematic
    cx = MG + 516
    bw = W - MG - cx
    panel(s, cx, y, bw, 400, 'Boxes 2 and 3 (not to scale)')
    bx, by, bwid, bh = cx + 60, y + 70, 120, 200
    pts2 = [(bx, by + bh), (bx, by), (bx + bwid, by), (bx + bwid, by + bh), (bx, by + bh)]
    s.apath(rounded(pts2, 12), c=ORANGE, sw=2.5)
    chevrons_on(s, pts2, minlen=60)
    num(s, bx - 20, by + bh / 2 - 30, 2); num(s, bx - 20, by + bh / 2 + 4, 3)
    s.line(cx + bw - 16, by + 4, cx + bw - 16, by + 48, c=BLUE, w=2.5, arrow=True)
    s.text(cx + bw - 16, by + 64, 'wind', 12, BLUE, 'middle')
    s.text(bx + 8, by + bh / 2 - 8, 'upwind leg:', 12, INK)
    s.text(bx + 8, by + bh / 2 + 8, 'note airspeed', 12, INK)
    s.text(cx + 14, by + bh + 34, 'long legs into and down wind;', 12, MUTED)
    s.text(cx + 14, by + bh + 50, 'box size not given (—)', 12, MUTED)
    # profile
    y0 = y + 420
    panel(s, MG, y0, W - 2 * MG, 316, 'Height and groundspeed, by build-up point')
    ch = Chart(s, MG + 70, y0 + 56, W - 2 * MG - 100, 160, (0, 100), (0, 12))
    ch.axes([], [0, 2, 4, 6, 8, 10, 12], None, 'height AGL, m')
    ch.poly([(0, 0), (3, 5), (27, 5), (30, 0), (33, 0)])
    for x0, x1 in ((38, 64), (70, 96)):
        s.add(f"<rect x='{ch.X(x0):.1f}' y='{ch.Y(10):.1f}' width='{ch.X(x1) - ch.X(x0):.1f}' height='{ch.Y(8) - ch.Y(10):.1f}' "
              f"fill='{OL}' stroke='{ORANGE}' stroke-width='1.5'/>")
        ch.poly([(x0 - 3, 0), (x0, 9)], w=2, dash='4 3'); ch.poly([(x1, 9), (x1 + 3, 0)], w=2, dash='4 3')
    for xm, hv, n, mode, spd in ((15, 5, 1, 'QLOITER', '3 m/s groundspeed'), (51, 10, 2, 'QLOITER', '5–8 m/s'),
                                 (83, 10, 3, 'QHOVER, by stick', '5–8 m/s')):
        num(s, ch.X(xm), ch.Y(hv) - 22, n)
        s.text(ch.X(xm), ch.Y(0) + 22, mode, 12, INK, 'middle')
        s.text(ch.X(xm), ch.Y(0) + 38, spd, 12, MUTED, 'middle')
    s.text(ch.X(51), ch.Y(9) + 4, '8–10 m', 11, INK, 'middle'); s.text(ch.X(83), ch.Y(9) + 4, '8–10 m', 11, INK, 'middle')
    ch.brk(35)
    s.para(MG + 70, y0 + 276, 'Sequence only (not to time scale). Abort (card): Q_ASSIST triggered unexpectedly; pitch attitude > 20° '
           'to hold speed; airspeed diverging from GPS by > 3 m/s on the upwind leg.', W - 2 * MG - 90, 12, MUTED, lh=16)
    footer(s, y0 + 334, 'F04')
    s.save(os.path.join(TEST_OUT, 'f04_low_speed_box.svg'))


# ================================================================== F05
def f05():
    s = D(W, 960, 'F05 hover failsafes: RC loss at 20 m, fence at 25 m, low and critical battery, E-stop, XT90-S (card FTC-F05)')
    y = header(s, 'F05', 'Hover failsafes and R20 demonstration',
               'Home set on the pad. Temporary parameters for this card only (FENCE_ALT_MAX 25; BATT_LOW_MAH and BATT_CRT_MAH '
               'raised), restored and checked with check_params.py after. PIC retakes control if an action is not seen within 10 s.')
    px, py = hover_plan(s, MG, y, 500, 400, wind_txt=['steady ≤ 3 m/s EST', 'gusts ≤ 5 m/s EST'],
                        extra_circles=[(5, 'touch', BLUE), (10, 'drift', RED)])
    s.label(px + 5 * PPM_H * 0.71, py + 5 * PPM_H * 0.71, 'pass: touchdown', px + 108, py + 30, anchor='start')
    s.text(px + 112, py + 49, 'within 5 m EST', 13, MUTED)
    s.label(px + 10 * PPM_H * 0.71, py - 10 * PPM_H * 0.71, 'abort: drift > 10 m', px + 108, py - 34, anchor='start')
    s.label(px - 7, py + 7, 'pad (home)', px - 108, py + 24, anchor='end')
    cx = MG + 516
    s.text(cx, y + 20, 'Expected actions (card)', 13, INK, weight=600)
    yy = s.para(cx, y + 40, f"RC loss in a Q mode → QLAND within FS_LONG_TIMEOUT {P('FS_LONG_TIMEOUT')} s + 1.5 s short EST. "
                f"Fence breach → RTL (FENCE_ACTION {P('FENCE_ACTION')}), which in Q modes lands via QRTL/QLAND. "
                f"Low battery → RTL (BATT_FS_LOW_ACT {P('BATT_FS_LOW_ACT')}); critical → QLAND (BATT_FS_CRT_ACT "
                f"{P('BATT_FS_CRT_ACT')}).", W - MG - cx, 12, MUTED, lh=16)
    s.text(cx, yy + 14, 'On the ground (points 5, 6)', 13, INK, weight=600)
    yy = s.para(cx, yy + 34, 'E-stop: armed at idle, CH7 → all motors stop (pass < 1 s). XT90-S: after disarm, pull the plug '
                'under the idle load; no arc.', W - MG - cx, 12, MUTED, lh=16)
    crew_note(s, cx, yy + 12, W - MG - cx)
    # four mini profiles
    y0 = y + 420
    panel(s, MG, y0, W - 2 * MG, 330, 'Height above the pad, one panel per point (sequence, not to time scale)')
    pw = (W - 2 * MG - 70) / 4
    specs = [
        (1, 'RC loss in hover', 20, [(0, 0), (1, 20), (4, 20), (8, 0), (10, 0)], 4, 'TX off', 'QLAND',
         None, 'QLOITER 20 m EST'),
        (2, 'Fence', 25, [(0, 0), (4, 27), (5, 27), (9, 0), (10, 0)], 4, 'climb through 25 m', 'RTL → QRTL/QLAND',
         ('FENCE_ALT_MAX 25 (temp.)', 25), 'QLOITER climb'),
        (3, 'Battery low', 10, [(0, 0), (1, 10), (4, 10), (8, 0), (10, 0)], 4, 'BATT_LOW_MAH raised', 'RTL, vertical land',
         None, 'hover 10 m'),
        (4, 'Battery critical', 5, [(0, 0), (1, 5), (4, 5), (8, 0), (10, 0)], 4, 'BATT_CRT_MAH raised', 'QLAND in place',
         None, 'hover 5 m'),
    ]
    for i, (n, title, hgt, prof, tev, ev, act, lim, start) in enumerate(specs):
        x0 = MG + 52 + i * (pw + 6)
        ch = Chart(s, x0 + 10, y0 + 80, pw - 22, 150, (0, 10), (0, 30))
        ch.axes([], [0, 10, 20, 30] if i == 0 else [], None, 'height AGL, m' if i == 0 else None, ylx=MG + 22)
        if i:
            for v in (10, 20, 30):
                s.line(ch.x, ch.Y(v), ch.x + ch.w, ch.Y(v), c=GROUND, w=1)
        if lim:
            ch.hline(lim[1], None)
            s.text(ch.x + ch.w - 2, ch.Y(lim[1]) - 5, 'fence 25 m', 11, RED, 'end')
        ch.poly(prof)
        s.line(ch.X(tev), ch.Y(0), ch.X(tev), ch.Y(30), c=BLUE, w=1.2, dash='3 3')
        num(s, x0 + 18, y0 + 52, n)
        s.text(x0 + 34, y0 + 56, title, 13, INK, weight=600)
        if len(ev) < 14:
            s.text(ch.X(tev) + 4, ch.Y(28.5), ev, 11, BLUE)
        s.text(ch.x + ch.w / 2, ch.Y(0) + 20, start, 11, MUTED, 'middle')
        s.para(ch.x, ch.Y(0) + 40, 'event: ' + ev, ch.w + 8, 11, BLUE, lh=14)
        s.para(ch.x, ch.Y(0) + 70, 'expect: ' + act, ch.w + 8, 11, INK, lh=14)
    footer(s, y0 + 348, 'F05', 'Card pass detail: RC loss → QLAND within 5 s + 1.5 s short EST; fence breach at 25 m → RTL logged within '
           '3 s EST of crossing (FENCE_MARGIN 2 m); low 21.0 V / 1,950 mAh → RTL and landing; critical 19.8 V / 1,300 mAh → QLAND; '
           'E-stop < 1 s; all temporary parameters restored (check_params.py zero mismatches).')
    s.save(os.path.join(TEST_OUT, 'f05_hover_failsafes.svg'))


# ------------------------------------------------------------------ transition-site plan (F06-F13)
def legend_rows(s, x, y, items, colw, ncol=2):
    """symbol + text rows; items are (kind, text); returns the y below the last row"""
    row = col = 0
    for kind, t in items:
        if kind == 'wind' and col:
            row, col = row + 1, 0
        lx, ly = x + col * colw, y + row * 20
        col += 1
        if col >= ncol or kind == 'wind':
            row, col = row + 1, 0
        if kind == 'fence':
            s.line(lx, ly - 4, lx + 26, ly - 4, c=MUTED, w=1.5, dash='9 5')
        elif kind == 'abort':
            s.line(lx, ly - 4, lx + 26, ly - 4, c=RED, w=1.2, dash='2 4')
        elif kind == 'crew':
            s.line(lx, ly - 4, lx + 14, ly - 4, c=INK, w=2.5)
            kit(s, lx + 21, ly - 4)
        elif kind == 'path':
            s.line(lx, ly - 4, lx + 26, ly - 4, c=ORANGE, w=3)
        elif kind == 'schem':
            s.line(lx, ly - 4, lx + 26, ly - 4, c=ORANGE, w=2.5, dash='6 4')
        elif kind == 'strip':
            s.rect(lx, ly - 9, 26, 10, fill=GL, c=LINE, sw=1, rx=2)
        elif kind == 'qrtl':
            s.line(lx, ly - 4, lx + 26, ly - 4, c=BLUE, w=1.5, dash='4 3')
        elif kind == 'wind':
            s.line(lx + 2, ly - 4, lx + 26, ly - 4, c=BLUE, w=2, arrow=True)
        elif kind == 'tick':
            s.line(lx + 6, ly - 4, lx + 20, ly - 4, c=BLUE, w=2.5)
        s.text(lx + 34, ly, t, 12, MUTED)
    return y + (row + (1 if col else 0)) * 20


def field_plan(s, x, y, w, ppm, title='Plan view', wind_txt=('≤ 5 m/s', 'gusts ≤ 8 m/s'), extra=(), ncol=2, scale=100):
    """home/pad at the centre of the geofence circle FENCE_RADIUS; 50 m fence-abort ring (TEST-PLAN.md §5);
    crew line 30 m crosswind of the take-off point, clear of the run (TEST-PLAN.md §4 rule 6)"""
    R = PARAM['FENCE_RADIUS'] * ppm
    items = [('fence', f"fence: FENCE_RADIUS {P('FENCE_RADIUS')} m"), ('abort', 'abort ring 50 m inside fence'),
             ('crew', 'crew line 30 m to the side'), ('path', 'path (dashed: schematic)')] + list(extra) +             [('wind', ('wind (from the top of the sheet): ' if ncol == 2 else 'wind: ') + ', '.join(wind_txt))]
    rows = (len(items) - 1 + ncol - 1) // ncol + 1
    h = 40 + 2 * R + 26 + rows * 20 + 34
    panel(s, x, y, w, h, title)
    cx, cy = x + w / 2, y + 40 + R
    s.circ(cx, cy, R, c=MUTED, sw=1.5, dash='9 5')
    s.circ(cx, cy, (PARAM['FENCE_RADIUS'] - 50) * ppm, c=RED, sw=1, dash='2 4')
    s.line(x + 22, y + 34, x + 22, y + 74, c=BLUE, w=2.5, arrow=True)
    s.text(x + 32, y + 46, 'wind', 12, BLUE, weight=600)
    ly = legend_rows(s, x + 14, cy + R + 30, items, (w - 28) / ncol, ncol)
    scalebar(s, x + 14, ly - 4, ppm, scale)
    return cx, cy, R, h


def crew_mark(s, cx, cy, ppm, dx=14):
    yc = cy - 30 * ppm
    s.line(cx + dx, yc, cx + dx + 14, yc, c=INK, w=2.5)
    kit(s, cx + dx + 21, yc)
    return yc


def points_list(s, x, y, width, items, title='Sequence (card build-up points)'):
    s.text(x, y, title, 13, INK, weight=600)
    y += 24
    for n, t in items:
        num(s, x + 10, y - 4, n)
        y = s.para(x + 28, y, t, width - 28, 12, INK, lh=16) + 8
    return y


PPM_F = 0.62      # px per metre on transition-site plans


# ================================================================== F06
def f06():
    ppm = PPM_F
    s = D(W, 1000, 'F06 partial transitions: from 30 m at the upwind edge, FBWA to 12 m/s, back to QHOVER, QLAND; three times (card FTC-F06)')
    y = header(s, 'F06', 'Partial transitions with Q_ASSIST',
               'RFS (≥ 30 m ceiling, ≥ 200 m straight). Climb in QLOITER to 30 m AGL into wind at the upwind field edge; '
               'FBWA with throttle ~60 %, wings level; at 12 m/s switch back to QHOVER (lift motors re-engage); QLAND. '
               'Review the log before the next attempt; three times, the last with throttle 75 %.')
    cx, cy, R, ph = field_plan(s, MG, y, 440, ppm, wind_txt=('≤ 5 m/s', 'gusts ≤ 8 m/s', 'into wind only'),
                               extra=[('strip', 'straight ≥ 200 m into wind (site rule)')])
    s.rect(cx - 5, cy - 200 * ppm, 10, 200 * ppm, fill=GL, c=LINE, sw=1, rx=2)
    crew_mark(s, cx, cy, ppm)
    s.apath(f'M{cx:.1f} {cy:.1f} L{cx:.1f} {cy - 84:.1f}', c=ORANGE, sw=3, dash='6 4')
    chevron(s, cx, cy - 40, -math.pi / 2)
    pad(s, cx, cy, 5)
    num(s, cx - 18, cy + 8, 1); num(s, cx - 18, cy - 30, 2); num(s, cx + 18, cy - 62, 3); num(s, cx - 18, cy - 84, 4)
    pl = MG + 456
    yy = points_list(s, pl, y + 20, W - MG - pl, [
        (1, 'Pad (home). Climb in QLOITER to 30 m AGL (climb ≤ 60 s), into wind, at the upwind field edge.'),
        (2, 'Select FBWA, throttle ~60 %; wings level; airspeed must rise within 6 s.'),
        (3, 'At 12 m/s switch back to QHOVER: lift motors re-engage (Q_ASSIST holds attitude below 13 m/s).'),
        (4, 'QLAND. Review airspeed rise time and altitude loss before the next run. Run length: — (not predicted).')])
    s.text(pl, yy + 8, 'Back-transition watch (card)', 13, INK, weight=600)
    s.para(pl, yy + 28, 'Back-transition only at ≥ 30 m AGL, wings level, into wind. Watch for pitch-up past 30°, a wing drop, '
           'sink > 2 m or current > 85 A.', W - MG - pl, 12, MUTED, lh=16)
    y0 = y + ph + 16
    panel(s, MG, y0, W - 2 * MG, 380, 'Airspeed and height against time from selecting FBWA')
    ch = Chart(s, MG + 70, y0 + 44, W - 2 * MG - 100, 130, (0, 20), (0, 18))
    ch.axes([0, 6, 10, 12, 16, 20], [0, 4, 8, 12, 16], None, 'airspeed, m/s')
    s.add(f"<rect x='{ch.X(0):.1f}' y='{ch.y:.1f}' width='{ch.X(6) - ch.X(0):.1f}' height='{ch.h:.1f}' fill='{BL}' opacity='0.6'/>")
    s.text(ch.X(3), ch.y + 16, 'rising within 6 s', 12, BLUE, 'middle')
    ch.hline(PARAM['Q_ASSIST_SPEED'], f"Q_ASSIST_SPEED {P('Q_ASSIST_SPEED')} m/s", c=BLUE, dash='3 3', dy=-6)
    ch.hline(12, 'switch to QHOVER at 12 m/s', c=ORANGE, dash='6 4', dy=16)
    ch.poly([(0, 0), (6, 12)], c=ORANGE, w=3)
    ch.poly([(6, 12), (10, 16)], c=LINE, w=1.5, dash='4 3')
    ch.poly([(6, 12), (9, 7), (13, 2), (16, 0)], c=ORANGE, w=3)
    s.circ(ch.X(10), ch.Y(16), 4, fill=BLUE, c=BLUE)
    s.text(ch.X(10) + 8, ch.Y(16) - 4, 'C0 SITL: 16 m/s 10 s after the start', 12, BLUE)
    num(s, ch.X(2.2), ch.Y(4.4) - 18, 2); num(s, ch.X(6), ch.Y(12) - 20, 3); num(s, ch.X(14), ch.Y(1.5) - 18, 4)
    ch2 = Chart(s, MG + 70, y0 + 230, W - 2 * MG - 100, 90, (0, 20), (0, 40))
    ch2.axes([0, 6, 8, 12, 16, 20], [0, 20, 30, 40], 'time from selecting FBWA, s (curve shapes schematic)', 'height, m')
    s.add(f"<rect x='{ch2.X(0):.1f}' y='{ch2.Y(30):.1f}' width='{ch2.w:.1f}' height='{ch2.Y(20) - ch2.Y(30):.1f}' fill='{OL}' opacity='0.7'/>")
    s.text(ch2.X(19.6), ch2.Y(20) - 6, 'altitude loss ≤ 10 m EST', 12, RED, 'end')
    ch2.poly([(0, 30), (20, 30)], c=ORANGE, w=3)
    footer(s, y0 + 398, 'F06', 'Airspeed line uses the C0 SITL rate (16 m/s at 10 s, card Predicted) only for its shape; '
           'F06 has no predicted time to 12 m/s. Abort (card): airspeed not rising within 6 s; loss > 10 m EST; pitch > +15 or < −10°.')
    s.save(os.path.join(TEST_OUT, 'f06_partial_transitions.svg'))


# ================================================================== F07
def f07():
    ppm = PPM_F
    s = D(W, 1060, 'F07 full transition from the upwind edge, immediate left turn, circuit at 50 m, back-transition into wind, QLAND (card FTC-F07)')
    y = header(s, 'F07', 'Full transition, fixed-wing circuit, back-transition, QLAND',
               f"QLOITER to 30 m at the upwind field edge; FBWA, throttle 70–75 %; transition completes at AIRSPEED_MIN "
               f"{P('AIRSPEED_MIN')} m/s, lift motors taper over 5 s; start the turn as soon as 'Transition done' appears. "
               f"Climb to 50 m, left-hand circuit (~300 m legs) in FBWA, second in CRUISE; final into wind at 50 m; QHOVER at the pad, QLAND.")
    cx, cy, R, ph = field_plan(s, MG, y, 440, ppm,
                               extra=[('tick', '100 m limit; 166 m C0 SITL'), ('tick', f'QHOVER ~{STOP:.0f} m before the pad')])
    crew_mark(s, cx, cy, ppm)
    L = 150 * ppm
    circ = [(cx, cy - L), (cx - L, cy - L), (cx - L, cy + L), (cx + L, cy + L), (cx + L, cy - L), (cx, cy - L)]
    s.apath(rounded([(cx, cy)] + circ, 12), c=ORANGE, sw=3)
    s.apath(rounded([(cx - L, cy + L), (cx, cy + L), (cx, cy)], 12), c=ORANGE, sw=3)
    chevrons_on(s, [(cx, cy)] + circ, minlen=60)
    chevron(s, cx, cy + L * 0.75, -math.pi / 2)
    for d_ in (100, 166):
        s.line(cx - 9, cy - d_ * ppm, cx + 9, cy - d_ * ppm, c=BLUE, w=2.5)
    s.text(cx - 13, cy - 100 * ppm + 4, '100 m', 11, BLUE, 'end')
    s.line(cx - 9, cy + STOP * ppm, cx + 9, cy + STOP * ppm, c=BLUE, w=2.5)
    s.text(cx - 13, cy + STOP * ppm + 4, f'{STOP:.0f} m', 11, BLUE, 'end')
    pad(s, cx, cy, 5)
    num(s, cx - 18, cy + 12, 1); num(s, cx + 17, cy - 32, 2); num(s, cx + 17, cy - 52, 3)
    num(s, cx - L - 17, cy, 4); num(s, cx + L + 17, cy, 5); num(s, cx + 18, cy + L - 16, 6)
    num(s, cx + 17, cy + STOP * ppm, 7); num(s, cx + 18, cy + 12, 8)
    s.line(cx - L, cy + L + 22, cx + L, cy + L + 22, c=MUTED, w=1, arrow=True, start=True)
    s.text(cx, cy + L + 38, '~300 m legs (card)', 12, MUTED, 'middle')
    pl = MG + 456
    points_list(s, pl, y + 20, W - MG - pl, [
        (1, 'Pad (home). QLOITER to 30 m AGL, into wind, at the upwind field edge.'),
        (2, f"FBWA, throttle 70–75 %; level; transition to AIRSPEED_MIN {P('AIRSPEED_MIN')} m/s, lift motors taper over 5 s."),
        (3, "'Transition done' (pass ≤ 100 m, ≤ 15 s; C0 SITL 15 s / 166 m): start the turn at once, ≤ 3 s."),
        (4, f'Climb to 50 m AGL at {VC:g} m/s; one left-hand circuit in FBWA; note trim and level-flight throttle.'),
        (5, f'Second circuit in CRUISE at {CRUISE} if FBWA was clean.'),
        (6, 'Turn final into wind at 50 m.'),
        (7, f"QHOVER: back-transition, Q_TRANS_DECEL {P('Q_TRANS_DECEL')} m/s², ~{STOP:.0f} m stop from {VC:g} m/s "
            f"({VC:g}² / (2 × {P('Q_TRANS_DECEL')}))."),
        (8, 'QLAND on the pad. Repeat on the second pack.')])
    y0 = y + ph + 16
    panel(s, MG, y0, W - 2 * MG, 300, 'Height along the track (axis broken across the circuits)')
    ch = Chart(s, MG + 70, y0 + 50, W - 2 * MG - 100, 150, (0, 100), (0, 60))
    ch.axes([], [0, 10, 20, 30, 40, 50, 60], None, 'height AGL, m')
    A = lambda d: d / 200 * 38
    C = lambda d: 62 + (150 - d) / 150 * 38
    ch.hline(PARAM['Q_ASSIST_ALT'], f"Q_ASSIST_ALT {P('Q_ASSIST_ALT')} m: lift motors assist below", c=BLUE, dash='3 3', side='right', dy=14)
    ch.poly([(0, 0), (0, 30), (A(150), 30), (A(200), 40), (40, 50), (60, 50), (C(STOP), 50), (C(0), 50), (C(0), 0)])
    ch.brk(40); ch.brk(60)
    for d in (0, 100, 200):
        s.line(ch.X(A(d)), ch.Y(0), ch.X(A(d)), ch.Y(0) + 5, c=INK, w=1)
        s.text(ch.X(A(d)), ch.Y(0) + 19, f'{d}', 12, MUTED, 'middle')
    for d in (150, 100, 50, 0):
        s.line(ch.X(C(d)), ch.Y(0), ch.X(C(d)), ch.Y(0) + 5, c=INK, w=1)
        s.text(ch.X(C(d)), ch.Y(0) + 19, f'{d}', 12, MUTED, 'middle')
    s.text(ch.X(19), ch.Y(0) + 38, 'distance from the pad, m', 12, MUTED, 'middle')
    s.text(ch.X(50), ch.Y(0) + 38, 'circuits × 2', 12, MUTED, 'middle')
    s.text(ch.X(81), ch.Y(0) + 38, 'distance to the pad, m', 12, MUTED, 'middle')
    s.text(ch.X(50), ch.Y(50) + 18, f'FBWA {VC:g} m/s, then', 12, INK, 'middle')
    s.text(ch.X(50), ch.Y(50) + 33, CRUISE, 12, INK, 'middle')
    num(s, ch.X(0) + 14, ch.Y(30) - 16, 1); num(s, ch.X(A(50)), ch.Y(30) - 16, 2); num(s, ch.X(A(100)), ch.Y(30) - 16, 3)
    num(s, ch.X(44), ch.Y(50) - 16, 4); num(s, ch.X(56), ch.Y(50) - 16, 5)
    num(s, ch.X(C(140)), ch.Y(50) - 16, 6); num(s, ch.X(C(STOP)), ch.Y(50) - 16, 7); num(s, ch.X(C(0)) - 16, ch.Y(36), 8)
    s.text(MG + 70, y0 + 284, 'Climb from 30 m to 50 m drawn after the turn (card gives no climb distance). Back-transition only at ≥ 30 m AGL.', 12, MUTED)
    footer(s, y0 + 318, 'F07', f"Cruise {CRUISE}: AIRSPEED_CRUISE {P('AIRSPEED_CRUISE')} in vtol_c0.param; results.json C0 Vc {VC:g}.")
    s.save(os.path.join(TEST_OUT, 'f07_transition_circuit.svg'))


# ================================================================== F08 and F13 shared racetrack plan
def racetrack_plan(s, x, y, w, ppm, wind_txt):
    cx, cy, R, ph = field_plan(s, x, y, w, ppm, wind_txt=wind_txt)
    crew_mark(s, cx, cy, ppm, dx=10)
    hx, hy = 75 * ppm, 190 * ppm          # racetrack drawn inside the 250 m abort ring
    rt = [(cx + hx, cy + hy), (cx + hx, cy - hy), (cx - hx, cy - hy), (cx - hx, cy + hy), (cx + hx, cy + hy)]
    s.apath(f'M{cx:.1f} {cy:.1f} L{cx:.1f} {cy - hy * 0.6:.1f} Q{cx:.1f} {cy - hy:.1f} {cx + hx:.1f} {cy - hy:.1f}', c=ORANGE, sw=2, dash='5 4')
    s.apath(rounded(rt, 30), c=ORANGE, sw=3)
    chevron(s, cx + hx, cy, -math.pi / 2); chevron(s, cx - hx, cy, math.pi / 2)
    pad(s, cx, cy, 5)
    return cx, cy, hx, hy, ph


# ================================================================== F08
def f08():
    ppm = PPM_F
    s = D(W, 1060, 'F08 airspeed calibration and cruise performance: autocal circuits, then reciprocal passes at 18, 20 and 22 m/s at 60 m, ≥ 60 s per heading (card FTC-F08)')
    y = header(s, 'F08', 'Airspeed calibration and cruise performance',
               'Flight 1: transition, climb to 60 m, circuits/LOITER for ~5 min with ARSPD_AUTOCAL 1; land, set 0, read '
               'ARSPD_RATIO. Flight 2: transition; reciprocal passes (≥ 15 s steady each, ≥ 60 s per heading) at 60 m AGL in CRUISE '
               'at each speed of the R11 band; record current and throttle on each leg; back-transition, QLAND.')
    cx, cy, hx, hy, ph = racetrack_plan(s, MG, y, 440, ppm, ('≤ 5 m/s', 'gusts ≤ 8 m/s', 'calm for power legs'))
    num(s, cx + hx + 17, cy + 30, 'A'); num(s, cx - hx - 17, cy - 30, 'B')
    s.text(cx + hx + 30, cy + 34, 'leg A, ≥ 15 s', 12, INK)
    s.text(cx - hx - 30, cy - 26, 'leg B, ≥ 15 s', 12, INK, 'end')
    pl = MG + 456
    yy = points_list(s, pl, y + 20, W - MG - pl, [
        (1, 'Flight 1: transition from the pad, climb to 60 m; circuits/LOITER ~5 min, ARSPD_AUTOCAL 1 (values save every 2 min '
            'when changed > 5 %). Land; ARSPD_AUTOCAL 0; read ARSPD_RATIO.'),
        (2, f'Flight 2: reciprocal passes A and B at 60 m AGL in CRUISE, each ≥ 15 s steady, repeated until each heading has ≥ 60 s: {CRUISE}, then 20 m/s, then 22 m/s.'),
        (3, 'Back-transition, QLAND.')])
    s.text(pl, yy + 8, 'Leg length check (calc)', 13, INK, weight=600)
    s.para(pl, yy + 28, f'A 60 s leg at {VC:g} m/s is {VC:g} × 60 = {VC * 60:,.0f} m; the straights inside the 250 m abort ring '
           'are shorter, so the card asks for ≥ 15 s passes ({VC * 15:,.0f} m) repeated to ≥ 60 s per heading. Leg heading: — (drawn along the wind); '
           'racetrack size set by the field.', W - MG - pl, 12, MUTED, lh=16)
    y0 = y + ph + 16
    panel(s, MG, y0, W - 2 * MG, 300, 'Flight 2: indicated airspeed against time (legs to time scale; turns and transitions not)')
    ch = Chart(s, MG + 70, y0 + 50, W - 2 * MG - 100, 160, (0, 440), (0, 26))
    ch.axes([], [0, 5, 10, 15, 20, 25], None, 'airspeed, m/s')
    ch.hline(PARAM['AIRSPEED_MIN'], f"AIRSPEED_MIN {P('AIRSPEED_MIN')} m/s", c=BLUE, dash='3 3', dy=-5, lx=ch.X(150))
    ch.hline(PARAM['Q_ASSIST_SPEED'], f"Q_ASSIST_SPEED {P('Q_ASSIST_SPEED')} m/s", c=BLUE, dash='3 3', dy=14, lx=ch.X(150))
    pts, t = [(0, 0), (14, 16)], 20
    for k, v in enumerate((VC, 20, 22)):
        for leg in 'AB':
            pts += [(t, v), (t + 60, v)]
            s.line(ch.X(t), ch.Y(0), ch.X(t), ch.Y(0) + 5, c=INK, w=1)
            s.text(ch.X(t + 30), ch.Y(v) - 8, leg, 12, INK, 'middle')
            t += 60 + (4 if leg == 'A' else 8)
        s.text(ch.X(t - 70), ch.Y(0) + 20, CRUISE if k == 0 else f'{v} m/s', 12, INK, 'middle')
    pts += [(t + 6, 0)]
    ch.poly(pts)
    s.text(ch.X(2), ch.Y(0) + 20, 'transition', 11, MUTED, 'start')
    s.text(ch.X(t - 2), ch.Y(0) + 20, 'land', 11, MUTED, 'start')
    s.text(MG + 70, y0 + 262, 'Each speed: reciprocal pair A/B, 60 s each, at 60 m AGL; record BAT current and volts, throttle, '
           'GPS speed per leg.', 12, MUTED)
    s.text(MG + 70, y0 + 280, 'Abort (card): ratio outside 1.5–3.0 in flight 1; cruise current > 22 A sustained EST; within 50 m of the fence.', 12, MUTED)
    footer(s, y0 + 318, 'F08', f'Pairs at {CRUISE} first (AIRSPEED_CRUISE {P("AIRSPEED_CRUISE")}), then 20 and 22 m/s. '
           'The 414 W / 18.6 A power line is the R10 threshold as the matrix states it.')
    s.save(os.path.join(TEST_OUT, 'f08_airspeed_legs.svg'))


# ================================================================== F13
def f13():
    ppm = PPM_F
    s = D(W, 1060, 'F13 gear-fairing A/B: the same reciprocal cruise legs flown with the four leg fairings on and then off (card FTC-F13)')
    y = header(s, 'F13', 'Gear-fairing A/B',
               'Flight A (faired): transition from the upwind edge, climb to 60 m, CRUISE, reciprocal passes as F08, log BAT '
               'current and volts; back-transition, QLAND. Remove the four fairings, re-check CG, weigh the fairings. Flight B '
               '(bare): same profile and legs. Refit the fairings before any further flight.')
    cx, cy, hx, hy, ph = racetrack_plan(s, MG, y, 440, ppm, ('≤ 4 m/s EST', 'gusts ≤ 6 m/s EST', 'calm preferred'))
    s.text(cx + hx + 14, cy + 34, 'leg 1, 60 s', 12, INK)
    s.text(cx - hx - 14, cy - 26, 'leg 2, 60 s', 12, INK, 'end')
    pl = MG + 456
    yy = points_list(s, pl, y + 20, W - MG - pl, [
        (1, f'Flight A, faired: CRUISE at {CRUISE}, 60 m AGL, reciprocal passes as F08 (≥ 60 s per heading); log BAT.Curr and Volt.'),
        (2, 'On the ground: tape off, slide the four fairings off; re-check CG (G01); weigh the fairings.'),
        (3, 'Flight B, bare legs: same profile and legs; log current; land.'),
        (4, 'Refit the fairings: they are part of the F11/F12 configuration.')])
    s.text(pl, yy + 8, 'Same for A and B (card)', 13, INK, weight=600)
    s.para(pl, yy + 28, 'Pack state (both start ≥ 4.15 V/cell), altitude band 60 m, ballast.', W - MG - pl, 12, MUTED, lh=16)
    y0 = y + ph + 16
    panel(s, MG, y0, 300, 300, 'Leg cross-sections (to scale)')
    k = 2.2                                  # px per mm
    ly = y0 + 150
    d = 25.4
    r = d / 2 * k
    lx = MG + 60
    s.circ(lx, ly, r, fill=GL, c=INK, sw=1.5)
    s.text(lx, ly + 52, 'B: bare leg', 12, INK, 'middle')
    s.text(lx, ly + 68, 'Ø 25.4 mm', 12, MUTED, 'middle')
    c = CAD['fairChord'] * 1000
    fx = MG + 140
    s.path(f'M{fx:.1f} {ly - r:.1f} A {r:.1f} {r:.1f} 0 0 0 {fx:.1f} {ly + r:.1f} L{fx + (c - d / 2) * k:.1f} {ly:.1f} Z', fill=OL, c=ORANGE, sw=1.5)
    s.circ(fx, ly, r, fill=GL, c=INK, sw=1)
    s.text(fx + 70, ly + 52, 'A: teardrop fairing', 12, INK, 'middle')
    s.text(fx + 70, ly + 68, f'chord {c:.1f} mm', 12, MUTED, 'middle')
    dim_h(s, fx - r, fx + (c - d / 2) * k, ly - r - 18, f'{c:.1f} mm (cad/params.txt fairChord)')
    s.line(MG + 40, y0 + 60, MG + 90, y0 + 60, c=BLUE, w=2, arrow=True)
    s.text(MG + 96, y0 + 64, 'airflow', 12, BLUE)
    s.para(MG + 16, y0 + 252, 'Fairings: 170 mm long, 3:1, vase-mode PETG, 101.5 g total for four (card).', 270, 12, MUTED, lh=16)
    bx = MG + 316
    panel(s, bx, y0, W - MG - bx, 300, 'Predicted cruise power (card)')
    ch = Chart(s, bx + 70, y0 + 50, W - MG - bx - 100, 180, (0, 2), (0, 500))
    ch.axes([], [0, 100, 200, 300, 400, 500], None, 'electrical power, W')
    AR = json.load(open(os.path.join(ROOT, 'analysis', 'aero', 'aero_results.json'), encoding='utf-8'))['drag']
    pfx, pbx = AR['gear_faired_case']['P_elec_W'], AR['gear_round_case']['P_elec_W']; pf, pb = round(pfx), round(pbx)   # predicted at the design cruise
    for i, (v, lab) in enumerate(((pf, 'A faired'), (pb, 'B bare'))):
        x0 = ch.X(0.3 + i)
        s.rect(x0, ch.Y(v), ch.X(0.7 + i) - x0, ch.Y(0) - ch.Y(v), fill=ORANGE if i == 0 else GL, c=ORANGE if i == 0 else INK, sw=1.2, rx=1)
        s.text((x0 + ch.X(0.7 + i)) / 2, ch.Y(v) + (18 if abs(v - 414) < 40 else -8), f'{v} W', 12, INK, 'middle', 600)   # inside the bar when near the R10 line
        s.text((x0 + ch.X(0.7 + i)) / 2, ch.Y(0) + 20, lab, 12, INK, 'middle')
    ch.hline(414, 'R10: faired ≤ 414 W', dy=-6, side='left')
    xm = ch.X(1.88)
    s.line(ch.X(0.7), ch.Y(pf), xm + 4, ch.Y(pf), c=LINE, w=1, dash='2 3')
    s.line(xm, ch.Y(pf), xm, ch.Y(pb), c=BLUE, w=1, arrow=True, start=True)
    s.text(xm + 5, ch.Y((pf + pb) / 2) + 4, f'Δ {pbx - pfx:.0f} W', 12, BLUE, 'start')
    s.text(bx + 16, y0 + 284, f'Predicted at {CRUISE} (aero_results.json); pass Δ ≥ 100 W EST.', 12, MUTED)
    footer(s, y0 + 318, 'F13', f'Legs flown at {CRUISE}. '
           'If the difference is < 50 W, record and move on (card).')
    s.save(os.path.join(TEST_OUT, 'f13_fairing_ab.svg'))


# ================================================================== F10
def f10():
    ppm = 0.42
    s = D(W, 1100, 'F10 fixed-wing failsafes: pusher to idle in cruise (Q_ASSIST, QLAND) and RC loss in cruise (RTL, QRTL, vertical land) (card FTC-F10)')
    y = header(s, 'F10', 'Fixed-wing failsafes: pusher-out (R15) and RC loss in cruise (R20)',
               f"Flight 1: transition, climb to 60 m AGL EST upwind of the pad, CRUISE; pusher to idle (FBWA, stick low), nose "
               f"level; Q_ASSIST engages below {P('Q_ASSIST_SPEED')} m/s; QLAND over open ground. Flight 2: CRUISE 200 m from home at "
               f"60 m; transmitter off; expect CIRCLE, RTL after {P('FS_LONG_TIMEOUT')} s, QRTL inside RTL_RADIUS {P('RTL_RADIUS')} m, "
               f"vertical landing. Transmitter on only after touchdown (or at once if ABORT).")
    pw = (W - 2 * MG - 12) / 2
    cx, cy, R, ph = field_plan(s, MG, y, pw, ppm, title='Flight 1: pusher-out', wind_txt=('≤ 4 m/s EST', 'gusts ≤ 6 m/s EST'), ncol=1, scale=200)
    crew_mark(s, cx, cy, ppm, dx=10)
    p1 = [(cx, cy), (cx, cy - 30), (cx - 18, cy - 48), (cx - 40, cy - 54)]
    s.apath(rounded(p1, 12), c=ORANGE, sw=3)
    s.apath(f'M{cx - 40:.1f} {cy - 54:.1f} Q{cx - 56:.1f} {cy - 57:.1f} {cx - 64:.1f} {cy - 57:.1f}', c=ORANGE, sw=3, dash='6 4')
    pad(s, cx, cy, 5)
    s.circ(cx - 64, cy - 57, 5, fill=PAPER, c=ORANGE, sw=2)
    num(s, cx - 16, cy - 18, 1); num(s, cx - 22, cy - 68, 2); num(s, cx - 50, cy - 74, 3); num(s, cx - 80, cy - 44, 4)
    x2 = MG + pw + 12
    cx2, cy2, R2, _ = field_plan(s, x2, y, pw, ppm, title='Flight 2: RC loss in cruise', wind_txt=('≤ 4 m/s EST', 'gusts ≤ 6 m/s EST'),
                                 ncol=1, scale=200, extra=[('qrtl', f"RTL_RADIUS {P('RTL_RADIUS')} m: switch to QRTL")])
    s.text(MG + pw - 12, cy + R + 22, 'positions schematic', 11, MUTED, 'end')
    crew_mark(s, cx2, cy2, ppm, dx=10)
    s.circ(cx2, cy2, PARAM['RTL_RADIUS'] * ppm, c=BLUE, sw=1.5, dash='4 3')
    a = math.radians(-125)
    ex, ey = cx2 + 200 * ppm * math.cos(a), cy2 + 200 * ppm * math.sin(a)
    s.apath(f'M{ex + 40:.1f} {ey - 12:.1f} L{ex:.1f} {ey:.1f}', c=ORANGE, sw=3)
    s.circ(ex - 11, ey + 10, 12, c=ORANGE, sw=2, dash='4 3')
    qx, qy = cx2 + 100 * ppm * math.cos(a), cy2 + 100 * ppm * math.sin(a)
    s.apath(f'M{ex:.1f} {ey:.1f} L{qx:.1f} {qy:.1f}', c=ORANGE, sw=3)
    s.apath(f'M{qx:.1f} {qy:.1f} L{cx2:.1f} {cy2:.1f}', c=ORANGE, sw=3, dash='6 4')
    chevron(s, (ex + qx) / 2, (ey + qy) / 2, math.atan2(qy - ey, qx - ex))
    pad(s, cx2, cy2, 5)
    num(s, ex + 52, ey - 14, 1); num(s, ex - 32, ey + 22, 2); num(s, (ex + qx) / 2 + 16, (ey + qy) / 2 - 10, 3)
    num(s, qx + 16, qy - 6, 4); num(s, cx2 + 16, cy2 + 12, 5)
    yl = y + ph + 28
    ya = points_list(s, MG + 4, yl, pw - 8, [
        (1, 'Transition; climb to 60 m AGL EST upwind of the pad.'),
        (2, f'CRUISE at {CRUISE}; pusher throttle to idle (FBWA, stick low); hold the nose level.'),
        (3, f"Airspeed decays; Q_ASSIST engages below {P('Q_ASSIST_SPEED')} m/s (lift motors), attitude held."),
        (4, 'Select QLAND over open ground. Record altitude lost from throttle cut to stable hover.')], title='Flight 1 sequence')
    yb = points_list(s, x2 + 4, yl, pw - 8, [
        (1, 'CRUISE 200 m from home (card) at 60 m; transmitter off.'),
        (2, 'FS short: CIRCLE.'),
        (3, f"After FS_LONG_TIMEOUT {P('FS_LONG_TIMEOUT')} s: RTL, fixed-wing return at RTL_ALTITUDE {P('RTL_ALTITUDE')} m."),
        (4, f"QRTL inside RTL_RADIUS {P('RTL_RADIUS')} m; vertical landing at Q_RTL_ALT {P('Q_RTL_ALT')} m."),
        (5, 'Touchdown within 10 m EST of home; no pilot input until touchdown.')], title='Flight 2 sequence')
    y0 = max(ya, yb) + 10
    panel(s, MG, y0, pw, 270, 'Flight 1: airspeed and height (schematic)')
    ch = Chart(s, MG + 56, y0 + 44, pw - 80, 80, (0, 10), (0, 20))
    ch.axes([], [0, 10, 20], None, 'm/s', ylx=MG + 22)
    ch.hline(PARAM['Q_ASSIST_SPEED'], f"Q_ASSIST {P('Q_ASSIST_SPEED')} m/s", c=BLUE, dash='3 3', dy=-5)
    ch.poly([(0, VC), (2, VC), (5, 13), (6.5, 6), (8, 0), (10, 0)])
    s.line(ch.X(2), ch.y, ch.X(2), ch.y + ch.h, c=LINE, w=1, dash='2 3')
    s.text(ch.X(2) + 4, ch.y + ch.h - 6, 'pusher idle', 11, MUTED)
    ch2 = Chart(s, MG + 56, y0 + 150, pw - 80, 80, (0, 10), (0, 70))
    ch2.axes([], [0, 30, 60], 'time (schematic)', 'm', ylx=MG + 22)
    s.add(f"<rect x='{ch2.X(2):.1f}' y='{ch2.Y(60):.1f}' width='{ch2.X(10) - ch2.X(2):.1f}' height='{ch2.Y(30) - ch2.Y(60):.1f}' fill='{OL}' opacity='0.7'/>")
    ch2.poly([(0, 60), (2, 60), (5, 52), (6.5, 50), (10, 0)])
    s.text(ch2.X(2.2), ch2.Y(30) + 14, 'loss ≤ 30 m EST (band)', 11, RED)
    x2p = MG + pw + 12
    panel(s, x2p, y0, pw, 270, 'Flight 2: height against distance from home')
    ch3 = Chart(s, x2p + 56, y0 + 54, pw - 80, 150, (200, 0), (0, 70))
    ch3.axes([200, 100, 0], [0, 15, 30, 60], 'distance from home, m', 'm', ylx=x2p + 22)
    ch3.poly([(200, 60), (100, 60), (40, 15), (0, 15), (0, 0)])
    s.line(ch3.X(100), ch3.y, ch3.X(100), ch3.y + ch3.h, c=BLUE, w=1, dash='3 3')
    s.text(ch3.X(100) + 4, ch3.y + 12, 'QRTL', 11, BLUE)
    s.text(ch3.X(200) + 4, ch3.Y(60) - 8, f"RTL at {P('RTL_ALTITUDE')} m", 11, INK)
    s.text(ch3.X(0) - 4, ch3.Y(15) + 14, f"Q_RTL_ALT {P('Q_RTL_ALT')} m", 11, INK, 'end')
    s.text(ch3.X(4), ch3.Y(50), 'descent after QRTL:', 11, MUTED, 'end')
    s.text(ch3.X(4), ch3.Y(50) + 14, 'shape schematic', 11, MUTED, 'end')
    footer(s, y0 + 288, 'F10', 'Card abort: flight 1 altitude < 30 m before the lift motors engage; flight 2 not turning toward home '
           'within 10 s of the long failsafe. The RC-off point is 200 m from home, inside the 250 m fence-abort ring (TEST-PLAN.md §5).')
    s.save(os.path.join(TEST_OUT, 'f10_fw_failsafes.svg'))


# ================================================================== F11 / F12 mission profiles
def mission(tid, cruise_s, title, proc, items, cruise_lab, extra_lines, ge=''):
    ppm = PPM_F
    s = D(W, 1060, f'{tid} mission profile: VTOL take-off and hover, transition, {cruise_lab}, back-transition at home, hover, vertical land (card FTC-{tid})')
    y = header(s, tid, title, proc)
    cx, cy, R, ph = field_plan(s, MG, y, 440, ppm)
    crew_mark(s, cx, cy, ppm, dx=10)
    hx, hy = 75 * ppm, 170 * ppm
    rt = [(cx + hx, cy + hy), (cx + hx, cy - hy), (cx - hx, cy - hy), (cx - hx, cy + hy), (cx + hx, cy + hy)]
    s.apath(f'M{cx:.1f} {cy:.1f} L{cx:.1f} {cy - hy * 0.6:.1f} Q{cx:.1f} {cy - hy:.1f} {cx + hx:.1f} {cy - hy:.1f}', c=ORANGE, sw=2.5, dash='6 4')
    s.apath(rounded(rt, 30), c=ORANGE, sw=3)
    s.apath(f'M{cx - hx:.1f} {cy + hy:.1f} Q{cx:.1f} {cy + hy:.1f} {cx:.1f} {cy + hy * 0.5:.1f} L{cx:.1f} {cy:.1f}', c=ORANGE, sw=2.5, dash='6 4')
    chevron(s, cx + hx, cy, -math.pi / 2); chevron(s, cx - hx, cy, math.pi / 2)
    pad(s, cx, cy, 5)
    num(s, cx - 18, cy - 4, 1); num(s, cx - 16, cy - hy * 0.5, 2); num(s, cx + hx + 17, cy + 30, 3); num(s, cx - 16, cy + hy * 0.6, 4)
    num(s, cx + 18, cy + 14, 5)
    pl = MG + 456
    yy = points_list(s, pl, y + 20, W - MG - pl, items)
    for ttl, txt in extra_lines:
        s.text(pl, yy + 8, ttl, 13, INK, weight=600)
        yy = s.para(pl, yy + 28, txt, W - MG - pl, 12, MUTED, lh=16) + 6
    y0 = y + ph + 16
    tf, tb = 15, 4                          # C0 SITL forward and back-transition times (TEST-PLAN.md E06)
    T = [0, 60, 60 + tf, 60 + tf + cruise_s, 60 + tf + cruise_s + tb, 60 + tf + cruise_s + tb + 60]
    tmax = (int(T[-1] / 60) + 1) * 60
    panel(s, MG, y0, W - 2 * MG, 330, 'Height against time (to scale)')
    ch = Chart(s, MG + 70, y0 + 74, W - 2 * MG - 100, 150, (0, tmax), (0, 40))
    ch.axes(list(range(0, tmax + 1, 60 if tmax <= 480 else 120)), [0, 10, 20, 30, 40], 'time from take-off, s', 'height AGL, m')
    phases = [(T[0], T[1], 'hover' + ge, OL), (T[1], T[2], '', BL), (T[2], T[3], cruise_lab, None), (T[3], T[4], '', BL),
              (T[4], T[5], 'hover' + ge, OL)]
    for a, b, lab, col in phases:
        if col:
            s.add(f"<rect x='{ch.X(a):.1f}' y='{ch.y:.1f}' width='{ch.X(b) - ch.X(a):.1f}' height='{ch.h:.1f}' fill='{col}' opacity='0.8'/>")
        if lab:
            s.text(ch.X((a + b) / 2), ch.y - 8, lab, 12, INK, 'middle')
    ch.poly([(0, 0), (30, 30), (T[1], 30), (T[3], 30), (T[4], 30), (T[5] - 30, 30), (T[5], 0)])
    ch.hline(PARAM['Q_ASSIST_ALT'], f"Q_ASSIST_ALT {P('Q_ASSIST_ALT')} m", c=BLUE, dash='3 3', dy=14, lx=ch.X(T[2]) + 30)
    s.label(ch.X((T[1] + T[2]) / 2), ch.y, f'transition ~{tf} s (C0 SITL)', ch.X(T[2]) + 20, ch.y - 34, anchor='start')
    s.label(ch.X((T[3] + T[4]) / 2), ch.y, f'back-transition ~{tb} s (SITL)', ch.X(T[3]) - 20, ch.y - 34, anchor='end')
    for n, x_, y_ in ((1, ch.X(30) + 22, ch.Y(14)), (2, ch.X((T[1] + T[2]) / 2), ch.Y(30) + 22), (3, ch.X((T[2] + T[3]) / 2), ch.Y(30) - 18),
                      (4, ch.X((T[3] + T[4]) / 2), ch.Y(30) + 22), (5, ch.X(T[5] - 30) - 22, ch.Y(14))):
        num(s, x_, y_, n)
    if cruise_s >= 600:
        for m_ in range(1, int(cruise_s / 60) + 1):
            xm = ch.X(T[2] + m_ * 60)
            s.line(xm, ch.Y(0) - 8, xm, ch.Y(0), c=BLUE, w=1.5)
        s.text(ch.X((T[2] + T[3]) / 2), ch.Y(0) - 14, 'GCS calls remaining mAh every minute', 11, BLUE, 'middle')
    s.text(MG + 70, y0 + 286, 'Climb to 30 m is part of the first hover (card). Cruise altitude is not stated after the 30 m take-off: '
           'drawn at 30 m.', 12, MUTED)
    s.text(MG + 70, y0 + 304, 'Phase times: hovers and cruise at the card minimum; transitions from the C0 SITL model (TEST-PLAN.md E06).', 12, MUTED)
    return s, y0 + 348


def f11():
    s, y = mission('F11', 300, 'Mission dress rehearsal (half duration)',
                   f'0.5 kg ballast. VTOL take-off to 30 m, hover 60 s total (take-off + climb); transition; cruise 5 min at {CRUISE} '
                   'on a racetrack inside the fence, log current; back-transition at home; hover 60 s; vertical landing. '
                   'Then compute energy used from BAT.CurrTot / EnrgTot against C11 usable.',
                   [(1, 'VTOL take-off to 30 m; hover 60 s total (take-off + climb).'),
                    (2, 'Transition (AUTO uses TKOFF_THR_MAX 75).'),
                    (3, f'Cruise 5 min at {CRUISE} on the racetrack inside the fence (size set by the field); log current.'),
                    (4, 'Back-transition at home.'),
                    (5, 'Hover 60 s; vertical landing; read BAT.CurrTot / EnrgTot.')],
                   '5 min cruise', [('Abort (card)', 'Remaining mAh below BATT_LOW_MAH 1950 at any point; any failsafe, EKF or airspeed fault.')],
                   ge=' 60 s')
    footer(s, y, 'F11', f'Cruise at {CRUISE} (AIRSPEED_CRUISE). Card prediction: (912.5 W × 120 s + 262.4 W × 300 s) / 3600 = 52.3 Wh, 48 % of the 109.7 Wh C11 usable (results.json sized P_hover, P_cruise).')
    s.save(os.path.join(TEST_OUT, 'f11_rehearsal.svg'))


def f12():
    s, y = mission('F12', 600, 'Full mission (R8, R9, R10)',
                   f'0.5 kg ballast, fairings on, fresh pack. VTOL take-off, hover ≥ 60 s (climb to 30 m included); transition; '
                   f'cruise ≥ 10 min at 18–22 m/s ({CRUISE} target) on the racetrack; back-transition at home; hover ≥ 60 s; '
                   'vertical landing (total hover ≥ 120 s). Temperatures within 30 s, then resting pack voltage and charge-return mAh.',
                   [(1, 'VTOL take-off; hover ≥ 60 s (climb to 30 m included).'),
                    (2, 'Transition.'),
                    (3, f'Cruise ≥ 10 min at 18–22 m/s, target {CRUISE}, on the racetrack; GCS calls remaining mAh every minute.'),
                    (4, 'Back-transition at home.'),
                    (5, 'Hover ≥ 60 s; vertical landing (total hover ≥ 120 s). Temperatures within 30 s.')],
                   '≥ 10 min cruise',
                   [('Abort (card)', 'Remaining capacity reaching BATT_LOW_MAH 1950 before 10 min cruise: the autopilot RTLs; FAIL '
                     'for R10, aircraft kept. Any failsafe, airspeed fault or wind above the limit.')], ge=' ≥ 60 s')
    footer(s, y, 'F12', 'Card pass detail: phases in order; cruise ≥ 600 s at 18–22 m/s calibrated; landing ≥ 20 % of C11 usable '
           'and ≥ 1,300 mAh; lift outputs at minimum ≥ 95 % of cruise (R1); date ≤ 2027-04-30 (R8); 0.5 kg ballast (R12).')
    s.save(os.path.join(TEST_OUT, 'f12_full_mission.svg'))


# ================================================================== G08
def g08():
    ppm = 4.0
    s = D(W, 900, 'G08 field layout: pad, 20 m clear radius, crew line 30 m upwind with the four crew roles, safety kit, LiPo charging, wind (TEST-PLAN.md §3, §4, §7)')
    y = header(s, 'G08', 'Field procedure rehearsal and field layout',
               'Full dry run of a flight session at the site without arming: set-up, pre-flight checklist, crew calls, abort call, '
               'post-flight temperatures, log download, pack change, field charging (time one full charge at the field supply).')
    ph = 400
    panel(s, MG, y, W - 2 * MG, ph, 'Plan view: hover-test layout (transition sites add the ≥ 200 m run and the 300 m fence)')
    px, py = MG + 330, y + ph - 20 * ppm - 50
    s.circ(px, py, 20 * ppm, c=LINE, sw=1, dash='5 4')
    pad(s, px, py, 1.5 * ppm + 2)
    s.label(px + 8, py - 8, 'pad 3 × 3 m, home point', px + 110, py - 30, anchor='start')
    s.text(px, py + 20 * ppm + 17, 'clear of obstacles, 20 m radius', 12, MUTED, 'middle')
    yc = py - 30 * ppm
    s.line(MG + 60, yc, W - MG - 16, yc, c=INK, w=1.5, dash='8 5')
    s.text(W - MG - 20, yc + 22, 'crew line', 12, INK, 'end')
    roles = [('TD', 'test director: card, go/no-go, abort authority'), ('SO / VO', 'safety officer and visual observer'),
             ('PIC', 'pilot in command: only one on the transmitter'), ('GCS', 'ground station: telemetry every 30 s, logs')]
    for i, (r, _) in enumerate(roles):
        pill(s, px - 120 + i * 80, yc, r)
    kit(s, px + 210, yc)
    s.text(px + 224, yc - 14, 'fire bag, extinguisher, first aid', 12, INK)
    dim_v(s, MG + 40, py, yc, '30 m', 'right')
    s.line(MG + 34, py, px - 12, py, c=LINE, w=1, dash='2 3')
    s.text(px, yc - 50, 'spectators behind the crew line', 12, MUTED, 'middle')
    for i in range(7):
        s.circ(px - 90 + i * 30, yc - 72, 5, fill=GL, c=LINE, sw=1)
    # charging area
    zx, zy = W - MG - 226, yc - 110
    s.rect(zx, zy, 150, 70, fill=GL, c=INK, sw=1.2, rx=4)
    s.rect(zx + 12, zy + 22, 36, 26, fill=PAPER, c=INK, sw=1.2, rx=2)
    s.text(zx + 30, zy + 40, 'can', 10, INK, 'middle')
    s.text(zx + 58, zy + 30, 'LiPo bag in', 11, INK)
    s.text(zx + 58, zy + 44, 'the ammo can', 11, INK)
    s.text(zx + 58, zy + 58, 'never unattended', 11, RED)
    s.text(zx, zy - 8, 'charging / LiPo area (position —)', 12, INK)
    wind(s, MG + 30, y + 40, ['wind ≤ 5 m/s steady,', 'gusts ≤ 8 m/s (R16);', 'F01–F06 ≤ 3 m/s EST'])
    s.text(MG + 16, y + ph - 46, 'crashed pack: isolated outdoors 30 min (place —)', 12, MUTED)
    scalebar(s, MG + 16, y + ph - 28, ppm, 20)
    # roles table
    y1 = y + ph + 20
    s.text(MG, y1, 'Crew roles (TEST-PLAN.md §3; review "Crew, field procedure and charging")', 13, INK, weight=600)
    for i, (r, d) in enumerate(roles):
        xx, yy = MG + (i % 2) * 370, y1 + 26 + (i // 2) * 26
        pill(s, xx + 34, yy - 4, r)
        s.text(xx + 74, yy, d, 12, INK)
    # session sequence
    y2 = y1 + 96
    s.text(MG, y2, 'Session sequence rehearsed (TEST-PLAN.md G08)', 13, INK, weight=600)
    steps = ['set-up', 'pre-flight checklist', 'crew calls', 'abort call', 'post-flight temps ≤ 30 s', 'log download', 'pack change',
             'field charging']
    bw, gap = (W - 2 * MG - 7 * 10) / 8, 10
    for i, t in enumerate(steps):
        bx = MG + i * (bw + gap)
        s.rect(bx, y2 + 14, bw, 44, fill=BL if i < 7 else OL, c=BLUE if i < 7 else ORANGE, sw=1, rx=4)
        lines = wrap(t, bw - 8, 11)
        for j, l in enumerate(lines):
            s.text(bx + bw / 2, y2 + 32 + j * 13 - (len(lines) - 1) * 6, l, 11, INK, 'middle')
        if i < 7:
            s.line(bx + bw + 1, y2 + 36, bx + bw + gap - 1, y2 + 36, c=MUTED, w=1)
    # charge time bar
    y3 = y2 + 96
    s.text(MG, y3, 'Charge time per 6500 mAh pack', 13, INK, weight=600)
    ch = Chart(s, MG + 70, y3 + 16, W - 2 * MG - 100, 36, (0, 2), (0, 1))
    ch.axes([0, 0.5, 1.0, 1.5, 2.0], [], 'hours', None, grid=False)
    s.rect(ch.X(0), y3 + 22, ch.X(1.1) - ch.X(0), 22, fill=OL, c=ORANGE, sw=1.2, rx=2)
    s.text(ch.X(0.55), y3 + 38, '~1.1 h at 6 A EST (HTRC C150, review)', 12, INK, 'middle')
    s.line(ch.X(1.5), y3 + 14, ch.X(1.5), y3 + 52, c=RED, w=2)
    s.text(ch.X(1.5) + 6, y3 + 14, 'pass ≤ 1.5 h', 12, RED)
    footer(s, y3 + 106, 'G08', 'Field power source: — (review; TEST-PLAN.md §13 Gaps). Two charged packs ≥ 4.15 V/cell on site (§6). '
           'Charging-area and crashed-pack positions are not set in the plan; shown behind the crew line.')
    s.save(os.path.join(TEST_OUT, 'g08_field_layout.svg'))


# ================================================================== E04
def e04():
    s = D(W, 700, 'E04 RC range walk: aircraft powered on a bench outdoors, transmitter walked out to 300 m with LQ read on its screen (TEST-PLAN.md E04)')
    y = header(s, 'E04', 'RC link: channel map, switches, telemetry and 300 m range walk',
               'Aircraft on the bench outdoors, powered, props off. Walk the transmitter 300 m away (the FENCE_RADIUS) with LQ/RSSI '
               'on the transmitter screen, antenna vertical; the second person watches a servo move at the bench.')
    ph = 230
    panel(s, MG, y, W - 2 * MG, ph, 'Plan view (to scale)')
    ppm = (W - 2 * MG - 140) / 300
    x0, yl = MG + 70, y + 120
    s.rect(x0 - 26, yl - 14, 34, 28, fill=GL, c=INK, sw=1.2, rx=2)
    plane_icon(s, x0 - 9, yl, 0.55, ang=math.pi / 2)
    s.circ(x0 - 9, yl + 34, 6, fill=PAPER, c=INK, sw=1.5)
    s.text(x0 - 9, yl + 56, 'watches a servo', 11, INK, 'middle')
    s.text(x0 - 9, yl - 26, 'bench', 12, INK, 'middle')
    s.line(x0 + 14, yl, x0 + 300 * ppm - 10, yl, c=ORANGE, w=2.5, dash='7 5', arrow=True)
    for d in (100, 200):
        s.line(x0 + d * ppm, yl - 6, x0 + d * ppm, yl + 6, c=INK, w=1)
    xe = x0 + 300 * ppm
    s.circ(xe, yl, 7, fill=ORANGE, c=INK, sw=1.2)
    s.line(xe + 10, yl - 2, xe + 10, yl - 30, c=INK, w=2)
    s.text(xe, yl + 28, 'PIC with transmitter', 12, INK, 'middle')
    s.text(xe, yl + 44, 'antenna vertical', 11, MUTED, 'middle')
    dim_h(s, x0, xe, yl - 46, '300 m = FENCE_RADIUS', c=BLUE)
    s.text(xe - 20, yl - 76, 'read LQ / RSSI here', 12, BLUE, 'end')
    scalebar(s, MG + 16, y + ph - 28, ppm, 100)
    # channel map table
    y1 = y + ph + 20
    s.text(MG, y1, 'Channel map to check (TEST-PLAN.md E04; firmware/vtol_c0.param)', 13, INK, weight=600)
    rows = [('CH1–4', 'AETR'), ('CH5', f"arm switch (RC5_OPTION {P('RC5_OPTION')})"), ('CH6', 'mode, six positions FLTMODE1–6'),
            ('CH7', f"E-stop (RC7_OPTION {P('RC7_OPTION')})"), ('CH8', f"Q_ASSIST 3-position (RC8_OPTION {P('RC8_OPTION')})"),
            ('CH9', f"RTL (RC9_OPTION {P('RC9_OPTION')})")]
    for i, (a, b) in enumerate(rows):
        xx, yy = MG + (i % 2) * 370, y1 + 26 + (i // 2) * 26
        s.rect(xx, yy - 15, 58, 21, fill=BL, c=BLUE, sw=1, rx=3)
        s.text(xx + 29, yy, a, 12, INK, 'middle', 600)
        s.text(xx + 68, yy, b, 12, INK)
    y2 = y1 + 116
    s.text(MG, y2, 'Telemetry (handset, CRSF)', 13, INK, weight=600)
    s.para(MG, y2 + 20, 'Battery V/A, mode, GPS, LQ on the handset; ELRS MAVLink overlay to Mission Planner if used (switchable, '
           'not simultaneous with CRSF). Predicted range: — (ELRS range at the Pocket output power not in the repo).',
           W - 2 * MG, 12, MUTED, lh=16)
    footer(s, y2 + 66, 'E04')
    s.save(os.path.join(TEST_OUT, 'e04_range_walk.svg'))


# ================================================================== E05
def e05():
    s = D(W, 900, 'E05 failsafe flow chart: each trigger and the configured action, with its parameters and how it is tested (firmware/README.md §8, vtol_c0.param)')
    y = header(s, 'E05', 'Failsafe triggers and configured actions',
               'Each trigger → the mode the autopilot selects, from the failsafe table in firmware/README.md §8 and the values in '
               'firmware/vtol_c0.param. Hardware bench steps (props off, armed in QLOITER outdoors with GPS lock) are numbered '
               'as in TEST-PLAN.md E05; SITL letters from firmware/sitl/results.')
    rows = [
        ('RC loss in a Q mode', f"THR_FAILSAFE {P('THR_FAILSAFE')}", [('QLAND in place', ORANGE)], 'bench 1, SITL C'),
        ('RC loss in fixed-wing modes', f"FS_SHORT_ACTN {P('FS_SHORT_ACTN')}, FS_LONG_ACTN {P('FS_LONG_ACTN')}",
         [('CIRCLE (short)', LINE), (f"RTL at {P('FS_LONG_TIMEOUT')} s", ORANGE), (f"QRTL < {P('RTL_RADIUS')} m", ORANGE), ('land', ORANGE)], 'SITL B'),
        ('Battery low', f"{P('BATT_LOW_MAH')} mAh or {PARAM['BATT_LOW_VOLT']:.1f} V for {P('BATT_LOW_TIMER')} s",
         [('RTL', ORANGE), ('QRTL', ORANGE)], 'bench 2, SITL E'),
        ('Battery critical', f"{P('BATT_CRT_MAH')} mAh or {P('BATT_CRT_VOLT')} V", [('QLAND in place', ORANGE)], 'bench 2'),
        ('Transition not done', f"Q_TRANS_FAIL {P('Q_TRANS_FAIL')} s", [('QRTL', ORANGE)], 'SITL D'),
        ('Geofence breach', f"{P('FENCE_ALT_MAX')} m up or {P('FENCE_RADIUS')} m out", [('RTL', ORANGE), ('QRTL near home', ORANGE)], 'bench 3, SITL F'),
        ('MAVLink RC override lost', 'ELRS MAVLink mode', [('QLAND', ORANGE)], 'SITL G'),
        ('Motor emergency stop', f"CH7, RC7_OPTION {P('RC7_OPTION')}", [('all motors stop', RED)], 'bench 4'),
        ('Arm request', f"CH5 only; VTOL modes only; ≥ {P('BATT_ARM_VOLT')} V", [('refused otherwise', LINE)], 'try FBWA'),
    ]
    tx, tw_ = MG, 214
    ax = tx + tw_ + 34
    y0 = y + 30
    s.text(tx, y0 - 8, 'Trigger and parameter', 12, MUTED, weight=600)
    s.text(ax, y0 - 8, 'Action (mode on event)', 12, MUTED, weight=600)
    s.text(W - MG, y0 - 8, 'Tested by', 12, MUTED, 'end', 600)
    rh = 56
    for i, (trg, par, acts, test) in enumerate(rows):
        yy = y0 + i * rh
        s.rect(tx, yy, tw_, rh - 12, fill=BL, c=BLUE, sw=1.2, rx=5)
        s.text(tx + 10, yy + 18, trg, 13, INK, weight=600)
        s.text(tx + 10, yy + 35, par, 11, MUTED)
        s.line(tx + tw_ + 2, yy + (rh - 12) / 2, ax - 2, yy + (rh - 12) / 2, c=INK, w=1.5, arrow=True)
        x = ax
        for j, (a, col) in enumerate(acts):
            bw = tw(a, 12) * 1.05 + 20
            s.rect(x, yy + 6, bw, rh - 24, fill=OL if col == ORANGE else (GL if col == LINE else '#f6dcd9'), c=col if col != LINE else INK,
                   sw=1.2, rx=4)
            s.text(x + bw / 2, yy + 26, a, 12, INK, 'middle', 600)
            x += bw
            if j < len(acts) - 1:
                s.line(x + 2, yy + (rh - 12) / 2, x + 16, yy + (rh - 12) / 2, c=INK, w=1.5, arrow=True)
                x += 18
        s.text(W - MG, yy + 26, test, 12, BLUE, 'end')
    yb = y0 + len(rows) * rh + 14
    yb = s.para(MG, yb, 'Bench steps (TEST-PLAN.md E05): 1 transmitter off → QLAND within FS_LONG_TIMEOUT 5 s + 1.5 s short; '
                '2 BATT_LOW_MAH and BATT_CRT_MAH temporarily 6,400 → RTL / QLAND, restore 1,950 / 1,300; 3 FENCE_ALT_MAX 1 m, lift the '
                'aircraft 2 m by hand → breach message, restore 110; 4 E-stop CH7 at 20 % command; 5 XT90-S pull under load.',
                W - 2 * MG, 12, MUTED, lh=16)
    yb = s.para(MG, yb + 4, 'Receiver failsafe: set to output no pulses on link loss; no failsafe position on the handset '
                '(firmware/README.md §8).', W - 2 * MG, 12, MUTED, lh=16)
    footer(s, yb + 10, 'E05')
    s.save(os.path.join(TEST_OUT, 'e05_failsafes.svg'))


# ================================================================== E07
def rot_arrow(s, x, y, rx, ry, c=BLUE):
    s.apath(f'M{x - rx:.1f} {y:.1f} A {rx:.1f} {ry:.1f} 0 1 0 {x:.1f} {y - ry:.1f}', c=c, sw=2, arrow=True)


def e07():
    s = D(W, 760, 'E07 compass and GPS calibration: site, compass rotations, accelerometer calibration, GPS settling, four-heading check (TEST-PLAN.md E07; firmware/README.md 6.3)')
    y = header(s, 'E07', 'Compass and GPS calibration',
               'Outdoors, away from steel. Mission Planner compass calibration (COMPASS_AUTO_ROT 2 detects the external compass '
               'orientation); accelerometer calibration; check HDOP and satellite count after 2 min; heading against a phone '
               'compass at four headings.')
    cw, chh = (W - 2 * MG - 2 * 12) / 3, 230
    cards = []
    for i in range(6):
        cx_ = MG + (i % 3) * (cw + 12)
        cy_ = y + (i // 3) * (chh + 12)
        panel(s, cx_, cy_, cw, chh)
        cards.append((cx_, cy_))

    def ttl(i, n, t):
        x_, y_ = cards[i]
        num(s, x_ + 20, y_ + 22, n, BLUE)
        s.text(x_ + 36, y_ + 27, t, 13, INK, weight=600)

    # 1 site
    x_, y_ = cards[0]; ttl(0, 1, 'Site')
    plane_icon(s, x_ + cw / 2 - 30, y_ + 110, 1.6)
    gx = x_ + cw / 2 + 50
    s.rect(gx - 20, y_ + 90, 40, 40, fill=GL, c=INK, sw=1.2, rx=2)
    s.text(gx, y_ + 148, 'steel', 11, INK, 'middle')
    s.line(gx - 26, y_ + 84, gx + 26, y_ + 136, c=RED, w=2.5)
    s.para(x_ + 14, y_ + 168, 'Outdoors, away from steel (TEST-PLAN.md E07).', cw - 28, 12, MUTED, lh=16)
    # 2 rotations
    x_, y_ = cards[1]; ttl(1, 2, 'Compass: rotate on all axes')
    for k, (lab, ang) in enumerate((('roll', 0), ('pitch', 0), ('yaw', 0))):
        ix = x_ + 40 + k * (cw - 80) / 2
        plane_icon(s, ix, y_ + 100, 0.9)
        if lab == 'yaw':
            rot_arrow(s, ix, y_ + 100, 26, 26)
        elif lab == 'roll':
            s.apath(f'M{ix - 26:.1f} {y_ + 72:.1f} Q{ix:.1f} {y_ + 60:.1f} {ix + 26:.1f} {y_ + 72:.1f}', c=BLUE, sw=2, arrow=True)
            s.line(ix, y_ + 76, ix, y_ + 128, c=LINE, w=1, dash='3 3')
        else:
            s.apath(f'M{ix + 30:.1f} {y_ + 84:.1f} Q{ix + 40:.1f} {y_ + 100:.1f} {ix + 30:.1f} {y_ + 116:.1f}', c=BLUE, sw=2, arrow=True)
            s.line(ix - 26, y_ + 100, ix + 26, y_ + 100, c=LINE, w=1, dash='3 3')
        s.text(ix, y_ + 148, lab, 12, INK, 'middle')
    s.para(x_ + 14, y_ + 176, 'Setup > Compass > Start; rotate the assembled airframe until fitness passes.', cw - 28, 12, MUTED, lh=16)
    # 3 large vehicle
    x_, y_ = cards[2]; ttl(2, 3, 'Or: Large Vehicle MagCal')
    plane_icon(s, x_ + cw / 2, y_ + 112, 1.5)
    s.line(x_ + cw / 2, y_ + 82, x_ + cw / 2, y_ + 50, c=BLUE, w=2, arrow=True)
    s.text(x_ + cw / 2 + 8, y_ + 62, 'known heading', 12, BLUE)
    s.para(x_ + 14, y_ + 168, 'For the 2.4 m airframe: GPS lock, nose on a known heading (firmware/README.md 6.3).', cw - 28, 12, MUTED, lh=16)
    # 4 accel
    x_, y_ = cards[3]; ttl(3, 4, 'Accelerometer calibration')
    plane_icon(s, x_ + cw / 2, y_ + 104, 1.5)
    s.line(x_ + 30, y_ + 140, x_ + cw - 30, y_ + 140, c=GROUND, w=4)
    s.para(x_ + 14, y_ + 168, 'Mission Planner accelerometer calibration (ArduPilot calibration page, firmware.md CAL).', cw - 28, 12, MUTED, lh=16)
    # 5 GPS
    x_, y_ = cards[4]; ttl(4, 5, 'GPS settles 2 min')
    gx, gy = x_ + cw / 2, y_ + 100
    s.circ(gx, gy, 34, c=BLUE, sw=1.5)
    s.line(gx, gy, gx, gy - 26, c=BLUE, w=2); s.line(gx, gy, gx + 18, gy, c=BLUE, w=2)
    s.text(gx, gy + 54, '2 min', 12, BLUE, 'middle')
    s.para(x_ + 14, y_ + 176, 'Then read HDOP ≤ 1.5 and satellites ≥ 10 EST.', cw - 28, 12, MUTED, lh=16)
    # 6 headings
    x_, y_ = cards[5]; ttl(5, 6, 'Heading check, 4 headings')
    hx, hy = x_ + cw / 2, y_ + 106
    for k in range(4):
        a = -math.pi / 2 + k * math.pi / 2
        plane_icon(s, hx + 44 * math.cos(a), hy + 44 * math.sin(a), 0.55, ang=a + math.pi / 2)
    s.circ(hx, hy, 9, fill=PAPER, c=BLUE, sw=1.5)
    s.text(hx, hy + 4, 'N', 9, BLUE, 'middle', 700)
    s.para(x_ + 14, y_ + 168, 'Compare with a phone compass; error ≤ 10° EST at each. Spacing not set (90° shown).', cw - 28, 12, MUTED, lh=16)
    footer(s, y + 2 * chh + 32, 'E07', 'No "compass inconsistent" message (TEST-PLAN.md E07).')
    s.save(os.path.join(TEST_OUT, 'e07_compass_cal.svg'))


# ================================================================== E02
def e02():
    s = D(W, 900, 'E02 motor order: top view of C0 to scale with lift motors M1-M4, spin directions, pusher and servo outputs (vtol_c0.param §2; cad/params.txt)')
    y = header(s, 'E02', 'ESC protocol, motor order, direction and spin thresholds',
               'Props off. Mission Planner motor test in the ArduPilot Quad X order at the 10 % command; set direction with DShot '
               'commands (SERVO_DSHOT_ESC 2) or BLHeli passthrough; find the lowest output that spins every motor (Q_M_SPIN_ARM) '
               'and that gives a little thrust (Q_M_SPIN_MIN). The pusher on S9 responds to throttle only in fixed-wing modes.')
    k = 228.0                                  # px per metre
    rd = CAD['liftProp'] / 2
    xf, xr = CAD['xFront'], CAD['xRear']
    ox, oy = W / 2, y + 62 + (xf + rd) * k      # wing LE on the centreline; front discs clear the dimension rows
    X = lambda xm: oy - xm * k                 # aircraft x (forward +) to sheet y
    Yp = lambda ym: ox + ym * k                # aircraft y (right +) to sheet x
    ch, half = CAD['chord'], C0['params']['span'] / 2
    yb = CAD['yIn']
    xnose = COMP['Fuselage_Pod'][0][0]; fusL = CAD['fusL']; fr = CAD['fusR']
    xs0 = CAD['xStub0']; xfin = CAD['xFinLE']; hc = CAD['hC']; hs = CAD['hSpan'] / 2; vc = CAD['vC']
    xbf = xr + CAD['segF']                     # front end of the boom (splice at xRear + front segment)
    # wing with ailerons (outboard ailSpan of each panel, hinge at the horn hardpoint chord station)
    s.rect(Yp(-half), X(0), 2 * half * k, ch * k, fill=GL, c=INK, sw=1.5, rx=2)
    ail0 = half - CAD['ailSpan']; xh = CAD['hornHpX']
    for sg in (-1, 1):
        x1, x2 = Yp(sg * ail0), Yp(sg * half)
        s.rect(min(x1, x2), X(xh), abs(x2 - x1), (ch + xh) * k, fill=BL, c=BLUE, sw=1.2, rx=1)
    for sg in (-1, 1):
        s.line(Yp(sg * yb), X(xbf), Yp(sg * yb), X(xs0), c=INK, w=4)
    s.rect(Yp(-hs), X(xfin), 2 * hs * k, hc * k, fill=GL, c=INK, sw=1.5, rx=1)
    s.rect(Yp(-CAD['elevSpan'] / 2), X(xfin - hc * 0.55), CAD['elevSpan'] * k, hc * 0.45 * k, fill=BL, c=BLUE, sw=1.2, rx=1)
    for sg in (-1, 1):
        s.line(Yp(sg * yb), X(xfin), Yp(sg * yb), X(xfin - vc), c=INK, w=6)
        s.line(Yp(sg * yb), X(xfin - vc * 0.6), Yp(sg * yb), X(xfin - vc), c=BLUE, w=6)
    xt = xnose - fusL
    d = (f'M{Yp(0):.1f} {X(xnose):.1f} Q{Yp(fr):.1f} {X(xnose):.1f} {Yp(fr):.1f} {X(xnose - 0.22):.1f} L{Yp(fr):.1f} {X(-0.05):.1f} '
         f'L{Yp(CAD["tailR"]):.1f} {X(xt):.1f} L{Yp(-CAD["tailR"]):.1f} {X(xt):.1f} L{Yp(-fr):.1f} {X(-0.05):.1f} '
         f'L{Yp(-fr):.1f} {X(xnose - 0.22):.1f} Q{Yp(-fr):.1f} {X(xnose):.1f} {Yp(0):.1f} {X(xnose):.1f} Z')
    s.path(d, fill='#dfe3e8', c=INK, sw=1.5)
    xp = COMP['Pusher_Prop_14in'][0][0]; rp = CAD['pushProp'] / 2
    s.line(Yp(-rp), X(xp), Yp(rp), X(xp), c=ORANGE, w=4)
    s.circ(Yp(0), X(xp), 5, fill=ORANGE, c=INK, sw=1)
    pz = COMP['Pitot_Tube'][0]
    s.line(Yp(pz[2]), X(pz[0] + CAD['pitotL'] * 0.6), Yp(pz[2]), X(pz[0] - CAD['pitotL'] * 0.4), c=BLUE, w=2.5)
    motors = [('M1', 'S5', xf, yb, 'CCW'), ('M2', 'S6', xr, -yb, 'CCW'), ('M3', 'S7', xf, -yb, 'CW'), ('M4', 'S8', xr, yb, 'CW')]
    for mname, srv, xm, ym, rot in motors:
        mx, my = Yp(ym), X(xm)
        s.circ(mx, my, rd * k, fill='none', c=ORANGE, sw=1.5, dash='6 4')
        s.circ(mx, my, 10, fill=ORANGE, c=INK, sw=1.2)
        r = rd * k - 12
        if rot == 'CCW':
            s.apath(f'M{mx + r * math.cos(-0.3):.1f} {my + r * math.sin(-0.3):.1f} A {r:.1f} {r:.1f} 0 0 0 {mx + r * math.cos(-2.2):.1f} {my + r * math.sin(-2.2):.1f}',
                    c=ORANGE, sw=2.5, arrow=True)
        else:
            s.apath(f'M{mx + r * math.cos(-2.84):.1f} {my + r * math.sin(-2.84):.1f} A {r:.1f} {r:.1f} 0 0 1 {mx + r * math.cos(-0.94):.1f} {my + r * math.sin(-0.94):.1f}',
                    c=ORANGE, sw=2.5, arrow=True)
        sg = 1 if ym > 0 else -1
        tx = mx + sg * (rd * k + 10)
        an = 'start' if sg > 0 else 'end'
        s.text(tx, my - 2, f'{mname} · {srv}', 13, INK, an, 600)
        s.text(tx, my + 14, rot, 12, ORANGE, an, 600)
    yb0 = X(xs0)
    s.label(Yp(-half + 0.3), X(xh - 0.03), 'S1 aileron, left', Yp(-half) + 4, X(-ch) + 40, anchor='start')
    s.label(Yp(half - 0.3), X(xh - 0.03), 'S2 aileron, right', Yp(half) - 4, X(-ch) + 40, anchor='end')
    s.label(Yp(-0.2), X(xfin - hc * 0.8), 'S3 elevator', Yp(-0.2), yb0 + 26, anchor='end')
    s.label(Yp(-yb), X(xfin - vc * 0.85), 'S4 rudder, left boom', Yp(-yb) - 60, yb0 + 26, anchor='end')
    s.label(Yp(yb), X(xfin - vc * 0.85), 'S11 rudder, right boom', Yp(yb) + 60, yb0 + 26, anchor='start')
    s.text(Yp(0), X(xp) + 40, 'S9 pusher', 12, INK, 'middle')
    s.text(Yp(0), X(xp) + 55, f'{CAD["pushProp"] / 0.0254:.0f} in prop', 12, MUTED, 'middle')
    s.label(Yp(pz[2]), X(pz[0] + 0.12), 'pitot (left wing)', Yp(pz[2]) - 30, X(0.2), anchor='end')
    s.line(Yp(0), X(xnose) - 8, Yp(0), X(xnose) - 30, c=INK, w=1.5, arrow=True)
    s.text(Yp(0) + 8, X(xnose) - 20, 'nose', 12, INK)
    top = X(xf + rd)
    dim_h(s, Yp(-half), Yp(half), top - 34, f"span {C0['params']['span']:.2f} m (results.json)")
    dim_h(s, Yp(-yb) - rd * k, Yp(-yb) + rd * k, top - 8, f'Ø {CAD["liftProp"] * 1000:.0f} mm (17 in)')
    dim_h(s, Yp(-yb), Yp(yb), yb0 + 56, f'booms ± {yb:.3f} m', above=False)
    xd = Yp(half) + 12
    s.line(Yp(half) + 2, X(0), xd + 6, X(0), c=LINE, w=1, dash='2 3')
    s.line(Yp(yb) + rd * k + 80, X(xf), xd + 6, X(xf), c=LINE, w=1, dash='2 3')
    s.line(Yp(yb) + rd * k + 80, X(xr), xd + 6, X(xr), c=LINE, w=1, dash='2 3')
    dim_v(s, xd, X(0), X(xf), f'+{xf:.3f} m', 'right')
    dim_v(s, xd, X(0), X(xr), f'{xr:.3f} m', 'right')
    s.text(xd + 6, X(0) + 4, 'LE', 11, MUTED)
    yy = s.para(MG, yb0 + 104, 'Outputs (vtol_c0.param §2): S5 M1 front-right CCW, S6 M2 rear-left CCW, S7 M3 front-left CW, S8 M4 rear-right '
                'CW (DShot); S9 pusher; S1, S2 ailerons; S3 elevator; S4, S11 rudders (PWM); S10 unused (DShot group 4); S12 spare. '
                'Spin as seen from above.', W - 2 * MG, 12, MUTED, lh=16)
    yy = s.para(MG, yy + 2, f"Predicted Q_M_SPIN_ARM {P('Q_M_SPIN_ARM')}, Q_M_SPIN_MIN {P('Q_M_SPIN_MIN')} (param file). Geometry to scale "
                f'from cad/params.txt (xFront, xRear, yIn, liftProp, fusL {fusL:.2f} m pod, comp= records; x from the wing LE, '
                'forward +); elevator chord split schematic.', W - 2 * MG, 12, MUTED, lh=16) - 16
    footer(s, yy + 30, 'E02')
    s.save(os.path.join(TEST_OUT, 'e02_motor_order.svg'))


# ================================================================== E03
def e03():
    s = D(W, 760, 'E03 servo directions: right roll stick raises the right aileron, back stick raises the elevator, right rudder moves both rudders right (TEST-PLAN.md E03)')
    y = header(s, 'E03', 'Servo direction, throws and centering on the airframe (5 servos)',
               'In MANUAL and FBWA: stick right → right aileron up; stick back → elevator up; rudder right → both rudders (S4 left '
               'boom, S11 right boom) trailing edge right. In FBWA roll the aircraft and check the surfaces counter the motion. '
               'Measure throws with a ruler at the trailing edge; set SERVOn_MIN/MAX/TRIM/REVERSED.')
    pw, ph = (W - 2 * MG - 24) / 3, 330

    def stick(x, yy, dx, dy, lab):
        s.rect(x - 26, yy - 26, 52, 52, fill=GL, c=INK, sw=1.2, rx=6)
        s.line(x, yy, x + dx * 18, yy + dy * 18, c=INK, w=2.5)
        s.circ(x + dx * 18, yy + dy * 18, 5, fill=INK, c=INK)
        s.text(x + 36, yy + 4, lab, 12, INK)

    def throw_arc(cx, cy, r, a0, a1, c=BLUE):
        s.apath(f'M{cx + r * math.cos(a0):.1f} {cy + r * math.sin(a0):.1f} A {r} {r} 0 0 {1 if a1 > a0 else 0} '
                f'{cx + r * math.cos(a1):.1f} {cy + r * math.sin(a1):.1f}', c=c, sw=1.2, arrow=True)

    # panel 1: ailerons, rear view
    x0 = MG
    panel(s, x0, y, pw, ph, 'Ailerons S1, S2 (from behind)')
    stick(x0 + 46, y + 70, 1, 0, 'roll stick right')
    cy_ = y + 170
    s.rect(x0 + 50, cy_ - 4, pw - 100, 8, fill=GL, c=INK, sw=1.2, rx=3)
    s.circ(x0 + pw / 2, cy_, 10, fill='#dfe3e8', c=INK, sw=1.2)
    a = math.radians(20)
    lx, rx_ = x0 + 50, x0 + pw - 50
    s.line(lx, cy_, lx - 40 * math.cos(a), cy_ + 40 * math.sin(a), c=ORANGE, w=5)
    s.line(rx_, cy_, rx_ + 40 * math.cos(a), cy_ - 40 * math.sin(a), c=ORANGE, w=5)
    s.line(rx_, cy_, rx_ + 40, cy_, c=LINE, w=1, dash='3 3'); s.line(lx, cy_, lx - 40, cy_, c=LINE, w=1, dash='3 3')
    s.text(rx_ + 14, cy_ - 30, 'up', 12, ORANGE, 'middle', 600)
    s.text(lx - 14, cy_ + 34, 'down', 12, ORANGE, 'middle', 600)
    s.text(lx - 6, cy_ - 14, 'left', 11, MUTED, 'middle'); s.text(rx_ + 2, cy_ + 22, 'right', 11, MUTED, 'middle')
    s.para(x0 + 14, y + 236, 'Right aileron up for stick right (card); left aileron opposite. Throw ± 20° EST.', pw - 28, 12, MUTED, lh=16)
    # panel 2: elevator, side view
    x1 = MG + pw + 12
    panel(s, x1, y, pw, ph, 'Elevator S3 (from the left)')
    stick(x1 + 46, y + 70, 0, 1, 'pitch stick back')
    hx, hy = x1 + 56, y + 170
    s.apath(f'M{hx:.1f} {hy:.1f} Q{hx + 10:.1f} {hy - 8:.1f} {hx + 60:.1f} {hy - 4:.1f} L{hx + 60:.1f} {hy + 4:.1f} Q{hx + 10:.1f} {hy + 8:.1f} {hx:.1f} {hy:.1f} Z',
            c=INK, sw=1.2, fill=GL)
    ex = hx + 62
    s.line(ex, hy, ex + 70, hy, c=LINE, w=1, dash='3 3')
    s.line(ex, hy, ex + 70 * math.cos(a), hy - 70 * math.sin(a), c=ORANGE, w=5)
    throw_arc(ex, hy, 58, 0, -a)
    throw_arc(ex, hy, 58, 0, a, c=LINE)
    s.text(ex + 74, hy - 30, 'up', 12, ORANGE, 'start', 600)
    s.text(ex + 64, hy - 10, '20° EST', 11, BLUE)
    s.text(ex + 64, hy + 30, '−20° EST', 11, MUTED)
    s.line(hx - 30, hy, hx - 6, hy, c=BLUE, w=1.5, arrow=True)
    s.text(hx - 32, hy - 8, 'flow', 11, BLUE, 'end')
    s.para(x1 + 14, y + 236, 'Elevator up for stick back. Throw ± 20° EST and ≥ 15° EST: trim needs about −8.2° at the stall '
           '(aero_results.json stall.trim_at_Vstall).', pw - 28, 12, MUTED, lh=16)
    # panel 3: rudders, top view
    x2 = MG + 2 * (pw + 12)
    panel(s, x2, y, pw, ph, 'Rudders S4, S11 (from above)')
    stick(x2 + 46, y + 70, 1, 0, 'rudder stick right')
    for k_, (bx, lab) in enumerate(((x2 + pw / 2 - 50, 'S4 left boom'), (x2 + pw / 2 + 50, 'S11 right boom'))):
        fy = y + 130
        s.rect(bx - 4, fy, 8, 46, fill=GL, c=INK, sw=1.2, rx=2)
        s.line(bx, fy + 46, bx, fy + 90, c=LINE, w=1, dash='3 3')
        s.line(bx, fy + 46, bx + 44 * math.sin(a), fy + 46 + 44 * math.cos(a), c=ORANGE, w=5)
        s.text(bx, fy - 8, lab, 11, INK, 'middle')
        s.text(bx + 18, fy + 104, 'TE right', 11, ORANGE, 'middle', 600)
    s.line(x2 + pw / 2, y + 190, x2 + pw / 2, y + 160, c=INK, w=1.5, arrow=True)
    s.text(x2 + pw / 2, y + 206, 'nose', 11, INK, 'middle')
    s.para(x2 + 14, y + 260, 'Both trailing edges right for rudder right. Throw ± 20° EST.', pw - 28, 12, MUTED, lh=16)
    footer(s, y + ph + 18, 'E03', 'Throws ± 20° EST are typical sport-plane values: the repo gives none (TEST-PLAN.md E03, "—"). '
           'Surfaces return within 1 mm of neutral; no binding at full throw; servo current at full throw ≤ 1 A each EST.')
    s.save(os.path.join(TEST_OUT, 'e03_servo_throws.svg'))


ALL = [f01, f02, f03, f04, f05, f06, f07, f08, f13, f10, f11, f12, g08, e04, e05, e07, e02, e03]

if __name__ == '__main__':
    only = sys.argv[1:]
    for fn in ALL:
        if not only or fn.__name__ in only:
            fn()
