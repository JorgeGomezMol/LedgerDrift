"""Unsupervised anomaly scoring to build a review queue.

Rule checks catch known defect types. The anomaly score catches records
that are unusual on several signals at once, including combinations no
single rule targets. It does not need labeled data: an Isolation Forest
learns what a normal invoice looks like in this ledger and ranks every
invoice by how hard it is to explain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .detect import TAX_WORDS, is_revenue_account, shape


def invoice_features(ledger: dict[str, pd.DataFrame]) -> pd.DataFrame:
    inv = ledger["invoices"].copy()
    lines = ledger["invoice_lines"]
    if inv.empty:
        return pd.DataFrame()
    f = pd.DataFrame(index=inv.doc_number)

    shares = inv.doc_number.map(shape).value_counts(normalize=True)
    f["shape_rarity"] = 1 - inv.doc_number.map(shape).map(shares).to_numpy()

    for col in ["terms", "tax_jurisdiction"]:
        usual = inv.groupby("customer")[col].agg(lambda s: s.value_counts().index[0])
        f[f"{col}_deviates"] = (inv[col].to_numpy() != inv.customer.map(usual).to_numpy()).astype(float)

    main = inv.copy()
    main["seq"] = main.doc_number.str.extract(r"(\d+)").astype(float)[0]
    main = main.sort_values("seq")
    days = main.txn_date.map(pd.Timestamp.toordinal).astype(float)
    neigh = days.rolling(11, center=True, min_periods=4).median()
    f["date_gap_days"] = (days - neigh).abs().reindex(main.index).set_axis(main.doc_number).reindex(f.index).fillna(0).to_numpy()

    counts = lines.groupby(["doc_number", "item", "amount"]).size()
    dup_docs = set(counts[counts > 1].index.get_level_values(0))
    f["has_repeated_line"] = f.index.isin(dup_docs).astype(float)

    bad_tax = lines[lines["item"].str.contains(TAX_WORDS) &
                    ((lines.line_type != "tax") | lines.account.map(is_revenue_account))]
    f["tax_as_revenue"] = f.index.isin(set(bad_tax.doc_number)).astype(float)

    log_total = np.log1p(inv.total.clip(lower=0))
    grp = log_total.groupby(inv.customer)
    z = (log_total - grp.transform("mean")) / grp.transform("std").replace(0, np.nan)
    f["total_z_within_customer"] = z.abs().fillna(0).to_numpy()

    n_lines = lines.groupby("doc_number").size()
    f["line_count"] = f.index.map(n_lines).fillna(0).astype(float)
    return f


def review_queue(ledger: dict[str, pd.DataFrame], seed: int = 0) -> pd.DataFrame:
    f = invoice_features(ledger)
    if f.empty or len(f) < 20:
        return pd.DataFrame(columns=["doc_number", "anomaly_score"])
    model = IsolationForest(n_estimators=300, random_state=seed)
    model.fit(f.to_numpy())
    score = -model.decision_function(f.to_numpy())
    out = pd.DataFrame({"doc_number": f.index, "anomaly_score": score})
    return out.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
