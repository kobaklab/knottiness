"""The First Seven Orders of Knottiness (Plate XLIV): census and traces, from the committed files."""
from collections import Counter
from tait.diagram import faces

def test_census_totals(seven_census):
    """Tait's totals (On Knots II, §5): 1, 1, 2, 3, 7, 18, 41 knots of 3..9 crossings; 144 figures"""
    assert len(seven_census) == 144
    types = {(r['order'], r['type']) for r in seven_census}
    assert Counter(o for o, _ in types) == {'3': 1, '4': 1, '5': 2, '6': 3, '7': 7, '8': 18, '9': 41}
    assert [int(r['seq']) for r in seven_census] == list(range(1, 145))

def test_traces_are_valid(seven_census, seven_traces):
    """every figure traced from the PDF: one strand, as many crossings as its order"""
    for r in seven_census:
        t = seven_traces[int(r['seq'])]
        assert t['ok'] and not t['problems'] and t['source'] == 'PDF', r['seq']
        assert len(t['crossings']) == int(r['order']), r['seq']

def test_faces(seven_census, seven_traces):
    for r in seven_census[::12]:
        n = int(r['order']); F = faces(seven_traces[int(r['seq'])]['curve'])
        assert len(F) == n + 2 and sum(map(len, F)) == 4 * n
