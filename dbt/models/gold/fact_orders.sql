{{
  config(
    materialized='table'
  )
}}

-- Gold Layer: Order facts with denormalized customer info

WITH orders AS (
    SELECT * FROM {{ ref('silver_orders') }}
),

customers AS (
    SELECT 
        customer_id,
        email,
        first_name,
        last_name,
        city,
        state,
        country
    FROM {{ ref('silver_customers') }}
),

order_facts AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.email AS customer_email,
        CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
        c.city AS customer_city,
        c.state AS customer_state,
        c.country AS customer_country,
        
        o.order_date,
        DATE_PART('year', o.order_date) AS order_year,
        DATE_PART('month', o.order_date) AS order_month,
        DATE_PART('quarter', o.order_date) AS order_quarter,
        DAYNAME(o.order_date) AS order_day_of_week,
        
        o.order_status,
        o.total_amount,
        
        -- Running totals per customer
        SUM(o.total_amount) OVER (
            PARTITION BY o.customer_id 
            ORDER BY o.order_date
        ) AS customer_running_total,
        
        -- Order sequence number per customer
        ROW_NUMBER() OVER (
            PARTITION BY o.customer_id 
            ORDER BY o.order_date
        ) AS customer_order_sequence,
        
        o.created_at,
        o.updated_at,
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
)

SELECT * FROM order_facts
