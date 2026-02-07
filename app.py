import io
import os

import pandas as pd
import streamlit as st

from pathlib import Path

from morphotag.clean import process_dir_to_folders, pretty_summarize_reports
from morphotag.diagnose import diagnose_with_api_pretty, pretty_print_diagnosis
from morphotag.parser import build_df_from_dir_without_pylangacq

st.set_page_config(page_title="ba2kit UI", page_icon="🗂️", layout="wide")

# ---------- utilidades ----------
def list_cha_files(folder: Path):
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.cha"))

def text_download(name: str, text: str, label="Descargar"):
    st.download_button(label, data=text.encode("utf-8"), file_name=name, mime="text/plain")

def df_download_button(df: pd.DataFrame, filename: str, label="Descargar CSV"):
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    st.download_button(label, buf.getvalue().encode("utf-8"), file_name=filename, mime="text/csv")

st.markdown("""
<style>
.small { font-size: 0.9rem; }
pre { white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

st.title("ba2kit — Toolkit para CHAT (.cha) y batchalign2")

with st.sidebar:
    st.header("Ajustes generales")
    base_dir = st.text_input("Carpeta base (ruta local)", value="")
    base = Path(base_dir) if base_dir else None
    st.caption("Introduce una ruta local con tus .cha. La app no sube datos a ningún sitio; todo corre en tu máquina.")

tabs = st.tabs([
    "🧼 Limpiar/validar",
    "🩺 Diagnosticar",
    "📊 CSV (sin pylangacq)",
    "🧩 pylangacq (post-fix opcional)",
    "🎙️ Transcribir audio"
])

# ---------- 1) limpiar / validar ----------
with tabs[0]:
    st.header("Limpieza y validación de .cha")
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        input_dir = st.text_input("Carpeta con .cha", value=str(base) if base else "")
    with col2:
        missing_policy = st.selectbox("Líneas sin cabecera", ["prefix_com","drop","report"], index=0)
    with col3:
        empty_policy = st.selectbox("Cabeceras vacías", ["drop","keep"], index=0)
    rename = st.checkbox("Renombrar archivos arreglados (evitar sobrescribir)", value=True)

    if st.button("Procesar carpeta", type="primary", use_container_width=True):
        if not input_dir:
            st.error("Indica una carpeta.")
        else:
            with st.status("Procesando…", expanded=True) as status:
                reports, clean_dir, review_dir = process_dir_to_folders(
                    input_dir,
                    rename_on_change=rename,
                    backup=True,
                    missing_hdr_policy=missing_policy,
                    empty_hdr_policy=empty_policy,
                )
                st.write("✅ Limpios/arreglados →", clean_dir)
                st.write("🧪 Necesitan revisión →", review_dir)
                summary = pretty_summarize_reports(reports)
                st.subheader("Resumen de cambios")
                st.code(summary)
                status.update(label="Hecho", state="complete")

# ---------- 2) diagnosticar ----------
with tabs[1]:
    st.header("Diagnóstico legible (API batchalign)")
    diag_path = st.text_input("Archivo .cha o carpeta", value=str(base) if base else "")
    before = st.number_input("Contexto: líneas antes", min_value=0, max_value=20, value=3, step=1)
    after  = st.number_input("Contexto: líneas después", min_value=0, max_value=20, value=3, step=1)
    if st.button("Diagnosticar", use_container_width=True):
        p = Path(diag_path)
        files = [p] if p.is_file() else list_cha_files(p)
        if not files:
            st.warning("No se encontraron .cha.")
        else:
            for f in files:
                diag = diagnose_with_api_pretty(str(f), before=before, after=after)
                st.subheader(f.name)
                if diag.get("ok"):
                    st.success("Sin errores al parsear (API).")
                    continue
                st.error(f"{diag.get('error_type','Error')}: {diag.get('message','')}")
                meta = []
                if diag.get("cha_line") is not None:
                    meta.append(f"Línea estimada: {diag['cha_line']}")
                if diag.get("py_line") is not None:
                    meta.append(f"(traceback) última 'line N': {diag['py_line']}")
                if meta:
                    st.caption(" · ".join(meta))
                if diag.get("utterance"):
                    st.code(f"Enunciado capturado: «{diag['utterance']}»")
                if diag.get("context_block"):
                    st.text("\n".join(diag["context_block"]))
                if diag.get("hints"):
                    st.info("Sugerencias:\n- " + "\n- ".join(diag["hints"]))

# ---------- 3) CSV ----------
with tabs[2]:
    st.header("CSV de tokens y avisos (sin pylangacq)")
    csv_dir = st.text_input("Carpeta con .cha", value=str(base) if base else "")
    recursive = st.checkbox("Buscar recursivamente", value=False)
    if st.button("Generar CSVs", use_container_width=True):
        if not csv_dir:
            st.error("Indica una carpeta.")
        else:
            with st.status("Construyendo DataFrames…", expanded=True) as status:
                df, df_issues = build_df_from_dir_without_pylangacq(Path(csv_dir), recursive=recursive)
                st.write("Tokens:", df.shape, " · Issues:", df_issues.shape)
                st.dataframe(df.head(50))
                df_download_button(df, "tokens.csv", "Descargar tokens.csv")
                if not df_issues.empty:
                    st.dataframe(df_issues.head(100))
                    df_download_button(df_issues, "issues.csv", "Descargar issues.csv")
                status.update(label="Hecho", state="complete")

# ---------- 4) transcripción de audio ----------
with tabs[4]:
    st.header("Transcripción de audio (faster-whisper)")
    audio_file = st.file_uploader("Sube un audio (.wav/.mp3/.m4a/.flac)", type=["wav","mp3","m4a","flac"])
    colm1, colm2, colm3 = st.columns(3)
    with colm1:
        model_size = st.selectbox("Modelo", ["tiny","base","small","medium","large-v3"], index=2)
    with colm2:
        lang = st.text_input("Idioma (ISO)", value="es")
    with colm3:
        vad = st.checkbox("VAD filter", value=True)

    if st.button("Transcribir", type="primary"):
        if not audio_file:
            st.error("Sube un audio.")
        else:
            try:
                from faster_whisper import WhisperModel
                model_path_env = os.environ.get("WHISPER_MODEL_DIR")
                if model_path_env and os.path.exists(model_path_env):
                    model = WhisperModel(model_path_env, device="auto", compute_type="auto")
                else:
                    # sigue admitiendo seleccionar tamaño por UI
                    model = WhisperModel(model_size, device="auto", compute_type="auto")
            except Exception:
                st.error("Instala primero: pip install faster-whisper soundfile")
            else:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
                    tmp.write(audio_file.read())
                    tmp_path = tmp.name
                model = WhisperModel(model_size, device="auto", compute_type="auto")
                segments, info = model.transcribe(tmp_path, language=lang, vad_filter=vad)
                full_text = []
                for s in segments:
                    full_text.append(s.text.strip())
                transcript = "\n".join(full_text)
                st.text_area("Transcripción", transcript, height=300)
                text_download(Path(audio_file.name).with_suffix(".txt").name, transcript, label="Descargar transcripción .txt")
                st.success("Transcripción completada.")
