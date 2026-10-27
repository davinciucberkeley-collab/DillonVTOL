"""Explanatory diagrams for the test plan and the build manual (SVG, generated so the numbers stay in step).

Writes docs/test/figures/*.svg (test set-ups) and docs/build/img/*.svg (cut diagram, wiring diagram, CG procedure).
Numbers come from analysis/results.json, docs/build/cut-list.csv, docs/build/wiring.csv and the test plan text;
nothing here is a measurement. CAD renders of the aircraft are made separately by cad/BuildFigs.cs.

Usage: python docs/figures/make_figures.py      (paths relative to the repository root)
"""
import csv, json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = json.load(open(os.path.join(ROOT, 'analysis/results.json'), encoding='utf-8'))
C0 = R['concepts']['C0']
TEST_OUT = os.path.join(ROOT, 'docs/test/figures')
BUILD_OUT = os.path.join(ROOT, 'docs/build/img')

# one look for every diagram: white sheet, dark line work, orange = the item under test or being fitted,
# blue = instruments and measurements, grey = fixtures and the ground
INK, MUTED, LINE, GROUND, ORANGE, BLUE, PAPER = '#1f2328', '#57606a', '#8c959f', '#d0d7de', '#d9771e', '#2f6fdb', '#ffffff'
FONT = "font-family='IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif'"


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts = w, h, []
        self.title = title

    def add(self, s):
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, c=INK, w=2, dash=None, arrow=False):
        d = f" stroke-dasharray='{dash}'" if dash else ''
        m = " marker-end='url(#arr)'" if arrow else ''
        self.add(f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{c}' stroke-width='{w}'{d}{m}/>")

    def rect(self, x, y, w, h, fill='none', c=INK, sw=2, rx=3):
        self.add(f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{rx}' fill='{fill}' stroke='{c}' stroke-width='{sw}'/>")

    def circle(self, x, y, r, fill='none', c=INK, sw=2):
        self.add(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r:.1f}' fill='{fill}' stroke='{c}' stroke-width='{sw}'/>")

    def path(self, d, fill='none', c=INK, sw=2, dash=None):
        dd = f" stroke-dasharray='{dash}'" if dash else ''
        self.add(f"<path d='{d}' fill='{fill}' stroke='{c}' stroke-width='{sw}'{dd} stroke-linejoin='round'/>")

    def text(self, x, y, s, size=14, c=INK, anchor='start', weight=400):
        s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        self.add(f"<text x='{x:.1f}' y='{y:.1f}' {FONT} font-size='{size}' fill='{c}' text-anchor='{anchor}' font-weight='{weight}'>{s}</text>")

    def label(self, x, y, s, tx, ty, c=MUTED, anchor=None):
        """leader line from a point on the drawing to a text label; the text sits on the far side of the line's end
        (to the left when the label is left of the point) so the leader never runs through it"""
        anchor = anchor or ('end' if tx < x else 'start')
        self.line(x, y, tx, ty, c=LINE, w=1)
        self.text(tx + (4 if anchor == 'start' else -4), ty + 4, s, 13, c, anchor)

    def save(self, path):
        head = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' width='{self.w}' height='{self.h}' role='img'>"
                f"<title>{self.title}</title><defs><marker id='arr' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' orient='auto-start-reverse'>"
                f"<path d='M0 0 L10 5 L0 10 z' fill='{INK}'/></marker></defs><rect width='100%' height='100%' fill='{PAPER}'/>")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(head + ''.join(self.parts) + '</svg>\n')
        print('wrote', os.path.relpath(path, ROOT))


def legend(s, x, y, items):
    for i, (col, name) in enumerate(items):
        s.rect(x + i * 190, y - 11, 14, 14, fill=col, c=col, sw=1, rx=2)
        s.text(x + i * 190 + 20, y, name, 13, MUTED)


# ---------------------------------------------------------------- test plan
def thrust_stand():
    s = Svg(760, 380, 'Thrust stand: pivot beam with the motor on one arm and the load cell under the other (tests C06, C07)')
    s.rect(60, 300, 640, 14, fill=GROUND, c=GROUND)                                   # bench
    s.path('M330 300 L350 250 L370 300 Z', fill=GROUND, c=INK)                         # pivot
    s.line(150, 250, 550, 250, w=6)                                                   # beam
    s.circle(350, 250, 5, fill=INK)
    s.rect(140, 200, 40, 50, fill=ORANGE, c=INK)                                      # motor
    s.line(100, 194, 220, 194, c=ORANGE, w=5)                                         # prop
    s.line(160, 196, 160, 120, arrow=True)                                            # thrust up
    s.text(152, 140, 'thrust T', 13, INK, 'end')
    s.rect(525, 255, 50, 30, fill=BLUE, c=INK)                                        # load cell
    s.line(550, 285, 550, 300, w=3)
    s.line(540, 230, 540, 248, arrow=True)
    s.text(470, 222, 'arm presses the cell', 13, INK)
    s.label(350, 268, 'pivot, arms equal (1:1): T = cell reading', 380, 345)
    s.label(550, 262, '20 kg load cell + HX711 + Arduino Nano', 640, 196, anchor='end')
    s.label(180, 215, 'motor + prop under test', 200, 176, anchor='start')
    s.rect(610, 60, 120, 46, fill='none', c=BLUE)                                     # watt meter
    s.text(670, 88, 'watt meter', 13, BLUE, 'middle')
    s.rect(610, 130, 120, 40, fill='none', c=INK)
    s.text(670, 155, '6S pack', 13, INK, 'middle')
    s.path('M610 150 L450 150 L450 120 L180 120 L180 200', c=INK, sw=1.5, dash='5 4')
    s.text(300, 112, 'ESC power and signal (servo tester or FC motor test)', 12, MUTED, 'middle')
    s.line(670, 106, 670, 130, c=INK, w=1.5)
    s.text(60, 40, 'Calibrate with weighed water jugs at the motor station: 0, 0.5, 1, 2, 3, 5, 10 kg, up and down', 13, MUTED)
    s.text(60, 60, 'Pass: within 2 % of reading from 0.5 to 5 kg; drift under 20 g over 10 min', 13, MUTED)
    legend(s, 60, 365, [(ORANGE, 'item under test'), (BLUE, 'instrument'), (GROUND, 'fixture')])
    s.save(os.path.join(TEST_OUT, 'thrust_stand.svg'))


def car_roof():
    V = C0['params']['Vc']; kmh = V * 3.6; mph = V * 2.23694
    cda = 0.00222; F = 0.5 * 1.225 * V ** 2 * cda
    s = Svg(760, 360, 'Car-roof test: one stopped lift unit on a pivot arm above the car, unpowered, at cruise speed (test C10)')
    s.rect(40, 300, 680, 10, fill=GROUND, c=GROUND)
    s.path('M120 300 L120 250 Q130 210 200 205 L420 200 Q470 200 500 240 L560 250 Q600 255 600 300 Z', fill='#eef1f4', c=INK)  # car
    s.circle(200, 300, 24, fill='#ffffff'); s.circle(500, 300, 24, fill='#ffffff')
    s.line(300, 200, 300, 120, w=4)                                                    # mast
    s.line(260, 120, 360, 120, w=3)                                                   # arm
    s.circle(300, 120, 5, fill=INK)
    s.rect(240, 96, 28, 24, fill=ORANGE, c=INK)                                        # motor
    s.line(206, 93, 302, 93, c=ORANGE, w=4)                                            # prop parked along the flow
    s.rect(352, 120, 22, 38, fill=BLUE, c=INK)                                         # luggage scale
    s.line(363, 158, 363, 200, c=INK, w=2)
    for y in (70, 110, 150):                                                          # airflow
        s.line(720, y, 610, y, c=BLUE, w=1.5, arrow=True)
    s.text(690, 60, f'airflow {V:g} m/s', 13, BLUE, 'end')
    s.label(254, 93, 'stopped prop: note where it parks', 330, 62)
    s.label(363, 140, 'luggage scale reads the drag on the arm', 420, 170)
    s.label(300, 160, 'mast on the roof rack', 160, 160)
    s.text(40, 30, f'Drive at {V:g} m/s = {kmh:.0f} km/h = {mph:.0f} mph on a closed lot; film the prop', 13, MUTED)
    s.text(40, 345, f'Pass: no windmilling; prop parks within 30° of the airflow; drag ≤ 0.8 N (model {F:.2f} N at {V:g} m/s)', 13, MUTED)
    s.save(os.path.join(TEST_OUT, 'car_roof.svg'))


def proof_load():
    m, mw = C0['sized']['m'], C0['sized']['m_wing']
    total = 3.0 * (m - mw)
    st = [0.1, 0.3, 0.5, 0.7, 0.9, 1.1]
    # elliptic spanwise share per 0.2 m bin (same method as the test plan's data sheet)
    b2 = 1.2
    def area(a, b):
        f = lambda y: 0.5 * (y * math.sqrt(max(0, 1 - (y / b2) ** 2)) * b2 + b2 * b2 * math.asin(min(1, y / b2))) / b2
        return f(b) - f(a)
    bins = [area(max(0, y - 0.1), min(b2, y + 0.1)) for y in st]; tot = sum(bins)
    kg = [total / 2 * a / tot for a in bins]
    s = Svg(760, 360, 'Wing proof load: the wing inverted on two supports at the pod width with weighed loads at six stations per side (test S01)')
    cx, sc, y0 = 380, 280, 210
    s.rect(60, 300, 640, 12, fill=GROUND, c=GROUND)
    for dx in (-28, 28):
        s.path(f'M{cx+dx-14} 300 L{cx+dx} 220 L{cx+dx+14} 300 Z', fill=GROUND, c=INK)
    s.rect(cx - 1.2 * sc, y0, 2.4 * sc, 12, fill='#eef1f4', c=INK, rx=6)            # wing (inverted)
    for side in (-1, 1):
        for y, k in zip(st, kg):
            x = cx + side * y * sc; h = 14 + 26 * k / max(kg)
            s.rect(x - 11, y0 - h, 22, h, fill=ORANGE, c=INK, rx=2)
        s.line(cx + side * 1.2 * sc, y0 + 12, cx + side * 1.2 * sc, y0 + 60, c=BLUE, w=2)
        s.text(cx + side * 1.2 * sc, y0 + 78, 'tip gauge', 12, BLUE, 'middle')
    for y, k in zip(st, kg):
        s.text(cx + y * sc, y0 - 50, f'{k:.2f}', 12, INK, 'middle')
    s.text(cx + 1.2 * sc, y0 - 70, 'kg per station (each side)', 12, MUTED, 'end')
    s.label(cx - 28, 262, 'supports about 0.1 m each side of centre', cx - 60, 290)
    s.text(60, 32, f'Total {total:.1f} kg = 3.0 g × ({m:.2f} − {mw:.2f}) kg, spread elliptically along the span,', 13, MUTED)
    s.text(60, 50, 'every load on the spar line at 30 % chord.', 13, MUTED)
    s.text(60, 70, 'Load in 25 % steps, hold 100 % for 30 s, unload; read both tips at every step.', 13, MUTED)
    s.text(60, 345, 'Pass: tip deflection ≤ 120 mm, residual ≤ 2 mm, joiner straight, no foam crush, stops intact', 13, MUTED)
    s.save(os.path.join(TEST_OUT, 'proof_load.svg'))


def cg_weigh(out):
    chord = C0['sized']['chord']; tgt = C0['cg']['pct']['target']; xt = C0['cg']['thrustCentroid']
    s = Svg(760, 340, 'Weight and balance: the aircraft on two scales at known stations; the CG follows from the moments (tests G01, G09; build step 12.2)')
    s.rect(40, 290, 680, 10, fill=GROUND, c=GROUND)
    s.rect(140, 262, 90, 28, fill=BLUE, c=INK); s.text(185, 281, 'scale 1', 12, '#ffffff', 'middle')
    s.rect(520, 262, 90, 28, fill=BLUE, c=INK); s.text(565, 281, 'scale 2', 12, '#ffffff', 'middle')
    s.path('M90 205 Q100 170 180 168 L640 172 Q690 176 700 200 Q690 222 640 224 L180 230 Q100 230 90 205 Z', fill='#eef1f4', c=INK)  # pod/side view
    s.line(185, 228, 185, 262, w=3); s.line(565, 222, 565, 262, w=3)
    s.rect(300, 160, 200, 10, fill=ORANGE, c=INK)                                      # wing chord (side)
    xcg = 300 + 200 * tgt / 100
    s.path(f'M{xcg-9} 140 L{xcg+9} 140 L{xcg} 155 Z', fill=INK)
    s.text(xcg, 132, f'CG target {tgt:g} % MAC', 13, INK, 'middle')
    s.line(185, 310, 565, 310, c=MUTED, w=1)
    s.text(185, 326, 'x1', 13, MUTED, 'middle'); s.text(565, 326, 'x2', 13, MUTED, 'middle')
    s.text(60, 30, 'Weigh with the pack and the 0.5 kg ballast (or payload) fitted.', 13, MUTED)
    s.text(60, 48, 'x is measured from the wing leading edge, forward positive.', 13, MUTED)
    s.text(60, 72, 'x_CG = (W1 × x1 + W2 × x2) / (W1 + W2)', 15, INK, weight=500)
    s.text(60, 94, f'Pass: CG at {tgt:g} ± 2 % MAC (MAC {chord*1000:.1f} mm, so ± {0.02*chord*1000:.1f} mm) and never aft of 31.8 % MAC;', 13, MUTED)
    s.text(60, 112, f'CG within 20 mm of the thrust centroid, {xt*1000:.1f} mm from the leading edge.', 13, MUTED)
    s.save(out)


def tethered_hover():
    s = Svg(760, 330, 'Tethered hover: two slack tethers from stakes 3 m apart to the gear clamps; crew 10 m away (test G05)')
    s.rect(40, 270, 680, 10, fill=GROUND, c=GROUND)
    for x in (230, 530):
        s.path(f'M{x-6} 270 L{x} 290 L{x+6} 270 Z', fill=INK)
    s.rect(330, 150, 100, 18, fill=ORANGE, c=INK, rx=8)                              # aircraft (front view)
    s.line(250, 150, 510, 150, c=ORANGE, w=4)
    for x in (300, 460):
        s.line(x - 30, 140, x + 30, 140, c=ORANGE, w=3)
    s.path('M230 270 Q260 240 340 168', c=BLUE, sw=1.5, dash='6 4')                   # slack tethers
    s.path('M530 270 Q500 240 420 168', c=BLUE, sw=1.5, dash='6 4')
    s.line(380, 268, 380, 172, c=MUTED, w=1, arrow=True); s.text(390, 230, 'hover at 1 m', 13, MUTED)
    s.text(230, 306, 'stake', 12, MUTED, 'middle'); s.text(530, 306, 'stake', 12, MUTED, 'middle')
    s.text(380, 306, '3 m between stakes', 12, MUTED, 'middle')
    s.label(470, 200, '4 m lines, slack to 1.5 m: never taut', 700, 112, anchor='end')
    s.circle(690, 250, 9, fill='#ffffff', c=INK); s.text(690, 230, 'crew ≥ 10 m', 12, INK, 'middle')
    s.text(40, 34, 'QSTABILIZE: throttle up until light on the gear, back down; then 1 m for 30 s. Then QHOVER, 1 m, 30 s. Three cycles.', 13, MUTED)
    s.text(40, 54, 'Wind ≤ 3 m/s, grass, ballast fitted; motors under 45 °C between cycles.', 13, MUTED)
    s.text(40, 320, 'Pass: 30 s stable; attitude error < 15°; lift output < 60 %; vibration < 30; no oscillation', 13, MUTED)
    s.save(os.path.join(TEST_OUT, 'tethered_hover.svg'))


def stall_profile():
    Vc, Vs = C0['params']['Vc'], R['concepts']['C0']['params']['Vs']
    s = Svg(760, 340, 'Stall test profile: level at cruise, idle, slow down at no more than 0.3 m/s per second to the pitch break, recover (test F09)')
    l, r, t, b = 70, 720, 50, 280
    x = lambda tt: l + (r - l) * tt / 40.0
    y = lambda v: b - (b - t) * (v - 8) / (Vc + 2 - 8)
    for v in range(8, int(Vc) + 3, 2):
        s.line(l, y(v), r, y(v), c=GROUND, w=1); s.text(l - 8, y(v) + 4, str(v), 12, MUTED, 'end')
    s.add(f"<text transform='rotate(-90 22 {(t + b) / 2:.0f})' x='22' y='{(t + b) / 2:.0f}' {FONT} font-size='13' fill='{MUTED}' text-anchor='middle'>airspeed, m/s</text>")
    tbreak = 6 + (Vc - Vs) / 0.3
    pts = [(0, Vc), (6, Vc), (min(tbreak, 34), Vs), (min(tbreak, 34) + 2, Vs - 0.6), (40, Vc - 2)]
    s.path(' '.join(('M' if i == 0 else 'L') + f'{x(a):.1f} {y(v):.1f}' for i, (a, v) in enumerate(pts)), c=ORANGE, sw=3)
    s.line(l, y(12), r, y(12), c='#ad2a1f', w=1.5, dash='6 4'); s.text(r, y(12) - 6, 'R11 limit 12 m/s', 12, '#ad2a1f', 'end')
    s.line(l, y(16), r, y(16), c=BLUE, w=1.5, dash='3 3'); s.text(r, y(16) - 6, 'AIRSPEED_MIN 16 m/s', 12, BLUE, 'end')
    s.label(x(3), y(Vc), f'level at {Vc:g} m/s, ≥ 80 m above ground, Q_ASSIST off', x(4), t - 14, anchor='start')
    s.label(x(16), y(Vc - (16 - 6) * 0.3), 'idle, decelerate ≤ 0.3 m/s²', x(18), y(Vc) + 4)
    s.label(x(min(tbreak, 34)), y(Vs), f'pitch break: record airspeed (predicted {Vs:g} m/s)', x(min(tbreak, 34)) - 10, y(9.0), anchor='end')
    s.label(x(38), y(Vc - 2.4), 'recover: nose down, throttle up', x(35), y(19.2), anchor='end')
    s.text(40, 330, 'Three runs. Pass: measured stall ≤ 12.0 m/s; 12.0–12.5 team decision; above 12.5 fail. Height loss ≤ 30 m (estimate).', 13, MUTED)
    s.save(os.path.join(TEST_OUT, 'stall_profile.svg'))


def flight_buildup():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'docs/test/test-matrix.csv'), encoding='utf-8')))
    order = ['F01', 'F02', 'F03', 'F04', 'F05', 'F06', 'F07', 'F08', 'F13', 'F09', 'F10', 'F11', 'F12']
    T = {x['ID']: re.sub(r'\s*\((?:card|FTC|new|review)[^)]*\)', '', x['Title']) for x in rows}
    phase = {'F01': 'hover', 'F02': 'hover', 'F03': 'hover', 'F04': 'hover', 'F05': 'hover',
             'F06': 'transition', 'F07': 'transition', 'F08': 'cruise', 'F13': 'cruise', 'F09': 'cruise',
             'F10': 'cruise', 'F11': 'mission', 'F12': 'mission'}
    col = {'hover': '#e7f2ec', 'transition': '#f6efe1', 'cruise': '#e8f0fb', 'mission': '#f7ece6'}
    s = Svg(760, 550, 'Flight-test build-up: each flight only after the one before it passes (F01 to F12)')
    y = 30
    for i, k in enumerate(order):
        s.rect(60, y, 640, 30, fill=col[phase[k]], c=LINE, sw=1, rx=4)
        s.text(74, y + 20, k, 13, INK, weight=600)
        title = T.get(k, '')
        s.text(124, y + 20, title[:78] + ('…' if len(title) > 78 else ''), 13, INK)
        s.text(690, y + 20, phase[k], 12, MUTED, 'end')
        if i < len(order) - 1:
            s.line(40, y + 15, 40, y + 53, c=LINE, w=1.5, arrow=True)
        y += 37
    s.text(60, y + 12, 'Each flight uses its card in docs/test/cards/; stop the build-up at the first failed pass criterion.', 13, MUTED)
    s.save(os.path.join(TEST_OUT, 'flight_buildup.svg'))


