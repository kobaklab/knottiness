"""Tenfold Knottiness: census, Kirkman labels and traces, checked from the committed files."""
import re
from collections import Counter
from tait.codes import parse, letter_style
from tait.diagram import faces, flaps, KIRKMAN_LISTS, KIRKMAN_LIST_LENGTH

def test_census_totals(tenfold_census):
    """Tait's own totals (On Knots III, §21): 364 forms of 123 types; 133 / 200 / 25 / 6 forms per family"""
    assert len(tenfold_census) == 364 and len({r['type'] for r in tenfold_census}) == 123
    assert Counter(r['family'] for r in tenfold_census) == {'6/6': 133, '5/7': 200, '4/8': 25, '3/9': 6}
    assert [int(r['seq']) for r in tenfold_census] == list(range(1, 365))
    assert Counter(r['plate'] for r in tenfold_census) == {'LXXX': 182, 'LXXXI': 182}

def test_region_codes(tenfold_census):
    """every code is a pair of partitions of 20 with the family's mesh counts; bars only in the 6/6 family"""
    counts = {'6/6': [6, 6], '5/7': [5, 7], '4/8': [4, 8], '3/9': [3, 9]}
    for r in tenfold_census:
        fam, parts, amph = parse(r['code'])
        assert fam == r['family'], r['seq']
        assert sorted(len(p) for p in parts) == counts[fam], r['seq']
        assert all(sum(p) == 20 for p in parts), r['seq']
        assert not amph or fam == '6/6'

def test_grid_positions(tenfold_census):
    """14 rows x 13 columns per plate, every position filled once"""
    for plate in ('LXXX', 'LXXXI'):
        pos = [(int(r['row']), int(r['col'])) for r in tenfold_census if r['plate'] == plate]
        assert sorted(pos) == [(i, j) for i in range(1, 15) for j in range(1, 14)]

def test_kirkman_labels(tenfold_census):
    """363 labels (#133, the solid knot, has none); the numbers of each list run 1..n, as long as Kirkman's list;
    only the C list is irregular: it runs to C80 without C52 (see tenfold/README.md)"""
    nums = {}
    for r in tenfold_census:
        if not r['kirkman']:
            assert r['seq'] == '133'; continue
        m = re.fullmatch(r'(\D+)(\d+)', r['kirkman']); nums.setdefault(m.group(1), []).append(int(m.group(2)))
    assert sum(map(len, nums.values())) == 363 and set(nums) == set(KIRKMAN_LIST_LENGTH)
    for letter, n in nums.items():
        assert len(n) == KIRKMAN_LIST_LENGTH[letter], letter
        want = [i for i in range(1, 81) if i != 52] if letter == 'C' else list(range(1, len(n) + 1))
        assert sorted(n) == want, letter

def test_traces_are_valid(tenfold_census, tenfold_traces):
    """all 364 traces were accepted: one strand, ten crossings, and the outer region in the class of the
    code's second letter (Tait's convention)"""
    assert sorted(tenfold_traces) == list(range(1, 365))
    for r in tenfold_census:
        t = tenfold_traces[int(r['seq'])]
        assert t['ok'] and not t['problems'] and t['source'] in ('HT', 'KA', 'IA'), r['seq']
        assert len(t['crossings']) == 10 and len(t['curve']) > 50, r['seq']
        second = ''.join(map(str, sorted(parse(r['code'])[1][1], reverse=True)))
        assert t['outer_class'] == second, (r['seq'], r['code'])
        assert (t['plate'], t['row'], t['col']) == (r['plate'], int(r['row']), int(r['col'])), r['seq']

def test_kirkman_letters_match_flaps(tenfold_census, tenfold_traces):
    """the letter of each Kirkman label is fixed by the flaps of the traced knot (the check of scripts/check_kirkman.py)"""
    inv = {tuple(sorted(v.items())): k for k, v in KIRKMAN_LISTS.items()}
    for r in tenfold_census:
        F = flaps(tenfold_traces[int(r['seq'])]['curve'])
        want = re.sub(r'\d+$', '', r['kirkman']) or 'solid'
        assert inv.get(tuple(sorted(F.items())), 'solid' if not F else '?') == want, r['seq']

def test_faces_of_a_ten_crossing_diagram(tenfold_traces):
    for seq in (1, 133, 364):
        F = faces(tenfold_traces[seq]['curve'])
        assert len(F) == 12 and sum(map(len, F)) == 40     # n + 2 faces, 4n corners

def test_letter_style():
    assert [letter_style(c, '6/6') for c in 'CG'] == ['upright'] * 2
    assert letter_style('a', '5/7') == 'italic' and letter_style('a', '4/8') == 'upright'
    assert letter_style('κ', '4/8') == 'italic'
