/* =========================================
   INVENTORY OPTIMIZATION SYSTEM
   PERFORMANCE INDEXES
========================================= */

-------------------------------------------------
-- SALES DAILY INDEXES
-------------------------------------------------

-- Fast lookup for SKU time series
CREATE INDEX idx_sales_item_date
ON sales_daily (item_id, sale_date);

-- Fast branch + SKU aggregation
CREATE INDEX idx_sales_branch_item
ON sales_daily (branch_id, item_id);

-- Fast date filtering
CREATE INDEX idx_sales_date
ON sales_daily (sale_date);


-------------------------------------------------
-- STOCK SNAPSHOT INDEXES
-------------------------------------------------

-- Fast warehouse SKU lookup
CREATE INDEX idx_stock_wh_item
ON stock_snapshot (warehouse_id, item_id);

-- Fast snapshot date filtering
CREATE INDEX idx_stock_snapshot_date
ON stock_snapshot (snapshot_date);


-------------------------------------------------
-- SKU CLASSIFICATION INDEXES
-------------------------------------------------

-- Fast classification lookup
CREATE INDEX idx_classification_item
ON sku_classification (item_id);

-- Fast ABC filtering
CREATE INDEX idx_classification_abc
ON sku_classification (abc_class);

-- Fast XYZ filtering
CREATE INDEX idx_classification_xyz
ON sku_classification (xyz_class);


-------------------------------------------------
-- FORECAST DAILY INDEXES
-------------------------------------------------

-- Fast forecast retrieval per SKU
CREATE INDEX idx_forecast_item_date
ON forecast_daily (item_id, forecast_date);

-- Fast branch-level forecast
CREATE INDEX idx_forecast_branch
ON forecast_daily (branch_id);


-------------------------------------------------
-- STOCK PROJECTION INDEXES
-------------------------------------------------

CREATE INDEX idx_projection_item_date
ON stock_projection (item_id, projection_date);


-------------------------------------------------
-- REPLENISHMENT RECOMMENDATION INDEXES
-------------------------------------------------

CREATE INDEX idx_replenishment_item
ON replenishment_recommendation (item_id);

CREATE INDEX idx_replenishment_warehouse
ON replenishment_recommendation (warehouse_id);


-------------------------------------------------
-- ITEMS INDEXES
-------------------------------------------------

-- Already UNIQUE on part_no, but ensure lookup speed
CREATE INDEX idx_items_part_no
ON items (part_no);


-------------------------------------------------
-- STOCK RAW INDEXES (for transformation performance)
-------------------------------------------------

CREATE INDEX idx_stock_raw_part_no
ON stock_raw (part_no);

CREATE INDEX idx_stock_raw_warehouse
ON stock_raw (warehouse_name);
