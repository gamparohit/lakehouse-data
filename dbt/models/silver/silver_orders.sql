{{
  config(
    materialized='incremental',
    unique_key='order_id',
    on_schema_change='append_new_columns'
  )
}}

-- Silver Layer: Cleansed order data with validations

WITH source_data AS (
    SELECT *
    FROM {{ source('bronze', 'orders') }}
    {% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY order_id 
            ORDER BY updated_at DESC
        ) AS row_num
    FROM source_data
),

cleansed AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        UPPER(TRIM(order_status)) AS order_status,
        -- Ensure total_amount is positive
        CASE 
            WHEN total_amount < 0 THEN 0 
            ELSE total_amount 
        END AS total_amount,
        created_at,
        updated_at,
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM deduplicated
    WHERE row_num = 1
        AND customer_id IS NOT NULL  -- Data quality: require customer_id
        AND order_date IS NOT NULL   -- Data quality: require order_date
)

SELECT * FROM cleansed
