# Evaluation on synthetic data

Run: `ledgerdrift evaluate --seed <n>`. Each run generates about 430 invoices, 380 payments and 2,800 time entries for 40 customers over 12 months; about 22% of invoices carry one injected defect, and about 4% carry legitimate variation that is not a defect.

## Reconciliation mode

Seeds 7, 11 and 23: every injected defect found, with no false positives, for all nine defect types (precision and recall 1.0).

## Ledger-only mode

| Defect | Recall (seeds 7 / 11 / 23) | Precision (seeds 7 / 11 / 23) |
| --- | --- | --- |
| IDENTIFIER | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| TAX_CLASSIFICATION | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| DUPLICATE_LINE | 1.00 / 1.00 / 1.00 | 0.86 / 0.87 / 0.69 |
| TAX_JURISDICTION | 1.00 / 1.00 / 1.00 | 0.68 / 0.63 / 0.69 |
| DATE | 1.00 / 0.95 / 1.00 | 0.87 / 0.79 / 0.89 |
| TERMS | 0.93 / 0.96 / 1.00 | 0.65 / 0.90 / 1.00 |
| PAYMENT_UNAPPLIED | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| PAYMENT_MISAPPLIED | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| LABOR_MISALLOCATION | 0.93 / 0.95 / 0.97 | 0.33 / 0.35 / 0.35 |

Review queue (anomaly score over invoices): ROC AUC 0.966 / 0.972 / 0.983.

## What these numbers do and do not show

* They show that each check detects the behavior it was designed for, and how much legitimate variation costs in false positives.
* They do **not** measure real-world performance. Real ledgers carry more kinds of legitimate variation and messier exports. Real-world results will be reported separately, from documented implementations, with permission, and only as aggregate counts.
