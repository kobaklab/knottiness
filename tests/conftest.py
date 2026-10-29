"""Shared fixtures. The tests read only committed files (no scans needed)."""
import csv, json
import pytest
from tait import TENFOLD, SEVEN_ORDERS

def read_csv(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))

@pytest.fixture(scope='session')
def tenfold_census(): return read_csv(TENFOLD.data / 'census.csv')

@pytest.fixture(scope='session')
def seven_census(): return read_csv(SEVEN_ORDERS.data / 'census.csv')

@pytest.fixture(scope='session')
def tenfold_traces():
    return {int(p.stem): json.load(open(p)) for p in sorted(TENFOLD.traced.glob('[0-9][0-9][0-9].json'))}

@pytest.fixture(scope='session')
def seven_traces():
    return {int(p.stem): json.load(open(p)) for p in sorted(SEVEN_ORDERS.traced.glob('[0-9][0-9][0-9].json'))}
