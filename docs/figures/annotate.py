"""Annotated figures from the Blender renders: numbered callouts at the features render_scenes.py located, a key,
and a caption band with the procedure and pass criterion. Writes JPEG-backed SVGs (one self-contained file each).

Usage: python docs/figures/annotate.py      (after render_scenes.py; paths relative to the repository root)
"""
import base64, io, json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, 'docs/figures/renders')
R = json.load(open(os.path.join(ROOT, 'analysis/results.json'), encoding='utf-8'))
C0 = R['concepts']['C0']
INK, MUTED, ACCENT, PAPER = '#1f2328', '#57606a', '#d9771e', '#ffffff'
FONT = "font-family='IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif'"
OUTW = 1400                                   # output width; the render is scaled to it


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def figure(scene, title, callouts, lines, out):
    """callouts: [(anchor key or (x, y) in render pixels, label, dx, dy)], label box offset from the anchor in output px"""
    meta = json.load(open(os.path.join(REN, scene + '.json'), encoding='utf-8'))
    rw, rh = meta['size']; k = OUTW / rw; ih = round(rh * k)
    im = Image.open(os.path.join(REN, scene + '.png')).convert('RGB').resize((OUTW, ih), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=86, optimize=True, progressive=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    band = 34 + 26 * len(lines)
    H = ih + band
    p = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {OUTW} {H}' width='{OUTW}' height='{H}' role='img'><title>{esc(title)}</title>",
         f"<rect width='100%' height='100%' fill='{PAPER}'/>",
         f"<image href='data:image/jpeg;base64,{b64}' x='0' y='0' width='{OUTW}' height='{ih}'/>"]
    for n, (anc, label, dx, dy) in enumerate(callouts, 1):
        ax, ay = (meta['anchors'][anc] if isinstance(anc, str) else anc)
        ax, ay = ax * k, ay * k
        tx, ty = ax + dx, ay + dy
        w = 18 + 7.9 * len(label)
        bx = tx if dx >= 0 else tx - w
        p.append(f"<line x1='{ax:.0f}' y1='{ay:.0f}' x2='{tx:.0f}' y2='{ty:.0f}' stroke='{PAPER}' stroke-width='4' opacity='0.85'/>")
        p.append(f"<line x1='{ax:.0f}' y1='{ay:.0f}' x2='{tx:.0f}' y2='{ty:.0f}' stroke='{INK}' stroke-width='1.6'/>")
        p.append(f"<circle cx='{ax:.0f}' cy='{ay:.0f}' r='5' fill='{ACCENT}' stroke='{PAPER}' stroke-width='2'/>")
        p.append(f"<rect x='{bx:.0f}' y='{ty - 17:.0f}' width='{w + 26:.0f}' height='34' rx='6' fill='{PAPER}' fill-opacity='0.94' stroke='#d0d7de'/>")
        p.append(f"<circle cx='{bx + 17:.0f}' cy='{ty:.0f}' r='11' fill='{ACCENT}'/>")
        p.append(f"<text x='{bx + 17:.0f}' y='{ty + 5:.0f}' {FONT} font-size='14' font-weight='600' fill='{PAPER}' text-anchor='middle'>{n}</text>")
        p.append(f"<text x='{bx + 36:.0f}' y='{ty + 6:.0f}' {FONT} font-size='16' fill='{INK}'>{esc(label)}</text>")
    p.append(f"<rect x='0' y='{ih}' width='{OUTW}' height='{band}' fill='#f6f8fa'/><line x1='0' x2='{OUTW}' y1='{ih}' y2='{ih}' stroke='#d0d7de'/>")
    for i, (txt, strong) in enumerate(lines):
        p.append(f"<text x='24' y='{ih + 30 + 26 * i}' {FONT} font-size='{17 if strong else 16}' font-weight='{600 if strong else 400}' fill='{INK if strong else MUTED}'>{esc(txt)}</text>")
    p.append('</svg>\n')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8', newline='\n').write(''.join(p))
    print('wrote', os.path.relpath(out, ROOT), f'{os.path.getsize(out) / 1024:.0f} kB')


def plain(scene, out, width=1400):
    """a render as a plain JPEG (no callouts), for figures whose caption carries the explanation"""
    im = Image.open(os.path.join(REN, scene + '.png')).convert('RGB')
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(out), exist_ok=True); im.save(out, 'JPEG', quality=86, optimize=True, progressive=True)
    print('wrote', os.path.relpath(out, ROOT), f'{os.path.getsize(out) / 1024:.0f} kB')


