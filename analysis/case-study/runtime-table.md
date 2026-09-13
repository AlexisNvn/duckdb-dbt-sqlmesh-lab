| Scenario | DuckDB alone | dbt + DuckDB | SQLMesh + DuckDB |
| --- | ---: | ---: | ---: |
| Initial build | 0.159 | 4.905 | 3.085 |
| No change | 0.159 | 5.144 | 2.788 |
| New data | 0.165 | 5.248 | 2.738 |
| Historical backfill | 0.176 | 5.382 | 2.717 |
| Business logic change | 0.167 | 5.179 | 3.109 |
| Development environment | 0.175 | 5.024 | 3.090 |
