"""Week 2 logistics transaction data cleaning and preprocessing demonstration.

Usage:
    python week2_preprocess.py --input data/raw/sample_orders.csv --output outputs
    python week2_preprocess.py --input data/raw/online_retail_II.xlsx --output outputs_uci

Uses the historical UCI Online Retail II schema (Invoice, StockCode, Description,
Quantity, InvoiceDate, Price, Customer ID, Country). Accepts renamed columns from
newer mirrors (InvoiceNo, UnitPrice, CustomerID). The provided CSV is synthetic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

CANONICAL = {
    "invoice": "invoice",
    "invoiceno": "invoice",
    "stockcode": "stock_code",
    "description": "description",
    "quantity": "quantity",
    "invoicedate": "invoice_date",
    "price": "unit_price",
    "unitprice": "unit_price",
    "customerid": "customer_id",
    "country": "country",
}
REQUIRED = ["invoice", "stock_code", "invoice_date", "quantity", "unit_price"]
FULL_ROW_FIELDS = ["invoice", "stock_code", "description", "quantity",
                   "invoice_date", "unit_price", "customer_id", "country"]


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, low_memory=False)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str)
        return pd.concat(sheets.values(), ignore_index=True)
    raise ValueError("Supported input formats: .csv, .xlsx, .xls")


def standardize_schema(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    keys = {c: "".join(char.lower() for char in str(c) if char.isalnum())
            for c in df.columns}
    df = df.rename(columns={c: CANONICAL[key] for c, key in keys.items()
                            if key in CANONICAL})
    if df.columns.duplicated().any():
        raise ValueError("Input contains multiple columns mapped to the same field")
    absent = sorted(set(REQUIRED) - set(df.columns))
    if absent:
        raise ValueError(f"Missing required columns: {absent}")
    for optional in set(FULL_ROW_FIELDS) - set(df.columns):
        df[optional] = pd.NA

    # Identifiers are categories: do not convert to numeric and lose leading zeros.
    for col in ["invoice", "stock_code", "description", "customer_id", "country"]:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    df["country"] = df["country"].str.title()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce", format="mixed")
    return df


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")


def run(input_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = load_data(input_path)
    df = standardize_schema(raw)
    raw_count = len(df)
    missing_before = {k: int(df[k].isna().sum()) for k in FULL_ROW_FIELDS}

    # Exact normalized row duplicates may be unsafe to remove in real data
    # without a source line ID. For this demonstrator, retain one copy.
    dupe_mask = df.duplicated(subset=FULL_ROW_FIELDS, keep="first")
    duplicates = df[dupe_mask].copy()
    write_csv(duplicates, output_dir / "duplicates_review.csv")
    df = df[~dupe_mask].copy()

    # Move documented cancellations / returns to a separate dataset.
    cancelled = df["invoice"].fillna("").str.upper().str.startswith("C")
    returned = df["quantity"] < 0
    is_return = cancelled | returned
    return_rows = df[is_return].copy()
    return_rows["issue"] = np.where(cancelled[is_return], "cancellation_invoice", "negative_quantity_return")
    write_csv(return_rows, output_dir / "returns_cancellations.csv")
    df = df[~is_return].copy()

    # Essential missing values cannot be safely invented; invalid numeric
    # values need review. Zero-price promotional items are kept and flagged.
    invalid_core = df[REQUIRED].isna().any(axis=1)
    invalid_numeric = (df["quantity"] <= 0) | (df["unit_price"] < 0)
    invalid_mask = invalid_core | invalid_numeric
    rejected = df[invalid_mask].copy()
    rejected["issue"] = np.select(
        [invalid_core[invalid_mask], invalid_numeric[invalid_mask]],
        ["missing_or_invalid_critical_field", "invalid_quantity_or_price"],
        default="review",
    )
    write_csv(rejected, output_dir / "rejected_review.csv")
    clean = df[~invalid_mask].copy()

    # Missing descriptions are represented by a label; missing customer IDs
    # stay missing (never fake a customer identity).
    clean["description_missing"] = clean["description"].isna()
    clean["customer_missing"] = clean["customer_id"].isna()
    clean["country_missing"] = clean["country"].isna()
    clean["description"] = clean["description"].fillna("UNSPECIFIED ITEM")
    clean["country"] = clean["country"].fillna("Unknown")
    clean["zero_price_item"] = clean["unit_price"].eq(0)
    clean["line_value_gbp"] = clean["quantity"] * clean["unit_price"]
    clean["order_date"] = clean["invoice_date"].dt.normalize()

    # IQR is a review flag, not a removal instruction: true wholesale orders
    # can be unusually large, and retaining original quantity avoids bias.
    q1, q3 = clean["quantity"].quantile([0.25, 0.75])
    upper_fence = float(q3 + 1.5 * (q3 - q1))
    clean["quantity_outlier_flag"] = clean["quantity"] > upper_fence
    clean = clean.sort_values(["invoice_date", "invoice", "stock_code"])
    write_csv(clean, output_dir / "clean_transactions.csv")

    daily = clean.groupby("order_date", as_index=True).agg(
        units_sold=("quantity", "sum"),
        order_lines=("invoice", "size"),
        gross_line_value_gbp=("line_value_gbp", "sum"),
    ).sort_index()
    # Fill absent calendar days with 0 for a *complete extract*. Check source
    # coverage before interpreting zeros as no trading activity.
    daily = daily.asfreq("D", fill_value=0)
    daily.index.name = "order_date"
    write_csv(daily.reset_index(), output_dir / "daily_demand.csv")

    features = daily.copy()
    features["lag_1_units"] = features["units_sold"].shift(1)
    features["lag_7_units"] = features["units_sold"].shift(7)
    features["prior_7day_mean_units"] = features["units_sold"].shift(1).rolling(7).mean()
    features["day_of_week"] = features.index.dayofweek
    features = features.dropna(subset=["lag_1_units", "lag_7_units", "prior_7day_mean_units"])
    feature_names = ["lag_1_units", "lag_7_units", "prior_7day_mean_units"]
    split_at = int(len(features) * 0.8)
    if len(features) < 8 or not (0 < split_at < len(features)):
        raise ValueError("At least 15 calendar days required for the lagged train/test demonstration")
    train, test = features.iloc[:split_at].copy(), features.iloc[split_at:].copy()
    scaler = RobustScaler()
    train[[f"scaled_{x}" for x in feature_names]] = scaler.fit_transform(train[feature_names])
    test[[f"scaled_{x}" for x in feature_names]] = scaler.transform(test[feature_names])
    write_csv(train.reset_index(), output_dir / "model_train.csv")
    write_csv(test.reset_index(), output_dir / "model_test.csv")

    report = {
        "source": str(input_path),
        "dataset_kind": "synthetic_demonstration" if "sample_orders" in input_path.name else "user_supplied",
        "raw_rows": int(raw_count),
        "exact_duplicate_rows_for_review": int(len(duplicates)),
        "returns_and_cancellations_separated": int(len(return_rows)),
        "invalid_rows_separated": int(len(rejected)),
        "clean_transaction_rows": int(len(clean)),
        "missing_values_before_cleaning": missing_before,
        "missing_customer_ids_in_clean_data": int(clean["customer_missing"].sum()),
        "missing_country_imputed_unknown": int(clean["country_missing"].sum()),
        "missing_description_labeled": int(clean["description_missing"].sum()),
        "zero_price_items_flagged": int(clean["zero_price_item"].sum()),
        "quantity_iqr_upper_fence": round(upper_fence, 2),
        "quantity_iqr_outlier_flags": int(clean["quantity_outlier_flag"].sum()),
        "daily_rows_with_calendar_zeros": int(len(daily)),
        "chronological_train_days": int(len(train)),
        "chronological_test_days": int(len(test)),
        "scaler": "RobustScaler fitted only on chronological training features",
        "train_feature_medians": dict(zip(feature_names, [round(float(x), 3) for x in scaler.center_])),
        "train_feature_iqr_scales": dict(zip(feature_names, [round(float(x), 3) for x in scaler.scale_])),
    }
    (output_dir / "quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Week 2 logistics preprocessing pipeline")
    parser.add_argument("--input", type=Path, default=Path("data/raw/sample_orders.csv"))
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    run(args.input, args.output)
