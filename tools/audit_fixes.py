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
    (31, 'reading'): {'10': 'A'},  # option B was Lord Rayleigh's own name; it is now another scientist (see REWORD)
    (32, 'reading'): {'40': 'K'},  # "its battery pack restricted cargo space" (summary reworded)
    # mock 34's page script loads a different Reading test at runtime (Plain English Campaign ...); its original
    # key matches what students see, so it is kept as it was (an earlier change based on the hidden text is undone here)
    (34, 'reading'): {'1': 'TRUE', '2': 'NOT GIVEN', '3': 'TRUE', '4': 'NOT GIVEN', '5': 'NOT GIVEN', '6': 'FALSE',
                      '7': 'jargon and waffle', '8': 'Gap', '9': 'do-it-yourself', '10': 'frustration',
                      '11': 'first-time user', '12': 'legal', '13': 'courts'},
    (35, 'reading'): {'11': 'FALSE', '23': 'J'},  # paragraph J (restored) has the 'before people did' point
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


# Round 2: every Reading key re-solved against its passage. KEY_SET replaces a key (the evidence is in the
# comment); KEY_ADD keeps the key and also accepts other correct wordings from the passage.
KEY_SET = {
    (4, 'reading'): {'13': 'C',             # laser surgery: "despite the growth of such surgery", "increasingly safe and affordable"
                     '25': 'NO'},           # Wada paralysed one side "of a healthy brain", not people with language problems
    (8, 'reading'): {'13': ['Port Jackson', 'Sydney Cove'],   # "This second location was strange and unfamiliar"
                     '36': ['San Andreas Fault', 'the San Andreas Fault', 'San Andreas']},  # Aegir Ridge "had never been active"
    # mock 13: statements 13 and 25 and summary gap 32 are reworded (see REWORD) so one answer fits
    (13, 'reading'): {'13': 'TRUE', '25': 'A', '32': 'developed countries'},
    (17, 'reading'): {'7': 'FALSE'},       # social impact comes from "the educative effect of travel and the effects on employment"
    (23, 'reading'): {'19': 'aimless'},    # 'empty' is how people feel after finding the item, not the gap's meaning
    (47, 'reading'): {'40': 'NOT GIVEN'},  # the brewery reuses spent grain; nothing about raising production
    (51, 'reading'): {'7': 'TRUE',         # "difficult to establish ... inhabited by notoriously vigorous competitors"
                      '19': 'iv'},         # paragraph F: "The design is for people with different culture background"
    (52, 'reading'): {'13': ['Port Jackson', 'Sydney Cove']},
    (54, 'reading'): {'26': 'April'},      # "In April the body of the 'Emu in the Sky' reaches a certain angle"
    (55, 'reading'): {'3': 'TRUE',         # "Even that has not been much use"
                      '7': 'FALSE'},       # floods were "wiping the slate dirty ... a muddy mess"
    (57, 'reading'): {'6': 'NO'},          # "Both wind and solar power are so successful"
    (59, 'reading'): {'10': 'NOT GIVEN'},  # the passage only says Brunel had already built a railway
    (62, 'reading'): {'24': ['vegetation']},
    (63, 'reading'): {'28': 'vi', '29': 'i', '30': 'iii', '32': 'ii'},  # headings checked against the heading list values
    # Listening: checked against transcripts of the recordings
    (2, 'listening'): {'4': '313859'},     # "reach me at home in the evening at 313859 ... not five at the end, nine"
    (18, 'listening'): {'2': 'Eshcol'},    # spelled "E-S-H-C-O-L"
    # the map in mock 6 belonged to another test; it now uses the station map (as in mock 42), whose letters these are
    (6, 'listening'): {'15': 'F', '16': 'C', '17': 'D', '18': 'E', '19': 'B', '20': 'A'},
    (39, 'listening'): {'q18': 'code'},    # "they will tell you the code you use to enter the door"
    (40, 'listening'): {'q13': 'E',        # USA: "their more rigid schedule of August to December"
                        'q14': 'C'},       # Australia: "willing to commit 8 months" (mock 5 has the same key)
    (51, 'listening'): {'q21': 'B'},       # "increased safeguards ... officially designated a nature reserve"
    (60, 'listening'): {'q14': 'A'},
    (14, 'listening'): {'36': ['water', 'sand']},  # "they needed water and sand"; the prompt asks for the first missing word       # "some rooms that adjoin one another with a door connecting them"
}
KEY_ADD = {
    (1, 'reading'): {'10': ['Rowling']},
    (2, 'reading'): {'14': ['chronometer', 'the marine chronometer']},
    (3, 'reading'): {'25': ['daytime predators'], '26': ['any visible']},
    (4, 'reading'): {'6': ['convex lens', 'convex']},
    (7, 'reading'): {'23': ['mosaic floors'], '25': ['AD 93', '93 AD']},
    (8, 'reading'): {'10': ['Philip'], '25': ['cow'], '33': ['tectonic plates']},
    (9, 'reading'): {'13': ['skin irritation', 'irritation'], '35': ['bitter', 'gritty', 'bitter and gritty']},
    (10, 'reading'): {'9': ['Domesday'], '17': ['psychological']},
    (15, 'reading'): {'25': ['sophisticated touch-tone systems']},
    (16, 'reading'): {'8': ['tails']},
    (20, 'reading'): {'13': ['airbags']},
    (23, 'reading'): {'34': ['arson investigators']},
    (24, 'reading'): {'5': ['season']},
    (26, 'reading'): {'24': ['sociopathic behavior']},
    (27, 'reading'): {'33': ['bottomfish'], '35': ['pollutants']},
    (47, 'reading'): {'26': ['freshwater']},
    (49, 'reading'): {'2': ['gopher tortoises', 'tortoise'], '8': ['ants'], '24': ['Eurasia']},
    (50, 'reading'): {'12': ['swallowed'], '24': ['Abraham Darby'], '26': ['Severn River', 'the Severn River', 'Severn']},
    (51, 'reading'): {'26': ['cost', 'costs']},
    (52, 'reading'): {'7': ['diaries', 'his diary', 'diary'], '10': ['Philip'], '22': ['lost time']},
    (53, 'reading'): {'11': ['the 1960s', '1960s'], '21': ['disposable income', 'more disposable incomes'],
                      '24': ['agricultural products'], '33': ['new']},
    (55, 'reading'): {'20': ['semantic'], '21': ['episodic', 'event']},
    (56, 'reading'): {'6': ['especially intelligent'], '9': ['100', 'almost one hundred', 'almost 100'], '11': ['colour'],
                      '12': ['pronunciation'], '13': ['a teenager']},
    (57, 'reading'): {'12': ['advanced technology'], '20': ["the UN's 1967 treaty", 'UN 1967 treaty', '1967 treaty']},
    (58, 'reading'): {'8': ['molds', 'mould', 'mold'], '13': ['20 millimeters', 'twenty millimeters'],
                      '22': ['star stock analysts'], '27': ['cough'], '29': ['family and friends', 'friends and family'],
                      '32': ['experience']},
    (60, 'reading'): {'13': ['a furnace'], '25': ['2 billion words', 'two billion words']},
    (61, 'reading'): {'25': ['host selling', 'hostselling']},
    (62, 'reading'): {'25': ['hunting']},
    (63, 'reading'): {'14': ['mosquito']},
    (64, 'reading'): {'11': ['nest building'], '34': ['code makers', 'codemakers'], '35': ['public key'], '36': ['private']},
    # Listening: answer words as spoken in the recording
    (37, 'listening'): {'q36': ['gray']},                 # "it is the gray mangroves"
    (45, 'listening'): {'q36': ['native language']},      # "in the native language of the majority of passengers"
    (52, 'listening'): {'q36': ['soundproof', 'sound-proof', 'sound-proofed']},  # "Subjects were put into soundproof rooms"
    (3, 'listening'): {'36': ['soundproof', 'sound-proof', 'sound-proofed']},
    (13, 'listening'): {'38': ['flow stone'], '40': ['bottom-up']},
    (11, 'listening'): {'28': ['low-fat organic yogurt', 'low-fat organic yoghurt'],
                        '30': ['alcohol and coffee', 'alcohol, coffee', 'alcohol coffee', 'coffee and alcohol']},
    (21, 'listening'): {'38': ['sea level', 'sea levels', 'water levels']},
    (15, 'listening'): {'37': ['early 20s', "early 20's"]},
    (16, 'listening'): {'29': ['profit']},
    (19, 'listening'): {'2': ['J06337'],                 # the passport number is read as "J-zero-six..."
                        '37': ['fifth taste']},          # "Ikeda identified a fifth taste"
    (20, 'listening'): {'37': ['early 20s', "early 20's"]},
    (22, 'listening'): {'32': ['grind their grain']},
    (28, 'listening'): {'3': ['socialise']},
    (35, 'listening'): {'q9': ['sawdicot']},              # spelled "S-A-W-D-I-C-O-T" in the recording
    (42, 'listening'): {'q34': ['flavor'], 'q35': ['fertilizers']},
    (56, 'listening'): {'q34': ['math department', 'maths', 'math']},
    (65, 'reading'): {'23': ['one sixth', '1/6'], '24': ['sixteenth century'], '34': ['a panoramic camera'],
                      '35': ['Sahara desert', 'the Sahara', 'Sahara'], '36': ['polarized light']},
}


