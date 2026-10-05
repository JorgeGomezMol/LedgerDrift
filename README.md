# LedgerDrift

**LedgerDrift finds the silent drift between operational records and the books:** open detection of financial data corruption in automated integrations between operational platforms and accounting systems.

Operational platforms (PSA, ERP, dealership and e-commerce systems) push invoices, payments and labor time into accounting systems through automated synchronization. When that synchronization alters a record, nothing fails visibly: totals still balance, entries exist, and no exception report is produced. The error simply becomes part of the books, and later part of tax filings and management decisions.

`ledgerdrift` finds those errors. It is built for organizations that cannot afford an internal audit function: small businesses, managed service providers (MSPs) and the small accounting firms that serve them.

## What it detects

| Defect | What happens in the ledger | Why it matters |
| --- | --- | --- |
| `IDENTIFIER` | Document numbers no longer match the source | Records cannot be traced back |
| `TAX_CLASSIFICATION` | Sales tax posted as a revenue line | Revenue overstated, tax liability understated |
| `DUPLICATE_LINE` | The same line appears twice | Revenue and receivables overstated |
| `TAX_JURISDICTION` | Tax assigned to the wrong county or state | State returns prepared on incorrect data |
| `DATE` | Document dated in the wrong period | Cut-off errors |
| `TERMS` | Net 30 becomes due on receipt, or similar | Distorted receivables aging and collections |
| `PAYMENT_UNAPPLIED` | Payment recorded but not applied | Paid invoices stay open; customers billed again |
| `PAYMENT_MISAPPLIED` | Payment applied to the wrong invoice | Two invoices wrong at once |
| `LABOR_MISALLOCATION` | Time entry assigned to another client or project | False project and client profitability |

The full taxonomy, with examples and detection logic, is in [docs/defect-taxonomy.md](docs/defect-taxonomy.md).

## Two modes

1. **Reconciliation** (source export available): every ledger record is compared with the record it came from. Exact.
2. **Ledger only** (no source export): each record is compared with the historical pattern of its own customer, numbering sequence, item and engineer. This is the common real-world case, because most organizations cannot pull a clean source export for past periods.

Both modes also produce a **review queue**: an unsupervised anomaly score (Isolation Forest) that ranks invoices by how unusual they are across several signals at once.

How each check works and its limits: [docs/methodology.md](docs/methodology.md).

## Quick start

New to Python? Follow the [step-by-step guide for accountants](docs/getting-started.md).

```bash
pip install -e .            # Python 3.10+

# Try it on synthetic data with known defects
ledgerdrift synth --out demo --seed 7
ledgerdrift audit --ledger demo/ledger --out demo/report
ledgerdrift audit --ledger demo/ledger --source demo/source --out demo/report_reconciliation

# Measure detection against the injected defects
ledgerdrift evaluate --seed 7
```

On your own data, export four CSV tables (`invoices`, `invoice_lines`, `payments`, `time_entries`) and, if your column names differ, describe them in a mapping file: see [docs/data-schema.md](docs/data-schema.md).

```bash
ledgerdrift audit --ledger exports/ledger --mapping my_mapping.json --out report \
                --log discrepancy_log.csv --env E01
```

## Privacy by design

* Everything runs locally. No data leaves your machine.
* `findings.csv` and `review_queue.csv` list individual records: keep them private.
* `summary.json`, `summary.md` and the discrepancy log hold **aggregate counts only**, with no document numbers, customers, amounts or names. Those are the only outputs meant to be shared.

Details: [docs/privacy.md](docs/privacy.md).

## Current results

On synthetic data with injected defects and realistic legitimate variation (three seeds), reconciliation finds every injected defect, and ledger-only detection finds 92% to 100% of each defect type. Ledger-only precision ranges from about 63% to 100% for invoice and payment defects, and is about 33% to 35% for labor allocation, which is a review aid rather than a verdict. See [docs/evaluation.md](docs/evaluation.md).

Synthetic results show the method works as designed; they are not a measure of real-world performance. Results from real implementations will be published as they are documented, with permission.

## Status and roadmap

Version 0.1. See [docs/roadmap.md](docs/roadmap.md).

## Contributing

Issues describing integration defects you have observed are especially welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
