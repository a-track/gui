from __future__ import annotations

from pathlib import Path

import duckdb

from pipeline.access_export import export_semantic_schema_to_access
from pipeline.semantic import friendly_column_name, semantic_table_name
from pipeline.sql_layers import discover_layer_sql, sort_layer_sql


def _read_sql(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    return txt.strip().rstrip(";")


def _ensure_schema(conn, schema: str) -> None:
    conn.execute(f'create schema if not exists "{schema}"')


def _create_layer_view(conn, *, schema: str, base_name: str, sql: str) -> None:
    conn.execute(f'create or replace view "{schema}"."{base_name}" as (\n{sql}\n)')


def _create_main_alias(conn, *, alias_name: str, target_schema: str, target_base: str) -> None:
    conn.execute(f'create or replace view "{alias_name}" as select * from "{target_schema}"."{target_base}"')


def _build_semantic(conn, *, core_schema: str = "core", semantic_schema: str = "semantic") -> None:
    conn.execute(f'drop schema if exists "{semantic_schema}" cascade')
    _ensure_schema(conn, semantic_schema)

    core_tables = [
        r[0]
        for r in conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = ? and table_type in ('BASE TABLE','VIEW')
            order by table_name
            """,
            [core_schema],
        ).fetchall()
    ]

    for core_base in core_tables:
        out_table = semantic_table_name(core_base)
        cols = [
            r[0]
            for r in conn.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = ? and table_name = ?
                order by ordinal_position
                """,
                [core_schema, core_base],
            ).fetchall()
        ]

        select_list = ",\n  ".join(
            f'"{c}" as "{friendly_column_name(c)}"' for c in cols
        )
        conn.execute(
            f'create or replace view "{semantic_schema}"."{out_table}" as (\n'
            f"select\n  {select_list}\n"
            f'from "{core_schema}"."{core_base}"\n'
            f")"
        )


def _export_semantic_to_csv(conn, *, semantic_schema: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = [
        r[0]
        for r in conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = ? and table_type in ('BASE TABLE','VIEW')
            order by table_name
            """,
            [semantic_schema],
        ).fetchall()
    ]
    for t in tables:
        df = conn.execute(f'SELECT * FROM "{semantic_schema}"."{t}"').df()
        df.to_csv(out_dir / f"{t}.csv", index=False, encoding="utf-8")


def run_pipeline(
    *,
    duckdb_path: Path | None = None,
    conn=None,
    sql_dir: Path,
    access_out: Path | None,
    access_overwrite: bool,
    csv_out_dir: Path | None = None,
) -> None:
    if conn is None:
        if duckdb_path is None:
            raise ValueError("Must provide either duckdb_path or conn")
        duckdb_path = duckdb_path.resolve()
        if not duckdb_path.exists():
            raise FileNotFoundError(f"DuckDB file not found: {duckdb_path}")
        conn = duckdb.connect(str(duckdb_path))
        close_conn = True
    else:
        close_conn = False

    sql_dir = sql_dir.resolve()
    if not sql_dir.exists():
        raise FileNotFoundError(f"SQL dir not found: {sql_dir}")

    # Schemas we use for generated objects.
    for schema in ("raw", "transf", "core", "semantic"):
        _ensure_schema(conn, schema)

    sql_items = sort_layer_sql(discover_layer_sql(sql_dir))

    for item in sql_items:
        sql = _read_sql(item.path)
        if item.layer == "raw":
            _create_layer_view(conn, schema="raw", base_name=item.name, sql=sql)
            # alias in main for downstream SQL that uses unqualified names
            _create_main_alias(conn, alias_name=item.name, target_schema="raw", target_base=item.name)
        elif item.layer == "transf":
            _create_layer_view(conn, schema="transf", base_name=item.name, sql=sql)
            _create_main_alias(
                conn,
                alias_name=f"transf_{item.name}",
                target_schema="transf",
                target_base=item.name,
            )
        elif item.layer == "core":
            print(f"Creating core view: {item.name}")
            _create_layer_view(conn, schema="core", base_name=item.name, sql=sql)
            _create_main_alias(
                conn,
                alias_name=f"core_{item.name}",
                target_schema="core",
                target_base=item.name,
            )

    _build_semantic(conn, core_schema="core", semantic_schema="semantic")

    if csv_out_dir is not None:
        _export_semantic_to_csv(conn, semantic_schema="semantic", out_dir=csv_out_dir)

    if access_out is not None:
        export_semantic_schema_to_access(
            duckdb_conn=conn,
            semantic_schema="semantic",
            access_path=access_out,
            overwrite=access_overwrite,
        )

    if close_conn:
        conn.close()

