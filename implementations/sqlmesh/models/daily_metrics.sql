MODEL (name analytics.daily_metrics, kind INCREMENTAL_BY_TIME_RANGE (time_column date, batch_size 3650), dialect duckdb, cron '@daily');

SELECT pickup_date AS date, COUNT(*) AS trip_count,
    SUM(revenue) AS total_revenue, AVG(fare_amount) AS average_fare,
    AVG(tip_percentage) AS average_tip_percentage,
    AVG(trip_distance) AS average_trip_distance,
    AVG(trip_duration_minutes) AS average_trip_duration,
    SUM(fare_amount) AS fare_sum, SUM(tip_amount) AS tip_sum,
    SUM(trip_distance) AS distance_sum
FROM analytics.fct_trips WHERE pickup_date BETWEEN @start_ds AND @end_ds
GROUP BY pickup_date;

