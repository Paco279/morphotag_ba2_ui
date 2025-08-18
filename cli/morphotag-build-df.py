#!/usr/bin/env python3
import argparse
from pathlib import Path
from morphotag.parser import build_df_from_dir_without_pylangacq

def main():
    ap = argparse.ArgumentParser(description="Construye CSV de tokens (mor/gra) SIN pylangacq")
    ap.add_argument("input_dir", help="Carpeta con .cha")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--out_csv", default="tokens.csv")
    ap.add_argument("--issues_csv", default="issues.csv")
    args = ap.parse_args()

    df, df_issues = build_df_from_dir_without_pylangacq(Path(args.input_dir), recursive=args.recursive)
    df.to_csv(args.out_csv, index=False, encoding="utf-8")
    df_issues.to_csv(args.issues_csv, index=False, encoding="utf-8")
    print("Escritos:", args.out_csv, "y", args.issues_csv)

if __name__ == "__main__":
    main()
