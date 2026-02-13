import pandas as pd
import pyodbc

# ==== CONFIG ====
server = "DESKTOP-MTAR4PV"
database = "Congo Supermarket Data"
branch_id = 1
# =================

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)

query = f"""
SELECT 
    sale_date,
    item_id,
    quantity_sold
FROM sales_daily
WHERE branch_id = {branch_id}
"""

df = pd.read_sql(query, conn)
conn.close()
df["sale_date"] = pd.to_datetime(df["sale_date"])
print("Raw sales shape:", df.shape)
#print(df.head())
# Aggregate to daily SKU level
df_daily = (
    df.groupby(["sale_date", "item_id"], as_index=False)
      .agg({"quantity_sold": "sum"})
)

print("After aggregation:", df_daily.shape)
#print(df_daily.head())
import numpy as np

# Create full date range
date_range = pd.date_range(
    start=df_daily["sale_date"].min(),
    end=df_daily["sale_date"].max(),
    freq="D"
)

# Get unique SKUs
unique_items = df_daily["item_id"].unique()

# Create full cartesian product
full_index = pd.MultiIndex.from_product(
    [unique_items, date_range],
    names=["item_id", "sale_date"]
)

df_full = pd.DataFrame(index=full_index).reset_index()

# Merge with actual sales
df_full = df_full.merge(
    df_daily,
    on=["item_id", "sale_date"],
    how="left"
)

# Fill missing demand with 0
df_full["quantity_sold"] = df_full["quantity_sold"].fillna(0)

print("Full time series shape:", df_full.shape)
print(df_full.head())
from prophet import Prophet

# Pick one SKU
test_item = df_full["item_id"].iloc[0]

df_sku = df_full[df_full["item_id"] == test_item].copy()

# Rename columns for Prophet
df_sku = df_sku.rename(columns={
    "sale_date": "ds",
    "quantity_sold": "y"
})
# Split train/test
train = df_sku[df_sku["ds"] <= "2025-11-23"]
test = df_sku[df_sku["ds"] > "2025-11-23"]

print("Train size:", len(train))
print("Test size:", len(test))

print(df_sku.head())
model = Prophet(
    yearly_seasonality=False,
    weekly_seasonality=True,
    daily_seasonality=False
)

model.fit(train)

future = model.make_future_dataframe(periods=7)
forecast = model.predict(future)

forecast_test = forecast[forecast["ds"].isin(test["ds"])]

# Merge actual vs predicted
comparison = test.merge(
    forecast_test[["ds", "yhat"]],
    on="ds",
    how="left"
)

print(comparison)
import numpy as np

comparison["error"] = abs(comparison["y"] - comparison["yhat"])
comparison["ape"] = np.where(
    comparison["y"] == 0,
    0,
    comparison["error"] / comparison["y"]
)

mape = comparison["ape"].mean() * 100

print("MAPE:", round(mape, 2), "%")

