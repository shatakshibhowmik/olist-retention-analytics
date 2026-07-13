\set ON_ERROR_STOP on

COPY category_translation FROM 'data/product_category_name_translation.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY customers FROM 'data/olist_customers_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY sellers FROM 'data/olist_sellers_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY products (product_id, product_category_name, product_name_length, product_description_length, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
FROM 'data/olist_products_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY orders FROM 'data/olist_orders_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY order_items FROM 'data/olist_order_items_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY order_payments FROM 'data/olist_order_payments_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');

COPY order_reviews FROM 'data/olist_order_reviews_dataset.csv' WITH (FORMAT csv, HEADER true, QUOTE '"');
