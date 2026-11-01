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


MOCK62_READING = r"""<script>
(function(){
  // Questions 19-23 say "You may use any letter more than once": keep each letter in the list after it is dropped.
  var G = 'q19-23', src = null;
  function bankOf(it){ return it && it.closest ? it.closest('.drag-options-container') : null; }
  function tidy(bank){
    var seen = {};
    Array.prototype.slice.call(bank.querySelectorAll('.drag-item')).forEach(function(x){ if (!x.hasAttribute('data-i7clone')) seen[x.dataset.value] = 1; });
    Array.prototype.slice.call(bank.querySelectorAll('.drag-item[data-i7clone]')).forEach(function(x){ if (seen[x.dataset.value]) x.remove(); else seen[x.dataset.value] = 1; });
  }
  document.addEventListener('dragstart', function(e){
    var it = e.target && e.target.closest ? e.target.closest('.drag-item') : null;
    src = (it && it.dataset.dndGroup === G && bankOf(it)) ? it : null;
  }, true);
  document.addEventListener('drop', function(e){
    var z = e.target && e.target.closest ? e.target.closest('.drop-zone') : null;
    if (!src || !z || z.dataset.dndGroup !== G) return;
    var it = src, bank = bankOf(it); src = null;
    var c = it.cloneNode(true); c.setAttribute('data-i7clone', '1'); c.setAttribute('draggable', 'false'); c.classList.remove('dragging', 'selected');
    bank.insertBefore(c, it);
    setTimeout(function(){
      if (it.parentNode && it.parentNode !== bank && c.parentNode === bank) {
        var mark = document.createComment(''); it.parentNode.insertBefore(mark, it);
        bank.replaceChild(it, c); mark.parentNode.replaceChild(c, mark);
        it.style.cursor = ''; c.style.cursor = 'default';
      } else if (c.parentNode === bank) { c.remove(); }
      tidy(bank);
    }, 0);
  }, true);
})();
</script>"""


def key_literal_replace(h, pairs):
    """Replace 'q': 'value' pairs inside the correctAnswers object only."""
    i = h.find('correctAnswers = {')
    if i < 0:
        return h
    j = h.find('};', i)
    seg = h[i:j]
    for old, new in pairs:
        seg = seg.replace(old, new)
    return h[:i] + seg + h[j:]


def fix_section(n, key, h):
    h = rebrand(h)
    block = ''
    if n == 31 and key == 'reading':   # options are TRUE / FALSE / NOT GIVEN
        h = key_literal_replace(h, [("'32': 'YES'", "'32': 'TRUE'"), ("'35': 'NO'", "'35': 'FALSE'")])
    if n == 34 and key == 'reading':   # options are YES / NO / NOT GIVEN
        h = key_literal_replace(h, [("'33': 'FALSE'", "'33': 'NO'"), ("'35': 'TRUE'", "'35': 'YES'"), ("'36': 'FALSE'", "'36': 'NO'")])
    if n == 42 and key == 'listening':  # the answer box for Q7 was missing ("£ ___ for retired or unemployed members")
        h = h.replace('£7 for retired or unemployed members',
                      '£<input type="text" id="q7" class="answer-input" placeholder="7"> for retired or unemployed members')
    if n == 51 and key == 'reading':   # matching headings Q14-20 were marked but never added to the score
        a = h.find('// Handle drag-and-drop headings for Questions 14-20')
        if a >= 0:
            old = 'isCorrect = userAnswer === correctAnswer;\n'
            b = h.find(old, a)
            if b >= 0 and 'if (isCorrect) { score++; } /*i7*/' not in h[b:b + 200]:
                h = h[:b + len(old)] + '                    if (isCorrect) { score++; } /*i7*/\n' + h[b + len(old):]
    if n == 65 and key == 'reading':   # Q26 is its own question; the engine copied Q25's answer over it
        h = re.sub(r'if \(answers\[25\]\) \{\s*answers\[26\] = answers\[25\];\s*\}', '/* Q26 is answered separately */', h)
    if n == 49 and key == 'listening':  # two option lists used the same ids, so a drop could grab the other list's letter
        seen = set()
        def uniq(m):
            i = m.group(1)
            if i in seen:
                return 'id="%s_2"' % i
            seen.add(i)
            return m.group(0)
        h = outside_scripts(h, lambda p: re.sub(r'id="(opt[A-H])"', uniq, p))
    if n == 64 and key == 'reading':   # Paragraph D (courtship display) is "Mating and breeding"; ix is not even in the list
        h = key_literal_replace(h, [("'3': 'ix'", "'3': 'viii'")])
    if n == 62 and key == 'reading':
        block = MOCK62_READING
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
