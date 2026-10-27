"""Callouts and captions for the step renders (docs/figures/renders/steps/*.png + .json from render_steps.py).
Numbered markers on the picture and a numbered legend under it, set large enough to read at half size; the caption band
takes the step's own title and Check line from the build manual (b_*) or the test's Pass line from the test plan (t_*).
Output: docs/build/img/<id>.svg and docs/test/figures/<id>.svg (one self-contained file each, JPEG inside).

Usage: python docs/figures/annotate_steps.py [ids...]
"""
import base64, glob, io, json, os, re, sys, textwrap
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REN = os.path.join(ROOT, 'docs/figures/renders/steps')
INK, MUTED, ACCENT, PAPER, EDGE = '#1f2328', '#57606a', '#d9771e', '#ffffff', '#d0d7de'
FONT = "font-family='IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif'"
OUTW = 1400


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def plain(md):
    md = re.sub(r'\*\(calc[^)]*\)\*', '', md)
    md = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', md)
    md = re.sub(r'[`*]', '', md)
    md = re.sub(r'\(([^()]*(?:review|cad/|docs/|analysis/|hardware-spec|params|aero_results)[^()]*)\)', '', md)
    return re.sub(r'\s+', ' ', md).strip(' ;')


def manual_step(no):
    L = open(os.path.join(ROOT, 'docs/build/BUILD-MANUAL.md'), encoding='utf-8').read().split('\n')
    for i, l in enumerate(L):
        m = re.match(r'\*\*' + re.escape(no) + r' (.+?)\*\*', l)
        if m:
            title, check = m.group(1).rstrip('.'), ''
            for k in range(i + 1, min(i + 14, len(L))):
                if L[k].startswith('**') or L[k].startswith('#'): break
                c = re.match(r'- Check[^:]*:\s*(.*)', L[k])
                if c: check = c.group(1)
            return plain(title), plain(check)
    return no, ''


def test_pass(tid):
    T = open(os.path.join(ROOT, 'docs/test/TEST-PLAN.md'), encoding='utf-8').read().split('\n')
    for i, l in enumerate(T):
        if l.startswith('#### ' + tid + ' '):
            title = re.sub(r'^#### \S+ [—–-] ', '', l)
            for k in range(i + 1, min(i + 20, len(T))):
                if T[k].startswith('#'): break
                p = re.match(r'- \*\*Pass\.\*\*\s*(.*)', T[k])
                if p: return plain(title), plain(p.group(1))
            return plain(title), ''
        if l.startswith('| ' + tid + ' |'):
            c = [x.strip() for x in l.strip('|').split('|')]
            return plain(c[1]), plain(c[4] if len(c) > 4 else '')
    return tid, ''


# The figures show at about half their width in the companion pages (a 690 px column), so text is set large:
# numbered markers on the full-width picture and the callouts as a numbered legend under it.
FS = 26            # legend font size (about 13 px on screen)
CH = 44            # characters per legend line (two columns)


def wrap(text, width):
    return textwrap.wrap(text, width) or ['']


