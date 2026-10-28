"""Tait's region codes (On Knots III, §18, p. 501).

Each letter stands for a partition of 20: the corner counts of one class of meshes
(the 'right-handed' or 'left-handed' regions of the checkerboard colouring).
The same Latin letter means different partitions depending on the mesh split, so the
table is chosen by the Greek letter in the code (or capitals for the 6/6 split)."""
SIX_SIX = dict(A="653222", B="643322", C="633332", D="554222", E="553322",
               F="544322", G="543332", H="533333", K="444332", L="443333")
FIVE = dict(a="77222", b="76322", c="75422", d="75332", e="74432", f="74333", g="66422",
            h="66332", k="65522", l="65432", m="65333", n="64442", p="64433", q="55532",
            r="55442", s="55433", t="54443", u="44444")
SEVEN = {"α": "5522222", "β": "5432222", "γ": "5333222", "δ": "4442222",
         "ε": "4433222", "ζ": "4333322", "η": "3333332"}
FOUR = dict(a="8732", b="8633", c="8552", d="8543", e="7742", f="7652", g="7643",
            h="7544", k="6653", l="6554")
EIGHT = {"θ": "43322222", "κ": "33332222"}
THREE = dict(p="992", q="983", r="974", s="965", t="875", u="776")
NINE = {"λ": "332222222"}

def parse(code):
    """'εk' -> ('5/7', [partition, partition]); 'C*' (barred) -> amphicheiral, both classes equal.
    Partitions are given in the order printed; the second is the class containing the outer region."""
    amph = code.endswith('*'); letters = list(code.rstrip('*'))
    if amph: letters = letters * 2
    if len(letters) != 2: raise ValueError(code)
    if all(c in SIX_SIX for c in letters):
        fam, tables = '6/6', [SIX_SIX]
    elif any(c in EIGHT for c in letters):
        fam, tables = '4/8', [FOUR, EIGHT]
    elif any(c in NINE for c in letters):
        fam, tables = '3/9', [THREE, NINE]
    else:
        fam, tables = '5/7', [FIVE, SEVEN]
    parts = []
    for c in letters:
        t = [tb for tb in tables if c in tb]
        if not t: raise ValueError(f'{code}: letter {c} not valid for {fam}')
        parts.append(tuple(int(x) for x in t[0][c]))
    return fam, parts, amph

def partitions(code):
    """unordered pair of sorted partitions, for comparison with a traced diagram"""
    return sorted(tuple(sorted(p, reverse=True)) for p in parse(code)[1])
