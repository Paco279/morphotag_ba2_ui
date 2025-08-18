import re, traceback
from pathlib import Path

def render_invisibles(s: str, show_tabs=True, show_ctrl=True) -> str:
    out = []
    for ch in s:
        oc = ord(ch)
        if ch == '\t' and show_tabs:
            out.append('⟶\\t')
        elif show_ctrl and (oc < 32 or oc == 127):
            out.append(f"⟦U+{oc:04X}⟧")
        else:
            out.append(ch)
    return "".join(out)

def context_block(chat_text: str, center_line: int, before=3, after=3) -> list[str]:
    lines = chat_text.splitlines()
    n = len(lines)
    if center_line is None or center_line < 1 or center_line > n:
        return []
    lo = max(1, center_line - before)
    hi = min(n, center_line + after)
    block = []
    for i in range(lo, hi + 1):
        prefix = "→ " if i == center_line else "  "
        content = render_invisibles(lines[i-1])
        block.append(f"{prefix}{i:>6}: {content}")
    return block

def _last_python_line_from_trace(tb_text: str) -> int | None:
    if not tb_text: return None
    nums = re.findall(r'line\s+(\d+)', tb_text, flags=re.IGNORECASE)
    return int(nums[-1]) if nums else None

def _utterance_from_trace(text_or_trace: str) -> str | None:
    if not text_or_trace: return None
    m = re.search(r"On line:\s*'(.*?)'", text_or_trace, flags=re.DOTALL)
    return m.group(1).strip() if m else None

def _normalize_ws(s: str) -> str:
    return " ".join(s.split())

def _find_utterance_line_in_chat(chat_text: str, utterance: str) -> int | None:
    if not utterance: return None
    target = _normalize_ws(utterance)
    for i, ln in enumerate(chat_text.splitlines(), start=1):
        if target in _normalize_ws(ln):
            return i
    return None

def _friendly_hints_from_message(msg_lower: str, utterance: str | None):
    hints = []
    if "unexpected end to utterance within form group" in msg_lower:
        hints.append("Posible grupo '<...>' sin cierre '>' en ese enunciado.")
        if utterance and '<' in utterance and '>' not in utterance[utterance.rfind('<')+1:]:
            hints.append("En el enunciado capturado hay '<' pero no se ve '>' después.")
    if "unknown speaker" in msg_lower or "unknown code" in msg_lower:
        hints.append("Código de hablante no reconocido: *XXX: debe existir en @Participants y @ID (campo 3).")
    if "dependent tier" in msg_lower or "unknown tier" in msg_lower:
        hints.append("Tier dependiente no permitido: permite %com, %err, %sit, %mor, %gra, %act (o amplía la lista).")
    if "@end" in msg_lower or "end tag" in msg_lower:
        hints.append("Debe existir un único @End y ser la última línea con contenido.")
    if "tab" in msg_lower or "tabulation" in msg_lower or "colon" in msg_lower:
        hints.append("Tras la cabecera debe haber un TAB (no espacio) y no debe quedar ':' extra tras el TAB.")
    return hints or None

def diagnose_with_api_pretty(cha_path: str, before=3, after=3):
    cha_path = str(cha_path)
    txt = Path(cha_path).read_text(encoding="utf-8", errors="ignore")
    try:
        import batchalign as ba
        chat = ba.CHATFile(path=cha_path)
        _ = chat.doc
        return {"ok": True, "file": cha_path}
    except Exception as e:
        msg = str(e); tb = traceback.format_exc()
        py_line = _last_python_line_from_trace(tb)
        utter = _utterance_from_trace(msg) or _utterance_from_trace(tb)
        cha_line = _find_utterance_line_in_chat(txt, utter) if utter else None
        ctx = context_block(txt, cha_line, before=before, after=after) if cha_line else None
        hints = _friendly_hints_from_message(msg.lower(), utter)
        utter_snippet = utter if (utter and len(utter) <= 400) else (utter[:400] + "…") if utter else None
        return {
            "ok": False, "file": cha_path,
            "error_type": type(e).__name__, "message": msg.strip(),
            "py_line": py_line, "utterance": utter_snippet,
            "cha_line": cha_line, "context_block": ctx, "hints": hints,
            "trace": tb,
        }

def pretty_print_diagnosis(diag: dict):
    if diag.get("ok"):
        print(f"✅ {diag['file']}: sin errores al parsear (API)."); return
    print(f"❌ {diag['file']}: {diag.get('error_type','Error')}")
    if diag.get("message"): print(f"   Mensaje: {diag['message']}")
    if diag.get("py_line") is not None: print(f"   (traceback) última 'line N': {diag['py_line']}")
    if diag.get("cha_line") is not None: print(f"   Línea estimada en .cha: {diag['cha_line']}")
    if diag.get("utterance"): print(f"   Enunciado capturado: «{diag['utterance']}»")
    if diag.get("context_block"):
        print("   Contexto:"); [print("   ", ln) for ln in diag["context_block"]]
    if diag.get("hints"):
        print("   Sugerencias:"); [print("    -", h) for h in diag["hints"]]
