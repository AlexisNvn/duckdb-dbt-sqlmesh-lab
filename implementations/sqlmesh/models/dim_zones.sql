MODEL (name analytics.dim_zones, kind FULL, dialect duckdb, cron '@daily',
 audits (not_null(columns := (zone_id)), unique_values(columns := (zone_id))));

SELECT CAST(LocationID AS BIGINT) AS zone_id,
    CAST(Borough AS VARCHAR) AS borough,
    CAST(Zone AS VARCHAR) AS zone_name,
    CAST(service_zone AS VARCHAR) AS service_zone
FROM raw.raw_zones;

