from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class AccessExportResult:
    tables_written: list[str]


def _create_access_db(path: Path) -> None:
    # Uses ADOX (COM) to create the file. Requires Microsoft Access Database Engine.
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    pythoncom.CoInitialize()
    try:
        catalog = win32com.client.Dispatch("ADOX.Catalog")
        conn_str = f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={path};"
        catalog.Create(conn_str)
    finally:
        # Ensure COM is torn down cleanly; we've seen Access violations on interpreter exit otherwise.
        try:
            catalog = None  # type: ignore
        finally:
            pythoncom.CoUninitialize()


def _connect_access(path: Path):
    import pyodbc  # type: ignore

    conn_str = (
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        + f"DBQ={path};"
        + "ExtendedAnsiSQL=1;"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def _access_type_from_duckdb_type(duckdb_type: str) -> str:
    t = duckdb_type.upper()
    if "BOOL" in t:
        return "YESNO"
    if "TINYINT" in t or "SMALLINT" in t:
        return "SMALLINT"
    if "INTEGER" in t or t == "INT":
        return "INTEGER"
    if "BIGINT" in t or "HUGEINT" in t:
        return "BIGINT"
    if "DECIMAL" in t or "NUMERIC" in t or "DOUBLE" in t or "REAL" in t or "FLOAT" in t:
        return "DOUBLE"
    if "DATE" in t or "TIMESTAMP" in t or "DATETIME" in t:
        return "DATETIME"
    if "VARCHAR" in t or "TEXT" in t or "UUID" in t:
        return "TEXT(255)"
    return "TEXT(255)"


def _bracket(name: str) -> str:
    safe = name.replace("]", "]]")
    if len(safe) > 64:
        safe = safe[:64]
    return f"[{safe}]"


def _chunks(it: list[tuple[Any, ...]], size: int) -> Iterable[list[tuple[Any, ...]]]:
    for i in range(0, len(it), size):
        yield it[i : i + size]


def _to_py_value(v: Any) -> Any:
    if v is None:
        return None

    try:
        import pandas as pd  # type: ignore

        if pd.isna(v):
            return None
    except Exception:
        # If pandas isn't available for some reason, fall back to a light check.
        try:
            if v != v:  # NaN/NaT
                return None
        except Exception:
            pass

    # pandas Timestamp -> datetime
    if hasattr(v, "to_pydatetime"):
        try:
            return v.to_pydatetime()
        except Exception:
            pass

    # numpy scalar -> python scalar
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass

    # Decimal -> float (Access ODBC is picky about Decimal bindings)
    try:
        from decimal import Decimal

        if isinstance(v, Decimal):
            return float(v)
    except Exception:
        pass

    return v


def _to_access_literal(v: Any) -> str:
    v = _to_py_value(v)
    if v is None:
        return "NULL"

    if isinstance(v, bool):
        return "-1" if v else "0"

    if isinstance(v, (int, float)):
        return str(v)

    if isinstance(v, datetime):
        # Access uses #...# for date/time literals
        return f"#{v.strftime('%Y-%m-%d %H:%M:%S')}#"

    if isinstance(v, date) and not isinstance(v, datetime):
        return f"#{v.strftime('%Y-%m-%d')}#"

    if isinstance(v, time):
        return f"#{v.strftime('%H:%M:%S')}#"

    # Default: treat as string
    s = str(v).replace("'", "''")
    return f"'{s}'"


def export_semantic_schema_to_access(
    *,
    duckdb_conn,
    semantic_schema: str,
    access_path: Path,
    overwrite: bool,
) -> AccessExportResult:
    access_path = access_path.resolve()
    if access_path.exists():
        if overwrite:
            access_path.unlink()
        else:
            raise FileExistsError(f"Access file already exists: {access_path}")

    try:
        _create_access_db(access_path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Failed to create .accdb via ADOX. You likely need Microsoft Access Database Engine installed.\n"
            "Try installing the 'Microsoft Access Database Engine 2016' (x64) and re-run."
        ) from e

    try:
        acc = _connect_access(access_path)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Failed to connect to Access via ODBC. Ensure the 'Microsoft Access Driver (*.mdb, *.accdb)' is installed.\n"
            "This is typically provided by Microsoft Access Database Engine."
        ) from e

    tables = [
        r[0]
        for r in duckdb_conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = ? and table_type in ('BASE TABLE','VIEW')
            order by table_name
            """,
            [semantic_schema],
        ).fetchall()
    ]

    written: list[str] = []
    cur = acc.cursor()
    for t in tables:
        cols = duckdb_conn.execute(
            """
            select column_name, data_type
            from information_schema.columns
            where table_schema = ? and table_name = ?
            order by ordinal_position
            """,
            [semantic_schema, t],
        ).fetchall()

        col_defs = ", ".join(f"{_bracket(c)} {_access_type_from_duckdb_type(dt)}" for c, dt in cols)
        cur.execute(f"CREATE TABLE {_bracket(t)} ({col_defs})")

        # pull data
        df = duckdb_conn.execute(f'SELECT * FROM "{semantic_schema}"."{t}"').df()
        if not df.empty:
            col_list = ", ".join(_bracket(c) for c in df.columns)
            rows = [row for row in df.itertuples(index=False, name=None)]

            # Many Access ODBC installs are unreliable with SQLBindParameter (HYC00).
            # Use literal INSERTs to avoid parameter binding entirely.
            for row in rows:
                values_sql = ", ".join(_to_access_literal(v) for v in row)
                insert_sql = f"INSERT INTO {_bracket(t)} ({col_list}) VALUES ({values_sql})"
                cur.execute(insert_sql)

        written.append(t)

    cur.close()
    acc.close()
    return AccessExportResult(tables_written=written)

