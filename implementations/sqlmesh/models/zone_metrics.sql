MODEL (name analytics.zone_metrics, kind FULL, dialect duckdb, cron '@daily');

SELECT pickup_zone_id, pickup_zone, COUNT(*) AS trip_count,
    SUM(revenue) AS total_revenue, AVG(fare_amount) AS average_fare,
    AVG(trip_distance) AS average_trip_distance
FROM analytics.fct_trips GROUP BY pickup_zone_id, pickup_zone;

