# Methodology

## Why detection needs more than rules

When the source export is available, finding a defect is a comparison: the source says one thing, the ledger says another. That is the **reconciliation** mode.

Most of the time the source export is not available for past periods, or it has been overwritten. Then the corrupted record is the only evidence and there is no list to check it against. What remains is the record itself and its history: machine-generated entries follow strong patterns, and a defective entry departs from the pattern of its own customer, item, numbering sequence or engineer. That is the **ledger-only** mode.

## Mode 1: reconciliation

1. **Match invoices.** Exact document number first. Unmatched ledger invoices are paired with unmatched source invoices of the same customer and total, choosing the closest date within 60 days. A pair matched this way is an `IDENTIFIER` defect.
2. **Compare each pair** on terms, tax jurisdiction and date (flagging dates that cross an accounting period), and compare their lines: extra copies of a source line are `DUPLICATE_LINE`; a source tax line arriving as a non-tax line or in another account is `TAX_CLASSIFICATION`.
3. **Compare payments** by payment id: applied in the source but not in the ledger is `PAYMENT_UNAPPLIED`; applied to a different invoice is `PAYMENT_MISAPPLIED`.
4. **Compare time entries** by entry id: a different client or project is `LABOR_MISALLOCATION`.
5. **Consequences.** The summary also counts invoices paid in the source but open in the ledger, which is the direct business impact of payment defects.

## Mode 2: ledger only

| Check | Signal | Default threshold | Confidence |
| --- | --- | --- | --- |
| `IDENTIFIER` | Number format (`INV-99999`) used by few invoices | Under 5% of invoices | High |
| `TAX_CLASSIFICATION` | A tax item posted as a non-tax line or to a revenue account | Any occurrence | High |
| `DUPLICATE_LINE` | Identical line repeated in a document, for an item rarely repeated | Item repeated in 5% of its documents or fewer | High |
| `TAX_JURISDICTION` | Jurisdiction differs from the customer's usual one | Customer has 4+ invoices and a usual value in 60%+ of them | High at 85%+, else medium |
| `TERMS` | Terms differ from the customer's usual terms | Same as above | High at 85%+, else medium |
| `DATE` | Date far from the dates of invoices numbered around it | More than 15 days from the median of 5 neighbors on each side | High above 30 days, else medium |
| `PAYMENT_UNAPPLIED` | Payment with no invoice applied | Any; high if an open invoice of the same customer has exactly that amount | High or medium |
| `PAYMENT_MISAPPLIED` | Payment amount differs from its invoice but equals an open invoice of the same customer | Any occurrence | High |
| `LABOR_MISALLOCATION` | Engineer rarely records time for this client | Under 2% of the engineer's entries, engineer with 50+ entries | Medium |

All thresholds are parameters in `ledgerdrift/detect.py`.

### Known limits of ledger-only detection

* **Legitimate change looks like a defect.** A customer that renegotiates terms or moves to another county produces the same signal as a corrupted record. Findings are prompts for review, not verdicts.
* **Labor allocation is the weakest signal.** Engineers do occasionally work for clients outside their usual ones, so precision is low. It narrows hundreds of entries to a short list; a person decides.
* **New customers have no history.** Customer-pattern checks need at least four invoices.
* **Numbering checks assume one dominant format** assigned in date order, which is how most systems number invoices.

## Review queue (anomaly score)

An Isolation Forest is trained on the ledger's own invoices, without labels, using these features: rarity of the number format, deviation from usual terms and jurisdiction, distance from the dates of neighboring numbers, repeated identical lines, tax posted as revenue, size of the invoice relative to the customer's usual size, and number of lines. Each invoice gets a score; the highest scores are the first to review. The score catches records that are unusual on several signals at once, including combinations no single rule targets.

## How results are measured

`ledgerdrift evaluate` generates a synthetic year of records, copies them into a ledger, injects defects at known rates, and adds legitimate variation (renegotiated terms, a customer that moves, backdated invoices, items billed twice on purpose) to both source and ledger. Detection is scored against the injected labels. See [evaluation.md](evaluation.md).
