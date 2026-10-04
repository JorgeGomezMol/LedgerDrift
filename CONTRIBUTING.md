# Contributing

Thank you for helping make financial records more reliable.

## Most useful contributions

1. **Defect reports.** You have seen an integration change a record. Open an issue with the dimension (identifier, classification, tax, timing, terms, payment, labor or a new one), an anonymized before-and-after example, and the consequence.
2. **Export mappings.** A mapping file for an export format the tool does not cover yet.
3. **Detection improvements** with a test and a before-and-after `ledgerdrift evaluate` result.

## Rules

- Never attach real transaction data. Anonymize first (see [docs/data-schema.md](docs/data-schema.md)).
- Describe observed behavior, not vendor intent or quality.
- Run `pytest` before opening a pull request.
