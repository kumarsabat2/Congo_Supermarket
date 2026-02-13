/* =========================================
   INVENTORY OPTIMIZATION SYSTEM
   SCHEMA CREATION SCRIPT
========================================= */

------------------------------------------
-- 1️⃣ WAREHOUSES
------------------------------------------
CREATE TABLE warehouses (
    warehouse_id INT IDENTITY(1,1) PRIMARY KEY,
    warehouse_code VARCHAR(20) NOT NULL UNIQUE,
    warehouse_name NVARCHAR(100),
    warehouse_type NVARCHAR(50),
    created_at DATETIME DEFAULT GETDATE()
);

------------------------------------------
-- 2️⃣ BRANCHES
------------------------------------------
CREATE TABLE branches (
    branch_id INT IDENTITY(1,1) PRIMARY KEY,
    branch_code VARCHAR(50) UNIQUE,
    branch_name NVARCHAR(100),
    linked_warehouse_id INT,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (linked_warehouse_id)
        REFERENCES warehouses(warehouse_id)
);

------------------------------------------
-- 3️⃣ ITEMS
------------------------------------------
CREATE TABLE items (
    item_id INT IDENTITY(1,1) PRIMARY KEY,
    part_no VARCHAR(100) UNIQUE,
    item_name NVARCHAR(255),
    item_description NVARCHAR(500),
    base_unit NVARCHAR(50),
    packing_description NVARCHAR(100),
    stock_group NVARCHAR(100),
    stock_category NVARCHAR(100),
    tax_detail NVARCHAR(100),
    reorder_level DECIMAL(18,4),
    reorder_qty DECIMAL(18,4),
    inactive BIT,
    department_id INT,
    group_id INT,
    brand NVARCHAR(100),
    purchase_type NVARCHAR(100),
    supplier_type NVARCHAR(100),
    department_name NVARCHAR(100),
    store_planogram NVARCHAR(100),
    expiry_date DATE,
    created_at DATETIME DEFAULT GETDATE()
);

------------------------------------------
-- 4️⃣ SALES DAILY
------------------------------------------
CREATE TABLE sales_daily (
    sales_id INT IDENTITY(1,1) PRIMARY KEY,
    sale_date DATE NOT NULL,
    branch_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity_sold DECIMAL(18,4),
    revenue DECIMAL(18,4),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (branch_id)
        REFERENCES branches(branch_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);

CREATE INDEX idx_sales_item_date
ON sales_daily (item_id, sale_date);

------------------------------------------
-- 5️⃣ STOCK RAW (Staging Table)
------------------------------------------
CREATE TABLE stock_raw (
    store_name NVARCHAR(100),
    warehouse_name NVARCHAR(100),
    stock_category NVARCHAR(100),
    stock_group NVARCHAR(100),
    part_no VARCHAR(100),
    item_name NVARCHAR(255),
    uom NVARCHAR(50),
    rate DECIMAL(18,4),
    op_qty DECIMAL(18,4),
    in_qty DECIMAL(18,4),
    sales_out_qty DECIMAL(18,4),
    other_out_qty DECIMAL(18,4),
    cl_qty DECIMAL(18,4)
);

------------------------------------------
-- 6️⃣ STOCK SNAPSHOT
------------------------------------------
CREATE TABLE stock_snapshot (
    snapshot_id INT IDENTITY(1,1) PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    warehouse_id INT NOT NULL,
    item_id INT NOT NULL,
    opening_qty DECIMAL(18,4),
    inward_qty DECIMAL(18,4),
    outward_qty DECIMAL(18,4),
    closing_qty DECIMAL(18,4),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);

CREATE INDEX idx_stock_wh_item
ON stock_snapshot (warehouse_id, item_id);

------------------------------------------
-- 7️⃣ SKU CLASSIFICATION (ABC–XYZ)
------------------------------------------
CREATE TABLE sku_classification (
    classification_id INT IDENTITY(1,1) PRIMARY KEY,
    branch_id INT NOT NULL,
    item_id INT NOT NULL,
    total_quantity DECIMAL(18,4),
    total_sales_value DECIMAL(18,4),
    avg_demand DECIMAL(18,4),
    std_demand DECIMAL(18,4),
    cv_value DECIMAL(18,4),
    abc_class CHAR(1),
    xyz_class CHAR(1),
    safety_stock DECIMAL(18,4),
    reorder_point DECIMAL(18,4),
    assumed_lead_time INT,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (branch_id)
        REFERENCES branches(branch_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);

------------------------------------------
-- 8️⃣ FORECAST DAILY
------------------------------------------
CREATE TABLE forecast_daily (
    forecast_id INT IDENTITY(1,1) PRIMARY KEY,
    forecast_date DATE NOT NULL,
    branch_id INT NOT NULL,
    item_id INT NOT NULL,
    forecast_qty DECIMAL(18,4),
    forecast_lower DECIMAL(18,4),
    forecast_upper DECIMAL(18,4),
    model_version VARCHAR(50),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (branch_id)
        REFERENCES branches(branch_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);

CREATE INDEX idx_forecast_item_date
ON forecast_daily (item_id, forecast_date);

------------------------------------------
-- 9️⃣ STOCK PROJECTION
------------------------------------------
CREATE TABLE stock_projection (
    projection_id INT IDENTITY(1,1) PRIMARY KEY,
    warehouse_id INT NOT NULL,
    item_id INT NOT NULL,
    projection_date DATE NOT NULL,
    projected_stock DECIMAL(18,4),
    stockout_flag BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);

------------------------------------------
-- 🔟 REPLENISHMENT RECOMMENDATION
------------------------------------------
CREATE TABLE replenishment_recommendation (
    recommendation_id INT IDENTITY(1,1) PRIMARY KEY,
    warehouse_id INT NOT NULL,
    item_id INT NOT NULL,
    recommended_order_qty DECIMAL(18,4),
    recommended_order_date DATE,
    risk_level VARCHAR(20),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
);
