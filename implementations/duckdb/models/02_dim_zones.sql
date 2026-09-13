CREATE OR REPLACE TABLE dim_zones AS
SELECT CAST(LocationID AS BIGINT) AS zone_id,
    CAST(Borough AS VARCHAR) AS borough,
    CAST(Zone AS VARCHAR) AS zone_name,
    CAST(service_zone AS VARCHAR) AS service_zone
FROM raw_zones;
