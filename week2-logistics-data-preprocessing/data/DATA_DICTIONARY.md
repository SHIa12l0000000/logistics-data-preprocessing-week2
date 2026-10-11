# Data dictionary (Week 2)

All packaged tabular data are **synthetic demonstration records**, not real deliveries.

## Raw transactions: `raw/sample_orders.csv`

- `Invoice`: string transaction / invoice identifier (an identifier, not a measure)
- `StockCode`: product reference code
- `Description`: item text, sometimes missing
- `Quantity`: transaction line units, can include negative returns or invalid values
- `InvoiceDate`: order/invoice timestamp
- `Price`: unit item price in the schema's native currency (GBP for the UCI reference)
- `Customer ID`: optional customer identifier (may be null)
- `Country`: optional customer country (may be null)

## Cleaned transactions: `processed/clean_transactions.csv`

Canonical column names include `invoice`, `stock_code`, `description`, `quantity`, `invoice_date`, `unit_price`, `customer_id`, `country`, plus flags including `description_missing`, `customer_missing`, `country_missing`, `zero_price_item` and `quantity_outlier_flag`. `line_value_gbp` is the quantity multiplied by unit price. `order_date` is date-normalized invoice time.

## Daily demand: `processed/daily_demand.csv`

- `order_date`: calendar day
- `units_sold`: total positive sale units from accepted transactions
- `order_lines`: count of accepted transaction lines
- `gross_line_value_gbp`: aggregate line monetary values before returns

## Train / test: `processed/model_train.csv`, `model_test.csv`

The daily dataset extended with `lag_1_units`, `lag_7_units`, `prior_7day_mean_units`, `day_of_week`, and scaled versions of the three lag features, with the scaler fitted only to training rows.

## Review folders

`review/duplicates_review.csv`, `review/returns_cancellations.csv`, and `review/rejected_review.csv` intentionally preserve separated records. Inspect them rather than treating removal as proof of invalidity in other datasets.
