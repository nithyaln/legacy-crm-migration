-- Dimension: customers, deduplicated by email
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_email TEXT UNIQUE NOT NULL
);

-- Dimension: normalized region values (US, EMEA, APAC, Unknown)
CREATE TABLE IF NOT EXISTS dim_region (
    region_id SERIAL PRIMARY KEY,
    region_name TEXT UNIQUE NOT NULL
);

-- Fact table: one row per order, referencing the dimensions above
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES dim_customer(customer_id),
    region_id INT REFERENCES dim_region(region_id),
    order_date DATE NOT NULL,
    product TEXT,
    amount NUMERIC(10,2) NOT NULL,
    status TEXT,
    source_record_id INT NOT NULL  -- traceability back to the raw CSV row
);