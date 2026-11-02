"""Liveness check of every http(s) URL cited in the repo docs and data.

Scans docs/**/*.md, cad/hardware.json, analysis/*.json and analysis/*.mjs, dedupes the URLs, and requests each
one politely (HEAD, falling back to GET; 15 s timeout; browser User-Agent; 4 workers; >= 0.3 s between requests
to the same host). Writes analysis/validation/link_check.json.

This is liveness only: "ok" means the server answered 2xx/3xx, not that the page still states the cited value
(see analysis/validation/source_audit.json for the value-by-value check).

Status per URL:
  ok           2xx/3xx after redirects
  dead         404 / 410, or the host does not resolve
  blocked      401 / 403 / 429 / 999 (site refused an automated request; may work in a browser)
  server_error 5xx
  error        timeout, TLS or connection error
  http_<code>  any other 4xx

Usage: py analysis/validation/link_check.py
"""
import glob, json, os, re, socket, ssl, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'analysis', 'validation', 'link_check.json')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/126.0 Safari/537.36')
TIMEOUT = 15
WORKERS = 4
HOST_GAP_S = 0.3
URL_RE = re.compile(r'https?://[^\s<>"\'`\]|]+')  # ')' allowed; unbalanced trailing ')' is trimmed in clean()
SKIP_HOSTS = {'www.w3.org'}  # XML namespace identifiers, not cited sources


def source_files():
    pats = ['docs/**/*.md', 'cad/hardware.json', 'analysis/*.json', 'analysis/*.mjs']
    files = set()
    for p in pats:
        files.update(glob.glob(os.path.join(ROOT, p), recursive=True))
    return sorted(files)


def clean(u):
    u = u.rstrip('.,;:*_\\')
    # balance a trailing ')' that belongs to markdown, keep ones that are part of the URL
    while u.endswith(')') and u.count('(') < u.count(')'):
        u = u[:-1]
    return u


def extract():
    found = {}
    for f in source_files():
        rel = os.path.relpath(f, ROOT).replace('\\', '/')
        with open(f, encoding='utf-8', errors='replace') as fh:
            for i, line in enumerate(fh, 1):
                for m in URL_RE.finditer(line):
                    raw = m.group(0)
                    if raw.endswith('...') or raw.endswith('…'):
                        continue  # truncated display snippet (e.g. sources.json "context"), not a real link
                    u = clean(raw)
                    host = urllib.parse.urlsplit(u).hostname or ''
                    if not host or '.' not in host or host in SKIP_HOSTS or '${' in u:
                        continue
                    found.setdefault(u, [])
                    loc = f'{rel}:{i}'
                    if loc not in found[u]:
                        found[u].append(loc)
    return found


_host_lock = threading.Lock()
_host_next = {}


def wait_host(host):
    while True:
        with _host_lock:
            now = time.monotonic()
            t = _host_next.get(host, 0.0)
            if now >= t:
                _host_next[host] = now + HOST_GAP_S
                return
            delay = t - now
        time.sleep(delay)


CTX = ssl.create_default_context()


def request(url, method):
    wait_host(urllib.parse.urlsplit(url).hostname or '')
    req = urllib.request.Request(url, method=method, headers={
        'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/pdf,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
        if method == 'GET':
            r.read(2048)
        return r.status


def classify(code):
    if code is None:
        return 'error'
    if 200 <= code < 400:
        return 'ok'
    if code in (404, 410):
        return 'dead'
    if code in (401, 403, 429, 999):
        return 'blocked'
    if code >= 500:
        return 'server_error'
    return f'http_{code}'


def check(url):
    code, err = None, None
    for method in ('HEAD', 'GET'):
        try:
            code, err = request(url, method), None
            break
        except urllib.error.HTTPError as e:
            code, err = e.code, f'HTTP {e.code} {e.reason}'
            if method == 'HEAD':
                continue  # many servers reject HEAD; retry with GET
            break
        except (urllib.error.URLError, socket.timeout, TimeoutError, ssl.SSLError, ConnectionError, OSError) as e:
            reason = getattr(e, 'reason', e)
            code, err = None, f'{type(e).__name__}: {reason}'
            if isinstance(reason, socket.gaierror):
                return url, None, err, 'dead'
            if method == 'HEAD':
                continue
            break
        except Exception as e:  # noqa: BLE001 - record anything else rather than crash the run
            code, err = None, f'{type(e).__name__}: {e}'
            break
    st = classify(code)
    return url, code, (None if st == 'ok' else err), st


def main():
    found = extract()
    urls = sorted(found)
    print(f'{len(urls)} unique URLs')
    with ThreadPoolExecutor(WORKERS) as ex:
        results = list(ex.map(check, urls))
    counts, links = {}, []
    for url, code, err, st in results:
        counts[st] = counts.get(st, 0) + 1
        links.append({'url': url, 'status': st, 'status_code': code, 'error': err, 'ok': st == 'ok',
                      'found_in': found[url]})
    out = {'generated': time.strftime('%Y-%m-%d %H:%M'), 'script': 'analysis/validation/link_check.py',
           'n': len(links), 'counts': dict(sorted(counts.items())), 'links': links}
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    print(json.dumps(out['counts']))


if __name__ == '__main__':
    main()
