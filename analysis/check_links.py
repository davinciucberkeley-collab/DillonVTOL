"""Link check for the source register: requests every URL in analysis/sources.json and records whether it still
resolves. Writes analysis/link_status.json, which analysis/sources.py merges into the register and the review shows.

Status per URL:
  ok          2xx/3xx (after redirects)
  dead        404 or 410, or the host no longer resolves
  unverified  the site refused an automated request (401, 403, 429, 5xx, bot walls) or timed out; it may well work
              in a browser, so it is NOT reported as dead
For dead links the Internet Archive's availability API is asked for the closest archived copy (archive field).

Usage: python analysis/check_links.py            (network access; about 5 min for ~600 URLs)
       python analysis/check_links.py --archive-only   (only the archived-copy lookups for links already found dead)
"""
import http.client, json, os, re, socket, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
TODAY = time.strftime('%Y-%m-%d')
CTX = ssl.create_default_context()


def fetch(url, method):
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA, 'Accept': 'text/html,application/pdf,*/*;q=0.8', 'Accept-Language': 'en-US,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
        return r.status, r.geturl()


def check(url):
    res = {'checked': TODAY}
    for method in ('HEAD', 'GET'):
        try:
            code, final = fetch(url, method)
            res.update(status='ok', code=code)
            if final != url: res['final'] = final
            return url, res
        except urllib.error.HTTPError as e:
            code = e.code
            if method == 'HEAD' and code in (400, 403, 404, 405, 406, 429, 500, 501, 503):
                continue                        # many servers answer HEAD badly: retry with GET
            res.update(code=code, status='dead' if code in (404, 410) else 'unverified')
            return url, res
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, socket.gaierror):
                res.update(status='dead', code=None, error='host not found'); return url, res
            if method == 'HEAD':
                continue
            res.update(status='unverified', code=None, error=str(reason)[:120]); return url, res
        except (socket.timeout, TimeoutError, ConnectionError, ssl.SSLError, OSError, http.client.HTTPException, ValueError) as e:
            if method == 'HEAD':
                continue
            res.update(status='unverified', code=None, error=type(e).__name__); return url, res
    return url, res


def archive(url):
    # the availability API rate-limits hard: callers run this one at a time, and a 429 is retried after a pause
    for attempt in range(4):
        try:
            return _archive(url)
        except urllib.error.HTTPError as e:
            if e.code != 429: return None
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException):   # network trouble: no archive, keep the run
            return None
    return None


def _archive(url):
    if True:
        q = 'https://archive.org/wayback/available?url=' + urllib.parse.quote(re.sub(r'^https?://', '', url), safe=':/')   # the API wants the bare host and path
        with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': UA}), timeout=20, context=CTX) as r:
            snap = json.load(r).get('archived_snapshots', {}).get('closest')
        if snap and snap.get('available'):
            return snap['url']
    return None


def archive_only():
    """redo just the archive lookups for the dead links in an existing link_status.json"""
    d = json.load(open('analysis/link_status.json', encoding='utf-8'))
    for u, r in d['links'].items():
        if r['status'] == 'dead' and not r.get('archive'):
            a = archive(u); time.sleep(3)
            if a: r['archive'] = a
            print('  dead', u, '->', a or 'no archive')
    with open('analysis/link_status.json', 'w', encoding='utf-8', newline=chr(10)) as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True); f.write(chr(10))


def main():
    if '--archive-only' in sys.argv:
        return archive_only()
    src = json.load(open('analysis/sources.json', encoding='utf-8'))
    urls = sorted({e['url'] for e in src['sources']} | {k['url'] for k in src.get('key', [])})
    out = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for url, res in ex.map(check, urls):
            out[url] = res
    # second, slower pass over the unverified ones: parallel requests trip rate limits that a patient request does not
    again = [u for u, r in out.items() if r['status'] == 'unverified']
    def slow(u):
        time.sleep(1.5); return check(u)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for url, res in ex.map(slow, again):
            if res['status'] != 'unverified': out[url] = res
    dead = [u for u, r in out.items() if r['status'] == 'dead']
    for u in dead:
        a = archive(u); time.sleep(2)
        if a: out[u]['archive'] = a
    counts = {s: sum(1 for r in out.values() if r['status'] == s) for s in ('ok', 'dead', 'unverified')}
    with open('analysis/link_status.json', 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'checked': TODAY, 'counts': counts, 'links': out}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
    print(len(urls), 'URLs:', counts, '| dead with an archived copy:', sum(1 for u in dead if out[u].get('archive')))
    for u in dead:
        print('  dead', out[u].get('code') or out[u].get('error'), u, '->', out[u].get('archive') or 'no archive')


if __name__ == '__main__':
    main()
