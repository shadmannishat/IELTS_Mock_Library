"""Add countdown alerts to every section of every mock.

At 10, 5, 2 and 1 minutes left: a red ribbon blinks across the top of the screen and the clock blinks red.
From 5 minutes left the clock stays red; in the last 30 seconds it blinks red continuously.

The script finds the clock by itself (any visible mm:ss display that counts down), so it works with
every test engine in the library. Running this again replaces the previous version.

    python3 tools/timer_alerts.py            # all mocks
    python3 tools/timer_alerts.py 5 29       # selected mocks
"""
import glob, json, re, sys, os

MARK_START = '<!--i7-timer-alerts-->'
MARK_END = '<!--/i7-timer-alerts-->'

BLOCK = MARK_START + r"""<style>
@keyframes i7tblink{0%,49%{background-color:#dc2626;color:#fff;box-shadow:0 0 0 4px #dc2626}50%,100%{background-color:#fee2e2;color:#dc2626;box-shadow:0 0 0 4px #fee2e2}}
@keyframes i7rblink{0%,49%{background:#dc2626}50%,100%{background:#7f1d1d}}
.i7-tred:not(.i7-tblink){background-color:#fee2e2!important;color:#dc2626!important;box-shadow:0 0 0 4px #fee2e2!important;border-radius:6px}
.i7-tred:not(.i7-tblink) *{color:#dc2626!important}
.i7-tblink{animation:i7tblink 1s infinite!important;border-radius:6px}
.i7-tblink *{color:inherit!important}
#i7-ribbon{position:fixed;left:0;right:0;top:0;z-index:2147483000;color:#fff;text-align:center;font:700 18px/1 Arial,Helvetica,sans-serif;letter-spacing:.02em;padding:12px 10px;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.3);transform:translateY(-110%);transition:transform .25s ease;background:#dc2626}
#i7-ribbon.on{transform:none;animation:i7rblink .8s infinite}
</style>
<script>
(function(){
  if (window.__i7timerAlerts) return; window.__i7timerAlerts = true;
  var RX = /^\s*(?:(\d{1,2}):)?(\d{1,3}):(\d{2})\s*$/;
  var STEPS = [[600, '10 minutes left'], [300, '5 minutes left'], [120, '2 minutes left'], [60, '1 minute left']];
  var BLINK_MS = 8000;
  var seen = new WeakMap(), clock = null, box = null, prev = null, flashUntil = 0, ribbon = null, ribbonTimer = null;

  function secs(t){ var m = RX.exec(t); if (!m) return null; return (+(m[1] || 0)) * 3600 + (+m[2]) * 60 + (+m[3]); }
  function visible(e){ return !!(e.offsetParent || e.getClientRects().length); }
  function boxFor(e){
    // colour the clock's own pill (e.g. clock icon + digits) when it holds nothing else
    var p = e.parentElement;
    if (p && p !== document.body && p.textContent.trim() === e.textContent.trim() && p.querySelectorAll('button,input,select').length === 0) return p;
    return e;
  }
  function find(){
    var els = document.body ? document.body.getElementsByTagName('*') : [];
    for (var i = 0; i < els.length; i++) {
      var e = els[i]; if (e.children.length > 1 || e.id === 'i7-ribbon') continue;
      var t = e.textContent; if (!t || t.length > 12) continue;
      var s = secs(t); if (s === null || !visible(e)) continue;
      var before = seen.get(e); seen.set(e, s);
      if (before !== undefined && s < before) return e;   // it is counting down: this is the clock
    }
    return null;
  }
  function showRibbon(msg){
    if (!ribbon) { ribbon = document.createElement('div'); ribbon.id = 'i7-ribbon'; ribbon.setAttribute('role', 'alert'); document.body.appendChild(ribbon); }
    ribbon.textContent = '⏰ ' + msg;
    ribbon.classList.add('on');
    clearTimeout(ribbonTimer); ribbonTimer = setTimeout(function(){ ribbon.classList.remove('on'); }, BLINK_MS);
  }
  function hideOldNotice(){
    var b = document.getElementById('i7-bar');
    if (b && /minutes left/.test(b.textContent)) b.className = '';
  }
  function tick(){
    if (!clock || !document.contains(clock)) { clock = find(); box = clock && boxFor(clock); prev = null; if (!clock) return; }
    var s = secs(clock.textContent); if (s === null) return;
    if (prev !== null && s < prev) {
      for (var i = 0; i < STEPS.length; i++) if (prev > STEPS[i][0] && s <= STEPS[i][0]) { showRibbon(STEPS[i][1]); flashUntil = Date.now() + BLINK_MS; }
    }
    prev = s;
    hideOldNotice();
    var running = s > 0;
    var blink = running && (s <= 30 || Date.now() < flashUntil);
    box.classList.toggle('i7-tblink', blink);
    box.classList.toggle('i7-tred', s <= 300);
  }
  setInterval(tick, 250);
})();
</script>""" + MARK_END


def add_block(html):
    html = re.sub(re.escape(MARK_START) + '.*?' + re.escape(MARK_END), '', html, flags=re.S)
    i = html.lower().rfind('</body>')
    return html[:i] + BLOCK + html[i:] if i >= 0 else html + BLOCK


def enc(html):
    return json.dumps(html, ensure_ascii=False).replace('</', '<\\/')


def patch_file(path):
    s = open(path, encoding='utf-8').read()
    i0 = s.index('const SECTIONS = {')
    dec = json.JSONDecoder()
    parts, pos, n = [], 0, 0
    for m in re.finditer(r'(listening|reading|writing):"', s[i0:]):
        start = i0 + m.end() - 1
        html, end = dec.raw_decode(s, start)
        parts.append(s[pos:start]); parts.append(enc(add_block(html))); pos = end; n += 1
    parts.append(s[pos:])
    open(path, 'w', encoding='utf-8').write(''.join(parts))
    return n


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    want = set(int(a) for a in sys.argv[1:])
    for f in sorted(glob.glob(os.path.join(root, 'mocks/mock-*/IELTS_Full_Mock_*.html'))):
        num = int(re.search(r'mock-(\d+)', f).group(1))
        if want and num not in want: continue
        print(num, patch_file(f), 'sections')