def merged(old, val, add):
    cur = old if isinstance(old, list) else [old]
    out = list(val if isinstance(val, list) else [val]) if val is not None else list(cur)
    for a in add or []:
        if a.lower() not in [str(x).lower() for x in out]:
            out.append(a)
    return out if len(out) > 1 else out[0]


def mindless_get(seg, q):
    m = re.search(r"""(['"]?)%s\1\s*:\s*(\[[^\]]*\]|'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""" % re.escape(q), seg)
    if not m:
        raise RuntimeError('key %s not found' % q)
    import ast
    return ast.literal_eval(m.group(2))


def apply_round2(n, key, h):
    sets, adds = KEY_SET.get((n, key), {}), KEY_ADD.get((n, key), {})
    if not sets and not adds:
        return h
    qs = list(dict.fromkeys(list(sets) + list(adds)))
    if 'const CONFIG = ' in h:                      # mocks 1-24
        i = h.index('const CONFIG = ') + len('const CONFIG = ')
        cfg, j = json.JSONDecoder().raw_decode(h, i)
        for q in qs:
            v = merged(cfg['answers'][q], sets.get(q), adds.get(q))
            cfg['answers'][q] = v if isinstance(v, list) else [v]
        return h[:i] + json.dumps(cfg, ensure_ascii=False) + h[j:]
    if 'var KEY = {' in h:                           # mock 60 (paper)
        i = h.index('var KEY = ') + len('var KEY = ')
        k, j = json.JSONDecoder().raw_decode(h, i)
        for q in qs:
            v = merged(k[q], sets.get(q), adds.get(q))
            k[q] = v if isinstance(v, list) else [v]
        return h[:i] + json.dumps(k, ensure_ascii=False) + h[j:]
    if 'const ANSWERS = {' in h:                     # listening in mocks 25-28
        for q in qs:
            m = re.search(r'(\b%s:)(\[[^\]]*\])' % q, h[h.index('const ANSWERS = {'):])
            if not m:
                raise RuntimeError('ANSWERS key %s not found' % q)
            base = h.index('const ANSWERS = {')
            import ast
            v = merged(ast.literal_eval(m.group(2)), sets.get(q), adds.get(q))
            v = v if isinstance(v, list) else [v]
            h = h[:base + m.start(2)] + json.dumps(v, ensure_ascii=False) + h[base + m.end(2):]
        return h
    if 'const testData' in h:                        # mocks 25-28 and 65
        for q in qs:
            m = re.search(r'("(?:q?id)"\s*:\s*%s\s*,(?:(?!"(?:q?id)"\s*:).)*?"correctAnswer"\s*:\s*)(\[[^\]]*\]|"[^"]*")' % q, h, flags=re.S)
            if not m:
                raise RuntimeError('testData key %s not found' % q)
            old = json.loads(m.group(2))
            v = merged(old, sets.get(q), adds.get(q))
            h = h[:m.start(2)] + json.dumps(v if isinstance(v, list) else v, ensure_ascii=False) + h[m.end(2):]
        return h
    i = h.find('correctAnswers = {')                 # mocks 29-66
    seg = h[i:h.find('};', i)]
    fixes = {q: merged(mindless_get(seg, q), sets.get(q), adds.get(q)) for q in qs}
    if any(isinstance(v, list) for v in fixes.values()):
        h = allow_alternatives(h)
    return set_keys(h, fixes)