def build(fid):
    meta = json.load(open(os.path.join(REN, fid + '.json'), encoding='utf-8'))
    rw, rh = meta['size']; k = OUTW / rw; ih = round(rh * k)
    im = Image.open(os.path.join(REN, fid + '.png')).convert('RGB').resize((OUTW, ih), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=86, optimize=True, progressive=True)
    if fid.startswith('b_'):
        no = fid[2:].replace('_', '.'); title, sub = manual_step(no); head = f'Step {no}: {title}'; sub = ('Check: ' + sub) if sub else ''
        out = os.path.join(ROOT, 'docs/build/img', fid + '.svg')
    else:
        tid = fid[2:].upper(); title, sub = test_pass(tid); head = f'{tid}: {title}'; sub = ('Pass: ' + sub) if sub else ''
        out = os.path.join(ROOT, 'docs/test/figures', fid + '.svg')
    # markers numbered top to bottom, then left to right, so the legend reads in picture order
    labs = sorted(meta['labels'], key=lambda L: (round(L['y'] / 120), L['x']))
    items = [(n, wrap(L['text'], CH)) for n, L in enumerate(labs, 1)]
    half = (len(items) + 1) // 2 if len(items) > 2 else len(items)
    cols = [items[:half], items[half:]] if len(items) > 2 else [items, []]
    lh = FS * 1.3; colh = [sum(len(r) * lh + 14 for _, r in c) for c in cols]
    legend = (28 + max(colh)) if items else 0
    lines = [(l, True) for l in wrap(head, 80)[:2]] + [(l, False) for l in wrap(sub, 96)[:3]]
    band = 28 + 36 * len(lines); H = ih + legend + band
    p = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {OUTW} {H}' width='{OUTW}' height='{H}' role='img'><title>{esc(head)}</title>",
         f"<rect width='100%' height='100%' fill='{PAPER}'/>",
         f"<image href='data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}' x='0' y='0' width='{OUTW}' height='{ih}'/>"]
    placed = []
    for n, L in enumerate(labs, 1):
        px, py = L['x'] * k, L['y'] * k; x, y = px, py
        # a marker that would cover an earlier one steps aside (right, then down) on a short leader to its point
        for dx, dy in ((0, 0), (46, 0), (-46, 0), (0, 46), (0, -46), (46, 46), (-46, 46), (46, -46), (-46, -46), (92, 0), (-92, 0)):
            x, y = min(OUTW - 22, max(22, px + dx)), min(ih - 22, max(22, py + dy))
            if all((x - qx) ** 2 + (y - qy) ** 2 >= 44 ** 2 for qx, qy in placed): break
        placed.append((x, y))
        if (x, y) != (px, py):
            p.append(f"<line x1='{px:.0f}' y1='{py:.0f}' x2='{x:.0f}' y2='{y:.0f}' stroke='{PAPER}' stroke-width='5'/><line x1='{px:.0f}' y1='{py:.0f}' x2='{x:.0f}' y2='{y:.0f}' stroke='{INK}' stroke-width='2'/>"
                     f"<circle cx='{px:.0f}' cy='{py:.0f}' r='6' fill='{ACCENT}' stroke='{PAPER}' stroke-width='2'/>")
        p.append(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='19' fill='{ACCENT}' stroke='{PAPER}' stroke-width='3.5'/>"
                 f"<text x='{x:.0f}' y='{y + 8:.0f}' {FONT} font-size='22' font-weight='700' fill='{PAPER}' text-anchor='middle'>{n}</text>")
    y0 = ih + 24
    for c, col in enumerate(cols):
        x0, y = 28 + c * OUTW / 2, y0
        for n, rows in col:
            p.append(f"<circle cx='{x0 + 17:.0f}' cy='{y + FS * 0.62:.0f}' r='16' fill='{ACCENT}'/><text x='{x0 + 17:.0f}' y='{y + FS * 0.62 + 7:.0f}' {FONT} font-size='19' font-weight='700' fill='{PAPER}' text-anchor='middle'>{n}</text>")
            for j, r in enumerate(rows):
                p.append(f"<text x='{x0 + 46:.0f}' y='{y + FS * 0.95 + lh * j:.0f}' {FONT} font-size='{FS}' fill='{INK}'>{esc(r)}</text>")
            y += len(rows) * lh + 14
    yb = ih + legend
    p.append(f"<rect x='0' y='{yb}' width='{OUTW}' height='{band}' fill='#f6f8fa'/><line x1='0' x2='{OUTW}' y1='{yb}' y2='{yb}' stroke='{EDGE}' stroke-width='2'/>")
    if items: p.append(f"<line x1='0' x2='{OUTW}' y1='{ih}' y2='{ih}' stroke='{EDGE}' stroke-width='2'/>")
    for i, (t, strong) in enumerate(lines):
        p.append(f"<text x='28' y='{yb + 44 + 36 * i}' {FONT} font-size='{29 if strong else 25}' font-weight='{600 if strong else 400}' fill='{INK if strong else MUTED}'>{esc(t)}</text>")
    p.append('</svg>\n')
    open(out, 'w', encoding='utf-8', newline='\n').write(''.join(p))
    return out


if __name__ == '__main__':
    ids = sys.argv[1:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(REN, '*.json')))
    for fid in ids:
        out = build(fid); print('wrote', os.path.relpath(out, ROOT), f'{os.path.getsize(out) / 1024:.0f} kB')
