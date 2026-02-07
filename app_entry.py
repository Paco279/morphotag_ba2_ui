# app_entry.py
import os, sys
from pathlib import Path
from streamlit.web import cli as stcli

def _base_dir():
    # Carpeta del bundle (sirve tanto para --onedir como --onefile)
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

def _maybe_prepend_to_path(p: Path):
    if p.exists():
        os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")

if __name__ == "__main__":
    base = _base_dir()

    # 1) FFmpeg (si lo empaquetas en ./ffmpeg/ffmpeg.exe)
    _maybe_prepend_to_path(base / "ffmpeg")

    # 2) Modelo local (si lo empaquetas en ./models/small)
    model_dir = base / "models" / "small"
    if model_dir.exists():
        os.environ["WHISPER_MODEL_DIR"] = str(model_dir)

    # 3) Lanza Streamlit con tu app
    sys.argv = [
        "streamlit", "run", str(base / "app.py"),
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
