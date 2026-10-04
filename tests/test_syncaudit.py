import json

import pandas as pd
import pytest

from ledgerdrift.cli import main
from ledgerdrift.detect import detect, is_revenue_account, shape
from ledgerdrift.evaluate import evaluate
from ledgerdrift.io import load_dir
from ledgerdrift.reconcile import reconcile
from ledgerdrift.synth import SynthConfig, generate


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    root = generate(tmp_path_factory.mktemp("synth"), SynthConfig(seed=3))
    return load_dir(root / "source"), load_dir(root / "ledger"), pd.read_csv(root / "labels.csv", dtype=str), root


def test_synthetic_tables_have_canonical_columns(data):
    source, ledger, labels, _ = data
    for t in source.values():
        assert len(t) > 0
    assert set(labels.defect) >= {"IDENTIFIER", "DATE", "TERMS", "PAYMENT_UNAPPLIED", "LABOR_MISALLOCATION"}


def test_reconciliation_finds_every_injected_defect(data):
    source, ledger, labels, _ = data
    findings, consequences = reconcile(source, ledger)
    found = set(zip(findings.ledger_key, findings.defect))
    missed = [r for r in labels.itertuples() if (r.ledger_key, r.defect) not in found]
    assert not missed
    assert consequences["invoices_paid_in_source_open_in_ledger"] > 0


def test_ledger_only_high_confidence_checks_have_no_false_positives_on_clean_patterns(data):
    _, ledger, labels, _ = data
    findings = detect(ledger)
    truth = set(zip(labels.ledger_key, labels.defect))
    for defect in ["IDENTIFIER", "TAX_CLASSIFICATION", "PAYMENT_MISAPPLIED"]:
        flagged = findings[findings.defect == defect]
        assert all((k, defect) in truth for k in flagged.ledger_key)


def test_helpers():
    assert shape("INV-10045") == "AAA-99999"
    assert is_revenue_account("Services Revenue")
    assert not is_revenue_account("Sales Tax Payable")


def test_summary_is_aggregate_only(data, tmp_path):
    _, _, _, root = data
    out = tmp_path / "report"
    log = tmp_path / "log.csv"
    assert main(["audit", "--ledger", str(root / "ledger"), "--out", str(out),
                 "--log", str(log), "--env", "E01"]) == 0
    text = (out / "summary.json").read_text() + (out / "summary.md").read_text()
    assert "INV-" not in text and "Customer " not in text and "PMT-" not in text
    assert json.loads((out / "summary.json").read_text())["mode"] == "ledger_only"
    assert log.read_text().count("E01") == 9


def test_evaluation_recall_floor():
    res = evaluate(seed=5)
    rec = res["reconciliation"].set_index("defect")
    assert (rec.recall.dropna() == 1.0).all()
    led = res["ledger_only"].set_index("defect")
    assert (led.recall.dropna() >= 0.85).all()
    assert res["anomaly_auc"] > 0.9
