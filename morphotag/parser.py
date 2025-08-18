from pathlib import Path
import re
from typing import List, Dict, Tuple, Optional
import pandas as pd

MAIN_HDR_RE = re.compile(r'^\s*\*([A-Za-z0-9]{1,7})\s*:\s*(.*)$')
MOR_RE      = re.compile(r'^\s*%mor\s*:\s*(.+)$', re.IGNORECASE)
GRA_RE      = re.compile(r'^\s*%gra\s*:\s*(.+)$', re.IGNORECASE)
DEP_ANY_RE  = re.compile(r'^\s*%[a-z0-9_+-]+\s*:', re.IGNORECASE)
MAIN_ANY_RE = re.compile(r'^\s*\*[A-Za-z0-9]{1,7}\s*:\s*')

def _split_mor_token(tok: Optional[str]):
    if not tok: return None, None, None
    if '|' in tok:
        pos, rest = tok.split('|', 1)
        stem = rest.split('-', 1)[0] if rest else None
        return pos, rest, stem
    if tok in {'.','!','?',';',',',':' }:
        return 'PUNCT', tok, tok
    return None, tok, tok

def _parse_gra_map(gra_line: str) -> Dict[int, Tuple[Optional[int], Optional[str]]]:
    out = {}
    for it in gra_line.split():
        parts = it.split('|')
        if len(parts) != 3: continue
        try:
            idx = int(parts[0]); head = int(parts[1]); rel = parts[2]
        except Exception:
            continue
        out[idx] = (head, rel)
    return out

def _next_mor_gra(lines: List[str], start_idx: int):
    mor_tokens = None; gra_map = None
    j = start_idx + 1
    while j < len(lines):
        ln = lines[j]
        if not ln.strip(): j += 1; continue
        if MAIN_ANY_RE.match(ln): break
        m = MOR_RE.match(ln); g = GRA_RE.match(ln)
        if m:
            mor_tokens = m.group(1).strip().split(); j += 1; continue
        if g:
            gra_map = _parse_gra_map(g.group(1).strip()); j += 1; continue
        if DEP_ANY_RE.match(ln): j += 1; continue
        break
    return mor_tokens, gra_map, j

def parse_chat_tolerant_to_rows(cha_path: str | Path):
    cha_path = Path(cha_path)
    text = cha_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    rows = []; issues = []; utt_idx = 0; i = 0
    while i < len(lines):
        ln = lines[i]
        m = MAIN_HDR_RE.match(ln)
        if not m:
            i += 1; continue
        utt_idx += 1
        speaker = m.group(1)
        main_text = m.group(2).strip()
        mor_tokens, gra_map, stop = _next_mor_gra(lines, i)
        if mor_tokens is None:
            issues.append({"utt_index": utt_idx, "reason": "sin_%mor"}); mor_tokens = []
        if gra_map is None:
            issues.append({"utt_index": utt_idx, "reason": "sin_%gra"}); gra_map = {}
        n_mor = len(mor_tokens); max_gra_idx = max(gra_map.keys(), default=0)
        N = max(n_mor, max_gra_idx)
        if n_mor != max_gra_idx and not (n_mor == 0 and max_gra_idx == 0):
            issues.append({"utt_index": utt_idx, "reason": f"desajuste_mor({n_mor})_gra({max_gra_idx})"})
        for k in range(1, N + 1):
            mor_tok = mor_tokens[k-1] if k-1 < n_mor else None
            mor_pos, mor_rest, stem = _split_mor_token(mor_tok)
            g_head, g_rel = gra_map.get(k, (None, None))
            rows.append({
                "file": cha_path.name,
                "utt_index": utt_idx,
                "token_index": k,
                "speaker": speaker,
                "word": stem,
                "mor_pos": mor_pos,
                "mor_rest": mor_rest,
                "head_index": g_head,
                "deprel": g_rel,
                "diag_mismatch": (k > n_mor) or (k not in gra_map),
                "utterance_text": main_text,
            })
        i = stop if stop > i else i + 1
    return rows, issues

def build_df_from_dir_without_pylangacq(folder: str | Path, recursive: bool = False):
    folder = Path(folder)
    pattern = "**/*.cha" if recursive else "*.cha"
    all_rows = []; all_issues = []
    for f in sorted(folder.glob(pattern)):
        rows, issues = parse_chat_tolerant_to_rows(f)
        all_rows.extend(rows)
        for it in issues: it["file"] = f.name
        all_issues.extend(issues)
    df = pd.DataFrame(all_rows)
    df_issues = pd.DataFrame(all_issues)
    return df, df_issues
