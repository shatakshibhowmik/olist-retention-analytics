-- Feature table: one row per customer, built ONLY from their first order.
-- Label: did this customer ever place a second order?

WITH customer_orders AS (
    SELECT c.customer_id, c.customer_unique_id, c.customer_state,
           o.order_id, o.order_purchase_timestamp,
           o.order_delivered_customer_date, o.order_estimated_delivery_date,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp) AS order_rank,
           COUNT(*) OVER (PARTITION BY c.customer_unique_id) AS total_orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
first_orders AS (
    SELECT * FROM customer_orders WHERE order_rank = 1
),
first_order_items AS (
    SELECT oi.order_id,
           MODE() WITHIN GROUP (ORDER BY ct.product_category_name_english) AS product_category,
           SUM(oi.price + oi.freight_value) AS order_value,
           COUNT(*) AS num_items
    FROM order_items oi
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    GROUP BY oi.order_id
),
first_order_payment AS (
    SELECT order_id,
           MODE() WITHIN GROUP (ORDER BY payment_type) AS payment_type,
           MAX(payment_installments) AS payment_installments
    FROM order_payments
    GROUP BY order_id
),
first_order_review AS (
    SELECT order_id, MAX(review_score) AS review_score
    FROM order_reviews
    GROUP BY order_id
)
SELECT
    fo.customer_unique_id,
    fo.order_id,
    fo.customer_state,
    fo.order_purchase_timestamp,
    EXTRACT(EPOCH FROM (fo.order_delivered_customer_date - fo.order_purchase_timestamp)) / 86400.0 AS delivery_days,
    EXTRACT(EPOCH FROM (fo.order_estimated_delivery_date - fo.order_delivered_customer_date)) / 86400.0 AS days_early_vs_estimate,
    foi.product_category,
    foi.order_value,
    foi.num_items,
    fop.payment_type,
    fop.payment_installments,
    fr.review_score,
    CASE WHEN fo.total_orders > 1 THEN 1 ELSE 0 END AS became_repeat_buyer
FROM first_orders fo
LEFT JOIN first_order_items foi ON fo.order_id = foi.order_id
LEFT JOIN first_order_payment fop ON fo.order_id = fop.order_id
LEFT JOIN first_order_review fr ON fo.order_id = fr.order_id;
