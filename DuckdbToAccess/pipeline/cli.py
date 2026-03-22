from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from pipeline.runner import run_pipeline


@dataclass(frozen=True)
class Args:
    duckdb_path: Path
    sql_dir: Path
    access_out: Path | None
    access_overwrite: bool
    csv_out_dir: Path | None


def _parse_args(argv: list[str] | None = None) -> Args:
    p = argparse.ArgumentParser(description="DuckDB layered pipeline + Access export")
    p.add_argument(
        "--duckdb",
        dest="duckdb_path",
        type=Path,
        default=Path("data.duckdb"),
        help="Path to DuckDB database file (default: data.duckdb)",
    )
    p.add_argument(
        "--sql-dir",
        dest="sql_dir",
        type=Path,
        default=Path("SQL"),
        help="Directory containing SQL layer files (default: SQL/)",
    )
    p.add_argument(
        "--access-out",
        dest="access_out",
        type=Path,
        default=Path("semantic.accdb"),
        help="Output Access database path (default: semantic.accdb). Use empty to disable.",
    )
    p.add_argument(
        "--no-access",
        action="store_true",
        help="Do not export to Access (still builds semantic layer in DuckDB).",
    )
    p.add_argument(
        "--access-overwrite",
        action="store_true",
        help="Overwrite existing Access .accdb if present.",
    )
    p.add_argument(
        "--csv-out-dir",
        type=Path,
        default=None,
        help="Optional: also export semantic tables to CSV in this folder.",
    )

    ns = p.parse_args(argv)
    access_out: Path | None = None if ns.no_access else ns.access_out

    return Args(
        duckdb_path=ns.duckdb_path,
        sql_dir=ns.sql_dir,
        access_out=access_out,
        access_overwrite=bool(ns.access_overwrite),
        csv_out_dir=ns.csv_out_dir,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_pipeline(
        duckdb_path=args.duckdb_path,
        sql_dir=args.sql_dir,
        access_out=args.access_out,
        access_overwrite=args.access_overwrite,
        csv_out_dir=args.csv_out_dir,
    )
    return 0

