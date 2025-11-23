{{
  config(
    materialized='incremental',
    unique_key='customer_id',
    on_schema_change='append_new_columns'
  )
}}

-- Silver Layer: Cleansed and standardized customer data
-- Removes duplicates, standardizes formats, handles nulls

WITH source_data AS (
    SELECT *
    FROM {{ source('bronze', 'customers') }}
    {% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id 
            ORDER BY updated_at DESC
        ) AS row_num
    FROM source_data
),

cleansed AS (
    SELECT
        customer_id,
        LOWER(TRIM(email)) AS email,
        TRIM(first_name) AS first_name,
        TRIM(last_name) AS last_name,
        -- Standardize phone format
        REGEXP_REPLACE(phone, '[^0-9]', '') AS phone_clean,
        TRIM(address) AS address,
        TRIM(city) AS city,
        UPPER(TRIM(state)) AS state,
        TRIM(zip_code) AS zip_code,
        UPPER(TRIM(country)) AS country,
        created_at,
        updated_at,
        CURRENT_TIMESTAMP AS dbt_updated_at
    FROM deduplicated
    WHERE row_num = 1  -- Keep only the most recent record
)

SELECT * FROM cleansed
