"""Transcribe the Listening recordings so answer keys can be checked against what is said.

Runs on GitHub Actions (see .github/workflows/transcribe.yml). Output goes to transcripts/ and is uploaded only
to a private draft release, never committed.

    python3 tools/offline/transcribe.py SHARD SHARDS
"""
import glob, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_offline import get_audio  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')


def audio_for(n, tmp, report):
    d = os.path.join(ROOT, 'mocks', 'mock-%02d' % n)
    local = glob.glob(os.path.join(d, '*.mp3'))
    if local:
        return local[0]
    html = open(glob.glob(os.path.join(d, 'IELTS_Full_Mock_*.html'))[0], encoding='utf-8').read()
    m = re.search(r"__i7remote = '([^']*)'", html)
    if not m:
        report.append('mock %d: no recording address' % n)
        return None
    out = os.path.join(tmp, 'mock-%02d' % n)
    if get_audio(m.group(1), out, n, report):
        return os.path.join(out, 'Listening.mp3')
    return None


def main():
    shard, shards = int(sys.argv[1]), int(sys.argv[2])
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small.en'), device='cpu', compute_type='int8')
    os.makedirs(os.path.join(ROOT, 'transcripts'), exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(1, 67):
            if n % shards != shard:
                continue
            path = audio_for(n, tmp, report)
            if not path:
                print('::error::mock %d: recording not available' % n)
                continue
            segments, info = model.transcribe(path, beam_size=1, vad_filter=False, condition_on_previous_text=False)
            lines = []
            for s in segments:
                lines.append('[%02d:%02d] %s' % (int(s.start // 60), int(s.start % 60), s.text.strip()))
            open(os.path.join(ROOT, 'transcripts', 'mock-%02d.txt' % n), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
            print('mock %d: %.0f min transcribed' % (n, info.duration / 60))
    for r in report:
        print(r)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        for line in traceback.format_exc().strip().splitlines()[-6:]:
            print('::error::' + line)
        raise
