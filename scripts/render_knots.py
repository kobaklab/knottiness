"""Re-render <poster>/output/knots/<seq>.svg from <poster>/traced/<seq>.json (no re-tracing), e.g.
after changing the rendering in tait/render.py. About 2 s per knot (Bézier fitting).

  uv run scripts/render_knots.py --poster tenfold              # all knots of the poster
  uv run scripts/render_knots.py --poster tenfold --seq 1-90   # a range
  uv run scripts/render_knots.py --poster tenfold --gap 2.0    # wider gaps -> output/knots/gap2/ (cache of the
                                                               # white posters; build_poster.py makes it itself)
  (from inside a poster directory, --poster can be left out: uv run ../scripts/render_knots.py)"""
import argparse, json
import numpy as np
from tait import Poster, poster_arg
from tait.render import svg

ap = argparse.ArgumentParser()
poster_arg(ap)
ap.add_argument('--seq', default='all', help="'all', '12' or '1-90'")
ap.add_argument('--stroke', type=float, default=6.5, help='line width in working px (median knot height: 314)')
ap.add_argument('--gap', type=float, default=None, help='margin of the gaps in stroke widths (default 1.1: the committed '
                'knots); another value writes to output/knots/gap<value>/')
a = ap.parse_args()
P = Poster(a.poster)
gap = a.gap if a.gap is not None else 1.1
outdir = P.output / 'knots' / (f'gap{gap:g}' if abs(gap - 1.1) > 1e-9 else '')
outdir.mkdir(parents=True, exist_ok=True)
if a.seq == 'all': lo, hi = 0, 10 ** 9
else: lo, hi = map(int, a.seq.split('-')) if '-' in a.seq else (int(a.seq), int(a.seq))
files = [p for p in sorted(P.traced.glob('[0-9][0-9][0-9].json')) if lo <= int(p.stem) <= hi]
bad = []
for p in files:
    rec = json.load(open(p))
    s, pieces = svg(np.array(rec['curve']), *rec['crop_size'], stroke=a.stroke, gap=gap)
    if pieces != len(rec['crossings']): bad.append((rec['seq'], pieces))   # one piece per crossing
    (outdir / f"{rec['seq']:03d}.svg").write_text(s)
print(f'{len(files)} knots rendered to', outdir, f'(stroke {a.stroke:g})')
print('knots not cut into one piece per crossing:', bad or 'none')
