-- Olist Brazilian E-Commerce — Analytics Schema
-- Source: Brazilian E-Commerce Public Dataset by Olist (real, anonymized commercial data)

DROP TABLE IF EXISTS order_reviews, order_payments, order_items, orders, customers, products, sellers, category_translation CASCADE;

CREATE TABLE customers (
    customer_id            VARCHAR(32) PRIMARY KEY,
    customer_unique_id     VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city           VARCHAR(100),
    customer_state           VARCHAR(2)
);

CREATE TABLE sellers (
    seller_id               VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix  VARCHAR(10),
    seller_city              VARCHAR(100),
    seller_state              VARCHAR(2)
);

CREATE TABLE category_translation (
    product_category_name          VARCHAR(100) PRIMARY KEY,
    product_category_name_english  VARCHAR(100)
);

CREATE TABLE products (
    product_id                   VARCHAR(32) PRIMARY KEY,
    product_category_name        VARCHAR(100) REFERENCES category_translation(product_category_name),
    product_name_length          INT,
    product_description_length   INT,
    product_photos_qty           INT,
    product_weight_g             NUMERIC,
    product_length_cm            NUMERIC,
    product_height_cm            NUMERIC,
    product_width_cm             NUMERIC
);

CREATE TABLE orders (
    order_id                        VARCHAR(32) PRIMARY KEY,
    customer_id                     VARCHAR(32) REFERENCES customers(customer_id),
    order_status                    VARCHAR(20),
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP
);

CREATE TABLE order_items (
    order_id             VARCHAR(32) REFERENCES orders(order_id),
    order_item_id         INT,
    product_id             VARCHAR(32) REFERENCES products(product_id),
    seller_id               VARCHAR(32) REFERENCES sellers(seller_id),
    shipping_limit_date     TIMESTAMP,
    price                     NUMERIC(10,2),
    freight_value             NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id                VARCHAR(32) REFERENCES orders(order_id),
    payment_sequential       INT,
    payment_type              VARCHAR(20),
    payment_installments       INT,
    payment_value               NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
    review_id                 VARCHAR(32),
    order_id                   VARCHAR(32) REFERENCES orders(order_id),
    review_score                 INT,
    review_comment_title           TEXT,
    review_comment_message          TEXT,
    review_creation_date              TIMESTAMP,
    review_answer_timestamp            TIMESTAMP
);

-- Indexes for the joins/aggregations you'll run constantly
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_payments_order ON order_payments(order_id);
CREATE INDEX idx_reviews_order ON order_reviews(order_id);
CREATE INDEX idx_customers_unique ON customers(customer_unique_id);
