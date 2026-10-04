# Privacy

`ledgerdrift` is designed so that the organization that owns the books keeps full control of its data.

1. **Local only.** The tool reads CSV files from disk and writes reports to disk. It makes no network calls.
2. **Two levels of output.**
   * Record level, private: `findings.csv`, `review_queue.csv`. They contain document numbers and are for the organization's own review.
   * Aggregate level, shareable: `summary.json`, `summary.md`, and rows appended to the discrepancy log. They contain counts by defect type and records processed, and nothing that identifies a transaction, customer, person or amount. A test in the suite enforces this.
3. **Anonymous environments.** The discrepancy log identifies each environment by a code you choose (`E01`, `E02`), never by name.
4. **No transactional content is stored** by the tool beyond the reports you ask it to write.

If you implement the method for a third party, agree in writing on what you may see and keep only the aggregate summary.
