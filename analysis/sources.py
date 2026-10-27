"""Source register: every URL cited anywhere in the repository, with the files that cite it, the date it was
checked (where the citation states one) and a category from the citing file. Writes analysis/sources.json, which
review/build.mjs embeds as the review's Sources section.

The key sources (the ones the design depends on most) are listed by hand in analysis/sources_key.json with the
reason each matters; this script checks that every key URL is also cited somewhere in the repository.

Usage: python analysis/sources.py      (from any directory; paths are relative to the repository root)
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# generated pages and bulk data are not citations; the review's own HTML is built from the files scanned here
SKIP = re.compile(r'^(VTOL-Review|build-manual|test-plan|flight-software|templates)\.html$|^review/.*\.html$|'
                  r'thermal_results|/flowviz/|^cad/mesh/|/archive_|^analysis/sources\.json$|^analysis/sources_key\.json$|^analysis/link_status\.json$|^analysis/check_links\.py$|^docs/superpowers/')
EXT = ('.md', '.csv', '.json', '.py', '.mjs', '.param', '.parm', '.txt', '.cs', '.ps1', '.yml')
URL = re.compile('https?://[^\\s\\]"\'<>`|,…]+')   # ')' allowed (clean() drops an unbalanced trailing one); an ellipsis ends a truncated URL
DATE = re.compile(r'(?:checked|accessed|retrieved)\D{0,12}(20\d\d-\d\d-\d\d)', re.I)
ANYDATE = re.compile(r'\b(20\d\d-\d\d-\d\d)\b')
MDLINK = re.compile(r'\[([^\]]{3,160})\]\((https?://[^)\s]+)\)')

# category from the citing file, most specific first
CATS = [
    (r'^docs/research/(benchmarks|review-formats)|^analysis/benchmarks/|^analysis/cruise_speed', 'Benchmarks and literature'),
    (r'^docs/research/aerodynamics|^docs/research/stall-margin|^analysis/aero/|^analysis/geometry|^analysis/vlm', 'Aerodynamics and CFD'),
    (r'^docs/research/thermal|^analysis/thermal/', 'Thermal'),
    (r'^docs/research/configurations|^docs/DESIGN-BASIS|^analysis/tradestudy', 'Configuration and trade study'),
    (r'^docs/research/(airframe-materials|budget-airframe)', 'Airframe and materials'),
    (r'^docs/research/(lift-propulsion|budget-lift|pusher-battery-servo|budget-energy-test)', 'Propulsion and energy'),
    (r'^docs/research/(avionics-autopilot|budget-avionics|firmware)|^firmware/', 'Avionics and flight software'),
    (r'^docs/research/hardware-spec|^cad/', 'Hardware, fasteners and CAD'),
    (r'^docs/build/|^docs/test/', 'Build and test'),
    (r'^docs/purchasing/|^analysis/export_bom|^analysis/sizing', 'Purchasing and sizing'),
]
ORDER = [c for _, c in CATS] + ['Other']


def category(path):
    for pat, name in CATS:
        if re.search(pat, path):
            return name
    return 'Other'


def clean(url):
    url = url.rstrip('.;:!?*_')
    while url.endswith(')') and url.count('(') < url.count(')'):
        url = url[:-1]
    return url


def snippet(line, url):
    t = line.replace(url, ' ')
    t = re.sub(r'\[([^\]]*)\]\(\s*\)', r'\1', t)
    t = re.sub(r'[*`#>|]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip(' -:;,()')
    return (t[:157] + '...') if len(t) > 160 else t


def main():
    files = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True).stdout.split('\n')
    files = sorted(f for f in files if f.endswith(EXT) and not SKIP.search(f) and os.path.isfile(f))
    reg = {}
    for f in files:
        try:
            lines = open(f, encoding='utf-8').read().split('\n')
        except UnicodeDecodeError:
            continue
        # a file that states one check date for its links (in its first 40 lines) gives undated citations that date
        head = re.search(r'(?:checked|accessed|retrieved|read live|live pages).{0,40}?(20\d\d-\d\d-\d\d)', ' '.join(lines[:40]), re.I)
        fdate = head.group(1) if head else None
        for i, line in enumerate(lines):
            if 'http' not in line:
                continue
            titles = {clean(u): t.strip() for t, u in MDLINK.findall(line)}
            for raw in URL.findall(line):
                u = clean(raw)
                if len(u) < 12 or re.search(r'localhost|127\.0\.0\.1|example\.(com|org)|^https?://fonts\.(googleapis|gstatic)\.com', u):   # the page's font files are not sources
                    continue
                e = reg.setdefault(u, {'url': u, 'files': [], 'checked': None, 'checkedFrom': None, 'title': None, 'context': None})
                if f not in e['files']:
                    e['files'].append(f)
                near = ' '.join(lines[max(0, i - 1):i + 2])
                m = DATE.search(line) or DATE.search(near) or ANYDATE.search(line)
                if m and (e['checked'] is None or e.get('checkedFrom') == 'file' or m.group(1) > e['checked']):
                    e['checked'] = m.group(1); e['checkedFrom'] = 'citation'
                elif not m and fdate and e['checked'] is None:
                    e['checked'] = fdate; e['checkedFrom'] = 'file'
                if not e['title'] and titles.get(u):
                    e['title'] = titles[u]
                if not e['context']:
                    e['context'] = snippet(line, raw)
    out = []
    for e in reg.values():
        e['domain'] = re.sub(r'^www\.', '', re.match(r'https?://([^/]+)', e['url']).group(1).lower())
        e['category'] = min((category(f) for f in e['files']), key=ORDER.index)
        out.append(e)
    out.sort(key=lambda e: (ORDER.index(e['category']), e['domain'], e['url']))

    key = json.load(open('analysis/sources_key.json', encoding='utf-8')) if os.path.exists('analysis/sources_key.json') else []
    urls = {e['url'] for e in out}
    missing = [k['url'] for k in key if k['url'] not in urls]
    if missing:
        print('key sources not cited anywhere in the repository:', *missing, sep='\n  ')
        sys.exit(1)

    # link status from analysis/check_links.py (run separately: it needs the network); a URL it has not seen stays unchecked
    LS = json.load(open('analysis/link_status.json', encoding='utf-8')) if os.path.exists('analysis/link_status.json') else {'links': {}, 'checked': None}
    for e in out:
        st = LS['links'].get(e['url'])
        if st: e['link'] = {k: st[k] for k in ('status', 'code', 'archive', 'checked') if st.get(k) is not None}
    linkc = {s_: sum(1 for e in out if e.get('link', {}).get('status') == s_) for s_ in ('ok', 'dead', 'unverified')}
    linkc['unchecked'] = sum(1 for e in out if 'link' not in e)
    res = {'note': 'generated by analysis/sources.py from the URLs cited in the repository; key sources from analysis/sources_key.json; link status from analysis/check_links.py',
           'count': len(out), 'linkCheck': {'date': LS.get('checked'), 'counts': linkc}, 'categories': [c for c in ORDER if any(e['category'] == c for e in out)],
           'key': key, 'sources': out}
    with open('analysis/sources.json', 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    by = {}
    for e in out:
        by[e['category']] = by.get(e['category'], 0) + 1
    print(len(out), 'sources;', ', '.join(f'{c} {n}' for c, n in by.items()))


if __name__ == '__main__':
    main()