def main():
    V = C0['params']['Vc']; cda = 0.00222; F = 0.5 * 1.225 * V ** 2 * cda
    chord = C0['sized']['chord']; tgt = C0['cg']['pct']['target']; xt = C0['cg']['thrustCentroid']
    m, mw = C0['sized']['m'], C0['sized']['m_wing']; total = 3.0 * (m - mw)
    T = os.path.join(ROOT, 'docs/test/figures'); B = os.path.join(ROOT, 'docs/build/img')
    plain('studio', os.path.join(B, 'fig00_render.jpg'))

    cg = dict(scene='cg_weigh', title='Weight and balance: the front and rear legs each on a board across one kitchen scale',
              callouts=[('scale1', 'Scale 1: front legs on a board', 120, 150), ('scale2', 'Scale 2: rear legs on a board', -170, 190),
                        ('cg', f'CG target {tgt:g} % MAC', 60, -110)],
              lines=[('x_CG = (W1 × x1 + W2 × x2) / (W1 + W2), with x measured from the wing leading edge', True),
                     ('Weigh with the pack and the 0.5 kg ballast (or payload) fitted; x1 and x2 are the gear stations.', False),
                     (f'Pass: CG at {tgt:g} ± 2 % MAC (± {0.02 * chord * 1000:.1f} mm), never aft of 31.8 % MAC, within 20 mm of the thrust centroid ({xt * 1000:.1f} mm).', False)])
    figure(out=os.path.join(T, 'cg_weigh.svg'), **cg); figure(out=os.path.join(B, 'fig12_cg_weigh.svg'), **cg)

    figure('tethered', 'Tethered hover: slack tethers from two stakes to the front gear clamps', [
        ('aircraft', 'Hover at 1 m: QSTABILIZE, then QHOVER', 90, -150),
        ('tether1', '4 m tether, slack to 1.5 m', 150, 40), ('stake1', 'Stake', 120, 30)], [
        ('Three cycles of 30 s at 1 m; crew 10 m away; wind 3 m/s or less; ballast fitted.', True),
        ('Throttle up until light on the gear and back down before the first lift; motors below 45 °C between cycles.', False),
        ('Pass: 30 s stable, attitude error under 15°, lift output under 60 %, vibration under 30, tethers never taut.', False)],
        os.path.join(T, 'tethered_hover.svg'))

    figure('thrust_stand', 'Thrust stand: the lift unit on one arm of a pivot beam, the load cell under the other', [
        ('motor', 'Lift unit under test (X4110S, 17 in prop)', -40, -140),
        ('pivot', 'Pivot: arms equal, so thrust = cell reading', 60, -120),
        ('cell', '20 kg load cell', 60, -90),
        ('hx711', 'HX711 + Arduino Nano', 60, -80),
        ('esc', 'ESC: servo tester or FC motor test', -60, 70)], [
        ('Calibrate with weighed water jugs at the motor station: 0, 0.5, 1, 2, 3, 5 and 10 kg, up and down.', True),
        ('Watt meter in the pack lead; tare with the motor and prop fitted; brace the stand if it flexes under 3 kgf.', False),
        ('Pass: within 2 % of reading from 0.5 to 5 kg; hysteresis 1 % or less; drift under 20 g over 10 min.', False)],
        os.path.join(T, 'thrust_stand.svg'))

    figure('car_roof', f'Car-roof test: one stopped lift unit on a pivot arm above the roof at {V:g} m/s', [
        ('prop', 'Stopped prop: note where it parks', 40, -110),
        ('scale', 'Luggage scale reads the drag on the arm', 70, 60),
        ('mast', 'Mast on the roof rack', -60, 120)], [
        (f'Unpowered, {V:g} m/s = {V * 3.6:.0f} km/h = {V * 2.23694:.0f} mph on a closed lot; film the prop; the driver only drives.', True),
        ('Repeat with the prop set along the flow and across it: the literature puts the difference at 25 to 30 %.', False),
        (f'Pass: no windmilling; the prop parks within 30° of the airflow; drag 0.8 N or less (model {F:.2f} N).', False)],
        os.path.join(T, 'car_roof.svg'))

    figure('proof_load', 'Wing proof load: the wing inverted on padded supports, weighed bags along the spar line', [
        ('bag', 'Weighed bags at six stations per side', 40, -120),
        ('support', 'Padded supports, about 0.1 m each side of centre', 60, 90),
        ('tip-1', 'Tip gauge', -40, 90)], [
        (f'Total {total:.1f} kg = 3.0 g × ({m:.2f} − {mw:.2f}) kg, elliptic along the span: 1.64 / 1.59 / 1.49 / 1.33 / 1.08 / 0.62 kg per side.', True),
        ('Load in 25 % steps, hold 100 % for 30 s, unload; read both tips at every step; nobody under the wing.', False),
        ('Pass: tip deflection 120 mm or less, residual 2 mm or less, joiner straight, no foam crush, stops intact.', False)],
        os.path.join(T, 'proof_load.svg'))


if __name__ == '__main__':
    main()
