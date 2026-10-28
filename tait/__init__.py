"""Vector reconstructions of P. G. Tait's knot tables: 'Tenfold Knottiness' (Trans. RSE 32, 1885) and
'The first seven orders of knottiness'.

The repository holds one directory per poster (tenfold/, seven-orders/), each with its own
sources/, data/, traced/, output/ and poster-specific scripts/; this package, the shared scripts in
scripts/ and the fonts in fonts/ serve both."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = ROOT / 'fonts'
POSTERS = ('tenfold', 'seven-orders')

class Poster:
    """The directories of one poster: <ROOT>/<name>/{sources,data,traced,output}."""
    def __init__(self, name):
        if name not in POSTERS: raise ValueError(f'unknown poster {name!r}; one of {", ".join(POSTERS)}')
        self.name = name
        self.dir = ROOT / name
        self.sources, self.data, self.traced, self.output = (self.dir / d for d in ('sources', 'data', 'traced', 'output'))
    def __repr__(self): return f'Poster({self.name!r})'

    @staticmethod
    def from_cwd():
        """the poster whose directory contains the working directory, or None"""
        cwd = Path(os.getcwd()).resolve()
        return next((Poster(n) for n in POSTERS if cwd == ROOT / n or (ROOT / n) in cwd.parents), None)

def poster_arg(ap):
    """add --poster to an argparse parser; default: the poster directory the command is run from"""
    here = Poster.from_cwd()
    ap.add_argument('--poster', choices=POSTERS, required=here is None, default=here and here.name,
                    help='which poster (default: the poster directory you are in)')

TENFOLD = Poster('tenfold')
SEVEN_ORDERS = Poster('seven-orders')
