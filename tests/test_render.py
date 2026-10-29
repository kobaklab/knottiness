"""Rendering: the committed knot SVGs are what the renderer produces from the committed traces."""
import json
import numpy as np
import pytest
from tait import TENFOLD, SEVEN_ORDERS
from tait.render import svg, DEFAULT_STROKE

SAMPLE = [(TENFOLD, s) for s in (1, 70, 133, 182, 183, 352, 364)] + [(SEVEN_ORDERS, s) for s in (1, 40, 144)]

@pytest.mark.parametrize('poster,seq', SAMPLE, ids=[f'{p.name}-{s}' for p, s in SAMPLE])
def test_committed_knot_svg_is_reproduced(poster, seq):
    rec = json.load(open(poster.traced / f'{seq:03d}.json'))
    s, pieces = svg(np.array(rec['curve']), *rec['crop_size'])
    assert pieces == len(rec['crossings'])                        # one piece per crossing
    assert s == (poster.output / 'knots' / f'{seq:03d}.svg').read_text()

def test_default_stroke_is_the_posters():
    assert DEFAULT_STROKE == 6.5
    for poster in (TENFOLD, SEVEN_ORDERS):
        assert f'stroke={DEFAULT_STROKE:g} margin={1.1 * DEFAULT_STROKE:g}' in (poster.output / 'knots' / '001.svg').read_text()
