"""Local DuckDB gateway; override the database with BENCH_SQLMESH_DATABASE."""

import os
from pathlib import Path

from sqlmesh.core.config import Config, DuckDBConnectionConfig, GatewayConfig, ModelDefaultsConfig

ROOT = Path(__file__).resolve().parents[2]
config = Config(
    gateways={
        "local": GatewayConfig(
            connection=DuckDBConnectionConfig(
                database=os.environ.get(
                    "BENCH_SQLMESH_DATABASE", str(ROOT / "data/generated/mesh_warehouse.duckdb")
                ),
                concurrent_tasks=1,
            )
        )
    },
    default_gateway="local",
    model_defaults=ModelDefaultsConfig(dialect="duckdb", start="2025-01-01"),
    disable_anonymized_analytics=True,
)
