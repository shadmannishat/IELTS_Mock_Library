"""Fixes from the November 2026 audit. Safe to run more than once.

- Replace other providers' Telegram links and watermarks with IELTS 7+ branding (mocks 29-66).
- "Check Answers" buttons read "Submit Test", as in mocks 1-28.
- Mock 55 Reading: correct the matching-headings key for Q28-33.
- Mock 29 Reading: the passage has 13 questions numbered 28-40 (there is no Q27), so score it out of 39
  and convert to a band on the 40-question scale.
- Mock 49 Writing: age group "40-46" -> "40-64".
- Mock 36 Reading: define a missing function the engine calls after marking.
- Review screen (all mocks): show question groups such as "28-30" instead of just "28".

    python3 tools/audit_fixes.py
"""
import glob, json, os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BRAND = ('<span class="i7-brand" style="font:800 20px/1 Arial,Helvetica,sans-serif;color:#111827;'
         'text-decoration:none;white-space:nowrap;letter-spacing:-.01em;cursor:default">IELTS '
         '<span style="color:#c8102e">7+</span></span>')
MARK_START, MARK_END = '<!--i7-audit-fix-->', '<!--/i7-audit-fix-->'


def outside_scripts(html, fn):
    """Apply fn only to the parts of html that are not inside <script> or <style>."""
    parts = re.split(r'(<script\b.*?</script>|<style\b.*?</style>)', html, flags=re.S | re.I)
    return ''.join(p if i % 2 else fn(p) for i, p in enumerate(parts))


def rebrand(html):
    def fix(p):
        # links to other providers' Telegram channels
        def link(m):
            inner = m.group(2)
            return inner if '<img' in inner else BRAND
        p = re.sub(r'<a\b([^>]*href="https?://t\.me/[^"]*"[^>]*)>(.*?)</a>', link, p, flags=re.S)
        p = p.replace('IELTS Research BD CD', 'IELTS 7+')
        p = re.sub(r'\s*T[Gg]:\s*@originalexams\.?', '', p)
        p = re.sub(r'(<title>[^<]*?)\bIELTS CDI\b', r'\1IELTS', p)
        p = re.sub(r'(<title>[^<]*?)\bCDI IELTS\b', r'\1IELTS', p)
        p = re.sub(r'(>\s*(?:<[^>]+>\s*)*)Check Answers(\s*<)', r'\1Submit Test\2', p)
        return p
    html = outside_scripts(html, fix)
    # page-wide watermarks drawn by CSS (body::after { content: "@MINDLESS_WRITER" } and similar)
    html = re.sub(r'content:\s*"[^"]*(?:MINDLESS|originalexams|CDI Report|Research BD|t\.me)[^"]*"', 'content: none', html, flags=re.I)
    html = html.replace('aria-label="Check Answers"', 'aria-label="Submit Test"')
    return html


def add_block(html, block):
    html = re.sub(re.escape(MARK_START) + '.*?' + re.escape(MARK_END), '', html, flags=re.S)
    if not block:
        return html
    i = html.lower().rfind('</body>')
    b = MARK_START + block + MARK_END
    return html[:i] + b + html[i:] if i >= 0 else html + b


MOCK29_READING = r"""<style>.subQuestion[onclick="goToQuestion(27)"]{display:none!important}</style>
<script>
(function(){
  // This passage has 13 questions (28-40); score out of 39 and convert to the 40-question band scale.
  var t = [[39,9],[37,8.5],[35,8],[33,7.5],[30,7],[27,6.5],[23,6],[19,5.5],[15,5],[13,4.5],[10,4],[8,3.5],[6,3],[4,2.5],[1,1]];
  function band(s){ for (var i = 0; i < t.length; i++) if (s >= t[i][0]) return t[i][1]; return 0; }
  var post = window.i7post;
  window.i7post = function(m){
    if (m && m.type === 'done' && m.section === 'reading') { m.total = 39; m.band = band(Math.round(m.raw * 40 / 39)); }
    return post(m);
  };
})();
</script>"""

MOCK36_READING = r"""<script>if (typeof showExplanationsWithHighlighting !== 'function') { window.showExplanationsWithHighlighting = function(){}; }</script>"""


def fix_section(n, key, h):
    h = rebrand(h)
    block = ''
    if n == 55 and key == 'reading':
        h = re.sub(r"'28': 'v', '29': 'x', '30': 'iii', '31': 'i', '32': 'vii', '33': 'viii'",
                   "'28': 'x', '29': 'iii', '30': 'i', '31': 'vii', '32': 'viii', '33': 'ii'", h)
    if n == 29 and key == 'reading':
        h = h.replace('Read the text and answer questions 27-40', 'Read the text and answer questions 28-40')
        block = MOCK29_READING
    if n == 49 and key == 'writing':
        h = re.sub(r'(>\s*)40-46(\s*<)', r'\g<1>40-64\2', h)
    if n == 36 and key == 'reading':
        # must exist before the engine's own scripts run, so put it in <head>
        h = re.sub(re.escape(MARK_START) + '.*?' + re.escape(MARK_END), '', h, flags=re.S)
        h = h.replace('</head>', MARK_START + MOCK36_READING + MARK_END + '</head>', 1)
        return h
    return add_block(h, block)


def enc(html):
    return json.dumps(html, ensure_ascii=False).replace('</', '<\\/')


def fix_shell(s):
    old = "t.match(/^Q(\\d+)\\s*(Correct|Incorrect)?/)"
    new = "t.match(/^Q(\\d+(?:\\s*[-\\u2013]\\s*\\d+)?)\\s*(Correct|Incorrect)?/)"
    return s.replace(old, new)


def patch_file(path, n):
    s = open(path, encoding='utf-8').read()
    i0 = s.index('const SECTIONS = {')
    dec = json.JSONDecoder()
    parts, pos = [], 0
    for m in re.finditer(r'(listening|reading|writing):"', s[i0:]):
        start = i0 + m.end() - 1
        html, end = dec.raw_decode(s, start)
        parts.append(s[pos:start]); parts.append(enc(fix_section(n, m.group(1), html))); pos = end
    parts.append(s[pos:])
    out = fix_shell(''.join(parts))
    if out != s:
        open(path, 'w', encoding='utf-8').write(out)
        return True
    return False


if __name__ == '__main__':
    for f in sorted(glob.glob(os.path.join(ROOT, 'mocks/mock-*/IELTS_Full_Mock_*.html'))):
        n = int(re.search(r'mock-(\d+)', f).group(1))
        print(n, 'changed' if patch_file(f, n) else 'no change')
