import re, shutil
from pathlib import Path
from .utils import (
    MAIN_HDR_RE, DEP_HDR_RE, ANY_HDR_RE, END_RE_LINE, ALLOWED_DEP_TIER_NAMES,
    split_header_body, parse_id_codes, count_header_occurrences, sanitize_controls,
    next_nonclobber_name
)

CLEAN_DIR_NAME = "clean"
REVIEW_DIR_NAME = "needs_review"

def force_tab_after_headers(text: str):
    lines = text.splitlines()
    changed = 0
    touched = []
    def _fix(regex, ln):
        m = regex.match(ln)
        if not m:
            return ln, False
        hdr, rest = m.group(1), m.group(2)
        new = f"{hdr}:\t{rest.lstrip()}"
        new = re.sub(r'^\s*\*', '*', new) if hdr.startswith('*') else re.sub(r'^\s*%', '%', new)
        return (new, new != ln)
    for i, ln in enumerate(lines, start=1):
        new_ln, ok1 = _fix(MAIN_HDR_RE, ln)
        if ok1:
            lines[i-1] = new_ln; changed += 1; touched.append(i); continue
        new_ln, ok2 = _fix(DEP_HDR_RE, ln)
        if ok2:
            lines[i-1] = new_ln; changed += 1; touched.append(i)
    return "\n".join(lines), changed, touched

def detect_and_fix_double_colon_after_header(text: str, mode: str = "remove"):
    lines = text.splitlines()
    changed, detected = [], []
    def _fix_line(i, m):
        hdr, rest = m.group(1), m.group(2)
        rest_stripped = rest.lstrip()
        if rest_stripped.startswith(':'):
            detected.append(i + 1)
            if mode == "remove":
                k = 0
                while k < len(rest_stripped) and rest_stripped[k] == ':':
                    k += 1
                new_rest = rest_stripped[k:].lstrip()
                lines[i] = f"{hdr}:\t{new_rest}"
                changed.append(i + 1)
    for i, s in enumerate(lines):
        m = MAIN_HDR_RE.match(s)
        if m: _fix_line(i, m); continue
        m = DEP_HDR_RE.match(s)
        if m: _fix_line(i, m)
    return ("\n".join(lines), changed, detected)

def ensure_end_at_eof_strict(text: str):
    lines = text.splitlines()
    end_idx = [i for i, ln in enumerate(lines) if END_RE_LINE.match(ln)]
    changed = False; added = False; moved = False; dups_removed = 0
    if not end_idx:
        while lines and not lines[-1].strip():
            lines.pop(); changed = True
        lines.append("@End"); added = True; changed = True
    else:
        dups_removed = max(0, len(end_idx) - 1)
        if dups_removed:
            keep_first = end_idx[0]
            lines = [ln for j, ln in enumerate(lines) if (j == keep_first or not END_RE_LINE.match(ln))]
            changed = True
        while lines and not lines[-1].strip():
            lines.pop(); changed = True
        end_positions = [i for i, ln in enumerate(lines) if END_RE_LINE.match(ln)]
        if end_positions:
            if end_positions[-1] != len(lines) - 1:
                lines = [ln for ln in lines if not END_RE_LINE.match(ln)]
                lines.append("@End"); moved = True; changed = True
        else:
            lines.append("@End"); added = True; changed = True
    txt = "\n".join(lines)
    if not txt.endswith("\n"): txt += "\n"
    return txt, {"end_added": added, "end_moved": moved, "end_dups_removed": dups_removed, "end_changed": changed}

