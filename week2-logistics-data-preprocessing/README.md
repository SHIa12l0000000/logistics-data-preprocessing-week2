# Week 2: Logistics Data Collection, Cleaning & Preprocessing

**Python Data Science Internship — Week 2 Assignment**  
**Student:** Bedi Shivam Jagjeet  
**Status:** Week 2 assignment with executable, verified synthetic-data demonstration

## Overview

This repository contains the complete Week 2 deliverables for a logistics analytics project, continuing the last-mile e-commerce demand-planning scenario from Week 1. It demonstrates data collection, schema checks, missing-value handling, duplicate identification, returns/cancellations review, invalid-record handling, outlier detection, daily aggregation, and train/test-safe normalization.

The **reference source** is the UCI Online Retail II dataset, while **all CSV data included in this repository is synthetic**. No business delivery records or GPS traces are implied.

## Contents

| Path | Contents |
| --- | --- |
| `report/Week2_Logistics_Data_Collection_Cleaning_Preprocessing.docx` | Comprehensive Word report for internship upload |
| `src/week2_preprocess.py` | Executable and documented Pandas/Scikit-learn pipeline |
| `requirements.txt` | Python packages needed to run the code |
| `data/raw/sample_orders.csv` | Synthetic input transactions (81 rows) |
| `data/processed/clean_transactions.csv` | Accepted, cleaned transactions |
| `data/processed/daily_demand.csv` | Daily time-series aggregation |
| `data/processed/model_train.csv`, `model_test.csv` | Chronological modeling datasets with training-only fitted scaling |
| `data/review/` | Removed duplicates, returns, cancellations, and invalid records retained for auditing |
| `reports/quality_report.json` | Machine-readable data quality audit results |
| `figures/` | Pipeline workflow and quality audit visualizations |

## Setup and run

Requirements: Python 3.10+ recommended, with Internet access during the initial dependency installation.

```bash
python -m pip install -r requirements.txt
python src/week2_preprocess.py --input data/raw/sample_orders.csv --output run_outputs
```

Windows: you can use `py` in place of `python` if necessary.

The `run_outputs/` folder will be created automatically. Its contents should match the packaged audit outputs when using the same sample dataset and compatible dependency versions.

## Verified example results

The supplied Python script was executed against the included sample input. Counts refer **only to synthetic demonstration data**.

| Audit metric | Result |
| --- | ---: |
| Raw records | 81 |
| Exact duplicate copies separated | 2 |
| Returns and cancellations separated | 3 |
| Missing/invalid critical records separated | 6 |
| Final accepted transaction records | 70 |
| Quantity IQR outliers *flagged* (not discarded) | 1 |
| Daily time-series length | 35 days |
| Model training examples | 22 days |
| Model test examples | 6 days |

Retained examples are not real business outcomes. Outlier flags do not prove errors. Missing customer IDs are retained as missing; missing descriptions and country values are labeled rather than inventing identities. Review subsets remain accessible for auditability.

## Technique and data leakage notes

- **Schema / types:** normalize UCI-style column names, parse timestamps and numeric values.
- **Duplicates:** isolate exact repeated rows for manual review; in production, use stable source row IDs to determine whether repeated order lines are legitimate.
- **Missing data:** separate records missing required fields; keep optional customer IDs missing, label missing description/country.
- **Returns / cancellations:** treat separately so that demand measures describe positive sales only.
- **Outliers:** IQR-based quantities are *flagged*, not automatically deleted; high-volume orders can be genuine.
- **Aggregation:** aggregate daily positive units; missing days are filled with zeros **only if** the extract covers the complete period.
- **Feature scaling:** generate lag-1, lag-7 and trailing seven-day mean features, sort chronologically, split training/test data by time, then fit `RobustScaler` only on training features to avoid leakage.

## Reference and limitations

UCI Online Retail II by Daqing Chen: https://archive.ics.uci.edu/dataset/502/online+retail+ii  
DOI: https://doi.org/10.24432/C5CG6D

The original publicly hosted UCI dataset is **not included in this ZIP**. It may be downloaded separately from its source, subject to its terms; the sample is sufficient to run and verify the coursework. Transaction data alone cannot establish shipment travel times, on-time delivery rates, distance savings, or vehicle routing performance.

To try a compatible UCI `.xlsx` input after downloading it:

```bash
python src/week2_preprocess.py --input data/raw/online_retail_II.xlsx --output run_uci
```

The workbook may require significant memory, and a data-quality audit is necessary before using the outputs for operational decisions.

## Internship submission

1. Upload the `.docx` from the `report/` folder to the internship form.
2. Upload the **extracted project files and folders**, not just the ZIP, to a GitHub repository. GitHub does not extract ZIPs automatically.
3. Paste the GitHub repository URL into the technical project field, after confirming the files are visible.
