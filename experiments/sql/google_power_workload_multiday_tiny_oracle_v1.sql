WITH
usage_raw AS (
  SELECT *
  FROM UNNEST([
    STRUCT(600000000 AS start_time, 4200000000 AS end_time, 0 AS collection_type, 10 AS collection_id, 0 AS instance_index, 1 AS machine_id, CAST('0.5' AS BIGNUMERIC) AS average_usage_cpus),
    STRUCT(600000000, 4200000000, 0, 10, 0, 1, CAST('0.5' AS BIGNUMERIC)),
    STRUCT(600000000, 4200000000, 0, 10, 0, 1, CAST('0.6' AS BIGNUMERIC)),
    STRUCT(600000000, 4200000000, 0, 20, 0, 2, CAST('0.25' AS BIGNUMERIC))
  ])
),
usage_values AS (
  SELECT
    *,
    COUNT(*) AS exact_duplicate_count
  FROM usage_raw
  GROUP BY start_time, end_time, collection_type, collection_id, instance_index, machine_id, average_usage_cpus
),
usage_rows AS (
  SELECT
    *,
    COUNT(*) OVER (
      PARTITION BY start_time, end_time, collection_type, collection_id, instance_index, machine_id
    ) AS cpu_value_conflict_count
  FROM usage_values
),
event_raw AS (
  SELECT *
  FROM UNNEST([
    STRUCT(0 AS event_time, 0 AS collection_type, 10 AS collection_id, 0 AS instance_index, 1 AS machine_id, CAST(50 AS INT64) AS priority),
    STRUCT(1800000000, 0, 10, 0, 1, CAST(NULL AS INT64)),
    STRUCT(3000000000, 0, 10, 0, 1, CAST(120 AS INT64)),
    STRUCT(3000000000, 0, 10, 0, 1, CAST(130 AS INT64))
  ])
),
priority_points AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    event_time,
    IF(
      COUNTIF(priority IS NULL) = 0 AND COUNT(DISTINCT priority) = 1,
      MIN(priority),
      CAST(NULL AS INT64)
    ) AS priority,
    COUNT(DISTINCT priority) + IF(COUNTIF(priority IS NULL) > 0, 1, 0) AS priority_conflict_count
  FROM event_raw
  GROUP BY collection_type, collection_id, instance_index, machine_id, event_time
),
priority_intervals AS (
  SELECT
    *,
    event_time AS interval_start,
    LEAD(event_time, 1, 4200000000) OVER (
      PARTITION BY collection_type, collection_id, instance_index, machine_id
      ORDER BY event_time
    ) AS interval_end
  FROM priority_points
),
fragments AS (
  SELECT
    usage.*,
    GREATEST(usage.start_time, COALESCE(priority.interval_start, 600000000), 600000000) AS fragment_start,
    LEAST(usage.end_time, COALESCE(priority.interval_end, 4200000000), 4200000000) AS fragment_end,
    priority.priority,
    COALESCE(priority.priority_conflict_count, 0) AS priority_conflict_count
  FROM usage_rows AS usage
  LEFT JOIN priority_intervals AS priority
    ON usage.collection_type = priority.collection_type
    AND usage.collection_id = priority.collection_id
    AND usage.instance_index = priority.instance_index
    AND usage.machine_id = priority.machine_id
    AND priority.interval_end > usage.start_time
    AND priority.interval_start < usage.end_time
),
identity_fragments AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    fragment_start,
    fragment_end,
    priority,
    priority_conflict_count,
    MIN(average_usage_cpus) AS cpu_lower,
    MAX(average_usage_cpus) AS cpu_upper,
    COUNT(*) AS cpu_variant_groups,
    MAX(exact_duplicate_count) AS maximum_exact_duplicate_count
  FROM fragments
  WHERE fragment_end > fragment_start
  GROUP BY collection_type, collection_id, instance_index, machine_id, fragment_start, fragment_end, priority, priority_conflict_count
),
tiered AS (
  SELECT
    CASE
      WHEN priority_conflict_count > 1 THEN 'ambiguous'
      WHEN priority IS NULL THEN 'unknown'
      WHEN priority BETWEEN 0 AND 99 THEN '1_free'
      WHEN priority BETWEEN 100 AND 115 THEN '2_beb'
      WHEN priority BETWEEN 116 AND 119 THEN '3_mid'
      WHEN priority BETWEEN 120 AND 359 THEN '4_production'
      ELSE '5_monitoring'
    END AS priority_tier,
    cpu_lower,
    cpu_upper,
    fragment_end - fragment_start AS overlap_us,
    cpu_variant_groups,
    maximum_exact_duplicate_count
  FROM identity_fragments
)
SELECT
  priority_tier,
  FORMAT('%.6f', SUM(cpu_lower * overlap_us) / CAST(1000000 AS BIGNUMERIC)) AS cpu_time_lower,
  FORMAT('%.6f', SUM(cpu_upper * overlap_us) / CAST(1000000 AS BIGNUMERIC)) AS cpu_time_upper,
  COUNTIF(cpu_variant_groups > 1) AS conflict_fragments,
  COUNTIF(maximum_exact_duplicate_count > 1) AS exact_duplicate_fragments
FROM tiered
GROUP BY priority_tier
ORDER BY priority_tier
