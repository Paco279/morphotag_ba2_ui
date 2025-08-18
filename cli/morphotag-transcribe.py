#!/usr/bin/env python3
import argparse, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="Transcribe audio a texto (stub con faster-whisper)")
    ap.add_argument("audio", help="Ruta a .wav/.mp3/.m4a/.flac")
    ap.add_argument("--model", default="medium", help="faster-whisper model size (tiny, base, small, medium, large-v3)")
    ap.add_argument("--language", default="es", help="Idioma (ej. 'es')")
    ap.add_argument("--out_txt", default=None, help="Ruta de salida TXT (por defecto <audio>.txt)")
    args = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except Exception:
        print("⚠️ Instala primero: pip install faster-whisper soundfile", file=sys.stderr)
        sys.exit(2)

    audio = Path(args.audio)
    out_txt = Path(args.out_txt) if args.out_txt else audio.with_suffix(".txt")

    model = WhisperModel(args.model, device="auto", compute_type="auto")
    segments, info = model.transcribe(str(audio), language=args.language, vad_filter=True)
    with open(out_txt, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(seg.text.strip() + "\n")
    print("✅ Transcripción escrita en", out_txt)

if __name__ == "__main__":
    main()
