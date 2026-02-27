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
# Initialize Session State
# ---------------------------------------------------
if "run" not in st.session_state:
    st.session_state.run = False

if "df" not in st.session_state:
    st.session_state.df = None
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

# Only run planning when button is clicked for the FIRST time
if "run" not in st.session_state:
    st.session_state.run = False

run_button = st.sidebar.button("Run Planning")

# ---------------------------------------------------
# Initialize Session State
# ---------------------------------------------------
if "run" not in st.session_state:
    st.session_state.run = False

if "df" not in st.session_state:
    st.session_state.df = None
# ---------------------------------------------------
# SQL Query Function
# ---------------------------------------------------
def load_data(period_days, planning_days):
    query = f"""
    WITH ho_data AS (
        SELECT
            sr.part_no,
            MAX(sr.item_name) AS item_name,
            MAX(i.stock_category) AS stock_category,
            SUM(ISNULL(sr.cl_qty,0)) AS ho_current_stock,
            SUM(ISNULL(sr.sales_out_qty,0)) AS total_sales_qty,
            SUM(ISNULL(sr.other_out_qty,0)) AS total_loss_qty,
            SUM(ISNULL(sr.sales_out_qty,0) + ISNULL(sr.other_out_qty,0)) AS total_consumption
        FROM stock_raw sr
        LEFT JOIN items i ON sr.part_no = i.part_no
        WHERE sr.store_name = 'HO'
        GROUP BY sr.part_no
    ),

    ho_requirement AS (
        SELECT
            h.part_no,
            h.item_name,
            h.stock_category,
            h.ho_current_stock,
            h.total_sales_qty,
            h.total_loss_qty,
            h.total_consumption,
            CEILING( ((h.total_consumption / {period_days}) * {planning_days}) - h.ho_current_stock ) AS ho_order_qty
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

        -- Department Mapping
        CASE
            WHEN hr.stock_category IN ('FRUITS VEGETABLES','FRUITS & VEGETABLES IMPORTATION','BAKERY & PATISSERIE','CHARCUTERIE','BOUCHERIE','YOGHURT','MILK')
                THEN 'Fresh Food'
            WHEN hr.stock_category IN ('FROZEN','FRIGO')
                THEN 'Frozen Foods'
            WHEN hr.stock_category IN ('RICE & FLOUR','SAUCES','CANNED FOOD','JAM & SPREAD','BREAKFAST','DRY FRUITS','PASTA','HERBS & SPICES')
                THEN 'Grocery'
            WHEN hr.stock_category IN ('BISCUIT','CHIPS AND NAMKEEN','COLD DRINK WATER JUICE','NON ALCOHOLIC DRINKS',
                                      'ENERGY DRINKS','CHOCOLATES','TEA & COFFEE','HEALTH DRINKS')
                THEN 'Snacks & Beverages'
            WHEN hr.stock_category IN ('BABY CARE','BABY FOOD')
                THEN 'Baby Products'
            WHEN hr.stock_category IN ('PERSONAL CARE','LADIES GROOMING','MENS GROOMING','HAIR AND CARE','ORAL CARE',
                                      'BATH & ACCESSORIES','DEODORANTS & PERFUMES')
                THEN 'Personal Care'
            WHEN hr.stock_category IN ('HOUSEHOLD CLEANING','HOUSEHOLD','DETERGENT & POWDER')
                THEN 'Home Care'
            WHEN hr.stock_category IN ('HOME DECOR','GLASSWARE','KITCHEN AND CROCKERY','TRAVEL & ACCESSORIES','PARTY & DECORATIONS','ELECTRONICS')
                THEN 'Home & Kitchen'
            WHEN hr.stock_category IN ('STATIONARY','SEASONAL STATIONERY')
                THEN 'Stationery'
            WHEN hr.stock_category = 'PET FOOD'
                THEN 'Pet Care'
            WHEN hr.stock_category = 'BARBECUE AND GRILL'
                THEN 'BBQ & Grill'
            ELSE 'Other'
        END AS department,

        hr.stock_category AS sub_department,

        -- Sales & Loss
        hr.total_sales_qty,
        hr.total_loss_qty,
        hr.total_consumption,

        -- HO Stock & Requirement
        hr.ho_current_stock,
        hr.ho_order_qty,

        CASE 
            WHEN hr.ho_order_qty > 0 THEN 'REORDER_REQUIRED'
            ELSE 'SUFFICIENT_STOCK'
        END AS ho_status,

        -- Central Stock
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
        END AS central_status,

        seg.abc_class,
        seg.xyz_class,
        seg.segment AS abc_xyz_segment

    FROM ho_requirement hr
    LEFT JOIN central_stock cs ON hr.part_no = cs.part_no
    LEFT JOIN abc_xyz_segments seg ON hr.part_no = seg.part_no
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
if run_button:

    df = load_data(period_days, planning_days)

    # ----------------------------
    # DYNAMIC FILTERS (AFTER df load)
    # ----------------------------
    st.sidebar.subheader("Filters")

    # Department Filter
    department_list = sorted(df["department"].dropna().unique())
    selected_departments = st.sidebar.multiselect(
        "Department",
        department_list
    )

    if selected_departments:
        df = df[df["department"].isin(selected_departments)]

    # Sub-Department Filter
    subdept_list = sorted(df["sub_department"].dropna().unique())
    selected_subdept = st.sidebar.multiselect(
        "Sub Department",
        subdept_list
    )

    if selected_subdept:
        df = df[df["sub_department"].isin(selected_subdept)]

    # ABC Filter
    abc_list = ["A", "B", "C"]
    selected_abc = st.sidebar.multiselect("ABC Class", abc_list)

    if selected_abc:
        df = df[df["abc_class"].isin(selected_abc)]

    # XYZ Filter
    xyz_list = ["X", "Y", "Z"]
    selected_xyz = st.sidebar.multiselect("XYZ Class", xyz_list)

    if selected_xyz:
        df = df[df["xyz_class"].isin(selected_xyz)]

    # Segment Filter
    segment_list = sorted(df["abc_xyz_segment"].dropna().unique())
    selected_segments = st.sidebar.multiselect(
        "Segment (ABC-XYZ)",
        segment_list
    )

    if selected_segments:
        df = df[df["abc_xyz_segment"].isin(selected_segments)]

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

if st.session_state.run and st.session_state.df is not None:

    df = st.session_state.df
    filtered_df = df.copy()

    st.sidebar.subheader("Filters")

    # Department Filter
    dept_list = sorted(df["department"].dropna().unique())
    selected_depts = st.sidebar.multiselect("Department", dept_list)

    if selected_depts:
        filtered_df = filtered_df[filtered_df["department"].isin(selected_depts)]

    # Sub Department Filter
    sub_list = sorted(filtered_df["sub_department"].dropna().unique())
    selected_sub = st.sidebar.multiselect("Sub Department", sub_list)

    if selected_sub:
        filtered_df = filtered_df[filtered_df["sub_department"].isin(selected_sub)]

    # ABC Filter
    abc_list = ["A", "B", "C"]
    selected_abc = st.sidebar.multiselect("ABC Class", abc_list)
    if selected_abc:
        filtered_df = filtered_df[filtered_df["abc_class"].isin(selected_abc)]

    # XYZ Filter
    xyz_list = ["X", "Y", "Z"]
    selected_xyz = st.sidebar.multiselect("XYZ Class", xyz_list)
    if selected_xyz:
        filtered_df = filtered_df[filtered_df["xyz_class"].isin(selected_xyz)]

    # Segment Filter
    seg_list = sorted(filtered_df["abc_xyz_segment"].dropna().unique())
    selected_seg = st.sidebar.multiselect("Segment (ABC-XYZ)", seg_list)
    if selected_seg:
        filtered_df = filtered_df[filtered_df["abc_xyz_segment"].isin(selected_seg)]

    # SKU Search
    if sku_search:
        filtered_df = filtered_df[filtered_df["part_no"].str.contains(sku_search, case=False)]

    # Minimum order filter
    filtered_df = filtered_df[filtered_df["ho_order_qty"] >= min_order_filter]
