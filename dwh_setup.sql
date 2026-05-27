-- Создаём схему dwh
CREATE SCHEMA IF NOT EXISTS dwh;

-- 1. Справочник дат
DROP TABLE IF EXISTS dwh.dim_date CASCADE;
CREATE TABLE dwh.dim_date (
    date_key      INTEGER PRIMARY KEY,
    date_actual   DATE NOT NULL,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    month         INTEGER NOT NULL,
    month_name    TEXT NOT NULL,
    day_of_week   INTEGER NOT NULL,
    day_name      TEXT NOT NULL
);

INSERT INTO dwh.dim_date (date_key, date_actual, year, quarter, month, month_name, day_of_week, day_name)
SELECT 
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS date_key,
    d AS date_actual,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    TO_CHAR(d, 'Month') AS month_name,
    EXTRACT(DOW FROM d)::INTEGER AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name
FROM generate_series('2023-01-01'::DATE, '2025-12-31'::DATE, '1 day'::INTERVAL) AS d;

-- 2. Справочник клиентов
DROP TABLE IF EXISTS dwh.dim_customer CASCADE;
CREATE TABLE dwh.dim_customer (
    customer_id     SERIAL PRIMARY KEY,
    customer_name   TEXT NOT NULL,
    industry        TEXT,
    country         TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

INSERT INTO dwh.dim_customer (customer_name, industry, country) VALUES
    ('Газпром нефть', 'Нефтегаз', 'Россия'),
    ('Сбербанк', 'Банки', 'Россия'),
    ('Ozon', 'IT', 'Россия'),
    ('Беларуськалий', 'Промышленность', 'Беларусь'),
    ('Kaspi.kz', 'IT', 'Казахстан');

-- 3. Справочник продуктов
DROP TABLE IF EXISTS dwh.dim_product CASCADE;
CREATE TABLE dwh.dim_product (
    product_id          SERIAL PRIMARY KEY,
    product_name        TEXT NOT NULL,
    product_type        TEXT NOT NULL,
    base_price          NUMERIC(10,2) NOT NULL,
    unit                TEXT NOT NULL
);

INSERT INTO dwh.dim_product (product_name, product_type, base_price, unit) VALUES
    ('TrueConf Server (100 users)', 'Server License', 600000.00, 'user'),
    ('TrueConf Server (500 users)', 'Server License', 2200000.00, 'user'),
    ('TrueConf Room License', 'Room License', 50000.00, 'room'),
    ('TrueConf Group Hardware', 'Hardware', 250000.00, 'unit');

-- Факт продаж
DROP TABLE IF EXISTS dwh.fact_sales CASCADE;
CREATE TABLE dwh.fact_sales (
    sale_id        SERIAL PRIMARY KEY,
    customer_id    INTEGER REFERENCES dwh.dim_customer(customer_id),
    product_id     INTEGER REFERENCES dwh.dim_product(product_id),
    date_key       INTEGER REFERENCES dwh.dim_date(date_key),
    quantity       INTEGER NOT NULL,
    total_amount   NUMERIC(12,2) NOT NULL,
    created_at     TIMESTAMP DEFAULT NOW()
);

-- Функция генерации случайных данных о продажах
CREATE OR REPLACE FUNCTION dwh.generate_sales_data(p_years INTEGER DEFAULT 2)
RETURNS VOID AS $$
DECLARE
    start_date DATE := (DATE_TRUNC('year', NOW()) - (p_years || ' years')::INTERVAL)::DATE;
    end_date DATE := NOW();
    date_rec RECORD;
    cust_rec RECORD;
    prod_rec RECORD;
    qty INTEGER;
    amount NUMERIC;
BEGIN
    FOR date_rec IN SELECT date_key, date_actual FROM dwh.dim_date WHERE date_actual BETWEEN start_date AND end_date LOOP
        IF RANDOM() < 0.4 THEN
            CONTINUE;
        END IF;
        FOR cust_rec IN SELECT customer_id FROM dwh.dim_customer LOOP
            IF RANDOM() < 0.3 THEN
                FOR prod_rec IN SELECT product_id, base_price FROM dwh.dim_product LOOP
                    IF RANDOM() < 0.5 THEN
                        qty := CASE 
                            WHEN prod_rec.product_id IN (1,2) THEN (RANDOM() * 200 + 1)::INTEGER
                            WHEN prod_rec.product_id = 3 THEN (RANDOM() * 10 + 1)::INTEGER
                            ELSE (RANDOM() * 3 + 1)::INTEGER
                        END;
                        amount := prod_rec.base_price * qty;
                        INSERT INTO dwh.fact_sales (customer_id, product_id, date_key, quantity, total_amount)
                        VALUES (cust_rec.customer_id, prod_rec.product_id, date_rec.date_key, qty, amount);
                    END IF;
                END LOOP;
            END IF;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Витрина с агрегированными показателями
DROP MATERIALIZED VIEW IF EXISTS dwh.sales_kpi CASCADE;
CREATE MATERIALIZED VIEW dwh.sales_kpi AS
SELECT 
    dim.year,
    dim.quarter,
    dim.month,
    cust.industry,
    prod.product_name,
    COUNT(DISTINCT fact.sale_id) AS total_transactions,
    SUM(fact.quantity) AS total_units_sold,
    SUM(fact.total_amount) AS total_revenue,
    AVG(fact.total_amount) AS avg_transaction_value,
    COUNT(DISTINCT fact.customer_id) AS active_customers
FROM dwh.fact_sales fact
JOIN dwh.dim_date dim ON fact.date_key = dim.date_key
JOIN dwh.dim_customer cust ON fact.customer_id = cust.customer_id
JOIN dwh.dim_product prod ON fact.product_id = prod.product_id
GROUP BY dim.year, dim.quarter, dim.month, cust.industry, prod.product_name;
-- Генерация тестовых данных (2 года)
SELECT dwh.generate_sales_data(2);
REFRESH MATERIALIZED VIEW dwh.sales_kpi;