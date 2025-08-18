import re
from pathlib import Path

ID_RE       = re.compile(r'^@ID:\s*(.+)$', re.MULTILINE)
MAIN_HDR_RE = re.compile(r'^\s*(\*[A-Za-z0-9]{1,7})\s*:(.*)$')
DEP_HDR_RE  = re.compile(r'^\s*(%[a-z0-9_+-]+)\s*:(.*)$', re.IGNORECASE)
ANY_HDR_RE  = re.compile(r'(\*[A-Za-z0-9]{1,7}\s*:|%[a-z0-9_+-]+\s*:)', re.IGNORECASE)
END_RE_LINE = re.compile(r'^\s*@End\s*$', re.MULTILINE)

CTRL_EXCEPT_TAB_RE = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
ZEROWIDTH_RE       = re.compile(r'[\u200B-\u200D\uFEFF]')
LEADING_JUNK_RE    = re.compile(r'^[ \x00-\x08\x0B\x0C\x0E-\x1F\u200B-\u200D\uFEFF]+')

ALLOWED_DEP_TIER_NAMES = {"err","com","sit","mor","gra","act"}

def split_header_body(text: str):
    lines = text.splitlines()
    i = 0
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith('@')):
        i += 1
    return i, lines

def parse_id_codes(text: str) -> set[str]:
    codes = set()
    for m in ID_RE.finditer(text):
        fields = [x.strip() for x in m.group(1).split('|')]
        if len(fields) >= 3 and fields[2]:
            codes.add(fields[2])
    return codes

def count_header_occurrences(line: str) -> int:
    return len([m.group(0) for m in ANY_HDR_RE.finditer(line)])

def sanitize_controls(text: str):
    lines = text.splitlines()
    touched = []
    for i, s in enumerate(lines):
        original = s
        s = ZEROWIDTH_RE.sub('', s)
        s = ''.join(ch for ch in s if (ch == '\t' or not CTRL_EXCEPT_TAB_RE.match(ch)))
        s = LEADING_JUNK_RE.sub('', s)
        if s != original:
            lines[i] = s
            touched.append(i + 1)
    return "\n".join(lines), touched

def next_nonclobber_name(path: Path, suffix: str = ".fix") -> Path:
    base = path.stem
    newp = path.with_name(f"{base}{suffix}{path.suffix}")
    k = 1
    while newp.exists():
        newp = path.with_name(f"{base}{suffix}.{k}{path.suffix}")
        k += 1
    return newp

def dir_has_cha(input_dir) -> dict:
    p = Path(input_dir)
    chas = sorted(p.rglob("*.cha"))
    return {"ok": len(chas) > 0, "count": len(chas), "examples": [str(x) for x in chas[:10]], "root": str(p.resolve())}
