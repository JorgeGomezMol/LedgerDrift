"""Loading and normalizing exported records into a canonical schema.

The toolkit works on four tables exported from an operational platform
(the "source") and from an accounting system (the "ledger"):

    invoices.csv       doc_number, customer, txn_date, terms, tax_jurisdiction, total
    invoice_lines.csv  doc_number, line_no, item, line_type, account, amount
    payments.csv       payment_id, customer, txn_date, amount, applied_doc_number
    time_entries.csv   entry_id, engineer, client, project, work_date, hours

Real exports rarely use these column names. A mapping file (JSON) renames
columns per table, for example:

    {"invoices": {"doc_number": "Invoice #", "txn_date": "Date"}}

Missing tables are allowed and load as empty frames, so a partial export
still produces whatever checks its data supports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SCHEMA: dict[str, list[str]] = {
    "invoices": ["doc_number", "customer", "txn_date", "terms", "tax_jurisdiction", "total"],
    "invoice_lines": ["doc_number", "line_no", "item", "line_type", "account", "amount"],
    "payments": ["payment_id", "customer", "txn_date", "amount", "applied_doc_number"],
    "time_entries": ["entry_id", "engineer", "client", "project", "work_date", "hours"],
}

DATE_COLUMNS = {"txn_date", "work_date"}
NUMBER_COLUMNS = {"total", "amount", "hours", "line_no"}


def empty_table(name: str) -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in SCHEMA[name]})


def normalize(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Keep the canonical columns, coerce types and trim text."""
    df = df.copy()
    for col in SCHEMA[name]:
        if col not in df.columns:
            df[col] = None
    df = df[SCHEMA[name]]
    for col in df.columns:
        if col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif col in NUMBER_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = df[col].fillna("").astype(str).str.strip()
    return df.reset_index(drop=True)


def load_dir(path: str | Path, mapping_file: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Load every canonical table found in a folder of CSV exports."""
    path = Path(path)
    mapping: dict[str, dict[str, str]] = {}
    if mapping_file:
        mapping = json.loads(Path(mapping_file).read_text(encoding="utf-8"))
    tables: dict[str, pd.DataFrame] = {}
    for name in SCHEMA:
        file = path / f"{name}.csv"
        if not file.exists():
            tables[name] = empty_table(name)
            continue
        raw = pd.read_csv(file, dtype=str, keep_default_na=False)
        rename = {src: canon for canon, src in mapping.get(name, {}).items()}
        tables[name] = normalize(name, raw.rename(columns=rename))
    return tables


def save_dir(tables: dict[str, pd.DataFrame], path: str | Path) -> None:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        out = df.copy()
        for col in out.columns:
            if col in DATE_COLUMNS:
                out[col] = pd.to_datetime(out[col]).dt.strftime("%Y-%m-%d")
        out.to_csv(path / f"{name}.csv", index=False)
