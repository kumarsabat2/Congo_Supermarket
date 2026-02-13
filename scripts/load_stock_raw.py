import pandas as pd
import pyodbc
import numpy as np

# ==== CONFIG ====
excel_path = r"F:\Congo_Supermarket\Congo_Supermarket\reference file\Share ITEM STOCK SUMMURY 01 OCT-30 NOV_2025.xlsx"
server = "DESKTOP-MTAR4PV"
database = "Congo Supermarket Data"
# =================

df = pd.read_excel(excel_path)
df.columns = df.columns.str.strip()

# Clean numeric columns
numeric_cols = [
    "Op Qty", "In Qty",
    "Sales Out Qty", "Other Out Qty",
    "Cl Qty"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(4)

df = df.replace({np.nan: None})

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()
cursor.fast_executemany = True

insert_query = """
INSERT INTO stock_raw (
    store_name,
    warehouse_name,
    stock_category,
    stock_group,
    part_no,
    item_name,
    uom,
    rate,
    op_qty,
    in_qty,
    sales_out_qty,
    other_out_qty,
    cl_qty
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

data = []

for _, row in df.iterrows():
    data.append((
        row.get("Store Name"),
        row.get("Warehouse Name"),
        row.get("Stock Category"),
        row.get("Stock Group"),
        str(row.get("Part No")).strip() if row.get("Part No") else None,
        row.get("Item Name"),
        row.get("UOM"),
        row.get("Rate"),
        row.get("Op Qty"),
        row.get("In Qty"),
        row.get("Sales Out Qty"),
        row.get("Other Out Qty"),
        row.get("Cl Qty")
    ))

cursor.executemany(insert_query, data)
conn.commit()

cursor.close()
conn.close()

print("Stock raw data loaded successfully!")
