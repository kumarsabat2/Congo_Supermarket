/* =========================================
   INVENTORY OPTIMIZATION SYSTEM
   SCHEMA ALTERATIONS / ENHANCEMENTS
========================================= */

-------------------------------------------------
-- 1️⃣ Ensure sales_daily uniqueness
-------------------------------------------------

-- Prevent duplicate entries for same SKU + branch + date
IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE name = 'uq_sales_unique'
)
BEGIN
    CREATE UNIQUE INDEX uq_sales_unique
    ON sales_daily (sale_date, branch_id, item_id);
END;


-------------------------------------------------
-- 2️⃣ Ensure stock_snapshot uniqueness
-------------------------------------------------

IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE name = 'uq_stock_snapshot_unique'
)
BEGIN
    CREATE UNIQUE INDEX uq_stock_snapshot_unique
    ON stock_snapshot (snapshot_date, warehouse_id, item_id);
END;


-------------------------------------------------
-- 3️⃣ Ensure forecast uniqueness
-------------------------------------------------

IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE name = 'uq_forecast_unique'
)
BEGIN
    CREATE UNIQUE INDEX uq_forecast_unique
    ON forecast_daily (forecast_date, branch_id, item_id);
END;


-------------------------------------------------
-- 4️⃣ Add model metadata columns (if missing)
-------------------------------------------------

IF COL_LENGTH('forecast_daily', 'model_type') IS NULL
BEGIN
    ALTER TABLE forecast_daily
    ADD model_type VARCHAR(50);
END;

IF COL_LENGTH('forecast_daily', 'training_date') IS NULL
BEGIN
    ALTER TABLE forecast_daily
    ADD training_date DATE;
END;


-------------------------------------------------
-- 5️⃣ Add last_updated to classification
-------------------------------------------------

IF COL_LENGTH('sku_classification', 'last_updated') IS NULL
BEGIN
    ALTER TABLE sku_classification
    ADD last_updated DATETIME DEFAULT GETDATE();
END;


-------------------------------------------------
-- 6️⃣ Add service level column
-------------------------------------------------

IF COL_LENGTH('sku_classification', 'service_level') IS NULL
BEGIN
    ALTER TABLE sku_classification
    ADD service_level DECIMAL(5,2);
END;


-------------------------------------------------
-- 7️⃣ Add reorder_flag to stock projection
-------------------------------------------------

IF COL_LENGTH('stock_projection', 'reorder_flag') IS NULL
BEGIN
    ALTER TABLE stock_projection
    ADD reorder_flag BIT DEFAULT 0;
END;


-------------------------------------------------
-- 8️⃣ Add supplier_lead_time column (future ready)
-------------------------------------------------

IF COL_LENGTH('items', 'supplier_lead_time') IS NULL
BEGIN
    ALTER TABLE items
    ADD supplier_lead_time INT;
END;


-------------------------------------------------
-- 9️⃣ Add discontinued flag
-------------------------------------------------

IF COL_LENGTH('items', 'is_discontinued') IS NULL
BEGIN
    ALTER TABLE items
    ADD is_discontinued BIT DEFAULT 0;
END;
