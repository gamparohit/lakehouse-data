{{
  config(
    materialized='table'
  )
}}

-- Gold Layer: Customer dimension table with aggregated metrics

WITH customer_base AS (
    SELECT * FROM {{ ref('silver_customers') }}
),

order_metrics AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(total_amount) AS total_revenue,
        AVG(total_amount) AS avg_order_value,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        MAX(CASE WHEN order_status = 'DELIVERED' THEN order_date END) AS last_delivered_date
    FROM {{ ref('silver_orders') }}
    GROUP BY customer_id
),

customer_segments AS (
    SELECT
        c.*,
        COALESCE(o.total_orders, 0) AS lifetime_orders,
        COALESCE(o.total_revenue, 0) AS lifetime_revenue,
        COALESCE(o.avg_order_value, 0) AS avg_order_value,
        o.first_order_date,
        o.last_order_date,
        o.last_delivered_date,
        
        -- Customer segmentation
        CASE
            WHEN COALESCE(o.total_revenue, 0) >= 1000 THEN 'VIP'
            WHEN COALESCE(o.total_revenue, 0) >= 500 THEN 'HIGH_VALUE'
            WHEN COALESCE(o.total_revenue, 0) >= 100 THEN 'MEDIUM_VALUE'
            WHEN COALESCE(o.total_revenue, 0) > 0 THEN 'LOW_VALUE'
            ELSE 'NEW'
        END AS customer_segment,
        
        -- Recency calculation (days since last order)
        CASE
            WHEN o.last_order_date IS NOT NULL 
            THEN DATEDIFF('day', o.last_order_date, CURRENT_DATE)
            ELSE NULL
        END AS days_since_last_order,
        
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM customer_base c
    LEFT JOIN order_metrics o ON c.customer_id = o.customer_id
)

SELECT * FROM customer_segments
