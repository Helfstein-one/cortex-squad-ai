# FinOps, Cloud Compute & Token Cost Thresholds

Use these quantified thresholds to calibrate `finops-tuner` Conditional Veto decisions (`QuorumPolicy.CONDITIONAL_VETO_PERSONAS`).

## 1. Conditional Veto Severity Matrix

| Severity | Quorum Vote | Trigger Thresholds (Concrete Evidence Required) |
|---|---|---|
| **CRITICAL** | `veto` | Unbounded `CartesianProduct` / `BroadcastNestedLoopJoin`; unpartitioned full-table scan on large datasets (`PartitionFilters: []`); unbounded `collect()`/`toPandas()` on distributed DataFrames; infinite/unbounded retry loops or unbounded N+1 API/DB calls. |
| **HIGH** | `veto` | Static high-DPU allocation without Auto Scaling (`G.2X`/`G.4X` idle headroom); S3 small-file explosion (<16 MB average files or >10x PUT/GET amplification without compaction); unpartitioned `Window` causing executor OOM/disk spill; Python UDFs (`BatchEvalPython`) on hot large-scale transforms; unbounded LLM context injection (>8k tokens/step for small `1.5B–7B` models). |
| **MEDIUM** | `conditional_approve` | Suboptimal Parquet codec (uncompressed/GZIP instead of Snappy/ZSTD); missing Z-order/compaction schedule (target 128 MB–512 MB); missing HTTP connection pooling or pagination cap; redundant prompt prose increasing token spend 20%–50%. |
| **LOW** | `approve` (Advisory) | Minor constant/cache tuning, speculative execution hints, or marginal compression gains (<10% impact). |

## 2. AWS Glue / EMR / S3 & Iceberg Heuristics

- **Worker Scaling**: Enable Glue Auto Scaling (`--enable-auto-scaling true`) instead of fixed peak `NumberOfWorkers`; size worker type (`G.1X` vs `G.2X`) to observed `ShuffleWriteTime` and memory spill metrics.
- **S3 Request & Small-File Math**: Writing 10,000 tiny 1 MB files instead of ~256 MB Iceberg targets multiplies S3 `PUT`/`LIST`/`GET` requests and Parquet footer reads by >250x. Enforce `write.target-file-size-bytes` (128 MB–512 MB) and `rewrite_data_files`.
- **Compression & Metrics**: Mandate `Snappy` (low CPU latency) or `ZSTD` (higher ratio for cold/archival tiers); monitor `ExecutorDeserializeTime`, `ShuffleWriteTime`, and `DiskBytesSpilled`.

## 3. Service Compute & LLM Token Budgets

- **API / DB Compute**: Reject unpaginated `SELECT *` / unbounded list endpoints, in-loop DB/HTTP N+1 queries, and missing cache/TTL on repeated static lookups.
- **LLM Token Budgets**: Route classification/lint/check tasks to `1.5B–3B` local models (`<=2k` prompt tokens) and complex synthesis to `7B` / frontier models only when justified; load L3 assets on demand to avoid context rot and quadratic attention waste.
