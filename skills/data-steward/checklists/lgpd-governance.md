# LGPD / GDPR, PII, Secrets & Governance Checklist

Audit every artifact against these mandatory gates before granting Quorum approval:

- [ ] **PII Classification & Minimization**: All personal/sensitive fields (CPF, CNPJ, email, phone, card/PAN, address, IP, health/biometric data) are explicitly classified and unused PII columns are dropped at ingestion.
- [ ] **Deterministic Hashing / Tokenization**: Direct identifiers leaving raw/restricted zones use keyed cryptographic hashing (`HMAC-SHA256` with secret salt from vault/env) or reversible vault tokenization — never unsalted MD5/SHA1 or plaintext PII.
- [ ] **Secrets & Credentials Hygiene**: Zero hardcoded API keys, passwords, JWT secrets, private keys, or credentialed connection strings in source code, YAML, SQL, or example configs; zero secrets or raw PII emitted to logs or exception tracebacks.
- [ ] **IAM Least Privilege & Access Control**: Service roles, table grants, and S3/DB permissions follow least privilege (no wildcard `*` resource/action grants on PII stores); column/row-level masking enforced for non-privileged consumers.
- [ ] **Retention, TTL & Right to Erasure**: Raw/bronze and analytical PII tables declare explicit retention/TTL policies and support deterministic subject deletion (`DELETE` / Iceberg row-level delete or crypto-shredding) within LGPD/GDPR SLA windows.
- [ ] **End-to-End Lineage & Auditability**: Dataset lineage (source -> transform -> sink), data owner, legal basis, and schema/classification tags are recorded for audit trails.
