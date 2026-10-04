"""Command line entry point.

    ledgerdrift audit --ledger exports/ledger [--source exports/source] --out report/
    ledgerdrift synth --out demo/ --seed 7
    ledgerdrift evaluate --seed 7
"""

from __future__ import annotations

import argparse
import sys

from .detect import detect
from .evaluate import evaluate, print_report
from .io import load_dir
from .ml import review_queue
from .reconcile import reconcile
from .report import append_log, summarize, to_markdown, write_reports
from .synth import SynthConfig, generate


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ledgerdrift", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit a ledger export, with or without the source export")
    a.add_argument("--ledger", required=True, help="folder with the accounting system's CSV exports")
    a.add_argument("--source", help="folder with the operational platform's CSV exports (optional)")
    a.add_argument("--mapping", help="JSON file mapping your column names to the canonical schema")
    a.add_argument("--out", required=True, help="folder for the reports")
    a.add_argument("--log", help="aggregate discrepancy log (CSV) to append to")
    a.add_argument("--env", default="E00", help="anonymous environment code for the log, e.g. E01")

    s = sub.add_parser("synth", help="generate synthetic data with known defects")
    s.add_argument("--out", required=True)
    s.add_argument("--seed", type=int, default=7)

    e = sub.add_parser("evaluate", help="measure detection on synthetic data")
    e.add_argument("--seed", type=int, default=7)

    args = p.parse_args(argv)

    if args.cmd == "audit":
        ledger = load_dir(args.ledger, args.mapping)
        if args.source:
            source = load_dir(args.source, args.mapping)
            findings, consequences = reconcile(source, ledger)
            mode = "reconciliation"
        else:
            findings, consequences, mode = detect(ledger), {}, "ledger_only"
        queue = review_queue(ledger)
        summary = summarize(findings, ledger, mode, consequences)
        write_reports(args.out, findings, summary, queue)
        if args.log:
            append_log(args.log, summary, args.env)
        print(to_markdown(summary))
        print(f"Detailed findings (keep private): {args.out}/findings.csv")
        return 0

    if args.cmd == "synth":
        out = generate(args.out, SynthConfig(seed=args.seed))
        print(f"Synthetic data written to {out}/source, {out}/ledger and {out}/labels.csv")
        return 0

    if args.cmd == "evaluate":
        print_report(evaluate(args.seed))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
