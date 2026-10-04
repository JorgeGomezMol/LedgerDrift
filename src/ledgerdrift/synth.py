"""Synthetic data with known, injected integration defects.

Nothing here comes from a real organization. The generator builds a year
of operational records (the "source"), copies them into a "ledger", and
alters a known share of ledger records the way a faulty synchronization
does. A labels file records every alteration, so detection can be
measured instead of asserted.

Each invoice carries at most one defect, which keeps the measurement clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .io import normalize, save_dir

DEFECTS_INVOICE = ["IDENTIFIER", "TAX_CLASSIFICATION", "DUPLICATE_LINE",
                   "TAX_JURISDICTION", "DATE", "TERMS"]

JURISDICTIONS = ["Kent County, MI", "Ottawa County, MI", "Wayne County, MI",
                 "Polk County, FL", "Hillsborough County, FL", "Cook County, IL",
                 "DuPage County, IL", "Lake County, IN", "Travis County, TX",
                 "Maricopa County, AZ", "King County, WA", "Fulton County, GA"]
TERMS = {"Net 30": 30, "Net 15": 15, "Due on receipt": 0}
ITEMS = {
    "Managed Services Agreement": "service", "Project Labor": "service",
    "Onsite Support": "service", "Remote Support": "service",
    "Firewall Appliance": "product", "Laptop": "product",
    "Network Switch": "product", "Software License": "product",
}
ACCOUNTS = {"service": "Services Revenue", "product": "Product Revenue", "tax": "Sales Tax Payable"}


@dataclass
class SynthConfig:
    seed: int = 7
    customers: int = 40
    months: int = 12
    start: str = "2025-01-01"
    invoice_defect_rate: float = 0.22   # share of invoices with one defect
    payment_unapplied_rate: float = 0.04
    payment_misapplied_rate: float = 0.02
    labor_defect_rate: float = 0.03
    engineers: int = 8
    entries_per_engineer: int = 350
    # Legitimate variation present in both source and ledger: a customer
    # renegotiates terms, moves, an invoice is backdated, an item is billed
    # twice on purpose. It is NOT a defect, and it is what makes ledger-only
    # detection produce false positives in real books.
    legit_noise: float = 0.04


def _customers(rng, n):
    out = []
    for i in range(n):
        out.append({
            "customer": f"Customer {i + 1:03d}",
            "jurisdiction": JURISDICTIONS[rng.integers(len(JURISDICTIONS))],
            "terms": rng.choice(list(TERMS), p=[0.6, 0.25, 0.15]),
            "tax_rate": round(float(rng.uniform(0.06, 0.0825)), 4),
            "projects": [f"C{i + 1:03d}-P{k + 1}" for k in range(int(rng.integers(1, 4)))],
        })
    return out


def generate_source(cfg: SynthConfig) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    rng = np.random.default_rng(cfg.seed)
    custs = _customers(rng, cfg.customers)
    start = pd.Timestamp(cfg.start)
    inv_rows, line_rows = [], []
    items = list(ITEMS)
    for m in range(cfg.months):
        month_start = start + pd.DateOffset(months=m)
        for c in custs:
            if rng.random() > 0.9:
                continue
            date = month_start + pd.Timedelta(days=int(rng.integers(0, 28)))
            chosen = rng.choice(items, size=int(rng.integers(1, 5)), replace=False)
            lines, taxable = [], 0.0
            for it in chosen:
                kind = ITEMS[it]
                amt = round(float(rng.uniform(150, 4500 if kind == "service" else 2500)), 2)
                lines.append((it, kind, ACCOUNTS[kind], amt))
                if kind == "product":
                    taxable += amt
            if taxable > 0:
                lines.append(("Sales Tax", "tax", ACCOUNTS["tax"], round(taxable * c["tax_rate"], 2)))
            inv_rows.append({"customer": c["customer"], "txn_date": date, "terms": c["terms"],
                             "tax_jurisdiction": c["jurisdiction"],
                             "total": round(sum(l[3] for l in lines), 2), "_lines": lines})
    inv_rows.sort(key=lambda r: (r["txn_date"], r["customer"]))
    for k, r in enumerate(inv_rows):
        r["doc_number"] = f"INV-{10001 + k}"
        for n, (it, kind, acct, amt) in enumerate(r.pop("_lines"), start=1):
            line_rows.append({"doc_number": r["doc_number"], "line_no": n, "item": it,
                              "line_type": kind, "account": acct, "amount": amt})
    invoices = pd.DataFrame(inv_rows)

    # Legitimate variation (see SynthConfig.legit_noise).
    line_df = pd.DataFrame(line_rows)
    extra_lines = []
    for i, r in invoices.iterrows():
        if rng.random() >= cfg.legit_noise:
            continue
        kind = ["terms", "jurisdiction", "date", "repeat_line"][int(rng.integers(4))]
        if kind == "terms":
            invoices.at[i, "terms"] = rng.choice([t for t in TERMS if t != r.terms])
        elif kind == "jurisdiction":
            invoices.at[i, "tax_jurisdiction"] = rng.choice([j for j in JURISDICTIONS if j != r.tax_jurisdiction])
        elif kind == "date":
            invoices.at[i, "txn_date"] = r.txn_date - pd.Timedelta(days=int(rng.integers(20, 40)))
        else:
            cand = line_df[(line_df.doc_number == r.doc_number) & (line_df.line_type != "tax")]
            dup = cand.iloc[0].to_dict()
            dup["line_no"] = int(line_df.loc[line_df.doc_number == r.doc_number, "line_no"].max()) + 1
            extra_lines.append(dup)
            invoices.at[i, "total"] = round(r.total + dup["amount"], 2)
    if extra_lines:
        line_rows = line_rows + extra_lines

    pay_rows = []
    for _, r in invoices.iterrows():
        if rng.random() < 0.85:
            days = TERMS[r["terms"]] + int(rng.integers(-5, 20))
            pay_rows.append({"customer": r["customer"],
                             "txn_date": r["txn_date"] + pd.Timedelta(days=max(days, 0)),
                             "amount": r["total"], "applied_doc_number": r["doc_number"]})
    pay_rows.sort(key=lambda r: r["txn_date"])
    for k, r in enumerate(pay_rows):
        r["payment_id"] = f"PMT-{50001 + k}"

    time_rows = []
    by_name = {c["customer"]: c for c in custs}
    names = list(by_name)
    for e in range(cfg.engineers):
        eng = f"Engineer {e + 1:02d}"
        primary = list(rng.choice(names, size=int(rng.integers(2, 5)), replace=False))
        for _ in range(cfg.entries_per_engineer):
            client = rng.choice(primary) if rng.random() < 0.95 else rng.choice(names)
            time_rows.append({"engineer": eng, "client": client,
                              "project": rng.choice(by_name[client]["projects"]),
                              "work_date": start + pd.Timedelta(days=int(rng.integers(0, cfg.months * 30))),
                              "hours": float(rng.choice([0.5, 1, 1.5, 2, 3, 4, 6, 8]))})
    for k, r in enumerate(time_rows):
        r["entry_id"] = f"TE-{100001 + k}"

    tables = {
        "invoices": normalize("invoices", invoices),
        "invoice_lines": normalize("invoice_lines", pd.DataFrame(line_rows)),
        "payments": normalize("payments", pd.DataFrame(pay_rows)),
        "time_entries": normalize("time_entries", pd.DataFrame(time_rows)),
    }
    return tables, custs


def inject_defects(source: dict[str, pd.DataFrame], custs: list[dict], cfg: SynthConfig):
    """Return a corrupted ledger copy and the labels of every alteration."""
    rng = np.random.default_rng(cfg.seed + 1)
    inv = source["invoices"].copy()
    lines = source["invoice_lines"].copy()
    pays = source["payments"].copy()
    time = source["time_entries"].copy()
    labels: list[dict] = []
    renamed: dict[str, str] = {}
    has_tax = set(lines.loc[lines.line_type == "tax", "doc_number"])
    other_terms = {t: [x for x in TERMS if x != t] for t in TERMS}

    for i, r in inv.iterrows():
        if rng.random() >= cfg.invoice_defect_rate:
            continue
        options = [d for d in DEFECTS_INVOICE if d != "TAX_CLASSIFICATION" or r.doc_number in has_tax]
        defect = options[int(rng.integers(len(options)))]
        doc = r.doc_number
        if defect == "IDENTIFIER":
            num = doc.split("-")[1]
            new = num if rng.random() < 0.5 else f"{doc}-1"
            renamed[doc] = new
            inv.at[i, "doc_number"] = new
            lines.loc[lines.doc_number == doc, "doc_number"] = new
        elif defect == "TAX_CLASSIFICATION":
            mask = (lines.doc_number == doc) & (lines.line_type == "tax")
            lines.loc[mask, "line_type"] = "service"
            lines.loc[mask, "account"] = ACCOUNTS["service"]
        elif defect == "DUPLICATE_LINE":
            cand = lines[(lines.doc_number == doc) & (lines.line_type != "tax")]
            dup = cand.iloc[[int(rng.integers(len(cand)))]].copy()
            dup["line_no"] = lines.loc[lines.doc_number == doc, "line_no"].max() + 1
            lines = pd.concat([lines, dup], ignore_index=True)
            inv.at[i, "total"] = round(r.total + float(dup.amount.iloc[0]), 2)
        elif defect == "TAX_JURISDICTION":
            choices = [j for j in JURISDICTIONS if j != r.tax_jurisdiction]
            inv.at[i, "tax_jurisdiction"] = choices[int(rng.integers(len(choices)))]
        elif defect == "DATE":
            shift = int(rng.integers(20, 46)) * (1 if rng.random() < 0.5 else -1)
            inv.at[i, "txn_date"] = r.txn_date + pd.Timedelta(days=shift)
        elif defect == "TERMS":
            choices = other_terms[r.terms]
            inv.at[i, "terms"] = choices[int(rng.integers(len(choices)))]
        labels.append({"record_type": "invoice", "source_key": doc,
                       "ledger_key": renamed.get(doc, doc), "defect": defect})

    pays["applied_doc_number"] = pays["applied_doc_number"].map(lambda d: renamed.get(d, d))
    by_customer = inv.groupby("customer")["doc_number"].apply(list).to_dict()
    for i, r in pays.iterrows():
        u = rng.random()
        if u < cfg.payment_unapplied_rate:
            pays.at[i, "applied_doc_number"] = ""
            labels.append({"record_type": "payment", "source_key": r.payment_id,
                           "ledger_key": r.payment_id, "defect": "PAYMENT_UNAPPLIED"})
        elif u < cfg.payment_unapplied_rate + cfg.payment_misapplied_rate:
            others = [d for d in by_customer.get(r.customer, []) if d != r.applied_doc_number]
            if others:
                pays.at[i, "applied_doc_number"] = others[int(rng.integers(len(others)))]
                labels.append({"record_type": "payment", "source_key": r.payment_id,
                               "ledger_key": r.payment_id, "defect": "PAYMENT_MISAPPLIED"})

    all_projects = [(c["customer"], p) for c in custs for p in c["projects"]]
    for i, r in time.iterrows():
        if rng.random() < cfg.labor_defect_rate:
            choices = [cp for cp in all_projects if cp[0] != r.client]
            client, project = choices[int(rng.integers(len(choices)))]
            time.at[i, "client"] = client
            time.at[i, "project"] = project
            labels.append({"record_type": "time_entry", "source_key": r.entry_id,
                           "ledger_key": r.entry_id, "defect": "LABOR_MISALLOCATION"})

    ledger = {"invoices": inv, "invoice_lines": lines, "payments": pays, "time_entries": time}
    return ledger, pd.DataFrame(labels)


def generate(out_dir: str | Path, cfg: SynthConfig | None = None) -> Path:
    cfg = cfg or SynthConfig()
    out = Path(out_dir)
    source, custs = generate_source(cfg)
    ledger, labels = inject_defects(source, custs, cfg)
    save_dir(source, out / "source")
    save_dir(ledger, out / "ledger")
    labels.to_csv(out / "labels.csv", index=False)
    return out
