# Apache Iceberg & PySpark Production Patterns

Apply these patterns to all PySpark jobs and Apache Iceberg tables.

## 1. Pure Transform Separation & Typing

- Isolate business transformations in pure Python functions accepting and returning `pyspark.sql.DataFrame` (`def transform_events(df: DataFrame) -> DataFrame:`).
- Keep `SparkSession` creation, catalog config, secrets, and `.write` / `.writeTo` calls in an adapter/entrypoint module so transforms are locally unit-testable with minimal deterministic DataFrame fixtures.
- Declare explicit `pyspark.sql.types.StructType` schemas on ingestion; reject `inferSchema=True` in production.

## 2. Iceberg Table Design, Compaction & Evolution

- **Hidden Partitioning**: Use Iceberg partition transforms (`days(event_ts)`, `bucket(64, tenant_id)`, `truncate(8, id)`) instead of materialized string partition columns.
- **File Sizing & Maintenance**: Target `128MB–512MB` Parquet files (`write.target-file-size-bytes`); schedule `rewrite_data_files` compaction and `expire_snapshots` (plus `remove_orphan_files`) to prevent metadata bloat and small-file S3 amplification.
- **Schema Evolution**: Prefer additive nullable columns (`ALTER TABLE ... ADD COLUMN`) with Iceberg field IDs; treat column renames/type narrowing as breaking changes requiring a dual-write or versioned contract.

## 3. Idempotency, CDC Deduplication & Late Data

- **Deterministic CDC Deduplication**: Deduplicate batches before `MERGE INTO` using `ROW_NUMBER() OVER (PARTITION BY <pk> ORDER BY <event_ts> DESC, <seq_id> DESC) = 1`.
- **Watermark & Late-Arriving Data**: In streaming or incremental batch jobs, configure explicit watermark / lookback windows (`event_ts >= max_processed_ts - INTERVAL N HOURS`) and deterministic `MERGE INTO` `WHEN MATCHED AND source.event_ts >= target.event_ts` guards.
- **No Unbounded Shuffles / Skew**: Avoid `CartesianProduct`, `BroadcastNestedLoopJoin`, unpartitioned `Window`, and Python UDFs (`BatchEvalPython`). For skewed keys, use Adaptive Query Execution (`spark.sql.adaptive.skewJoin.enabled=true`) or explicit key salting.
- **Plan Verification**: Run `skills/staff-data-engineer/scripts/explain_plan_check.py` against `df.explain(mode="extended")` output before submitting to Quorum.
