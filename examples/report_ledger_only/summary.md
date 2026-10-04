# Integration integrity summary (ledger only)

Run 2026-10-04 with ledgerdrift 0.1.0. Aggregate counts only.

| Records processed | Count |
| --- | --- |
| invoices | 445 |
| invoice lines | 1441 |
| payments | 380 |
| time entries | 2800 |

| Defect | Records flagged | Meaning |
| --- | --- | --- |
| IDENTIFIER | 15 | Document number does not match the source, or breaks the ledger's own numbering pattern |
| TAX_CLASSIFICATION | 14 | Sales tax recorded as a revenue line instead of a tax liability |
| DUPLICATE_LINE | 22 | The same line appears twice in one document |
| TAX_JURISDICTION | 19 | Tax assigned to a different county or state |
| DATE | 15 | Document date differs from the source or from its place in the numbering sequence |
| TERMS | 20 | Payment terms differ from the source or from the customer's usual terms |
| PAYMENT_UNAPPLIED | 13 | Payment recorded without being applied to its invoice |
| PAYMENT_MISAPPLIED | 8 | Payment applied to the wrong invoice |
| LABOR_MISALLOCATION | 187 | Time entry assigned to a different client or project |
