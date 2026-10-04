"""The shared shape of every finding."""

from __future__ import annotations

import pandas as pd

COLUMNS = ["mode", "record_type", "ledger_key", "source_key", "defect", "confidence", "detail"]

# Defect vocabulary, shared by both detection modes and by the synthetic labels.
DEFECTS = {
    "IDENTIFIER": "Document number does not match the source, or breaks the ledger's own numbering pattern",
    "TAX_CLASSIFICATION": "Sales tax recorded as a revenue line instead of a tax liability",
    "DUPLICATE_LINE": "The same line appears twice in one document",
    "TAX_JURISDICTION": "Tax assigned to a different county or state",
    "DATE": "Document date differs from the source or from its place in the numbering sequence",
    "TERMS": "Payment terms differ from the source or from the customer's usual terms",
    "PAYMENT_UNAPPLIED": "Payment recorded without being applied to its invoice",
    "PAYMENT_MISAPPLIED": "Payment applied to the wrong invoice",
    "LABOR_MISALLOCATION": "Time entry assigned to a different client or project",
}


def make(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows)[COLUMNS]


def finding(mode, record_type, ledger_key, defect, detail, confidence="high", source_key=""):
    return {"mode": mode, "record_type": record_type, "ledger_key": ledger_key,
            "source_key": source_key, "defect": defect, "confidence": confidence, "detail": detail}