def check_and_fix_body(text: str,
                       allowed_dep_tiers=None,
                       missing_hdr_policy="prefix_com",
                       empty_hdr_policy="drop",
                       merge_orphan_with_prev_main=True):
    if allowed_dep_tiers is None:
        allowed_dep_tiers = ALLOWED_DEP_TIER_NAMES
    id_codes = parse_id_codes(text)
    start, lines = split_header_body(text)
    errors, warnings, fixed_lines, dropped_lines = [], [], [], []
    merged_orphan_lines = []
    dropped_initial_missing_header = None

    i = start
    first_body_seen = False
    while i < len(lines):
        s = lines[i]
        num = i + 1
        if not s.strip():
            i += 1; continue
        if not first_body_seen:
            first_body_seen = True
        if END_RE_LINE.match(s.strip()):
            i += 1; continue

        occ = count_header_occurrences(s)
        if occ > 1:
            errors.append(f"L{num}: hay {occ} cabeceras en la misma línea.")

        m_main = re.match(MAIN_HDR_RE, s)
        m_dep  = re.match(DEP_HDR_RE, s)

        if m_main:
            code, rest = m_main.group(1)[1:], m_main.group(2)
            if code not in id_codes:
                errors.append(f"L{num}: '*{code}:' no coincide con ningún código de @ID {sorted(id_codes)}")
            if rest.strip() == "":
                msg = f"L{num}: cabecera '*{code}:' sin contenido."
                if empty_hdr_policy == "drop":
                    lines.pop(i); dropped_lines.append(num); errors.append(msg + " (eliminada)"); continue
                else:
                    errors.append(msg)
            i += 1; continue

        if m_dep:
            tier, rest = m_dep.group(1)[1:], m_dep.group(2)
            if tier.lower() not in {t.lower() for t in allowed_dep_tiers}:
                errors.append(f"L{num}: '%{tier}:' no permitida. Permitidas: {sorted(allowed_dep_tiers)}")
            if rest.strip() == "":
                msg = f"L{num}: cabecera '%{tier}:' sin contenido."
                if empty_hdr_policy == "drop":
                    lines.pop(i); dropped_lines.append(num); errors.append(msg + " (eliminada)"); continue
                else:
                    errors.append(msg)
            i += 1; continue

        # Texto sin cabecera
        if first_body_seen and num == (start + 1):
            dropped_initial_missing_header = {'line_number': num, 'content': s}
            lines.pop(i); continue

        if merge_orphan_with_prev_main:
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            if j >= 0 and re.match(MAIN_HDR_RE, lines[j]):
                hdr_m = re.match(MAIN_HDR_RE, lines[j])
                hdr, rest_prev = hdr_m.group(1), hdr_m.group(2)
                new_prev = f"{hdr}:\t{rest_prev.rstrip()} {s.strip()}".rstrip()
                lines[j] = new_prev
                lines.pop(i)
                merged_orphan_lines.append({'line_number': num, 'into_line': j + 1})
                continue

        msg = f"L{num}: línea con texto sin cabecera (*CODE: o %tier:)."
        if missing_hdr_policy == "prefix_com":
            lines[i] = f"%com:\t{s.strip()}"; fixed_lines.append(num); warnings.append(msg + " (prefijada como '%com:')."); i += 1
        elif missing_hdr_policy == "drop":
            lines.pop(i); dropped_lines.append(num); warnings.append(msg + " (eliminada).")
        else:
            errors.append(msg); i += 1

    return {
        "ok": not errors, "errors": errors, "warnings": warnings,
        "text": "\n".join(lines),
        "fixed_lines": fixed_lines, "dropped_lines": dropped_lines,
        "merged_orphan_lines": merged_orphan_lines,
        "dropped_initial_missing_header": dropped_initial_missing_header,
    }

def drop_initial_dep_tier_if_present(text: str):
    start, lines = split_header_body(text)
    i = start
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        if re.match(r'^\s*%[a-z0-9_+-]+\s*:', lines[i].strip(), flags=re.IGNORECASE):
            info = {'line_number': i + 1, 'content': lines[i], 'tier': lines[i].split(':',1)[0][1:]}
            del lines[i]
            return "\n".join(lines), info
    return text, None

def process_file(path: str | Path,
                 rename_on_change=True,
                 backup=True,
                 allowed_dep_tiers=None,
                 missing_hdr_policy="prefix_com",
                 empty_hdr_policy="drop",
                 merge_orphan_with_prev_main=True):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(errors="ignore")
    original_text = text

    text, sanitized_lines = sanitize_controls(text)
    text, end_info_pre = ensure_end_at_eof_strict(text)
    text, tabs_fixed_count, tabs_fixed_lines = force_tab_after_headers(text)
    text, dblcol_changed, dblcol_detected = detect_and_fix_double_colon_after_header(text, mode="remove")

    rep_body = check_and_fix_body(
        text,
        allowed_dep_tiers=allowed_dep_tiers,
        missing_hdr_policy=missing_hdr_policy,
        empty_hdr_policy=empty_hdr_policy,
        merge_orphan_with_prev_main=merge_orphan_with_prev_main,
    )
    text = rep_body["text"]

    text, end_info_post = ensure_end_at_eof_strict(text)
    text, initial_dep_removed = drop_initial_dep_tier_if_present(text)
    text, end_info_final = ensure_end_at_eof_strict(text)

    changed = (text != original_text)
    wrote_path = path
    if changed:
        if rename_on_change:
            wrote_path = next_nonclobber_name(path, suffix=".fix")
            wrote_path.write_text(text, encoding="utf-8")
        else:
            if backup:
                shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
            path.write_text(text, encoding="utf-8")

    final_ok = (len(rep_body["errors"]) == 0)

    return {
        "file": str(path),
        "renamed_to": (str(wrote_path) if wrote_path != path else None),
        "changed": changed,
        "ok": final_ok,
        "tabs_fixed_count": tabs_fixed_count,
        "tabs_fixed_lines": tabs_fixed_lines,
        "double_colon_fixed_lines": dblcol_changed,
        "double_colon_detected_lines": dblcol_detected,
        "fixed_lines_prefix_com": rep_body["fixed_lines"],
        "dropped_lines": rep_body["dropped_lines"],
        "merged_orphan_lines": rep_body["merged_orphan_lines"],
        "dropped_initial_missing_header": rep_body["dropped_initial_missing_header"],
        "initial_dep_removed": initial_dep_removed,
        "sanitized_lines": sanitized_lines,
        "errors": rep_body["errors"],
        "warnings": rep_body["warnings"],
        "end_changes": {"pre": end_info_pre, "post": end_info_post, "final": end_info_final},
        "output_path": str(wrote_path if changed else path),
    }

