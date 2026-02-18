import pandas as pd
import pyodbc
import numpy as np
from datetime import date

# ==== CONFIG ====
excel_path = r"F:\Congo_Supermarket\Congo_Supermarket\reference file\Share ITEM STOCK SUMMURY 01 OCT-30 NOV_2025.xlsx"
server = "DESKTOP-MTAR4PV"
database = "Congo Supermarket Data"
snapshot_date = date(2025, 11, 30)  # end of period
# =================

df = pd.read_excel(excel_path)
df.columns = df.columns.str.strip()

# Clean numeric columns
numeric_cols = ["Op Qty", "In Qty", "Sales Out Qty", "Other Out Qty", "Cl Qty"]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").round(4)

df = df.replace({np.nan: None})

# Compute outward quantity
df["outward_qty"] = (
    (df["Sales Out Qty"].fillna(0)) +
    (df["Other Out Qty"].fillna(0))
)

# SQL Connection
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()
cursor.fast_executemany = True

insert_query = """
INSERT INTO stock_snapshot (
    snapshot_date,
    warehouse_id,
    item_id,
    opening_qty,
    inward_qty,
    outward_qty,
    closing_qty
)
SELECT ?, w.warehouse_id, i.item_id, ?, ?, ?, ?
FROM warehouses w
JOIN items i ON i.part_no = ?
WHERE w.warehouse_name = ?
"""

data = []

for _, row in df.iterrows():
    data.append((
        snapshot_date,
        row["Op Qty"],
        row["In Qty"],
        row["outward_qty"],
        row["Cl Qty"],
        row["Part No"],
        row["Warehouse Name"]
    ))

cursor.executemany(insert_query, data)
conn.commit()

cursor.close()
conn.close()

print("Stock snapshot loaded successfully!")
