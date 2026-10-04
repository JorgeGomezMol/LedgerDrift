# Changelog

## 0.1.1

- Infer the line type (sale or tax) when an export has no such column, as most accounting exports do. Without it, tax lines from real exports could be flagged incorrectly.
- Number invoice lines automatically when the export has no line number.

## 0.1.0

First public version: canonical schema and mapping, reconciliation and ledger-only detection for nine defect types, unsupervised review queue, synthetic data generator, aggregate summaries and discrepancy log.