# Passage and question text that was wrong in the source files.
TEXT_FIXES = {
    (1, 'reading'): [
        ('allows for intelligence brought up in normal conditions and then mn t and creative ability',
         'allows for intelligence and creative ability'),
        # the source file lost the paragraph that Q35 (the 1952 flame) is about; restored here in summary form
        ('<p>Committee in the hope of getting the chance to create the torch.',
         '<p>The flame returned in modern times. A cauldron burned at the 1928 Amsterdam Games, though without a relay, '
         'and the first Olympic torch relay was held for the 1936 Berlin Summer Games. The Winter Olympics did not have '
         'a relay until 1952, and in that year the torch was lit not in Olympia, Greece, but in Norway. Since the 1964 '
         'Innsbruck Winter Games the flame has been lit at Olympia.</p>\n<p>Today, design teams from around the world '
         'submit their proposals to the Olympic Committee in the hope of getting the chance to create the torch.'),
    ],
    (22, 'reading'): [('Rightly, Davies his story', 'Rightly, Davies begins his story'),
                      ('the belief that inner of pleasure', 'the belief that inner experiences of pleasure'),
                      ('lad analyses', 'lab analyses')],
    (34, 'listening'): [('adding a lot of retial outlet', 'adding a lot of retail outlets'),
                        ('How did the students feel about the software?', 'How did the department begin its contact with Willows?'),
                        ('How did the student fell about the software', 'How did the student feel about the software?')],
    # the crested moa is also described as laying larger eggs, so "the biggest eggs" fitted Q28 as well as the keyed B
    (54, 'listening'): [('data-letter="C" draggable="true">C the biggest eggs<', 'data-letter="C" draggable="true">C the longest neck<')],
    (48, 'listening'): [('Originally, country</p>', 'Originally, country towns</p>')],
    (6, 'listening'): [('<strong>A–G</strong>, next to Questions 15–20', '<strong>A–F</strong>, next to Questions 15–20')],
    (42, 'listening'): [('<strong>A-G</strong>, next to questions 15-20', '<strong>A-F</strong>, next to questions 15-20'),
                        # Q23: Jen also says the boys' maths is helpful, so option A was a second correct answer
                        ('&nbsp;&nbsp;The boys are good at maths which is very helpful.', '&nbsp;&nbsp;The boys rely too much on her for the calculations.')],
    # passage 2 stopped mid-sentence in paragraph I and had lost paragraph J (Q17, Q23, Q26 depend on them);
    # restored here in summary form from the article's content
    (35, 'reading'): [('But Cameron was the first one in\n                </div>',
                       'But Cameron was the first one to scrape it off, grow it and find out what it actually is." The white '
                       'coating turned out to be a species of <em>Streptomyces</em> bacterium, the group that supplies about half '
                       'of the antibiotics used in medicine. This species is a potent poisoner of Escovopsis, and Mr Currie found '
                       'it on the leaf-cutters and on the lower attines alike: both carry it on a special patch of the cuticle and '
                       'use it to keep the deadly mold in check.</p>\n'
                       '                    <p><strong>J</strong>&nbsp;&nbsp;In other words, it seems that some ant equivalent of '
                       'Alexander Fleming discovered antibiotics millions of years before people did. The researchers point out '
                       'that the leaf-cutters have achieved two things that human farmers have not: they grow a single-variety '
                       'crop on a huge scale without it being wiped out by disease, and they have relied on an antibiotic for '
                       'millions of years without the pathogen becoming resistant to it.</p>\n                </div>')],
    # paragraph E began mid-sentence ("Smithsonian Tropical Research Institute in Panama. Smith had...")
    (42, 'reading'): [('<strong>E</strong>&nbsp;&nbsp;Smithsonian Tropical Research Institute in Panama. Smith had',
                       '<strong>E</strong>&nbsp;&nbsp;The next major breakthrough came in 1990 from Alan Smith of the '
                       'Smithsonian Tropical Research Institute in Panama. Smith had')],
    # Q25: the "looking forward" line is Annie's (she answers the professor's question to her), not the man's
    (35, 'listening'): [("What is the man\'s attitude after the discussion?", "How does Annie feel about the reflective journal after talking to the professor?"),
                        ('A   He thinks it is useless.', 'A   She thinks it is pointless.'),
                        ('B   He is looking forward to doing the assignment', 'B   She is looking forward to writing it.'),
                        ('C   He feels uncertain about it.', 'C   She feels uncertain about it.')],
    # Q29-30: the tutor also talks about where people live and work, which matched B and E as well as the keyed C/D
    (7, 'listening'): [('<span>the employment strategy</span>', '<span>the tourism industry</span>'),
                       ('<span>the suburban areas</span>', '<span>the water supply</span>')],
    (48, 'reading'): [('value="A"> easoning of Worse Choice Making', 'value="A"> Reasoning of Worse Choice Making')],
    (63, 'reading'): [('The text has four sections. Choose the correct heading', 'The text has six sections. Choose the correct heading')],
    (34, 'reading'): [('value=\\"C\\"> explain why he needs to do away with the simple observation',
                       'value=\\"C\\"> explain how people understand music')],
    (28, 'writing'): [('employment in the UK in 1998 and 2012', 'employment in the UK in 1988 and 2012')],   # the charts say 1988
    (32, 'writing'): [('the reasons of students to study a particular in a UK university in the year 1987 and 2007',
                       'the main reasons why students chose a particular college or university in the UK in 1987 and 2007')],
    (34, 'writing'): [('countries,students', 'countries, students'), ('others,the government', 'others, the government')],
    (37, 'writing'): [('in four countries in four countries', 'in four countries'),
                      # Task 2 was the same question as Mock 36's
                      ('Some people think parents should read or tell stories to children. Others think parents needn’t do that as children can read books or watch TV, movies by themselves.',
                       'Some people believe that children should be given regular household chores from an early age. Others think that children’s time is better spent on schoolwork and play.')],
    (39, 'writing'): [('Some scientist think that there are intelligent life forms on other planets and message should be sent to contact them other scientist think that it is a bad idea and would be dangerous. <br><br> Discuss both the view and give your opinion.',
                       'Some scientists think that there are intelligent life forms on other planets and that messages should be sent to contact them. Other scientists think that this is a bad idea and could be dangerous. <br><br> Discuss both these views and give your own opinion.')],
    (48, 'writing'): [('The percentage of 3 types of crimes: car theft, house burglary &amp; street robbery in England &amp; Wales from 1970 to 2015.',
                       'The graph shows the percentage of three types of crime (car theft, house burglary and street robbery) in England and Wales from 1970 to 2000.'),
                      ('<p><em><strong>Give reasons for your answer and include any relevant examples from your own knowledge or experience.</strong></em></p>\n                        </div>',
                       '</div>')],
    (49, 'writing'): [('text-align:center">4,410,284</td>', 'text-align:center">4,407,267</td>')],  # the age groups add up to 4,407,267
    (65, 'writing'): [(' The graph below shows the production levels of the main kinds of fuel in the UK between 1981 and 2000.\n</strong></p>\n                        <p><strong></strong></p>',
                       ' The graph below shows the production levels of the main kinds of fuel in the UK between 1981 and 2000.</strong></p>\n                        <p><strong>Summarise the information by selecting and reporting the main features, and make comparisons where relevant.</strong></p>'),
                      ('Is this a positive or negative development?<br><br></strong></em></p>\n                        </div>\n                        <p></p>',
                       'Is this a positive or negative development?</strong></em></p>\n                        </div>\n                        <p>Give reasons for your answer and include any relevant examples from your own knowledge or experience.</p>')],
}

