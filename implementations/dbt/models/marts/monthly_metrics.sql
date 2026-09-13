WITH monthly AS (
    SELECT CAST(DATE_TRUNC('month', date) AS DATE) AS month,
        CAST(SUM(trip_count) AS BIGINT) AS trip_count,
        SUM(total_revenue) AS revenue,
        SUM(fare_sum) / SUM(trip_count) AS average_fare,
        SUM(tip_sum) / SUM(trip_count) AS average_tip,
        SUM(distance_sum) / SUM(trip_count) AS average_distance
    FROM {{ ref('daily_metrics') }} GROUP BY 1
), previous AS (
    SELECT *, LAG(month) OVER (ORDER BY month) AS previous_month,
        LAG(trip_count) OVER (ORDER BY month) AS previous_trips,
        LAG(revenue) OVER (ORDER BY month) AS previous_revenue
    FROM monthly
)
SELECT month, trip_count, revenue, average_fare, average_tip, average_distance,
    CASE WHEN month = previous_month + INTERVAL '1 month'
        THEN (trip_count - previous_trips) / NULLIF(previous_trips, 0)
        END AS month_over_month_trip_growth,
    CASE WHEN month = previous_month + INTERVAL '1 month'
        THEN (revenue - previous_revenue) / NULLIF(previous_revenue, 0)
        END AS month_over_month_revenue_growth
FROM previous