# ---------------------------------------------------------------- build manual
def cut_diagram():
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'docs/build/cut-list.csv'), encoding='utf-8')))
    T = {r['id']: r for r in rows if r['id'].startswith('T')}
    num = lambda s: float(re.match(r'[\d.]+', s).group())
    stocks = [('72 in (1828.8 mm) 1.000 × 0.035 in tube, × 2', 1828.8, [('T01', 'boom front'), ('T02', 'boom stub')]),
              ('96 in (2438.4 mm) 1.000 × 0.058 in tube', 2438.4, [('T03', 'spar socket'), ('T03', 'spar socket')] + [('T04', 'leg')] * 4),
              ('36 in (914.4 mm) 0.875 × 0.058 in tube', 914.4, [('T05', 'wing joiner')])]
    kerf = 1.5
    s = Svg(780, 300, 'Tube cut diagram: how each stock tube is cut, with a 1.5 mm kerf per cut (cut list T01 to T05)')
    sc = 680 / 2438.4; y = 40
    for name, L, cuts in stocks:
        s.text(40, y, name, 13, INK, weight=600)
        x = 40; s.rect(40, y + 10, L * sc, 34, fill='#eef1f4', c=LINE, sw=1, rx=2)
        for cid, lab in cuts:
            w = num(T[cid]['cut_len_mm']) * sc
            s.rect(x, y + 10, w, 34, fill=ORANGE if cid in ('T01', 'T03', 'T05') else '#f2b880', c=INK, sw=1, rx=2)
            if w > 46:
                s.text(x + w / 2, y + 26, cid, 12, INK, 'middle', 600)
                s.text(x + w / 2, y + 40, f"{num(T[cid]['cut_len_mm']):g}", 11, INK, 'middle')
            x += w + kerf * sc
        left = L - sum(num(T[c]['cut_len_mm']) for c, _ in cuts) - kerf * len(cuts)
        ox = 40 + L * sc + 8
        if ox > 700: s.text(40 + L * sc, y + 4, f'offcut {left:.0f} mm', 12, MUTED, 'end')
        else: s.text(ox, y + 32, f'offcut {left:.0f} mm', 12, MUTED)
        y += 80
    s.text(40, 284, 'Lengths in mm from docs/build/cut-list.csv; cut T01 and T02 from each 72 in tube so the splice faces are factory-square. Deburr every cut.', 12, MUTED)
    s.save(os.path.join(BUILD_OUT, 'fig03_cut_diagram.svg'))


