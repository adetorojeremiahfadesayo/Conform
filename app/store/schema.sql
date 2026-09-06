-- CONFORM ClickHouse schema (applied idempotently at startup).
-- See docs/PRD.md §6. Seeded demo history is labelled via is_seeded.

CREATE TABLE IF NOT EXISTS node_runs (
    tenant         LowCardinality(String),
    campaign_id    LowCardinality(String),
    territory      LowCardinality(String),
    build_id       String,
    run_id         String,
    parent_run_id  Nullable(String),
    node_id        String,
    node_kind      LowCardinality(String),
    fingerprint    FixedString(64),
    inputs_hash    FixedString(64),
    recipe_hash    FixedString(64),
    status         LowCardinality(String),
    cache_hit      UInt8,
    attempt        UInt8,
    error_class    LowCardinality(String),
    is_seeded      UInt8,
    started_at     DateTime64(3),
    ended_at       Nullable(DateTime64(3)),
    duration_ms    UInt32,
    cost_usd       Decimal(12, 6),
    bytes_out      UInt64
) ENGINE = MergeTree
ORDER BY (tenant, campaign_id, started_at, node_id);

CREATE TABLE IF NOT EXISTS provider_calls (
    run_id        String,
    build_id      String,
    model         LowCardinality(String),
    modality      LowCardinality(String),
    region        LowCardinality(String),
    latency_ms    UInt32,
    input_tokens  UInt32,
    output_tokens UInt32,
    media_seconds Float32,
    cost_usd      Decimal(12, 6),
    http_status   UInt16,
    retryable     UInt8,
    is_seeded     UInt8,
    called_at     DateTime64(3)
) ENGINE = MergeTree
ORDER BY (called_at, model);

CREATE TABLE IF NOT EXISTS artifacts (
    fingerprint  FixedString(64),
    build_id     String,
    node_id      String,
    uri          String,
    sha256       FixedString(64),
    bytes        UInt64,
    content_type LowCardinality(String),
    verify_ok    Nullable(UInt8),
    verified_at  Nullable(DateTime64(3)),
    created_at   DateTime64(3)
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (fingerprint, node_id);

CREATE TABLE IF NOT EXISTS graph_closure (
    campaign_id LowCardinality(String),
    build_id    String,
    ancestor    String,
    descendant  String,
    depth       UInt8
) ENGINE = MergeTree
ORDER BY (campaign_id, build_id, ancestor, depth);

CREATE TABLE IF NOT EXISTS rule_findings (
    change_id   String,
    rule_id     LowCardinality(String),
    node_id     String,
    territory   LowCardinality(String),
    severity    LowCardinality(String),
    reason      String,
    detected_at DateTime64(3)
) ENGINE = MergeTree
ORDER BY (change_id, rule_id, node_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS build_savings_mv
ENGINE = SummingMergeTree
ORDER BY (campaign_id, build_id) AS
SELECT campaign_id,
       build_id,
       countIf(cache_hit = 1)         AS nodes_reused,
       countIf(cache_hit = 0)         AS nodes_rebuilt,
       sumIf(cost_usd, cache_hit = 0) AS spend_usd,
       sumIf(cost_usd, cache_hit = 1) AS avoided_usd
FROM node_runs
GROUP BY campaign_id, build_id;
