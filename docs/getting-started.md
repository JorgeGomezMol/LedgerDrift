# Getting started: a step-by-step guide for accountants

This guide is for bookkeepers, accountants and business owners who have never used Python. It takes about an hour the first time. Everything runs on your own computer: no data is uploaded anywhere.

## What you need

* A Windows or Mac computer where you are allowed to install software.
* Exports (CSV or Excel saved as CSV) from your accounting system for the period you want to review. Three to twelve months is a good start.

## Step 1. Install Python (once)

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest Python 3 installer.
2. Run it. **On Windows, check the box "Add python.exe to PATH"** on the first screen, then click *Install Now*.
3. To confirm it worked, open a terminal (Windows: press the Windows key, type `cmd`, press Enter; Mac: open *Terminal*) and type:

   ```
   python --version
   ```

   You should see `Python 3.10` or newer. On a Mac, if `python` is not found, use `python3` in every command below.

## Step 2. Download LedgerDrift (once)

1. Open [github.com/JorgeGomezMol/LedgerDrift](https://github.com/JorgeGomezMol/LedgerDrift).
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip it somewhere easy to find, for example `Documents\LedgerDrift`.

## Step 3. Install it (once)

In the terminal, go to the folder you unzipped and install:

```
cd Documents\LedgerDrift
python -m pip install .
```

(On a Mac: `cd Documents/LedgerDrift`.) The installation takes a minute or two.

## Step 4. Try it on sample data first

Before using your own records, run it on the built-in sample, which contains deliberately planted errors:

```
python -m ledgerdrift synth --out demo --seed 7
python -m ledgerdrift audit --ledger demo/ledger --out demo/report
```

Open `demo/report/summary.md` (any text editor works) to see what a result looks like. If you got this far, the tool is working.

## Step 5. Export your own records

Create a folder, for example `my-review/ledger`, and save up to four CSV files in it with these exact names:

| File | One row per | Minimum columns |
| --- | --- | --- |
| `invoices.csv` | invoice | number, customer, date, terms, tax code or jurisdiction, total |
| `invoice_lines.csv` | invoice line | invoice number, product/service, account, amount |
| `payments.csv` | customer payment | payment ID, customer, date, amount, invoice it was applied to |
| `time_entries.csv` | time entry (if you bill labor) | entry ID, technician, client, project, date, hours |

You do not need all four. Invoices and invoice lines alone already allow most checks. Most accounting systems can produce these as reports exported to CSV; the column names do not need to match, because the next step tells the tool what each column means.

If you also have exports from the platform that sends data to your accounting system (your PSA, POS, store or dealer system), save them in a second folder, `my-review/source`, with the same file names. The tool then compares record by record, which is the most precise mode.

## Step 6. Tell the tool what your columns are called

Copy `docs/mapping-example.json` to `my-review/mapping.json` and edit it in a text editor so that, for each file, every name on the left points to the exact header in your CSV on the right. Details and an example: [data-schema.md](data-schema.md).

## Step 7. Run the review

```
python -m ledgerdrift audit --ledger my-review/ledger --mapping my-review/mapping.json --out my-review/report
```

Add `--source my-review/source` if you saved platform exports in Step 5.

## Step 8. Read the results

The `my-review/report` folder contains:

| File | What it is | Share it? |
| --- | --- | --- |
| `summary.md` and `summary.json` | Counts by defect type. No names, numbers or amounts | Yes, if you want to |
| `findings.csv` | Every flagged record and why it was flagged | **No. Keep it private** |
| `review_queue.csv` | Invoices ranked by how unusual they look | **No. Keep it private** |

A flag is not a verdict. Open `findings.csv` in Excel, look at each flagged record in your books, and add a column `confirmed` with `yes` or `no`. The errors you confirm are the real result of the review; the rest are records that looked unusual but were correct.

## If something goes wrong

* **`python` is not recognized** (Windows): Python was installed without "Add to PATH". Run the installer again, choose *Modify*, and enable that option, or reinstall with the box checked.
* **`No module named ledgerdrift`**: you are not in the LedgerDrift folder, or Step 3 did not finish. Repeat Step 3.
* **The summary shows zero records, or a check finds nothing at all**: a name in `mapping.json` probably does not exactly match a header in your CSV, so that column was read as empty. Check spelling, spaces and capital letters, and that the file names in Step 5 are exact.
* Anything else: open an issue on GitHub describing the error message, **without** attaching your data.