def process_dir_to_folders(input_dir: str | Path,
                           rename_on_change=True,
                           backup=True,
                           allowed_dep_tiers=None,
                           missing_hdr_policy="prefix_com",
                           empty_hdr_policy="drop"):
    input_dir = Path(input_dir)
    clean_dir = input_dir / CLEAN_DIR_NAME
    review_dir = input_dir / REVIEW_DIR_NAME
    clean_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    reports = []
    for cha in sorted(input_dir.rglob("*.cha")):
        if clean_dir in cha.parents or review_dir in cha.parents:
            continue
        rep = process_file(
            cha,
            rename_on_change=rename_on_change,
            backup=backup,
            allowed_dep_tiers=allowed_dep_tiers,
            missing_hdr_policy=missing_hdr_policy,
            empty_hdr_policy=empty_hdr_policy,
        )
        reports.append(rep)
        src_path = Path(rep["output_path"])
        target_dir = clean_dir if rep["ok"] else review_dir
        target_path = target_dir / src_path.name
        i = 1
        while target_path.exists():
            target_path = target_dir / f"{src_path.stem}.{i}{src_path.suffix}"
            i += 1
        shutil.move(str(src_path), str(target_path))
    return reports, str(clean_dir), str(review_dir)

def pretty_summarize_reports(reports: list[dict]) -> str:
    lines = []
    for rep in reports:
        status = "OK" if rep["ok"] else "REVISAR"
        renamed = f" → guardado como: {rep['renamed_to']}" if rep["renamed_to"] else ""
        lines.append(f"Archivo: {rep['file']}  [{status}]{renamed}")
        if rep.get("sanitized_lines"):
            lines.append(f"  · Saneado de invisibles en líneas: {rep['sanitized_lines']}")
        if rep.get("tabs_fixed_count"):
            lines.append(f"  · Tabulación tras cabeceras corregida en {rep['tabs_fixed_count']} líneas: {rep['tabs_fixed_lines']}")
        if rep.get("double_colon_detected_lines"):
            if rep.get("double_colon_fixed_lines"):
                lines.append(f"  · ':' duplicado tras cabecera corregido en: {rep['double_colon_fixed_lines']}")
            else:
                lines.append(f"  · ':' duplicado tras cabecera detectado en: {rep['double_colon_detected_lines']}")
        if rep.get("dropped_initial_missing_header"):
            info = rep["dropped_initial_missing_header"]
            lines.append(f"  · Línea {info['line_number']} (primera del cuerpo) sin cabecera → BORRADA.")
        if rep.get("initial_dep_removed"):
            info = rep["initial_dep_removed"]
            lines.append(f"  · Primera línea del cuerpo era '%{info['tier']}:' → BORRADA.")
        if rep.get("merged_orphan_lines"):
            pairs = ", ".join([f"L{x['line_number']}→L{x['into_line']}" for x in rep["merged_orphan_lines"]])
            lines.append(f"  · Huérfanas fusionadas con la anterior *CODE:: {pairs}")
        if rep.get("fixed_lines_prefix_com"):
            lines.append(f"  · Líneas sin cabecera prefijadas como %com: {rep['fixed_lines_prefix_com']}")
        if rep.get("dropped_lines"):
            lines.append(f"  · Cabeceras vacías eliminadas en líneas: {rep['dropped_lines']}")
        end_pre, end_post, end_final = rep["end_changes"]["pre"], rep["end_changes"]["post"], rep["end_changes"]["final"]
        msgs = []
        for tag, info in (("pre", end_pre), ("post", end_post), ("final", end_final)):
            parts = []
            if info.get("end_added"): parts.append("añadido")
            if info.get("end_moved"): parts.append("recolocado")
            if info.get("end_dups_removed"): parts.append(f"duplicados eliminados={info['end_dups_removed']}")
            if parts:
                msgs.append(f"{tag}: " + ", ".join(parts))
        if msgs:
            lines.append("  · @End → " + " | ".join(msgs))
        if rep.get("errors"):
            lines.append("  × Errores restantes:")
            lines.extend([f"    - {e}" for e in rep["errors"]])
        if rep.get("warnings"):
            lines.append("  ⚠ Avisos:")
            lines.extend([f"    - {w}" for w in rep["warnings"]])
        lines.append("")
    return "\n".join(lines)
