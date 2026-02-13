import pandas as pd
import pyodbc
import numpy as np

# ==== CONFIG ====
excel_path = r"F:\Congo_Supermarket\Congo_Supermarket\reference file\Share Daily Sales Report (1-30 Nov)_HO LOCATION ONLY.xlsx"
server = "DESKTOP-MTAR4PV"
database = "Congo Supermarket Data"
branch_id = 1
# =================

df = pd.read_excel(excel_path)
df.columns = df.columns.str.strip()

# Clean date
df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")

# Clean numeric fields
df["Total Qty"] = pd.to_numeric(df["Total Qty"], errors="coerce").round(4)
df["Net Amount"] = pd.to_numeric(df["Net Amount"], errors="coerce").round(4)

df = df.replace({np.nan: None})

# SQL Connection
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Trusted_Connection=yes;"
)

cursor = conn.cursor()

# Insert query (join with items using part_no)
insert_query = """
INSERT INTO sales_daily (sale_date, branch_id, item_id, quantity_sold, revenue)
SELECT ?, ?, item_id, ?, ?
FROM items
WHERE part_no = ?
"""

for _, row in df.iterrows():
    cursor.execute(insert_query,
        row["Transaction Date"],
        branch_id,
        row["Total Qty"],
        row["Net Amount"],
        row["Part No."]
    )

conn.commit()
cursor.close()
conn.close()

print("Sales data loaded successfully!")
