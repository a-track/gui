from __future__ import annotations

import re


def _title_token(tok: str) -> str:
    if tok.lower() in {"id", "ids"}:
        return tok.upper()
    if tok.lower() == "sk":
        return "Key"
    if tok.lower() in {"chf", "usd", "eur", "gbp"}:
        return tok.upper()
    return tok.capitalize()


def friendly_column_name(col: str) -> str:
    col = col.strip()
    col = re.sub(r"\s+", " ", col)
    parts = [p for p in col.split("_") if p]
    if not parts:
        return col

    titled = [_title_token(p) for p in parts]

    # common cleanups
    if titled[-1] == "Key" and len(titled) >= 2 and titled[-2] == "Date":
        return "Date Key"

    return " ".join(titled)


def semantic_table_name(core_base: str) -> str:
    base = core_base.lower()
    if base == "date":
        return "dim_date"
    if base in {"account", "category"}:
        return f"dim_{base}"
    if base in {"transaction", "balance", "budget"}:
        return f"fact_{base}"
    return base