def wiring_diagram(hl=None, out=None, note=None):
    """the wiring overview; with hl (a set of circuit IDs) those circuits are drawn orange and the rest faded,
    so each electrical step shows exactly which wires it means"""
    FADE = '#c4c9cf'
    on = lambda tags: hl is None or bool(set(tags) & hl)
    s = Svg(800, 540 if note else 520, 'Wiring overview' + (f': {note}' if note else ': power from the packs through the power board to five ESCs, and signals from the flight controller'))
    y0 = 24 if note else 0
    if note: s.text(30, 22, note, 14, ORANGE, weight=600)
    def box(tags, x, y, w, h, t1, t2=None, fill='#ffffff'):
        lit = on(tags); hot = hl is not None and lit
        s.rect(x, y + y0, w, h, fill=('#fbe9da' if hot else fill) if lit else '#f6f7f8', c=(ORANGE if hot else INK) if lit else FADE, sw=2.5 if hot else 1.5, rx=4)
        s.text(x + w / 2, y + y0 + (h / 2 if not t2 else h / 2 - 4), t1, 13, INK if lit else FADE, 'middle', 600)
        if t2: s.text(x + w / 2, y + y0 + h / 2 + 13, t2, 11, MUTED if lit else FADE, 'middle')
    def ln(tags, x1, y1, x2, y2, w=2, signal=False, arrow=False):
        lit = on(tags); hot = hl is not None and lit
        c = (ORANGE if hot else (BLUE if signal else INK)) if lit else FADE
        s.line(x1, y1 + y0, x2, y2 + y0, c=c, w=(w + 1.5) if hot else w, dash='5 4' if signal else None, arrow=arrow and lit)
    MS = ['M01', 'M02', 'M03', 'M04', 'M05']; SS = ['S01', 'S02', 'S03', 'S04', 'S11']; AA = ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A08']
    box(['W01'], 30, 40, 150, 50, 'two 6S 6500 packs', 'XT90-S, W01', '#f7ece6')
    box(['W02', 'W03', 'W06'], 240, 40, 190, 50, 'power board (PDB)', 'on the CoreWing F405, W02', '#eef1f4')
    box(MS + SS + AA, 240, 200, 190, 70, 'flight controller', 'CoreWing F405 Wing V2', '#e8f0fb')
    ln(['W01', 'W02'], 180, 65, 240, 65, w=3, arrow=True); s.text(210, 58 + y0, '10 AWG', 11, MUTED if on(['W01', 'W02']) else FADE, 'middle')
    ln(['A06'], 335, 90, 335, 200, w=1.5); s.text(342, 150 + y0, 'board power', 11, MUTED if on(['A06']) else FADE)
    names = ['M1 front-right', 'M2 rear-left', 'M3 front-left', 'M4 rear-right']
    for i, n in enumerate(names):
        y = 30 + i * 60
        box(['W03', 'W04', MS[i]], 520, y, 120, 44, 'lift ESC 45 A', 'W03 + W04, 12 AWG')
        box(['W05'], 670, y, 110, 44, n, 'X4110S, W05')
        ln(['W03', 'W04'], 430, 65, 520, y + 22, arrow=True); ln(['W05'], 640, y + 22, 670, y + 22)
    box(['W06', 'W07', 'M05'], 520, 270, 120, 44, 'pusher ESC 45 A', 'W06, 14 AWG'); box(['W07'], 670, 270, 110, 44, 'pusher', 'X4110S, W07')
    ln(['W06'], 430, 70, 520, 292, arrow=True); ln(['W07'], 640, 292, 670, 292)
    ln(MS, 430, 235, 512, 235, w=1.5, signal=True); s.text(438, 228 + y0, 'DShot', 12, (ORANGE if hl and on(MS) else BLUE) if on(MS) else FADE)
    sigs = [(SS, '5 servos S1–S4, S11', 'ailerons, elevator, rudders'), (['A01'], 'GPS + compass A01', 'HGLRC M100-5883'), (['A02'], 'receiver A02', 'RadioMaster RP3 V2'),
            (['A03'], 'Remote ID A03', 'BeeID, 5 V only'), (['A04', 'A05'], 'airspeed A04 + A05', 'MS5525 + PT40 pitot')]
    for i, (tags, a, b) in enumerate(sigs):
        x = 30 + i * 154
        box(tags, x, 400, 140, 50, a, b); ln(tags, 335, 270, x + 70, 400, w=1.2, signal=True)
    s.text(30, 478 + y0, 'Solid lines carry battery power; dashed lines are signals (DShot M01–M05 from the flight controller to the five ESCs).', 12, MUTED)
    s.text(30, 496 + y0, 'Circuit IDs match docs/build/wiring.csv, which gives gauge, length, connector and termination for each one.', 12, MUTED)
    s.text(30, 514 + y0, 'Motor numbers and spin directions follow ArduPilot Quad X (build step 7.2).', 12, MUTED)
    s.save(out or os.path.join(BUILD_OUT, 'fig09_wiring.svg'))