# Question statements that allowed more than one defensible answer; reworded so that only the keyed answer fits.
REWORD = {
    (6, 'reading'): [('Flood makes the river shorter than it used to be, which means faster speed and more damage to the constructions on the flood plain.',
                      'Engineering work has made the Rhine shorter than it used to be, so it flows faster and floods do more damage to buildings on the flood plain.')],
    (31, 'reading'): [('name="q10" value="B"> John William Strutt</label>', 'name="q10" value="B"> Daniel Colladon</label>')],
    (32, 'reading'): [('Still, the load capacity of current Prius version was limited in its ', 'Still, the battery pack of this Prius version limited its ')],
    (13, 'reading'): [('Smoking habits are a crucial cause in some cancers.',
                       'Researchers are certain that air pollution alone explains the rise in lung cancer.'),
                      ('Continuing physical exercise is likely to assist digestive function.',
                       'Cotman found that exercise made no difference to the brains of rats.'),
                      ('Isolation may cause a higher level of stress hormones.',
                       'Elderly people who live alone can have high levels of stress hormones even while they sleep.'),
                      ('The time for the highest level of efficacy of the flu shot turned out to be within the weeks previous to the flu season.',
                       "Jackson's study found that the flu shot gave its greatest benefit after the flu season had started."),
                      ('The flu deaths account for five per cent of annual winter deaths in the age group of 65 or over.',
                       'Flu kills approximately 36,000 people in the US every winter.'),
                      ('These ethical dilemmas have influenced health problems in ',
                       'These ethical dilemmas have affected healthcare in '),
                      (' where drug companies encouraged their trials.', ' where clinical trials are a prospering industry.')],
    (28, 'reading'): [('REM sleep is felt to be the most important for the body’s rest.',
                       'People who dream more feel more rested the next day.')],
    (30, 'reading'): [('Socialization takes a long process, while compliance is the beginning of it.',
                       'Scientists agree on exactly how long the process of socialization takes.'),
                      ('Noncompliant Children are simple to deal with the relationship with the people at the same age when they are growing up.',
                       'Henry Porter says that as children grow older, they become more skilful at negotiating or giving reasons for refusing.')],
    (48, 'reading'): [('explained children are less likely to tell something interactive to their mother than to their friends',
                       'argued that interacting with other children is more challenging because children do not adapt to each other\'s communicative needs')],
    (49, 'reading'): [('Increasing pay can lead to the high work motivation.', 'Money is always the most effective way to motivate employees.'),
                      ('The two studies are done to analyze the relationship between the natural drives and the attitude of employees.',
                       'The two studies found that the four drives had little connection with employee motivation.')],
    (50, 'reading'): [('The Lapita could canoe in the prevailing wind.', 'The Lapita sailed eastward against the prevailing trade winds.'),
                      ('The majority of the Lapita dwelled on Fiji.', 'The Lapita numbered many hundreds of thousands.')],
    (51, 'reading'): [('Interrupted brome became extinct because they were kept accidentally at room temperature.',
                       'The interrupted brome seeds stored at Cambridge died because they were kept at room temperature.'),
                      ('9. identified interrupted brome as another species of brome.',
                       '9. found evidence that interrupted brome developed from another weedy grass.')],
    (57, 'reading'): [('The Central Government of China concluded the second research scheme of climate change is less than one year.',
                       "China's highest government body recently published the conclusions of a twelve-month research session on climate change."),
                      ('The main topic of the G8 Meeting in Japan was to discuss greenhouse gas emissions.',
                       'The Chinese prime minister was unwilling to raise climate change at the G8 summit in Japan.')],
}

