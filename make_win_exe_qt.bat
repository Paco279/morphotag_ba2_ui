@echo off
setlocal
echo === ba2kit GUI (Qt) — build EXE ===

if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate

pip install -U pip wheel
pip install -e .
pip install PySide6 pyinstaller faster-whisper soundfile huggingface_hub

REM Modelo offline opcional
if not exist models\small (
  echo Descargando modelo offline a models\small ...
  python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-small', local_dir='models/small', local_dir_use_symlinks=False)"
)

REM Aviso FFmpeg
if not exist ffmpeg\ffmpeg.exe (
  echo [AVISO] No se encontro ffmpeg\ffmpeg.exe. Ponlo ahi para soportar MP3/M4A/FLAC.
)

pyinstaller ba2kit-ui-qt.spec

echo.
echo ✅ Listo: dist\ba2kit-ui\ba2kit-ui.exe
pause
endlocal
