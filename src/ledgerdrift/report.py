"""Reports.

Two levels, on purpose:

* findings.csv and review_queue.csv list individual records. They stay
  with the organization that owns the books and are never shared.
* summary.json and summary.md hold aggregate counts by defect type only:
  no document numbers, customers, amounts or names. They are safe to share
  and are what feeds the aggregate discrepancy log.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import __version__
from .findings import DEFECTS


def summarize(findings: pd.DataFrame, ledger: dict[str, pd.DataFrame], mode: str,
              consequences: dict | None = None) -> dict:
    by_defect = findings.groupby("defect").ledger_key.nunique().to_dict() if not findings.empty else {}
    by_conf = (findings.groupby(["defect", "confidence"]).ledger_key.nunique()
               .unstack(fill_value=0).to_dict(orient="index") if not findings.empty else {})
    return {
        "tool": "ledgerdrift", "version": __version__, "mode": mode,
        "run_date": date.today().isoformat(),
        "records_processed": {k: int(len(v)) for k, v in ledger.items()},
        "records_flagged_by_defect": {k: int(by_defect.get(k, 0)) for k in DEFECTS},
        "records_flagged_by_defect_and_confidence": by_conf,
        "consequences": consequences or {},
    }


def to_markdown(summary: dict) -> str:
    rp = summary["records_processed"]
    lines = [
        f"# Integration integrity summary ({summary['mode'].replace('_', ' ')})",
        "",
        f"Run {summary['run_date']} with ledgerdrift {summary['version']}. Aggregate counts only.",
        "",
        "| Records processed | Count |", "| --- | --- |",
        *[f"| {k.replace('_', ' ')} | {v} |" for k, v in rp.items()],
        "",
        "| Defect | Records flagged | Meaning |", "| --- | --- | --- |",
        *[f"| {k} | {v} | {DEFECTS[k]} |" for k, v in summary["records_flagged_by_defect"].items()],
    ]
    if summary["consequences"]:
        lines += ["", "| Consequence | Count |", "| --- | --- |",
                  *[f"| {k.replace('_', ' ')} | {v} |" for k, v in summary["consequences"].items()]]
    return "\n".join(lines) + "\n"


def write_reports(out_dir: str | Path, findings: pd.DataFrame, summary: dict,
                  queue: pd.DataFrame | None = None) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    findings.to_csv(out / "findings.csv", index=False)
    if queue is not None:
        queue.to_csv(out / "review_queue.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "summary.md").write_text(to_markdown(summary), encoding="utf-8")
    return out


LOG_FIELDS = ["date", "environment", "cycle", "records_processed", "defect", "count", "detected_by"]
CYCLE_OF = {"PAYMENT_UNAPPLIED": "payments", "PAYMENT_MISAPPLIED": "payments",
            "LABOR_MISALLOCATION": "time_entries"}


def append_log(log_file: str | Path, summary: dict, environment: str) -> None:
    """Append one aggregate row per defect type to the discrepancy log."""
    log_file = Path(log_file)
    new = not log_file.exists()
    with log_file.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        for defect, count in summary["records_flagged_by_defect"].items():
            cycle = CYCLE_OF.get(defect, "invoices")
            w.writerow({"date": summary["run_date"], "environment": environment, "cycle": cycle,
                        "records_processed": summary["records_processed"].get(cycle, 0),
                        "defect": defect, "count": count,
                        "detected_by": f"ledgerdrift {summary['version']} ({summary['mode']})"})
