AUDIT (name trip_quality);
SELECT * FROM @this_model
WHERE pickup_datetime IS NULL OR dropoff_datetime IS NULL
    OR dropoff_datetime < pickup_datetime
    OR trip_distance IS NULL OR NOT isfinite(trip_distance) OR trip_distance < 0
    OR total_amount IS NULL OR NOT isfinite(total_amount) OR total_amount NOT BETWEEN 0 AND 10000
    OR trip_duration_minutes IS NULL OR trip_duration_minutes NOT BETWEEN 0 AND 1440
    OR pickup_zone_id NOT IN (SELECT zone_id FROM analytics.dim_zones)
    OR dropoff_zone_id NOT IN (SELECT zone_id FROM analytics.dim_zones);
