"""Mode 1: reconciliation against the source export.

When the operational platform's own export is available, every ledger
record can be compared with the record it came from. This is exact, and
it is the reference against which the ledger-only mode is measured.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from .findings import finding, make

MODE = "reconciliation"


def match_invoices(src_inv: pd.DataFrame, led_inv: pd.DataFrame, max_days: int = 60) -> dict[str, str]:
    """Map ledger doc_number -> source doc_number.

    Exact number matches first; the rest are paired by customer, total and
    the closest date within ``max_days``.
    """
    src_docs = set(src_inv.doc_number)
    pairs = {d: d for d in led_inv.doc_number if d in src_docs}
    used = set(pairs.values())
    pool = src_inv[~src_inv.doc_number.isin(used)]
    for _, l in led_inv[~led_inv.doc_number.isin(pairs)].iterrows():
        cand = pool[(pool.customer == l.customer) & ((pool.total - l.total).abs() < 0.01)]
        if cand.empty:
            continue
        gap = (cand.txn_date - l.txn_date).abs().dt.days
        cand = cand[gap <= max_days]
        if cand.empty:
            continue
        best = cand.loc[(cand.txn_date - l.txn_date).abs().idxmin(), "doc_number"]
        pairs[l.doc_number] = best
        pool = pool[pool.doc_number != best]
    return pairs


def reconcile(source: dict[str, pd.DataFrame], ledger: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    s_inv = source["invoices"].set_index("doc_number", drop=False)
    l_inv = ledger["invoices"]
    pairs = match_invoices(source["invoices"], l_inv)

    s_lines = source["invoice_lines"].groupby("doc_number")
    l_lines = ledger["invoice_lines"].groupby("doc_number")

    for _, l in l_inv.iterrows():
        sdoc = pairs.get(l.doc_number)
        if sdoc is None:
            continue
        s = s_inv.loc[sdoc]
        if sdoc != l.doc_number:
            rows.append(finding(MODE, "invoice", l.doc_number, "IDENTIFIER",
                                f"ledger number differs from source number", source_key=sdoc))
        if l.terms != s.terms:
            rows.append(finding(MODE, "invoice", l.doc_number, "TERMS",
                                f"terms '{l.terms}' vs source '{s.terms}'", source_key=sdoc))
        if l.tax_jurisdiction != s.tax_jurisdiction:
            rows.append(finding(MODE, "invoice", l.doc_number, "TAX_JURISDICTION",
                                "jurisdiction differs from source", source_key=sdoc))
        if pd.notna(l.txn_date) and pd.notna(s.txn_date) and l.txn_date != s.txn_date:
            days = (l.txn_date - s.txn_date).days
            period = " (crosses accounting period)" if l.txn_date.to_period("M") != s.txn_date.to_period("M") else ""
            rows.append(finding(MODE, "invoice", l.doc_number, "DATE",
                                f"date differs by {days} days{period}", source_key=sdoc))
        sl = s_lines.get_group(sdoc) if sdoc in s_lines.groups else source["invoice_lines"].iloc[0:0]
        ll = l_lines.get_group(l.doc_number) if l.doc_number in l_lines.groups else ledger["invoice_lines"].iloc[0:0]
        s_count = Counter(zip(sl["item"], sl["amount"]))
        l_count = Counter(zip(ll["item"], ll["amount"]))
        if any(l_count[k] > s_count.get(k, 0) and s_count.get(k, 0) > 0 for k in l_count):
            rows.append(finding(MODE, "invoice", l.doc_number, "DUPLICATE_LINE",
                                "ledger carries more copies of a line than the source", source_key=sdoc))
        for _, st in sl[sl.line_type == "tax"].iterrows():
            match = ll[(ll["item"] == st["item"]) & ((ll.amount - st.amount).abs() < 0.01)]
            if not match.empty and ((match.line_type != "tax") | (match.account != st.account)).any():
                rows.append(finding(MODE, "invoice", l.doc_number, "TAX_CLASSIFICATION",
                                    "tax line posted as a non-tax line or to a different account", source_key=sdoc))
                break

    # Payments: compare where each payment was applied.
    l_to_s = pairs
    s_pay = source["payments"].set_index("payment_id")
    led_paid_src_docs = set()
    for _, p in ledger["payments"].iterrows():
        if p.payment_id not in s_pay.index:
            continue
        s_applied = s_pay.at[p.payment_id, "applied_doc_number"]
        l_applied = l_to_s.get(p.applied_doc_number, p.applied_doc_number) if p.applied_doc_number else ""
        if l_applied:
            led_paid_src_docs.add(l_applied)
        if s_applied and not l_applied:
            rows.append(finding(MODE, "payment", p.payment_id, "PAYMENT_UNAPPLIED",
                                "applied in source, unapplied in ledger", source_key=p.payment_id))
        elif s_applied and l_applied != s_applied:
            rows.append(finding(MODE, "payment", p.payment_id, "PAYMENT_MISAPPLIED",
                                "applied to a different invoice than in source", source_key=p.payment_id))

    # Labor: compare client and project per time entry.
    s_time = source["time_entries"].set_index("entry_id")
    for _, t in ledger["time_entries"].iterrows():
        if t.entry_id not in s_time.index:
            continue
        s = s_time.loc[t.entry_id]
        if (t.client, t.project) != (s.client, s.project):
            rows.append(finding(MODE, "time_entry", t.entry_id, "LABOR_MISALLOCATION",
                                "client or project differs from source", source_key=t.entry_id))

    src_paid = set(source["payments"].applied_doc_number) - {""}
    consequences = {
        "invoices_paid_in_source_open_in_ledger": len(src_paid - led_paid_src_docs),
        "ledger_invoices_without_source_match": int(len(l_inv) - len(pairs)),
    }
    return make(rows), consequences
