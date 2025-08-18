#!/usr/bin/env python3
import argparse, sys
from pathlib import Path
from morphotag.diagnose import diagnose_with_api_pretty, pretty_print_diagnosis

def main():
    ap = argparse.ArgumentParser(description="Diagnóstico legible con batchalign.CHATFile API")
    ap.add_argument("path", help="Archivo .cha o carpeta")
    ap.add_argument("--before", type=int, default=3)
    ap.add_argument("--after", type=int, default=3)
    args = ap.parse_args()

    p = Path(args.path)
    files = [p] if p.is_file() else sorted(p.rglob("*.cha"))
    if not files:
        print("No se encontraron .cha en", p, file=sys.stderr); sys.exit(1)
    for f in files:
        d = diagnose_with_api_pretty(str(f), before=args.before, after=args.after)
        pretty_print_diagnosis(d)

if __name__ == "__main__":
    main()
