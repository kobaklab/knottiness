"""The documentation: relative links and anchors resolve, and the scripts the READMEs name exist."""
import re, unicodedata
import pytest
from tait import ROOT

MD = sorted(p for p in ROOT.rglob('*.md') if '.venv' not in p.parts and 'node_modules' not in p.parts)
LINK = re.compile(r'!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')

def prose(path):
    """the lines of a markdown file outside code fences"""
    fence = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith('```'): fence = not fence; continue
        if not fence: yield line

def slug(heading):
    """GitHub's anchor of a heading"""
    h = re.sub(r'[`*_]', '', heading).strip().lower()
    h = ''.join(c for c in h if c == ' ' or c == '-' or unicodedata.category(c)[0] in 'LN')
    return h.replace(' ', '-')

def anchors(path):
    seen, out = {}, set()
    for line in prose(path):
        m = re.match(r'#{1,6}\s+(.*?)\s*#*$', line)
        if m:
            s = slug(m.group(1)); n = seen.get(s, 0); seen[s] = n + 1
            out.add(s if n == 0 else f'{s}-{n}')
    return out

@pytest.mark.parametrize('md', MD, ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_resolve(md):
    for line in prose(md):
        for target in LINK.findall(re.sub(r'`[^`]*`', '', line)):
            if re.match(r'(https?:|mailto:)', target): continue
            path, _, frag = target.partition('#')
            dest = (md.parent / path).resolve() if path else md
            assert dest.exists(), f'{md.name}: {target} does not exist'
            if frag and dest.suffix == '.md':
                assert frag in anchors(dest), f'{md.name}: no heading for #{frag} in {dest.name}'

def test_scripts_named_in_the_docs_exist():
    have = {p.name for p in ROOT.rglob('*.py') if '.venv' not in p.parts}
    for md in MD:
        text = '\n'.join(prose(md))
        for name in set(re.findall(r'\b([A-Za-z_][\w]*\.py)\b', text)):
            assert name in have, f'{md.relative_to(ROOT)} mentions {name}'