# Task 1 pictures with errors in the source: Mock 39's legend read "1992" three times (1992, 1997, 2002);
# Mock 64's table listed "Cetirizine" (a medicine) as a car company (Citroën).
# Charts redrawn by tools/charts/make_task1_charts.py: the source images carried site watermarks or logos (29, 30,
# 31, 32, 34, 41, 55, 63, 65), misspellings (12: "Belguim", "pounds string"), untitled and identical pies (9), shares adding
# up to over 100% (55) or the same data as another mock (33). Maps: watermarks removed (56, 58), "schme" fixed (56),
# year labels added (18).
IMAGE_FIXES = {(39, 'writing'): 'mock39_task1.png', (64, 'writing'): 'mock64_task1.png',
               **{(n, 'writing'): 'mock%02d_task1.png' % n for n in (9, 12, 18, 29, 30, 31, 32, 33, 34, 41, 55, 56, 58, 63, 65)},
               # station map: mock 6 showed a gallery plan from another test; mock 42's copy had a site watermark
               (6, 'listening'): 'station_map.png', (42, 'listening'): 'station_map.png'}

# Hide panels that should never be shown during a test: the Part 3 "Show Explanation" button (it reveals the answers;
# the adapter only hid the Part 2 one), explanations copied from another test (mocks 51, 55, 66), and a made-up
# "Results 7.0 Good User" band panel in some Writing papers.
HIDE_CSS = {
    'reading': '<style>[id^="show-explanation-btn"],.explanation-section{display:none!important}</style>',
    'writing': '<style>#resultsContainer{display:none!important}</style>',
}


