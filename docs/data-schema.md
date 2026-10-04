# Data schema and column mapping

Put one CSV per table in a folder (one folder for the ledger, another for the source if you have it). Missing tables are allowed; the checks that need them are skipped.

| Table | Columns |
| --- | --- |
| `invoices.csv` | `doc_number`, `customer`, `txn_date`, `terms`, `tax_jurisdiction`, `total` |
| `invoice_lines.csv` | `doc_number`, `line_no`, `item`, `line_type` (`service`, `product` or `tax`), `account`, `amount` |
| `payments.csv` | `payment_id`, `customer`, `txn_date`, `amount`, `applied_doc_number` (blank if unapplied) |
| `time_entries.csv` | `entry_id`, `engineer`, `client`, `project`, `work_date`, `hours` |

Dates in any format pandas can parse; amounts as plain numbers.

## Mapping your own column names

If your export uses other names, write a JSON file that maps each canonical column to your column, per table, and pass it with `--mapping`. Example (adjust to the exact headers of your export):

```json
{
  "invoices": {
    "doc_number": "Num",
    "customer": "Customer",
    "txn_date": "Date",
    "terms": "Terms",
    "tax_jurisdiction": "Tax Code",
    "total": "Amount"
  },
  "invoice_lines": {
    "doc_number": "Num",
    "item": "Product/Service",
    "account": "Account",
    "amount": "Amount"
  }
}
```

An example file is in [mapping-example.json](mapping-example.json).

## Anonymizing before sharing an example

If you share a sample to report a new defect type, replace customer names, engineers and document numbers with codes first. Never share transaction-level exports publicly.
