#!/usr/bin/env python3
"""Make mocks 29-66 work offline.

Run by the 'Build offline pack' GitHub Action (it needs internet access).

1. Images, stylesheets and scripts that the mocks load from other websites are
   downloaded and embedded straight into each mock's HTML (committed to the repo).
2. Each Listening recording is downloaded, saved as mocks/mock-NN/Listening.mp3
   (not committed - too large for GitHub Pages) and the mock is changed to play
   that local file when opened from the computer, and the online copy otherwise.
3. A complete offline zip of the whole library is written to dist/.
"""
import base64, json, os, re, subprocess, sys, time, urllib.request, zipfile, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FIRST, LAST = 29, 66
UA = {'User-Agent': 'Mozilla/5.0 (offline-pack builder)'}
SKIP_HOSTS = ('t.me', 'www.w3.org', 'w3.org')
_cache = {}


def fetch(url):
    if url in _cache:
        return _cache[url]
    last = None
    urls = [url]
    m = re.match(r'https?://ia\d+\.us\.archive\.org/\d+/items/(.+)$', url)
    if m:  # a single storage server can be down; the main address picks a working copy
        urls.append('https://archive.org/download/' + m.group(1))
    for attempt in range(8):
        try:
            req = urllib.request.Request(urls[attempt % len(urls)], headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
                ctype = r.headers.get('Content-Type', '').split(';')[0].strip()
            if len(data) < 5_000_000:
                _cache[url] = (data, ctype)
            return data, ctype
        except Exception as e:  # retry with a growing pause
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError('download failed: %s (%s)' % (url, last))


def sniff(data, ctype, url):
    if ctype.startswith('image/'):
        return ctype
    head = data[:16]
    if head.startswith(b'\x89PNG'): return 'image/png'
    if head[:3] == b'\xff\xd8\xff': return 'image/jpeg'
    if head[:4] == b'GIF8': return 'image/gif'
    if head[:4] == b'RIFF' and data[8:12] == b'WEBP': return 'image/webp'
    if b'<svg' in data[:300]: return 'image/svg+xml'
    ext = url.split('?')[0].rsplit('.', 1)[-1].lower()
    return {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'gif': 'image/gif', 'webp': 'image/webp'}.get(ext, 'image/png')


def data_uri(url):
    data, ctype = fetch(url)
    return 'data:%s;base64,%s' % (sniff(data, ctype, url), base64.b64encode(data).decode())


FA_CSS = None
def font_awesome_css(url):
    global FA_CSS
    if FA_CSS is None:
        css = fetch(url)[0].decode('utf-8')
        base = url.rsplit('/css/', 1)[0]
        woff2 = fetch(base + '/fonts/fontawesome-webfont.woff2?v=4.7.0')[0]
        face = "@font-face{font-family:'FontAwesome';src:url(data:font/woff2;base64,%s) format('woff2');font-weight:normal;font-style:normal}" % base64.b64encode(woff2).decode()
        css = re.sub(r'@font-face\{[^}]*\}', lambda m: face, css, count=1)
        FA_CSS = css
    return FA_CSS


def get_audio(remote, audio_dir, n, report):
    os.makedirs(audio_dir, exist_ok=True)
    raw = os.path.join(audio_dir, 'source.bin'); out = os.path.join(audio_dir, 'Listening.mp3')
    cands = [remote]
    m = re.match(r'https?://ia\d+\.us\.archive\.org/\d+/items/(.+)$', remote)
    if m:
        cands.append('https://archive.org/download/' + m.group(1))
    errs = []
    for url in cands * 2:
        try:
            _cache.pop(url, None)
            data, ctype = fetch(url)
            if data[:200].lstrip().lower().startswith((b'<!doctype', b'<html')) or len(data) < 100_000:
                raise RuntimeError('got %s, %d bytes, not a recording' % (ctype, len(data)))
            open(raw, 'wb').write(data)
            # tolerate a damaged frame or two instead of failing the whole file
            r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-err_detect', 'ignore_err', '-i', raw, '-vn', '-ac', '1',
                                '-b:a', os.environ.get('AUDIO_BITRATE', '96k'), out], capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) < 100_000:
                info = 'ffmpeg could not shrink it (%d bytes, starts %r): %s' % (len(data), data[:8], (r.stderr or '').strip()[:200])
                if data[:3] == b'ID3' or (data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
                    # still a playable MP3 for browsers; keep the original file
                    os.replace(raw, out)
                    report.append('::warning::mock %d audio kept at original size. %s' % (n, info))
                    return True
                raise RuntimeError(info)
            os.remove(raw)
            report.append('mock %d audio %.1f MB -> %.1f MB' % (n, len(data) / 1e6, os.path.getsize(out) / 1e6))
            return True
        except Exception as e:
            errs.append(str(e)[:160])
    if os.path.exists(raw): os.remove(raw)
    report.append('::error::mock %d audio not downloaded: %s' % (n, ' | '.join(errs)[:600]))
    return False


def split_sections(shell):
    """Return list of (key, start, end, html) for the JSON strings inside const SECTIONS."""
    dec = json.JSONDecoder(); out = []
    i0 = shell.index('const SECTIONS = {')
    for m in re.finditer(r'\n(listening|reading|writing):', shell[i0:]):
        start = i0 + m.end()
        html, end = dec.raw_decode(shell, start)
        out.append((m.group(1), start, end, html))
    return out


def enc(html):
    return json.dumps(html, ensure_ascii=False).replace('</', '<\\/')


def fix_section(key, html, n, audio_dir, report):
    # stylesheets
    def css_link(m):
        url = m.group(1)
        if 'font-awesome' in url:
            return '<style>' + font_awesome_css(url) + '</style>'
        return '<style>' + fetch(url)[0].decode('utf-8', 'ignore') + '</style>'
    def safe(fn):
        def w(m):
            try:
                return fn(m)
            except Exception as e:
                report.append('::error::mock %d %s asset not embedded: %s' % (n, key, str(e)[:200]))
                return m.group(0)
        return w
    html = re.sub(r'<link[^>]+href=["\'](https?://[^"\']+\.css[^"\']*)["\'][^>]*>', safe(css_link), html)
    # scripts
    def script_src(m):
        js = fetch(m.group(1))[0].decode('utf-8', 'ignore').replace('</script', '<\\/script')
        return '<script>' + js + '</script>'
    html = re.sub(r'<script[^>]*src=["\'](https?://[^"\']+)["\'][^>]*>\s*</script>', safe(script_src), html)
    # audio (listening)
    if key == 'listening':
        m = re.search(r"const audioSource\s*=\s*'([^']+)'\s*;", html)
        if not m:
            raise RuntimeError('mock %d: no audioSource' % n)
        remote = m.group(1).replace('http://', 'https://')
        get_audio(remote, audio_dir, n, report)
        new = "const audioSource = (window.__i7remote = '%s', /^file:/.test(document.baseURI) ? 'Listening.mp3' : window.__i7remote);" % remote
        html = html[:m.start()] + new + html[m.end():]
        html = html.replace(
            "ap.addEventListener('error', function(){ if (started && !finished) say(",
            "ap.addEventListener('error', function(){ if (window.__i7remote && ap.src.indexOf('Listening.mp3') >= 0) { ap.src = window.__i7remote; if (started) ap.play(); return; } if (started && !finished) say(")
        html = html.replace('<li>The recording streams from the internet, so stay online.</li>', '')
    # images (img src, css url())
    def img(m):
        url = m.group(2)
        host = url.split('/')[2]
        if host in SKIP_HOSTS:
            return m.group(0)
        try:
            return m.group(1) + data_uri(url) + m.group(3)
        except Exception as e:
            report.append('::error::mock %d %s image not embedded: %s' % (n, key, str(e)[:200]))
            return m.group(0)
    html = re.sub(r'(<img[^>]*?\ssrc=["\'])(https?://[^"\']+)(["\'])', img, html)
    html = re.sub(r'(url\(["\']?)(https?://[^"\')]+\.(?:png|jpe?g|gif|webp|svg)[^"\')]*)(["\']?\))', img, html)
    left = sorted(set(u for u in re.findall(r'<(?:img|script|link|audio|source|iframe|video)[^>]+(?:src|href)=["\'](https?://[^"\']+)', html)
                      if u.split('/')[2] not in SKIP_HOSTS))
    if left:
        report.append('mock %d %s still links: %s' % (n, key, left[:5]))
    return html


def main():
    report = []
    stage = os.path.join(ROOT, 'dist', 'site')
    for n in range(FIRST, LAST + 1):
        rel = 'mocks/mock-%02d/IELTS_Full_Mock_%d.html' % (n, n)
        path = os.path.join(ROOT, rel)
        shell = open(path, encoding='utf-8').read()
        if '__i7remote' in shell and 'cdnjs.cloudflare.com' not in shell:
            print('mock %d already converted - audio only' % n)
        secs = split_sections(shell)
        audio_dir = os.path.join(stage, 'mocks', 'mock-%02d' % n)
        try:
          for key, start, end, html in reversed(secs):
              if key == 'listening' and '__i7remote' in html:
                  m = re.search(r"window.__i7remote = '([^']+)'", html)
                  get_audio(m.group(1), audio_dir, n, report)
                  continue
              new = fix_section(key, html, n, audio_dir, report)
              shell = shell[:start] + enc(new) + shell[end:]
        except Exception as e:
            report.append('::error::mock %d not converted: %s' % (n, str(e)[:200]))
            continue
        open(path, 'w', encoding='utf-8').write(shell)
        print('done mock', n, flush=True)
    print('\n'.join(report))
    errs = [r for r in report if r.startswith('::error::')]
    total = sum(os.path.getsize(os.path.join(b, f)) for b, _, fs in os.walk(stage) for f in fs) if os.path.isdir(stage) else 0
    print('::notice::offline pack: %d problems, audio total %.0f MB' % (len(errs), total / 1e6))
    if os.environ.get('NO_ZIP'):
        return
    # complete offline zip: whole site + downloaded audio
    zpath = os.path.join(ROOT, 'dist', 'IELTS7plus_Mock_Library_Offline.zip')
    top = 'IELTS7plus_Mock_Library'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in ('.git', '.github', 'dist', 'tools')]
            for f in files:
                p = os.path.join(base, f)
                rel = os.path.relpath(p, ROOT)
                if rel == 'index.html':
                    # every mock works offline in this pack, so drop the "Needs internet" labels
                    z.writestr(os.path.join(top, rel), open(p, encoding='utf-8').read().replace('"online": true', '"online": false'))
                elif rel == 'READ ME FIRST.txt':
                    txt = open(p, encoding='utf-8').read()
                    txt = re.sub(r'- Mocks 1-28 work fully offline\.[^\n]*', '- All mocks work fully offline from this folder. Keep index.html and the mocks folder together. Nothing you type is sent over the internet.', txt)
                    z.writestr(os.path.join(top, rel), txt)
                elif rel in ('.gitignore',):
                    continue
                else:
                    z.write(p, os.path.join(top, rel))
        for base, dirs, files in os.walk(stage):
            for f in files:
                p = os.path.join(base, f)
                z.write(p, os.path.join(top, os.path.relpath(p, stage)))
    print('::notice::zip %.0f MB' % (os.path.getsize(zpath) / 1e6))


if __name__ == '__main__':
    main()
