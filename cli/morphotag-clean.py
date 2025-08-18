#!/usr/bin/env python3
import argparse
from morphotag.clean import process_dir_to_folders, pretty_summarize_reports

def main():
    ap = argparse.ArgumentParser(description="Limpia/valida .cha y separa en clean/ y needs_review/")
    ap.add_argument("input_dir", help="Carpeta con .cha")
    ap.add_argument("--no-rename", action="store_true", help="No renombrar cuando haya cambios (sobrescribe con .bak)")
    ap.add_argument("--missing-policy", default="prefix_com", choices=["prefix_com","drop","report"], help="Líneas sin cabecera (no primeras)")
    ap.add_argument("--empty-policy", default="drop", choices=["drop","keep"], help="Cabeceras vacías")
    args = ap.parse_args()

    reports, clean_dir, review_dir = process_dir_to_folders(
        args.input_dir,
        rename_on_change=not args.no_rename,
        backup=True,
        missing_hdr_policy=args.missing_policy,
        empty_hdr_policy=args.empty_policy,
    )
    print("✅ Limpios/arreglados →", clean_dir)
    print("🧪 Necesitan revisión →", review_dir)
    print()
    print(pretty_summarize_reports(reports))

if __name__ == "__main__":
    main()
