"""Generate dashboard-ready aggregated CSVs for Tableau Public / Power BI.
Each CSV maps to one visual — connect and drag, no wrangling needed."""
import psycopg2
import pandas as pd
import numpy as np

conn = psycopg2.connect(dbname="olist_project", user="postgres", password="olist", host="localhost")
OUT = "dashboard_data/"
import os; os.makedirs(OUT, exist_ok=True)

def q(sql):
    return pd.read_sql(sql, conn)

# ------------------------------------------------------------------
# 1. KPI cards: repeat rate + CLV comparison
# ------------------------------------------------------------------
kpi = q("""
WITH customer_rev AS (
    SELECT c.customer_unique_id,
           COUNT(DISTINCT o.order_id) AS order_count,
           SUM(oi.price + oi.freight_value) AS total_revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*) AS total_customers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)/COUNT(*), 2) AS repeat_rate_pct,
    ROUND(AVG(CASE WHEN order_count = 1 THEN total_revenue END), 2) AS avg_clv_one_time,
    ROUND(AVG(CASE WHEN order_count > 1 THEN total_revenue END), 2) AS avg_clv_repeat
FROM customer_rev;
""")
kpi.to_csv(OUT + "kpi_summary.csv", index=False)
print("kpi_summary.csv:\n", kpi, "\n")

# ------------------------------------------------------------------
# 2. Repeat rate + customer count by STATE (map / bar chart)
# ------------------------------------------------------------------
by_state = q("""
WITH cust AS (
    SELECT c.customer_unique_id, MAX(c.customer_state) AS state,
           COUNT(DISTINCT o.order_id) AS order_count,
           SUM(oi.price + oi.freight_value) AS total_revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
    GROUP BY c.customer_unique_id
)
SELECT state,
       COUNT(*) AS customers,
       ROUND(100.0 * SUM(CASE WHEN order_count>1 THEN 1 ELSE 0 END)/COUNT(*), 2) AS repeat_rate_pct,
       ROUND(AVG(total_revenue), 2) AS avg_customer_revenue
FROM cust GROUP BY state ORDER BY customers DESC;
""")
by_state.to_csv(OUT + "repeat_rate_by_state.csv", index=False)
print("repeat_rate_by_state.csv: top 5\n", by_state.head(), "\n")

# ------------------------------------------------------------------
# 3. Repeat rate + review dissatisfaction by CATEGORY (bar chart)
#    Category = category of the customer's FIRST order
# ------------------------------------------------------------------
by_cat = q("""
WITH cust_orders AS (
    SELECT c.customer_unique_id, o.order_id, o.order_purchase_timestamp,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp) AS rk,
           COUNT(*) OVER (PARTITION BY c.customer_unique_id) AS total_orders
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
),
first_cat AS (
    SELECT co.customer_unique_id, co.total_orders,
           MODE() WITHIN GROUP (ORDER BY ct.product_category_name_english) AS category
    FROM cust_orders co
    JOIN order_items oi ON co.order_id = oi.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    WHERE co.rk = 1
    GROUP BY co.customer_unique_id, co.total_orders
)
SELECT category,
       COUNT(*) AS first_time_customers,
       ROUND(100.0 * SUM(CASE WHEN total_orders>1 THEN 1 ELSE 0 END)/COUNT(*), 2) AS repeat_rate_pct
FROM first_cat
WHERE category IS NOT NULL
GROUP BY category
HAVING COUNT(*) >= 500
ORDER BY repeat_rate_pct DESC;
""")
by_cat.to_csv(OUT + "repeat_rate_by_category.csv", index=False)
print("repeat_rate_by_category.csv: top 5\n", by_cat.head(), "\n")

