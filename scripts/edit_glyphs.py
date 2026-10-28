"""Re-apply the hand edits of <poster>/data/glyphs.yaml ('edit' lists) to <poster>/traced/glyphs.json,
without re-tracing from the scans (tenfold/scripts/trace_glyphs.py applies them too). Idempotent: every edited glyph
keeps its untouched trace under 'traced', and the edits always start from that.

  uv run scripts/edit_glyphs.py --poster tenfold && uv run scripts/plot_glyphs.py --poster tenfold
  (from inside tenfold/: uv run ../scripts/edit_glyphs.py)"""
import argparse, json
from tait import Poster, poster_arg
from tait.glyphs import load_choices, apply_edits

ap = argparse.ArgumentParser(); poster_arg(ap); P = Poster(ap.parse_args().poster)
path = P.traced / 'glyphs.json'
data = json.load(open(path, encoding='utf-8'))
apply_edits(data['glyphs'], load_choices(P))
path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
print('edited:', ', '.join(k for k, g in data['glyphs'].items() if g.get('edited')) or 'none')
