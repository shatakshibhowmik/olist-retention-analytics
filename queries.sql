-- ============================================================
-- Olist E-Commerce Analytics — Core KPI Queries
--
-- IMPORTANT DATASET NUANCE:
-- customer_id is unique PER ORDER in this dataset (Olist assigns
-- a new customer_id every time someone orders). customer_unique_id
-- is the real person. Every query below joins through customers
-- and groups by customer_unique_id, or repeat-purchase numbers
-- come out at ~97% "churn," which is a data-modeling mistake,
-- not a business insight. This is worth a line in your case study.
-- ============================================================

-- KPI 1: Repeat Purchase Rate
-- (Olist is a marketplace, not a subscription — repeat-purchase rate
-- is the honest analogue of "retention" here, not monthly churn.)
WITH customer_order_counts AS (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*) AS total_customers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_purchase_rate_pct
FROM customer_order_counts;


-- KPI 2: Monthly Cohort Retention Matrix
-- For each customer's first-purchase month, what % of that cohort
-- placed another order in month+1, month+2, etc.
WITH first_purchase AS (
    SELECT c.customer_unique_id,
           DATE_TRUNC('month', MIN(o.order_purchase_timestamp)) AS cohort_month
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
orders_with_cohort AS (
    SELECT c.customer_unique_id,
           DATE_TRUNC('month', o.order_purchase_timestamp) AS order_month,
           fp.cohort_month,
           (DATE_PART('year', DATE_TRUNC('month', o.order_purchase_timestamp)) - DATE_PART('year', fp.cohort_month)) * 12
           + (DATE_PART('month', DATE_TRUNC('month', o.order_purchase_timestamp)) - DATE_PART('month', fp.cohort_month)) AS month_number
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS num_customers
    FROM first_purchase
    GROUP BY cohort_month
)
SELECT owc.cohort_month,
       owc.month_number,
       COUNT(DISTINCT owc.customer_unique_id) AS active_customers,
       cs.num_customers AS cohort_size,
       ROUND(100.0 * COUNT(DISTINCT owc.customer_unique_id) / cs.num_customers, 2) AS retention_pct
FROM orders_with_cohort owc
JOIN cohort_size cs ON owc.cohort_month = cs.cohort_month
GROUP BY owc.cohort_month, owc.month_number, cs.num_customers
ORDER BY owc.cohort_month, owc.month_number;


-- KPI 3: Customer Lifetime Value (CLV) — overall, and one-time vs repeat buyers
WITH customer_revenue AS (
    SELECT c.customer_unique_id,
           SUM(oi.price + oi.freight_value) AS total_revenue,
           COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
)
SELECT
    ROUND(AVG(total_revenue), 2) AS avg_clv_all,
    ROUND(AVG(CASE WHEN order_count = 1 THEN total_revenue END), 2) AS avg_clv_one_time_buyers,
    ROUND(AVG(CASE WHEN order_count > 1 THEN total_revenue END), 2) AS avg_clv_repeat_buyers
FROM customer_revenue;


-- KPI 4: Churn/dissatisfaction signal by product category (feeds the ML model's features)
SELECT ct.product_category_name_english AS category,
       COUNT(DISTINCT o.order_id) AS num_orders,
       ROUND(AVG(r.review_score), 2) AS avg_review_score,
       ROUND(100.0 * SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) / COUNT(r.review_score), 2) AS pct_low_reviews
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
LEFT JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY ct.product_category_name_english
HAVING COUNT(DISTINCT o.order_id) > 100
ORDER BY pct_low_reviews DESC
LIMIT 15;