# ------------------------------------------------------------------
# 4. Monthly cohort retention (heatmap)
# ------------------------------------------------------------------
cohort = q("""
WITH first_purchase AS (
    SELECT c.customer_unique_id,
           DATE_TRUNC('month', MIN(o.order_purchase_timestamp)) AS cohort_month
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
    GROUP BY c.customer_unique_id
),
owc AS (
    SELECT c.customer_unique_id, fp.cohort_month,
           (DATE_PART('year', DATE_TRUNC('month', o.order_purchase_timestamp)) - DATE_PART('year', fp.cohort_month))*12
           + (DATE_PART('month', DATE_TRUNC('month', o.order_purchase_timestamp)) - DATE_PART('month', fp.cohort_month)) AS month_number
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
),
cs AS (SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_size FROM first_purchase GROUP BY cohort_month)
SELECT TO_CHAR(owc.cohort_month, 'YYYY-MM') AS cohort_month,
       owc.month_number::int,
       COUNT(DISTINCT owc.customer_unique_id) AS active_customers,
       cs.cohort_size,
       ROUND(100.0 * COUNT(DISTINCT owc.customer_unique_id)/cs.cohort_size, 2) AS retention_pct
FROM owc JOIN cs ON owc.cohort_month = cs.cohort_month
WHERE owc.cohort_month >= '2017-01-01'
GROUP BY owc.cohort_month, owc.month_number, cs.cohort_size
ORDER BY owc.cohort_month, owc.month_number;
""")
cohort.to_csv(OUT + "cohort_retention.csv", index=False)
print(f"cohort_retention.csv: {len(cohort)} rows\n")

# ------------------------------------------------------------------
# 5. Monthly order volume + revenue trend (line chart)
# ------------------------------------------------------------------
monthly = q("""
SELECT TO_CHAR(DATE_TRUNC('month', o.order_purchase_timestamp), 'YYYY-MM') AS month,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status NOT IN ('canceled','unavailable')
GROUP BY 1 ORDER BY 1;
""")
monthly.to_csv(OUT + "monthly_trend.csv", index=False)
print(f"monthly_trend.csv: {len(monthly)} rows\n")

# ------------------------------------------------------------------
# 6. Delivery performance vs repeat behavior (the model's key insight)
# ------------------------------------------------------------------
delivery = q("""
WITH cust_orders AS (
    SELECT c.customer_unique_id, o.order_id,
           o.order_delivered_customer_date, o.order_estimated_delivery_date,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp) AS rk,
           COUNT(*) OVER (PARTITION BY c.customer_unique_id) AS total_orders
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled','unavailable')
)
SELECT CASE
         WHEN order_delivered_customer_date IS NULL THEN '1. Never delivered'
         WHEN order_delivered_customer_date > order_estimated_delivery_date THEN '2. Delivered late'
         WHEN order_delivered_customer_date > order_estimated_delivery_date - INTERVAL '3 days' THEN '3. Just on time'
         ELSE '4. Early'
       END AS first_delivery_experience,
       COUNT(*) AS customers,
       ROUND(100.0 * SUM(CASE WHEN total_orders>1 THEN 1 ELSE 0 END)/COUNT(*), 2) AS repeat_rate_pct
FROM cust_orders WHERE rk = 1
GROUP BY 1 ORDER BY 1;
""")
delivery.to_csv(OUT + "delivery_vs_repeat.csv", index=False)
print("delivery_vs_repeat.csv:\n", delivery, "\n")

# ------------------------------------------------------------------
# 7. Threshold decision matrix (from the model results — static)
# ------------------------------------------------------------------
thresholds = pd.DataFrame({
    "retention_action": ["Email nudge (near-zero cost)", "Discount code (moderate cost)", "VIP perk / outreach (high cost)"],
    "threshold": [0.41, 0.53, 0.635],
    "precision_pct": [4.1, 5.1, 6.0],
    "recall_pct": [60, 30, 10],
    "customers_flagged_test_set": [8429, 3381, 974],
})
thresholds.to_csv(OUT + "threshold_decision_matrix.csv", index=False)
print("threshold_decision_matrix.csv written")

conn.close()
print("\nAll dashboard CSVs written to", OUT)
