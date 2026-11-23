"""Catalog of realistic project questions and the personas that must be routed to."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    question: str
    triggers: tuple[str, ...]
    expected_personas: frozenset[str]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "iceberg-cdc",
        "Ingest CDC streams into Iceberg idempotently",
        ("iceberg", "etl"),
        frozenset({"staff-data-engineer"}),
    ),
    Scenario(
        "pyspark-skew",
        "Fix data skew in a PySpark join",
        ("pyspark", "shuffle", "chaos"),
        frozenset({"staff-data-engineer", "finops-tuner", "chaos-qa-critic"}),
    ),
    Scenario(
        "lgpd-pii",
        "Expose customer API without leaking CPF",
        ("pii", "lgpd", "api"),
        frozenset({"data-steward", "staff-software-engineer"}),
    ),
    Scenario(
        "hex-api",
        "Design a hexagonal Python async API",
        ("clean-architecture", "async", "adr"),
        frozenset({"staff-software-engineer", "principal-architect"}),
    ),
    Scenario(
        "glue-cost",
        "Cut AWS Glue DPU cost by half",
        ("aws-glue", "cost"),
        frozenset({"finops-tuner"}),
    ),
    Scenario(
        "dbt-contracts",
        "Add dbt contracts to the staging layer",
        ("dbt", "schema"),
        frozenset({"staff-data-engineer"}),
    ),
    Scenario(
        "schema-drift",
        "Survive upstream schema drift and nulls",
        ("schema-drift", "nulls"),
        frozenset({"chaos-qa-critic"}),
    ),
    Scenario(
        "lineage",
        "Prove end to end lineage for audit",
        ("lineage", "governance"),
        frozenset({"data-steward"}),
    ),
    Scenario(
        "prd",
        "Turn a vague idea into acceptance criteria",
        ("requirements", "acceptance-criteria"),
        frozenset({"product-manager"}),
    ),
    Scenario(
        "retro",
        "Squad is stuck in a failure loop, run a retro",
        ("retro", "blocker"),
        frozenset({"scrum-master"}),
    ),
)
