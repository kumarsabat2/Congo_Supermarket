import streamlit as st
import pandas as pd
import pyodbc
import base64
import plotly.express as px
from io import BytesIO

# ---------------------------------------------------
# Page Config
# ---------------------------------------------------
st.set_page_config(layout="wide")

# ---------------------------------------------------
# Black Theme Styling
# ---------------------------------------------------
st.markdown("""
    <style>
        .stApp {
            background-color: #111111;
            color: white;
        }
        h1, h2, h3, h4 {
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# Database Connection
# ---------------------------------------------------
def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=DESKTOP-MTAR4PV;"
        "DATABASE=Congo Supermarket Data;"
        "Trusted_Connection=yes;"
    )

# ---------------------------------------------------
# Background (30% Visibility)
# ---------------------------------------------------
def set_background(image_file):
    with open(image_file, "rb") as file:
        encoded = base64.b64encode(file.read()).decode()

    page_bg_img = f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(255,255,255,0.5),
                                     rgba(255,255,255,0.5)),
                    url("data:image/webp;base64,{encoded}");
        background-size: cover;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

set_background("app/assets/OIP.webp")

st.markdown("""
    <h1 style='text-align: center; color: black;'>
    🏬 HO Inventory Planning Dashboard
    </h1>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------
st.sidebar.header("Planning Controls")

period_days = st.sidebar.number_input("Historical Period Days", value=61)
planning_days = st.sidebar.number_input("Planning Days", value=45)
min_order_filter = st.sidebar.number_input("Minimum Order Qty Filter", value=0)
sku_search = st.sidebar.text_input("Search SKU")
run_button = st.sidebar.button("Run Planning")

if "run_planning" not in st.session_state:
    st.session_state.run_planning = False

if run_button:
    st.session_state.run_planning = True

# ---------------------------------------------------
# SQL Query Function
# ---------------------------------------------------
def load_data(period_days, planning_days):
    query = f"""
    WITH ho_data AS (
        SELECT
            sr.part_no,
            MAX(sr.item_name) AS item_name,
            SUM(ISNULL(sr.cl_qty,0)) AS ho_current_stock,
            SUM(ISNULL(sr.sales_out_qty,0) + ISNULL(sr.other_out_qty,0)) AS total_consumption
        FROM stock_raw sr
        WHERE sr.store_name = 'HO'
        GROUP BY sr.part_no
    ),

    ho_requirement AS (
        SELECT
            h.part_no,
            h.item_name,
            h.ho_current_stock,
            CEILING(
                ((h.total_consumption / {period_days}) * {planning_days})
                - h.ho_current_stock
            ) AS ho_order_qty
        FROM ho_data h
    ),

    central_stock AS (
        SELECT
            i.part_no,
            ss.closing_qty AS central_current_stock
        FROM stock_snapshot ss
        JOIN items i ON ss.item_id = i.item_id
        WHERE ss.warehouse_id = 1
    )

    SELECT
        hr.part_no,
        hr.item_name,
        hr.ho_current_stock,
        hr.ho_order_qty,

        CASE 
            WHEN hr.ho_order_qty > 0 THEN 'REORDER_REQUIRED'
            ELSE 'SUFFICIENT_STOCK'
        END AS ho_status,

        ISNULL(cs.central_current_stock,0) AS central_current_stock,

        CASE
            WHEN (ISNULL(cs.central_current_stock,0) - hr.ho_order_qty) < 0
            THEN ABS(ISNULL(cs.central_current_stock,0) - hr.ho_order_qty)
            ELSE 0
        END AS central_purchase_qty,

        CASE
            WHEN (ISNULL(cs.central_current_stock,0) - hr.ho_order_qty) < 0
            THEN 'PURCHASE_REQUIRED'
            ELSE 'CENTRAL_SUFFICIENT'
        END AS central_status

    FROM ho_requirement hr
    LEFT JOIN central_stock cs
        ON hr.part_no = cs.part_no
    WHERE hr.ho_order_qty > 0
    ORDER BY hr.ho_order_qty DESC
    """

    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df


# ---------------------------------------------------
# Run Planning
# ---------------------------------------------------
if st.session_state.run_planning:

    df = load_data(period_days, planning_days)

    if sku_search:
        df = df[df["part_no"].str.contains(sku_search, case=False)]

    df = df[df["ho_order_qty"] >= min_order_filter]

    # ---------------- Metrics ----------------
    col1, col2, col3 = st.columns(3)
    col1.metric("SKUs Needing Reorder", len(df))
    col2.metric("Total HO Order Qty", int(df["ho_order_qty"].sum()))
    col3.metric("Central Purchase Required", int(df["central_purchase_qty"].sum()))

    # ---------------- Top 10 Chart ----------------
    st.subheader("Top 10 Risk SKUs")
    top10 = df.sort_values("ho_order_qty", ascending=False).head(10)

    fig = px.bar(
        top10,
        x="part_no",
        y="ho_order_qty",
        color="ho_order_qty",
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------- Status Coloring ----------------
    def highlight_status(val):
        if val == "REORDER_REQUIRED":
            return "background-color: #ff4d4d; color: white;"
        elif val == "PURCHASE_REQUIRED":
            return "background-color: #ff9900; color: white;"
        elif val == "CENTRAL_SUFFICIENT":
            return "background-color: #4CAF50; color: white;"
        return ""

    styled_df = df.style.applymap(
        highlight_status,
        subset=["ho_status", "central_status"]
    )

    # ---------------- Table ----------------
    st.subheader("Detailed Replenishment Plan")
    st.dataframe(styled_df, use_container_width=True)

    # ---------------- Excel Export ----------------
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Replenishment')
        return output.getvalue()

    excel_data = convert_df_to_excel(df)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name="HO_Replenishment_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