def apply_text_fixes(n, key, h):
    for old, new in TEXT_FIXES.get((n, key), []):
        if new in h and old not in h:
            continue
        if old not in h:
            raise RuntimeError('text fix not found in mock %d %s: %s' % (n, key, old[:60]))
        h = h.replace(old, new, 1)
    if (n, key) in IMAGE_FIXES:
        import base64
        p = os.path.join(ROOT, 'tools', 'assets', IMAGE_FIXES[(n, key)])
        uri = 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()
        h = re.sub(r'(<img\b[^>]*\bsrc=")data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', lambda m: m.group(1) + uri, h, count=1)
        if key == 'writing':   # several source images carried alt text from another task
            h = re.sub(r'(<img\b[^>]*?\balt=")[^"]*(")', r'\1Task 1 visual\2', h, count=1)
    h = h.replace(".map(p => p.textContent.replace(/\\s+/g, ' ').trim())", ".map(p => { const c = p.cloneNode(true); c.querySelectorAll('br').forEach(b => b.replaceWith(' ')); return c.textContent.replace(/\\s+/g, ' ').trim(); })")
    if key == 'writing' and 'Question: The bar chart shows the type of music bought in the USA in 2010' in h:
        # the saved copy of the answers printed another test's questions; it now copies this paper's own prompts
        h = h.replace('function saveWritingToFile(', "function __i7prompt(n) { const box = document.querySelector('#part-' + n + ' .instructions') || document.querySelector('#part-' + n); return box ? [...box.querySelectorAll('.task-prompt p, .task-prompt + p')].map(p => { const c = p.cloneNode(true); c.querySelectorAll('br').forEach(b => b.replaceWith(' ')); return c.textContent.replace(/\\s+/g, ' ').trim(); }).filter(Boolean).join('\\n\\n') : ''; }\n        function saveWritingToFile(", 1)
        h = re.sub(r'Question: The bar chart shows the type of music bought in the USA in 2010, by age group\.\n\nSummari[sz]e the information by selecting and reporting the main points and make comparisons where relevant\.',
                   lambda m: 'Question: ${__i7prompt(1)}', h)
        h = re.sub(r'Question: Modern buildings change the character and appearance of towns and cities\..*?experience\.',
                   lambda m: 'Question: ${__i7prompt(2)}', h, flags=re.S)
    if n == 9 and key == 'writing':    # the three pies are now one image
        h = re.sub(r'\s*<img src="data:image/jpeg;base64,[A-Za-z0-9+/=]+" alt="(Coffee consumers pie chart|Who gets the profit pie chart)"[^>]*/>', '', h)
        h = re.sub(r'<p style="text-align:center;font-size:13px;color:#4b5563;margin:-4px 0 14px;">Figure [123]: (Coffee producers|Coffee consumers|Who gets the profit)</p>', '', h)
    if n == 12 and key == 'writing':   # the chart has four countries
        h = h.replace('five countries', 'four countries')
    if n == 33 and key == 'writing':   # the Task 1 data repeated mock 32's; this mock now has its own task
        new33 = 'The charts below show how students at one UK university spent their weekly budget in 1997 and 2007.'
        for old33 in ('The charts below show the main reasons why students chose a particular university in the UK in 1997 and 2007.',
                      'The charts below show the reasons of students to study a particular in a UK university in the year 1987 and 2007.'):
            h = h.replace(old33, new33)
    for old, new in REWORD.get((n, key), []):
        if old not in h and new not in h:
            raise RuntimeError('reword not found in mock %d %s: %s' % (n, key, old[:60]))
        h = h.replace(old, new)
    if n == 48 and key == 'reading':   # passage 2 printed the Harris paragraph twice (as H and again as I)
        h = re.sub(r'\n\s*<p><strong>I</strong> A different explanation has been put forward by Harris\..*?counterfactual reasoning\.</p>', '', h, count=1, flags=re.S)
    if n == 35 and key == 'reading':   # paragraph E was printed twice (second copy without its letter)
        h = re.sub(r'\n\s*<p>But after three years of sifting[^<]*</p>', '', h, count=1)
    if n == 51 and key == 'reading':   # paragraphs H and I of passage 2 belong to another passage (memory and age)
        h = re.sub(r'\s*<p><strong>H</strong>&nbsp;&nbsp;"You could say metamemory.*?mental prime\.</p>', '', h, count=1, flags=re.S)
    return h


