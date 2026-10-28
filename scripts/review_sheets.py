"""Rebuild review sheets from existing traces (no re-tracing), e.g. after editing data/census.csv.
Shared by the posters: the plate selects the poster. Needs traced/candidates/ from a trace_rows.py run.

  uv run scripts/review_sheets.py --plate LXXXI            # all rows
  uv run scripts/review_sheets.py --plate LXXX --rows 1-3
  uv run scripts/review_sheets.py --plate XLIV
"""
import argparse
from tait.review import make_sheets
from tait.sources import PLATES

ap = argparse.ArgumentParser()
ap.add_argument('--plate', required=True, choices=list(PLATES))
ap.add_argument('--rows', default='all', help="'all', '3' or '1-3' (1-based)")
a = ap.parse_args()
if a.rows == 'all': rows = None
elif '-' in a.rows: lo, hi = map(int, a.rows.split('-')); rows = list(range(lo, hi + 1))
else: rows = [int(a.rows)]
make_sheets(a.plate, rows)
print('done')
