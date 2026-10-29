"""The traced annotation glyphs of both posters."""
import json
from collections import Counter
from tait import TENFOLD, SEVEN_ORDERS, ROOT
from tait.glyphs import path_to_geom

def load(poster): return json.load(open(poster.traced / 'glyphs.json', encoding='utf-8'))

def test_tenfold_glyph_set():
    g = load(TENFOLD)['glyphs']
    assert len(g) == 84
    assert Counter(v['cls'] for v in g.values()) == {'digits': 10, 'capitals': 30, 'italic': 18, 'upright': 16, 'greek': 10}
    for name, v in g.items():
        assert name == f"{v['cls']}/{v['char']}" and v['width'] > 0, name
        assert not path_to_geom(v['d']).is_empty, name

def test_seven_orders_adds_to_tenfold():
    ten, sev = load(TENFOLD), load(SEVEN_ORDERS)
    assert sev['based_on'] == 'tenfold/traced/glyphs.json' and (ROOT / sev['based_on']).exists()
    assert sev['stroke_width'] == ten['stroke_width']
    assert set(sev['glyphs']) == {f'upright/{c}' for c in 'ijmnvwxyz'} | {'punct/,'}
    assert not set(sev['glyphs']) & set(ten['glyphs'])

def test_every_label_character_has_a_glyph(tenfold_census, seven_census):
    """the characters of all labels set in traced glyphs exist in the glyph sets"""
    have = {k.split('/', 1)[1] for k in [*load(TENFOLD)['glyphs'], *load(SEVEN_ORDERS)['glyphs']]}
    need = set()
    for r in tenfold_census:
        need |= set(r['code'].rstrip('*')) | set(r['kirkman']) | set(r['type'])
    for r in seven_census:
        need |= set(r['kirkman']) | set(r['former']) | set(r['order'])
        if r['former'][:1].isupper(): need.add(',')
    assert need <= have, sorted(need - have)
