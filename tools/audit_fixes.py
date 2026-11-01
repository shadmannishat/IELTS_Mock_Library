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


import json as _json

# Answer-key corrections from checking each key against its passage (and published keys where available).
# value: a string or a list of accepted answers (first one is shown as "the" answer)
KEY_FIXES = {
    (31, 'reading'): {'10': ['A', 'B']},  # Lord Rayleigh and John William Strutt are the same person
    (32, 'reading'): {'40': ['K', 'G']},  # "its battery pack restricted cargo space"
    # mock 34's page script loads a different Reading test at runtime (Plain English Campaign ...); its original
    # key matches what students see, so it is kept as it was (an earlier change based on the hidden text is undone here)
    (34, 'reading'): {'1': 'TRUE', '2': 'NOT GIVEN', '3': 'TRUE', '4': 'NOT GIVEN', '5': 'NOT GIVEN', '6': 'FALSE',
                      '7': 'jargon and waffle', '8': 'Gap', '9': 'do-it-yourself', '10': 'frustration',
                      '11': 'first-time user', '12': 'legal', '13': 'courts'},
    (35, 'reading'): {'11': 'FALSE', '23': 'I'},
    (36, 'reading'): {'34': ['first luxuries', 'luxuries', 'the first luxury', 'first luxury', 'luxury']},
    (37, 'reading'): {'3': 'TRUE', '24': 'B', '25': 'A', '35': ['wastewater', 'waste water']},
    (38, 'reading'): {'20': ['centre', 'center']},
    (41, 'reading'): {'34': ['neorealism', 'neorealist', 'neorealist films']},
    (42, 'reading'): {'7': ['inventor', 'normal inventor']},
    (52, 'reading'): {'8': ['three years', '3 years', 'three', '3'], '33': ['marketing team', 'marketing teams'],
                      '34': ['designers', 'design agencies', 'external designers'],
                      '35': ['consumer group', 'consumer groups', 'consumers'],
                      '36': ['in-house teams', 'in-house team', 'in-house designers']},
    (52, 'listening'): {'q8': ['scooter', 'scooters']},
    (53, 'reading'): {'25': ['rural economies', 'rural economics']},
    (57, 'reading'): {'9': ['NGO', 'non-governmental organization', 'non-governmental organisation', 'non governmental organization'],
                      '11': ['solar, wind, biomass', 'biomass, solar and wind', 'biomass solar and wind', 'solar wind and biomass', 'solar, wind and biomass']},
    (64, 'reading'): {'10': ['sky pointing', 'skypointing', 'sky-pointing']},
    (66, 'reading'): {'33': ['breathing', 'eating'], '34': ['eating', 'breathing'], '35': 'babies', '36': 'brain activity',
                      '37': 'vigorous exercise', '38': 'temperature', '39': 'scanning techniques'},
}


def set_keys(h, fixes):
    i = h.find('correctAnswers = {')
    if i < 0:
        return h
    j = h.find('};', i)
    seg = h[i:j]
    for q, val in fixes.items():
        lit = _json.dumps(val, ensure_ascii=False).replace('"', "'") if isinstance(val, list) else "'%s'" % val
        pat = r"""((['"]?)%s\2\s*:\s*)(\[[^\]]*\]|'[^']*'|"[^"]*")""" % re.escape(q)
        seg, k = re.subn(pat, lambda m: m.group(1) + lit, seg, count=1)
        if not k:
            raise RuntimeError('key %s not found' % q)
    return h[:i] + seg + h[j:]


def allow_alternatives(h):
    """Let exact-match comparisons accept a list of answers (needed for keys with alternatives)."""
    if 'correctAnswer.includes(userAnswer) : userAnswer === correctAnswer' in h:
        return h
    h = re.sub(r'(?<![\w.(])userAnswer === correctAnswer(?![.\w])',
               '(Array.isArray(correctAnswer) ? correctAnswer.includes(userAnswer) : userAnswer === correctAnswer)', h)
    h = h.replace('isCorrect = userAnswer === correctAnswer.toLowerCase();',
                  'isCorrect = (Array.isArray(correctAnswer) ? correctAnswer : [correctAnswer]).some(a => userAnswer === String(a).toLowerCase());')
    return h


def fix_section(n, key, h):
    h = rebrand(h)
    block = ''
    if (n, key) in KEY_FIXES:
        h = allow_alternatives(h)
        h = set_keys(h, KEY_FIXES[(n, key)])
    if n == 66 and key == 'reading':   # Q33/Q34 are separate boxes: breathing and eating, either order, one per box
        h = re.sub(r"if \(i === 33\) \{\s*const answers = userAnswer\.split\('&'\)\.map\(ans => ans\.trim\(\)\);\s*isCorrect = answers\.includes\('breathing'\) && answers\.includes\('eating'\);\s*\}",
                      lambda m: "if (i === 33 || i === 34) { const other = ((document.getElementById(i === 33 ? 'q34' : 'q33') || {}).value || '').trim().toLowerCase(); isCorrect = ['breathing', 'eating'].includes(userAnswer) && userAnswer !== other; }", h)
    if n == 66 and key == 'reading' and '/*i7pair*/' not in h:   # no second mark for repeating Q33's word in Q34
        h = re.sub(r"(userAnswer\.toLowerCase\(\) === correctAnswer\.toLowerCase\(\);\s*\})",
                   lambda m: m.group(1) + " /*i7pair*/ if (i === 34 && isCorrect && ((document.getElementById('q33') || {}).value || '').trim().toLowerCase() === userAnswer.toLowerCase()) { isCorrect = false; }",
                   h, count=1)
    if n == 61 and key == 'reading':   # passage typo
        h = h.replace('took the form of tringles', 'took the form of triangles')
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
