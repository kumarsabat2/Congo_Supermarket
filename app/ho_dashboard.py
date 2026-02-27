import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
from io import BytesIO
from datetime import datetime

# ---------------------------------------------------
# Page Config + Theme
# ---------------------------------------------------
st.set_page_config(
    page_title="HO Inventory Planning Dashboard",
    page_icon="🏬",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
            color: #e5e7eb;
        }
        .main-title {
            text-align: center;
            color: #f8fafc;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            text-align: center;
            color: #94a3b8;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background: rgba(17, 24, 39, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 14px;
            padding: 12px 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='main-title'>🏬 HO Inventory Planning Dashboard</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='subtitle'>Real-time style planning with cached data and fast filter interactions.</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------
# Session State
# ---------------------------------------------------
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "filters" not in st.session_state:
    st.session_state.filters = {
        "department": [],
        "sub_department": [],
        "abc_class": [],
        "xyz_class": [],
        "segment": [],
        "sku_search": "",
        "min_order": 0,
    }


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
# SQL Query Function (cached)
# ---------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data(period_days: int, planning_days: int) -> pd.DataFrame:
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
        CASE
            WHEN hr.stock_category IN ('FRUITS VEGETABLES','FRUITS & VEGETABLES IMPORTATION','BAKERY & PATISSERIE','CHARCUTERIE','BOUCHERIE','YOGHURT','MILK') THEN 'Fresh Food'
            WHEN hr.stock_category IN ('FROZEN','FRIGO') THEN 'Frozen Foods'
            WHEN hr.stock_category IN ('RICE & FLOUR','SAUCES','CANNED FOOD','JAM & SPREAD','BREAKFAST','DRY FRUITS','PASTA','HERBS & SPICES') THEN 'Grocery'
            WHEN hr.stock_category IN ('BISCUIT','CHIPS AND NAMKEEN','COLD DRINK WATER JUICE','NON ALCOHOLIC DRINKS','ENERGY DRINKS','CHOCOLATES','TEA & COFFEE','HEALTH DRINKS') THEN 'Snacks & Beverages'
            WHEN hr.stock_category IN ('BABY CARE','BABY FOOD') THEN 'Baby Products'
            WHEN hr.stock_category IN ('PERSONAL CARE','LADIES GROOMING','MENS GROOMING','HAIR AND CARE','ORAL CARE','BATH & ACCESSORIES','DEODORANTS & PERFUMES') THEN 'Personal Care'
            WHEN hr.stock_category IN ('HOUSEHOLD CLEANING','HOUSEHOLD','DETERGENT & POWDER') THEN 'Home Care'
            WHEN hr.stock_category IN ('HOME DECOR','GLASSWARE','KITCHEN AND CROCKERY','TRAVEL & ACCESSORIES','PARTY & DECORATIONS','ELECTRONICS') THEN 'Home & Kitchen'
            WHEN hr.stock_category IN ('STATIONARY','SEASONAL STATIONERY') THEN 'Stationery'
            WHEN hr.stock_category = 'PET FOOD' THEN 'Pet Care'
            WHEN hr.stock_category = 'BARBECUE AND GRILL' THEN 'BBQ & Grill'
            ELSE 'Other'
        END AS department,
        hr.stock_category AS sub_department,
        hr.total_sales_qty,
        hr.total_loss_qty,
        hr.total_consumption,
        hr.ho_current_stock,
        hr.ho_order_qty,
        CASE
            WHEN hr.ho_order_qty > 0 THEN 'REORDER_REQUIRED'
            ELSE 'SUFFICIENT_STOCK'
        END AS ho_status,
        ISNULL(cs.central_current_stock,0) AS central_current_stock,
        CASE
            WHEN (ISNULL(cs.central_current_stock,0) - hr.ho_order_qty) < 0 THEN ABS(ISNULL(cs.central_current_stock,0) - hr.ho_order_qty)
            ELSE 0
        END AS central_purchase_qty,
        CASE
            WHEN (ISNULL(cs.central_current_stock,0) - hr.ho_order_qty) < 0 THEN 'PURCHASE_REQUIRED'
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

    with get_connection() as conn:
        return pd.read_sql(query, conn)


# ---------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------
st.sidebar.header("Planning Controls")
period_days = st.sidebar.number_input("Historical Period Days", min_value=1, value=61)
planning_days = st.sidebar.number_input("Planning Days", min_value=1, value=45)

refresh_clicked = st.sidebar.button("Run / Refresh Planning", type="primary")

if refresh_clicked:
    with st.spinner("Fetching latest planning data..."):
        st.session_state.raw_df = load_data(period_days, planning_days)
    st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if st.session_state.raw_df is None:
    st.info("Click **Run / Refresh Planning** to load data.")
    st.stop()

if st.session_state.last_refresh:
    st.caption(f"Last refreshed: {st.session_state.last_refresh}")


# ---------------------------------------------------
# Filter Form (applies once on submit, avoids rerun-heavy UX)
# ---------------------------------------------------
df = st.session_state.raw_df.copy()

with st.sidebar.form("filters_form"):
    st.subheader("Filters")

    selected_departments = st.multiselect(
        "Department",
        sorted(df["department"].dropna().unique()),
        default=st.session_state.filters["department"],
    )
    selected_subdept = st.multiselect(
        "Sub Department",
        sorted(df["sub_department"].dropna().unique()),
        default=st.session_state.filters["sub_department"],
    )
    selected_abc = st.multiselect(
        "ABC Class",
        ["A", "B", "C"],
        default=st.session_state.filters["abc_class"],
    )
    selected_xyz = st.multiselect(
        "XYZ Class",
        ["X", "Y", "Z"],
        default=st.session_state.filters["xyz_class"],
    )
    selected_segments = st.multiselect(
        "Segment (ABC-XYZ)",
        sorted(df["abc_xyz_segment"].dropna().unique()),
        default=st.session_state.filters["segment"],
    )
    sku_search = st.text_input("Search SKU", value=st.session_state.filters["sku_search"])
    min_order_filter = st.number_input(
        "Minimum Order Qty Filter",
        min_value=0,
        value=int(st.session_state.filters["min_order"]),
    )

    apply_filters = st.form_submit_button("Apply Filters")

if apply_filters:
    st.session_state.filters = {
        "department": selected_departments,
        "sub_department": selected_subdept,
        "abc_class": selected_abc,
        "xyz_class": selected_xyz,
        "segment": selected_segments,
        "sku_search": sku_search,
        "min_order": min_order_filter,
    }

filters = st.session_state.filters

if filters["department"]:
    df = df[df["department"].isin(filters["department"])]
if filters["sub_department"]:
    df = df[df["sub_department"].isin(filters["sub_department"])]
if filters["abc_class"]:
    df = df[df["abc_class"].isin(filters["abc_class"])]
if filters["xyz_class"]:
    df = df[df["xyz_class"].isin(filters["xyz_class"])]
if filters["segment"]:
    df = df[df["abc_xyz_segment"].isin(filters["segment"])]
if filters["sku_search"]:
    df = df[df["part_no"].astype(str).str.contains(filters["sku_search"], case=False, na=False)]

df = df[df["ho_order_qty"] >= filters["min_order"]]


# ---------------------------------------------------
# Dashboard Components
# ---------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("SKUs Needing Reorder", len(df))
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Total HO Order Qty", int(df["ho_order_qty"].sum()))
    st.markdown("</div>", unsafe_allow_html=True)
with col3:
    st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
    st.metric("Central Purchase Required", int(df["central_purchase_qty"].sum()))
    st.markdown("</div>", unsafe_allow_html=True)

st.subheader("Top 10 Risk SKUs")
top10 = df.sort_values("ho_order_qty", ascending=False).head(10)
fig = px.bar(
    top10,
    x="part_no",
    y="ho_order_qty",
    color="ho_order_qty",
    template="plotly_dark",
)
fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=380)
st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------
# Table + Export
# ---------------------------------------------------
def highlight_status(val):
    if val == "REORDER_REQUIRED":
        return "background-color: #ef4444; color: white;"
    if val == "PURCHASE_REQUIRED":
        return "background-color: #f59e0b; color: white;"
    if val == "CENTRAL_SUFFICIENT":
        return "background-color: #22c55e; color: white;"
    return ""


styled_df = df.style.applymap(highlight_status, subset=["ho_status", "central_status"])

st.subheader("Detailed Replenishment Plan")
st.dataframe(styled_df, use_container_width=True, height=430)


def convert_df_to_excel(source_df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        source_df.to_excel(writer, index=False, sheet_name="Replenishment")
    return output.getvalue()


excel_data = convert_df_to_excel(df)
st.download_button(
    label="📥 Download Excel Report",
    data=excel_data,
    file_name="HO_Replenishment_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
