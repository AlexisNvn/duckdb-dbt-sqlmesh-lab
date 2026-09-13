MODEL (name analytics.fct_trips, kind FULL, dialect duckdb, cron '@daily',
 audits (trip_quality));

SELECT t.*, p.zone_name AS pickup_zone, d.zone_name AS dropoff_zone,
    t.fare_amount AS revenue,
    t.fare_amount / NULLIF(t.trip_distance, 0) AS revenue_per_mile,
    100.0 * t.tip_amount / NULLIF(t.fare_amount, 0) AS tip_percentage
FROM analytics.stg_trips t
JOIN analytics.dim_zones p ON t.pickup_zone_id = p.zone_id
JOIN analytics.dim_zones d ON t.dropoff_zone_id = d.zone_id;

