"""Read the census tables: <poster>/data/census.csv (one row per form), and the tenfold transcription
tenfold/data/census_p503.txt (Tait's list, On Knots III §21)."""
import csv
from . import TENFOLD
DATA_DIR = TENFOLD.data

PLATE_SIZE = {'LXXX': 182, 'LXXXI': 182, 'XLIV': 144}
INT_COLS = ('seq', 'type', 'form', 'order', 'n_forms')

def parse_transcription(path=DATA_DIR / 'census_p503.txt'):
    """-> list of dicts (type, form, n_forms, code) in plate order"""
    forms = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'): continue
        t, codes = line.split(':'); codes = codes.split()
        for i, c in enumerate(codes):
            forms.append(dict(type=int(t), form=i + 1, n_forms=len(codes), code=c))
    return forms

def load(path=DATA_DIR / 'census.csv'):
    """census.csv of a poster (default: tenfold) -> list of dicts; integer columns converted"""
    with open(path, encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in INT_COLS:
            if k in r: r[k] = int(r[k])
        for k in ('row', 'col'): r[k] = int(r[k]) if r.get(k) else None
    return rows

def plate_forms(plate):
    """census rows of one plate, in plate (reading) order"""
    from . import SEVEN_ORDERS
    poster = SEVEN_ORDERS if plate == 'XLIV' else TENFOLD
    return [r for r in load(poster.data / 'census.csv') if r['plate'] == plate]
