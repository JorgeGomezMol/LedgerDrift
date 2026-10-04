"""Measure detection against synthetic data with known defects."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

from .detect import detect
from .findings import DEFECTS
from .io import load_dir
from .ml import review_queue
from .reconcile import reconcile
from .synth import SynthConfig, generate


def score(findings: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for defect in DEFECTS:
        truth = set(labels.loc[labels.defect == defect, "ledger_key"])
        found = set(findings.loc[findings.defect == defect, "ledger_key"]) if not findings.empty else set()
        tp = len(truth & found)
        rows.append({"defect": defect, "injected": len(truth), "flagged": len(found), "correct": tp,
                     "precision": round(tp / len(found), 3) if found else None,
                     "recall": round(tp / len(truth), 3) if truth else None})
    return pd.DataFrame(rows)


def evaluate(seed: int = 7) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = generate(tmp, SynthConfig(seed=seed))
        source, ledger = load_dir(root / "source"), load_dir(root / "ledger")
        labels = pd.read_csv(root / "labels.csv", dtype=str)
    rec, _ = reconcile(source, ledger)
    led = detect(ledger)
    queue = review_queue(ledger)
    bad = set(labels.loc[labels.record_type == "invoice", "ledger_key"])
    auc = roc_auc_score(queue.doc_number.isin(bad), queue.anomaly_score) if len(queue) else None
    top = queue.head(max(1, len(bad)))
    return {
        "reconciliation": score(rec, labels),
        "ledger_only": score(led, labels),
        "anomaly_auc": round(float(auc), 3) if auc is not None else None,
        "anomaly_precision_at_k": round(float(top.doc_number.isin(bad).mean()), 3) if len(top) else None,
        "invoices": int(len(ledger["invoices"])),
        "defective_invoices": len(bad),
    }


def print_report(res: dict) -> None:
    print(f"Synthetic ledger: {res['invoices']} invoices, {res['defective_invoices']} with an injected defect\n")
    for mode in ["reconciliation", "ledger_only"]:
        print(f"== {mode} ==")
        print(res[mode].to_string(index=False))
        print()
    print(f"Anomaly score: ROC AUC {res['anomaly_auc']}, precision in top-k {res['anomaly_precision_at_k']}")
