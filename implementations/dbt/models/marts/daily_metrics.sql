{{ config(materialized='incremental', unique_key='date', incremental_strategy='delete+insert') }}
SELECT pickup_date AS date, COUNT(*) AS trip_count,
    SUM(revenue) AS total_revenue, AVG(fare_amount) AS average_fare,
    AVG(tip_percentage) AS average_tip_percentage,
    AVG(trip_distance) AS average_trip_distance,
    AVG(trip_duration_minutes) AS average_trip_duration,
    SUM(fare_amount) AS fare_sum, SUM(tip_amount) AS tip_sum,
    SUM(trip_distance) AS distance_sum
FROM {{ ref('fct_trips') }} 
{% if is_incremental() %}
WHERE pickup_date >= (SELECT COALESCE(MAX(date), DATE '0001-01-01') FROM {{ this }})
{% endif %}
GROUP BY pickup_date
