from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LayerSql:
    layer: str  # raw|transf|core
    name: str  # object base name (e.g. account)
    path: Path


_LAYER_RE = re.compile(r"^(raw|transf|core)\.(.+)\.sql$", re.IGNORECASE)


def discover_layer_sql(sql_dir: Path) -> list[LayerSql]:
    items: list[LayerSql] = []
    for p in sorted(sql_dir.glob("*.sql")):
        m = _LAYER_RE.match(p.name)
        if not m:
            continue
        layer, name = m.group(1).lower(), m.group(2)
        items.append(LayerSql(layer=layer, name=name, path=p))
    return items


def sort_layer_sql(items: list[LayerSql]) -> list[LayerSql]:
    layer_rank = {"raw": 0, "transf": 1, "core": 2}

    preferred: dict[str, list[str]] = {
        "raw": ["account", "category", "budget", "currency", "investment", "transaction"],
        "transf": [
            "account",
            "category",
            "currency",
            "investment",
            "transaction",
            "date",
            "balance",
        ],
        "core": ["date", "account", "category", "budget", "transaction", "balance"],
    }

    preferred_rank: dict[tuple[str, str], int] = {}
    for layer, names in preferred.items():
        for i, name in enumerate(names):
            preferred_rank[(layer, name)] = i

    def key(x: LayerSql) -> tuple[int, int, str]:
        return (
            layer_rank.get(x.layer, 99),
            preferred_rank.get((x.layer, x.name), 999),
            x.name.lower(),
        )

    return sorted(items, key=key)

