# dbt Model Contracts & Quality Gates

Apply these standards to all dbt staging, intermediate, and mart models.

## 1. Enforced Schema Contracts

- Enable `config.contract.enforced: true` on all staging and public mart models.
- Declare explicit column names, warehouse-exact `data_type`, and `constraints: [{type: not_null}]` / `primary_key` in YAML schema files.
- Cast and normalize types explicitly in `staging` (`TRY_CAST` / `CAST`, trimmed strings, UTC timestamps) so downstream models never rely on implicit type coercion.

## 2. Mandatory Data & Integrity Tests

- **Primary Keys**: Every model must enforce `unique` + `not_null` (or `dbt_utils.unique_combination_of_columns` for composite keys) with `severity: error`.
- **Referential Integrity**: Enforce `relationships` tests on foreign keys across critical fact-to-dimension joins (`severity: error`).
- **Domain Constraints**: Add `accepted_values` for enums/status codes and range/freshness checks (`loaded_at_field`, `warn_after`, `error_after`) on raw sources.
- **Severity Split**: Use `severity: error` for PK/FK/null-safety/PII invariants; reserve `severity: warn` strictly for soft statistical drift alerts.

## 3. Incremental Idempotency & Schema Evolution

- Configure `materialized='incremental'` with `incremental_strategy='merge'` and deterministic `unique_key` (plus lookback watermark window for late-arriving facts).
- Set `on_schema_change='append_new_columns'` or `'fail'` explicitly; never allow silent column drops or type-widening regressions in contracted models.
- Filter incremental runs with `{% if is_incremental() %}` bounded by an indexed/partitioned event timestamp rather than scanning full history.
