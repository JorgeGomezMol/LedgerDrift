"""Mode 2: detection from the ledger alone.

This is the harder and more useful case. Most small organizations cannot
pull a clean source export for past periods, so the corrupted record is
the only evidence. Each check compares a record with the historical
pattern of its own customer, item, numbering sequence or engineer.

Every check returns a confidence:
    high    the record breaks a pattern that is almost never broken legitimately
    medium  the record is unusual and worth a human look
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .findings import finding, make

MODE = "ledger_only"
TAX_WORDS = re.compile(r"\b(?:sales\s*tax|tax|vat|iva|gst)\b", re.I)
REVENUE_WORDS = re.compile(r"(?:revenue|income|sales)", re.I)
LIABILITY_WORDS = re.compile(r"(?:payable|liabilit|accrued|tax)", re.I)


def is_revenue_account(account: str) -> bool:
    """'Services Revenue' -> True; 'Sales Tax Payable' -> False."""
    return bool(REVENUE_WORDS.search(account)) and not LIABILITY_WORDS.search(account)


def shape(doc: str) -> str:
    """'INV-10045' -> 'AAA-99999'."""
    return re.sub(r"[A-Za-z]", "A", re.sub(r"\d", "9", doc))


def identifier_pattern(inv: pd.DataFrame, rare_share: float = 0.05) -> list[dict]:
    if inv.empty:
        return []
    shares = inv.doc_number.map(shape).value_counts(normalize=True)
    rare = set(shares[shares < rare_share].index)
    return [finding(MODE, "invoice", d, "IDENTIFIER",
                    f"number format '{shape(d)}' is used by under {rare_share:.0%} of invoices")
            for d in inv.doc_number if shape(d) in rare]


def tax_classification(lines: pd.DataFrame) -> list[dict]:
    out, seen = [], set()
    for _, l in lines.iterrows():
        is_tax_item = bool(TAX_WORDS.search(l["item"]))
        wrong = (is_tax_item and (l.line_type != "tax" or is_revenue_account(l.account))) or \
                (l.line_type == "tax" and is_revenue_account(l.account))
        if wrong and l.doc_number not in seen:
            seen.add(l.doc_number)
            out.append(finding(MODE, "invoice", l.doc_number, "TAX_CLASSIFICATION",
                               "tax item posted as a revenue line"))
    return out


def duplicate_lines(lines: pd.DataFrame, max_repeat_share: float = 0.05) -> list[dict]:
    if lines.empty:
        return []
    counts = lines.groupby(["doc_number", "item", "amount"]).size().rename("n").reset_index()
    repeats = counts[counts.n > 1]
    docs_per_item = lines.groupby("item").doc_number.nunique()
    repeat_docs_per_item = repeats.groupby("item").doc_number.nunique()
    out, seen = [], set()
    for _, r in repeats.iterrows():
        share = repeat_docs_per_item.get(r["item"], 0) / max(docs_per_item.get(r["item"], 1), 1)
        if share <= max_repeat_share and r.doc_number not in seen:
            seen.add(r.doc_number)
            out.append(finding(MODE, "invoice", r.doc_number, "DUPLICATE_LINE",
                               f"identical line repeated {int(r.n)} times; this item is rarely repeated"))
    return out


def customer_mode_deviation(inv: pd.DataFrame, column: str, defect: str,
                            min_docs: int = 4, min_share: float = 0.6) -> list[dict]:
    out = []
    for cust, g in inv.groupby("customer"):
        if len(g) < min_docs:
            continue
        counts = g[column].value_counts()
        usual, share = counts.index[0], counts.iloc[0] / len(g)
        if share < min_share:
            continue
        for _, r in g[g[column] != usual].iterrows():
            conf = "high" if share >= 0.85 else "medium"
            out.append(finding(MODE, "invoice", r.doc_number, defect,
                               f"{column} differs from the customer's usual value ({share:.0%} of its invoices)",
                               confidence=conf))
    return out


def date_sequence(inv: pd.DataFrame, window: int = 5, max_days: int = 15) -> list[dict]:
    """Invoices are numbered in date order; a date far from its neighbors' is suspect."""
    if inv.empty:
        return []
    shapes = inv.doc_number.map(shape)
    main = inv[shapes == shapes.value_counts().index[0]].copy()
    main["seq"] = main.doc_number.str.extract(r"(\d+)").astype(float)[0]
    main = main.dropna(subset=["seq", "txn_date"]).sort_values("seq").reset_index(drop=True)
    days = main.txn_date.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    out = []
    for i in range(len(main)):
        lo, hi = max(0, i - window), min(len(main), i + window + 1)
        neigh = np.delete(days[lo:hi], i - lo)
        if len(neigh) < 3:
            continue
        gap = days[i] - np.median(neigh)
        if abs(gap) > max_days:
            out.append(finding(MODE, "invoice", main.doc_number[i], "DATE",
                               f"date is {gap:+.0f} days from invoices numbered around it",
                               confidence="high" if abs(gap) > 2 * max_days else "medium"))
    return out


def payments(inv: pd.DataFrame, pays: pd.DataFrame) -> list[dict]:
    if pays.empty:
        return []
    out = []
    applied = pays[pays.applied_doc_number != ""]
    paid_docs = set(applied.applied_doc_number)
    open_inv = inv[~inv.doc_number.isin(paid_docs)]
    totals = inv.set_index("doc_number").total
    for _, p in pays.iterrows():
        same = open_inv[(open_inv.customer == p.customer) & ((open_inv.total - p.amount).abs() < 0.01)]
        if p.applied_doc_number == "":
            conf = "high" if not same.empty else "medium"
            out.append(finding(MODE, "payment", p.payment_id, "PAYMENT_UNAPPLIED",
                               "payment not applied to any invoice" +
                               ("; an open invoice of the same customer has exactly this amount" if not same.empty else ""),
                               confidence=conf))
        elif p.applied_doc_number in totals.index and abs(totals[p.applied_doc_number] - p.amount) >= 0.01 and not same.empty:
            out.append(finding(MODE, "payment", p.payment_id, "PAYMENT_MISAPPLIED",
                               "amount does not match the invoice it was applied to, "
                               "but matches an open invoice of the same customer"))
    return out


def labor_allocation(time: pd.DataFrame, min_entries: int = 50, rare_share: float = 0.02) -> list[dict]:
    if time.empty:
        return []
    out = []
    for eng, g in time.groupby("engineer"):
        if len(g) < min_entries:
            continue
        share = g.client.value_counts(normalize=True)
        rare = set(share[share < rare_share].index)
        for _, t in g[g.client.isin(rare)].iterrows():
            out.append(finding(MODE, "time_entry", t.entry_id, "LABOR_MISALLOCATION",
                               "engineer rarely records time for this client", confidence="medium"))
    return out


def detect(ledger: dict[str, pd.DataFrame]) -> pd.DataFrame:
    inv, lines = ledger["invoices"], ledger["invoice_lines"]
    rows = []
    rows += identifier_pattern(inv)
    rows += tax_classification(lines)
    rows += duplicate_lines(lines)
    rows += customer_mode_deviation(inv, "tax_jurisdiction", "TAX_JURISDICTION")
    rows += customer_mode_deviation(inv, "terms", "TERMS")
    rows += date_sequence(inv)
    rows += payments(inv, ledger["payments"])
    rows += labor_allocation(ledger["time_entries"])
    return make(rows)
