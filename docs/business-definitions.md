# Shared business definitions (baseline A)

These definitions are the contract for later dbt and SQLMesh implementations.
They are benchmark choices, not TLC-endorsed cleaning rules.

Input selection uses monthly **file names**, not pickup-date filters. Rows whose
pickup dates fall outside their file's month remain eligible. This matters for
later incremental strategies: file month and event date are not interchangeable.
Duplicates are preserved because no reliable trip key is supplied.

Staging casts timestamps to timezone-naive TIMESTAMP (no UTC conversion), zone
IDs to BIGINT, and numeric measurements to DOUBLE. Passenger count can be null.
It rejects null pickup/dropoff timestamps; durations outside 0-1440 minutes;
null, nonfinite or negative distance; total amounts outside $0-$10,000 including
null/nonfinite values; and null/nonfinite fare, tip or toll amounts. Duration uses
elapsed seconds divided by 60, preserving fractional minutes. Endpoints are inclusive.
Negative component fares/tips/tolls are retained if the total passes; these may
represent adjustments. Malformed casts fail the build rather than silently erase rows.

Payment codes 1-6 map to credit_card, cash, no_charge, dispute, unknown and voided.
Other codes and null map to unknown. Pickup date and hour derive from pickup time.

The zone dimension retains every lookup row. Zone IDs must be unique and nonnull.
The fact table inner-joins both zone references: missing/unknown IDs are excluded
and counted separately from staging rejections. IDs that exist in the official
lookup remain valid even if their descriptive names indicate an unknown location.

Revenue A is fare_amount. Revenue B, for the later logic-change scenario, will be
fare_amount + tip_amount + tolls_amount. Neither is total_amount or net profit.
Revenue per mile is revenue / distance; zero distance gives NULL. Tip percentage
is 100 * tip_amount / fare_amount; zero fare gives NULL. SQL AVG ignores NULLs.
No deduplication, cash-tip imputation, currency rounding or ML filtering is applied.

Daily metrics group by pickup date. Extra fare_sum, tip_sum and distance_sum
columns support correct monthly aggregation. Monthly average fare, tip **amount**
and distance are trip-weighted (sum / total trips), not averages of daily averages.
Zone metrics cover the entire selected dataset, grouped by pickup ID and name.
Unused zones appear in dim_zones but do not get zero-filled metric rows.

Month-over-month growth is a fraction, e.g. 0.1 means 10%. The first month, gaps
in consecutive calendar months, and a zero previous denominator yield NULL.
Empty months/days are not synthesized. DOUBLE arithmetic may require a documented
numeric tolerance in future cross-framework comparisons.
