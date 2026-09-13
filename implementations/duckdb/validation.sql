SELECT 'zone_keys' AS check_name,
    (SELECT COUNT(*) - COUNT(DISTINCT zone_id) FROM dim_zones) AS failures
UNION ALL
SELECT 'timestamps', COUNT(*) FROM fct_trips
WHERE pickup_datetime IS NULL OR dropoff_datetime IS NULL
    OR dropoff_datetime < pickup_datetime
UNION ALL
SELECT 'distance', COUNT(*) FROM fct_trips
WHERE trip_distance IS NULL OR NOT isfinite(trip_distance) OR trip_distance < 0
UNION ALL
SELECT 'total_amount', COUNT(*) FROM fct_trips
WHERE total_amount IS NULL OR NOT isfinite(total_amount) OR total_amount NOT BETWEEN 0 AND 10000
UNION ALL
SELECT 'duration', COUNT(*) FROM fct_trips
WHERE trip_duration_minutes IS NULL OR trip_duration_minutes NOT BETWEEN 0 AND 1440
UNION ALL
SELECT 'zone_references', COUNT(*) FROM fct_trips t
WHERE NOT EXISTS (SELECT 1 FROM dim_zones z WHERE z.zone_id = t.pickup_zone_id)
    OR NOT EXISTS (SELECT 1 FROM dim_zones z WHERE z.zone_id = t.dropoff_zone_id)
UNION ALL
SELECT 'daily_trip_count', ABS(
    (SELECT COUNT(*) FROM fct_trips) - COALESCE((SELECT SUM(trip_count) FROM daily_metrics), 0))
UNION ALL
SELECT 'monthly_trip_count', ABS(
    (SELECT COUNT(*) FROM fct_trips) - COALESCE((SELECT SUM(trip_count) FROM monthly_metrics), 0))
UNION ALL
SELECT 'zone_trip_count', ABS(
    (SELECT COUNT(*) FROM fct_trips) - COALESCE((SELECT SUM(trip_count) FROM zone_metrics), 0));