def set_keys(h, fixes):
    i = h.find('correctAnswers = {')
    if i < 0:
        return h
    j = h.find('};', i)
    seg = h[i:j]
    for q, val in fixes.items():
        lit = _json.dumps(val, ensure_ascii=False) if (isinstance(val, list) or "'" in val) else "'%s'" % val
        pat = r"""((['"]?)%s\2\s*:\s*)(\[[^\]]*\]|'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""" % re.escape(q)
        seg, k = re.subn(pat, lambda m: m.group(1) + lit, seg, count=1)
        if not k:
            raise RuntimeError('key %s not found' % q)
    return h[:i] + seg + h[j:]


ALT_EQ = ("(Array.isArray(correctAnswer) ? correctAnswer.some(a => String(a).trim().toLowerCase() === "
          "String(userAnswer).trim().toLowerCase()) : userAnswer === correctAnswer)")


def allow_alternatives(h):
    """Let exact-match comparisons accept a list of answers (needed for keys with alternatives)."""
    h = h.replace('(Array.isArray(correctAnswer) ? correctAnswer.includes(userAnswer) : userAnswer === correctAnswer)', ALT_EQ)
    if ALT_EQ in h:
        return h
    h = re.sub(r'(?<![\w.(])userAnswer === correctAnswer(?![.\w])', lambda m: ALT_EQ, h)
    h = h.replace('isCorrect = userAnswer === correctAnswer.toLowerCase();',
                  'isCorrect = (Array.isArray(correctAnswer) ? correctAnswer : [correctAnswer]).some(a => userAnswer === String(a).toLowerCase());')
    return h


def fix_section(n, key, h):
    h = rebrand(h)
    block = ''
    if (n, key) in KEY_FIXES:
        h = allow_alternatives(h)
        h = set_keys(h, KEY_FIXES[(n, key)])
    h = apply_round2(n, key, h)
    h = apply_text_fixes(n, key, h)
    hide = HIDE_CSS.get(key, '') if n >= 29 else ''
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
        h = h.replace('</head>', MARK_START + MOCK36_READING + hide + MARK_END + '</head>', 1)
        return h
    return add_block(h, block + hide)


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
