# Taxonomy of integration defects

A defect is any change an automated synchronization makes to a record between the operational platform (the source) and the accounting system (the ledger) that the source did not intend. Every defect below was first documented as observed behavior in a production integration between a professional services automation platform and an accounting system, across multiple client environments. The descriptions are of behavior, not of any vendor's intent or quality.

What makes these defects dangerous is that they are **silent**: totals still balance, entries exist, and the integration reports success.

## Dimensions of the accounting record

| Dimension | Defect code | Example | Consequence |
| --- | --- | --- | --- |
| Identifier | `IDENTIFIER` | Source `INV-10045` arrives as `10045` or `INV-10045-1` | Records cannot be traced; duplicates go unnoticed |
| Classification | `TAX_CLASSIFICATION` | The sales tax line posts to *Services Revenue* instead of *Sales Tax Payable* | Revenue overstated; tax liability understated |
| Classification | `DUPLICATE_LINE` | One service line appears twice | Revenue and receivables overstated |
| Tax calculation | `TAX_JURISDICTION` | Tax assigned to another county or state | State tax returns prepared on incorrect data |
| Timing | `DATE` | Invoice dated 30 days earlier than in the source | Period cut-off errors |
| Commercial terms | `TERMS` | Net 30 changed to due on receipt | Distorted receivables aging and collection activity |
| Payments | `PAYMENT_UNAPPLIED` | Payment recorded but not applied to its invoice | Paid invoices remain open; risk of billing a customer who already paid |
| Payments | `PAYMENT_MISAPPLIED` | Payment applied to a different invoice of the same customer | Two invoices wrong at once |
| Labor cost | `LABOR_MISALLOCATION` | A time entry assigned to another client or project | False project and client profitability, used for pricing and renewals |

## Why each dimension matters beyond one company

* **Identifiers** are what auditors, reviewers and tax examiners use to trace a transaction. A broken identifier turns a routine sample into an investigation.
* **Classification** errors change reported revenue and liabilities without changing the invoice total, so a review that only checks totals cannot see them.
* **Tax jurisdiction** errors flow directly into state sales tax returns.
* **Timing** errors move revenue between periods, which affects monthly, quarterly and annual reporting.
* **Terms** errors distort cash-flow forecasting and trigger collection activity against customers who are not late.
* **Payment** errors corrupt accounts receivable, the asset small businesses depend on most.
* **Labor** errors falsify the cost side of service businesses, where pricing and contract renewals are decided on project profitability.

## Extending the taxonomy

New defect types are added when they are observed in at least one real environment and can be described as a change between source and ledger. Open an issue with the dimension, an anonymized example and the consequence.
