# Synthetic TLC-shaped fixtures

These are invented records and zone names, not a sample of real passengers or
the official zone lookup. The tiny files are intentionally committed for offline CI.
The generator is `scripts/generate_fixtures.py`; run it through `python -m` from
the repository root. It uses the pinned DuckDB writer, no randomness or network.

Seven files represent January-July 2025, with 16 rows per month. Use January-June
for the initial build and July for new data. `cases.json` labels each row by its
zero-based file insertion index; these labels are test metadata, not raw columns.

Cases cover card/cash/unknown payment, zero distance/fare, null passengers,
missing pickup/dropoff, negative duration/distance/total, excessive total/duration,
invalid pickup/dropoff zone references, and a pickup exactly at the month boundary.
The three-zone lookup includes an unused zone. Numeric fields use DOUBLE to mimic
raw input; transformations will define rounding and quality thresholds in Phase 3.
Do not interpret every unusual case as invalid: zero-distance trips, for example,
are needed to exercise safe division. Expected transformed outputs come later.

Columns follow the names in the
[TLC yellow trip dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf),
including the 2025 `cbd_congestion_fee` field. The fixture is not a guarantee of
identical physical types across every real monthly TLC file. Deliberately altered
values need not reconcile to the raw total; these are quality-test inputs.
