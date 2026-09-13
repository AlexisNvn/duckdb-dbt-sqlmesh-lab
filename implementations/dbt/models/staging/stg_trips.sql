WITH renamed AS (
    SELECT
        CAST(tpep_pickup_datetime AS TIMESTAMP) AS pickup_datetime,
        CAST(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_datetime,
        CAST(PULocationID AS BIGINT) AS pickup_zone_id,
        CAST(DOLocationID AS BIGINT) AS dropoff_zone_id,
        CAST(passenger_count AS DOUBLE) AS passenger_count,
        CAST(trip_distance AS DOUBLE) AS trip_distance,
        CASE payment_type
            WHEN 1 THEN 'credit_card' WHEN 2 THEN 'cash'
            WHEN 3 THEN 'no_charge' WHEN 4 THEN 'dispute'
            WHEN 5 THEN 'unknown' WHEN 6 THEN 'voided'
            ELSE 'unknown'
        END AS payment_type,
        CAST(fare_amount AS DOUBLE) AS fare_amount,
        CAST(tip_amount AS DOUBLE) AS tip_amount,
        CAST(tolls_amount AS DOUBLE) AS tolls_amount,
        CAST(total_amount AS DOUBLE) AS total_amount
    FROM {{ source('tlc', 'raw_yellow_trips') }}
), derived AS (
    SELECT *, CAST(pickup_datetime AS DATE) AS pickup_date,
        CAST(EXTRACT(HOUR FROM pickup_datetime) AS INTEGER) AS pickup_hour,
        EPOCH(dropoff_datetime - pickup_datetime) / 60.0 AS trip_duration_minutes
    FROM renamed
)
SELECT * FROM derived
WHERE pickup_datetime IS NOT NULL AND dropoff_datetime IS NOT NULL
    AND trip_duration_minutes BETWEEN 0 AND 1440
    AND isfinite(trip_distance) AND trip_distance >= 0
    AND isfinite(total_amount) AND total_amount BETWEEN 0 AND 10000
    AND isfinite(fare_amount) AND isfinite(tip_amount) AND isfinite(tolls_amount)