WIRE_STEPS = {  # build step -> circuits it wires (docs/build/wiring.csv IDs, from the step titles)
    '9.2': ({'W01'}, 'W01: the packs re-terminated to XT90-S'),
    '9.3': ({'W02'}, 'W02: battery pigtail to the power board'),
    '9.4': ({'W03', 'W04'}, 'W03 + W04: the four lift ESC feeds'),
    '9.5': ({'W05', 'W07'}, 'W05 + W07: motor phase leads'),
    '9.6': ({'W06'}, 'W06: pusher ESC feed'),
    '9.7': ({'M01', 'M02', 'M03', 'M04', 'M05'}, 'M01 to M05: DShot signal leads to the five ESCs'),
    '9.8': ({'S01', 'S02', 'S03', 'S04', 'S11'}, 'S01 to S11: servo leads'),
    '9.9': ({'A01', 'A02', 'A03', 'A04', 'A05', 'A08'}, 'A01 to A04, A08: avionics power and data'),
    '10.2': ({'A01'}, 'A01: GPS and compass'), '10.3': ({'A02'}, 'A02: receiver'), '10.4': ({'A03'}, 'A03: Remote ID'),
}


def wiring_steps():
    for st, (hl, note) in WIRE_STEPS.items():
        wiring_diagram(hl, os.path.join(BUILD_OUT, 'wire_' + st.replace('.', '_') + '.svg'), 'Step ' + st + ' highlighted: ' + note)

if __name__ == '__main__':
    # thrust stand, car roof, proof load, weighing and tethered hover are now photoreal renders (render_scenes.py + annotate.py);
    # their schematic versions above are kept only as fallbacks and are not written here
    stall_profile(); flight_buildup()
    cut_diagram(); wiring_diagram(); wiring_steps()
