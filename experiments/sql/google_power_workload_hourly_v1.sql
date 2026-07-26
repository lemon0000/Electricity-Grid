WITH compact_extract AS (
  SELECT *
  FROM `__SOURCE_TABLE__`
),
usage_fragments_raw AS (
  SELECT *
  FROM compact_extract
  WHERE record_type = 'usage_fragment'
),
quality AS (
  SELECT
    COUNT(*) AS fragment_rows,
    COUNT(DISTINCT usage_group_id) AS usage_groups,
    COUNT(DISTINCT IF(
      exact_duplicate_count != 1,
      usage_group_id,
      NULL
    )) AS exact_duplicate_groups,
    COUNT(DISTINCT IF(
      cpu_value_conflict_count != 1,
      TO_JSON_STRING(STRUCT(
        start_time,
        end_time,
        collection_type,
        collection_id,
        instance_index,
        machine_id
      )),
      NULL
    )) AS cpu_value_conflict_keys,
    COUNT(DISTINCT IF(
      fragment_covered_us != expected_covered_us,
      usage_group_id,
      NULL
    )) AS coverage_mismatch_groups,
    COUNTIF(fragment_overlap) AS overlapping_fragments,
    COUNT(DISTINCT IF(
      priority_conflict_count > 1,
      usage_group_id,
      NULL
    )) AS ambiguous_priority_groups,
    COUNT(DISTINCT IF(
      priority IS NULL AND priority_conflict_count <= 1,
      usage_group_id,
      NULL
    )) AS unknown_priority_groups,
    COUNT(DISTINCT IF(
      priority_synthesized,
      usage_group_id,
      NULL
    )) AS synthesized_priority_groups,
    COUNT(DISTINCT IF(
      average_usage_cpus IS NULL,
      usage_group_id,
      NULL
    )) AS missing_cpu_groups,
    COUNT(DISTINCT IF(
      average_usage_cpus < 0
      OR IS_NAN(average_usage_cpus)
      OR IS_INF(average_usage_cpus),
      usage_group_id,
      NULL
    )) AS invalid_cpu_groups,
    COUNT(DISTINCT IF(
      priority < 0 OR priority > 450,
      usage_group_id,
      NULL
    )) AS invalid_priority_groups,
    COUNT(DISTINCT IF(
      collection_type NOT IN (0, 1),
      usage_group_id,
      NULL
    )) AS unexpected_collection_type_groups,
    COUNTIF(
      start_time IS NULL
      OR end_time IS NULL
      OR collection_type IS NULL
      OR collection_id IS NULL
      OR instance_index IS NULL
      OR machine_id IS NULL
      OR fragment_start IS NULL
      OR fragment_end IS NULL
      OR priority_conflict_count IS NULL
      OR priority_synthesized IS NULL
      OR exact_duplicate_count IS NULL
      OR cpu_value_conflict_count IS NULL
      OR usage_group_id IS NULL
      OR fragment_covered_us IS NULL
      OR expected_covered_us IS NULL
      OR fragment_overlap IS NULL
    ) AS malformed_fragment_rows,
    COUNTIF(
      priority_event_time IS NOT NULL
      AND priority_event_time > fragment_start
    ) AS future_priority_rows,
    COUNTIF(
      fragment_start < 0
      OR fragment_end > 86400000000
      OR fragment_end <= fragment_start
    ) AS out_of_window_fragment_rows
  FROM usage_fragments_raw
),
quality_checked AS (
  SELECT *
  FROM quality
  WHERE IF(
    fragment_rows > 0
    AND usage_groups > 0
    AND coverage_mismatch_groups = 0
    AND overlapping_fragments = 0
    AND invalid_cpu_groups = 0
    AND invalid_priority_groups = 0
    AND unexpected_collection_type_groups = 0
    AND malformed_fragment_rows = 0
    AND future_priority_rows = 0
    AND out_of_window_fragment_rows = 0,
    TRUE,
    ERROR(FORMAT(
      'Compact quality gate failed: duplicates=%d cpu_conflicts=%d coverage=%d overlaps=%d invalid_cpu=%d invalid_priority=%d collection_type=%d malformed=%d future=%d out_of_window=%d',
      exact_duplicate_groups,
      cpu_value_conflict_keys,
      coverage_mismatch_groups,
      overlapping_fragments,
      invalid_cpu_groups,
      invalid_priority_groups,
      unexpected_collection_type_groups,
      malformed_fragment_rows,
      future_priority_rows,
      out_of_window_fragment_rows
    ))
  )
),
usage_identity_fragments AS (
  SELECT
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    fragment_start,
    fragment_end,
    priority_event_time,
    priority,
    priority_conflict_count,
    priority_synthesized,
    TO_HEX(SHA256(TO_JSON_STRING(STRUCT(
      start_time,
      end_time,
      collection_type,
      collection_id,
      instance_index,
      machine_id
    )))) AS usage_identity_id,
    MIN(average_usage_cpus) AS average_cpu_lower,
    MAX(average_usage_cpus) AS average_cpu_upper,
    COUNT(*) AS cpu_variant_groups,
    MAX(cpu_value_conflict_count) AS declared_cpu_variant_groups,
    COUNTIF(average_usage_cpus IS NULL) AS missing_cpu_variants,
    MAX(exact_duplicate_count) AS maximum_exact_duplicate_count
  FROM usage_fragments_raw
  CROSS JOIN quality_checked
  GROUP BY
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    fragment_start,
    fragment_end,
    priority_event_time,
    priority,
    priority_conflict_count,
    priority_synthesized
),
identity_quality AS (
  SELECT COUNTIF(
    cpu_variant_groups != declared_cpu_variant_groups
  ) AS inconsistent_cpu_variant_fragments
  FROM usage_identity_fragments
),
usage_identity_checked AS (
  SELECT usage.*
  FROM usage_identity_fragments AS usage
  CROSS JOIN identity_quality AS audit
  WHERE IF(
    audit.inconsistent_cpu_variant_fragments = 0,
    TRUE,
    ERROR(FORMAT(
      'CPU variant interval mismatch: %d fragments',
      audit.inconsistent_cpu_variant_fragments
    ))
  )
),
hour_fragments AS (
  SELECT
    hour_index,
    usage.collection_type,
    CASE
      WHEN usage.priority_conflict_count > 1 THEN 'ambiguous'
      WHEN usage.priority IS NULL THEN 'unknown'
      WHEN usage.priority BETWEEN 0 AND 99 THEN '1_free'
      WHEN usage.priority BETWEEN 100 AND 115 THEN '2_beb'
      WHEN usage.priority BETWEEN 116 AND 119 THEN '3_mid'
      WHEN usage.priority BETWEEN 120 AND 359 THEN '4_production'
      ELSE '5_monitoring'
    END AS priority_tier,
    usage.usage_identity_id,
    usage.average_cpu_lower,
    usage.average_cpu_upper,
    usage.cpu_variant_groups,
    usage.missing_cpu_variants,
    usage.maximum_exact_duplicate_count,
    usage.priority_synthesized,
    GREATEST(
      0,
      LEAST(usage.fragment_end, (hour_index + 1) * 3600000000)
        - GREATEST(usage.fragment_start, hour_index * 3600000000)
    ) AS overlap_us
  FROM usage_identity_checked AS usage
  CROSS JOIN UNNEST(GENERATE_ARRAY(
    DIV(usage.fragment_start, 3600000000),
    DIV(usage.fragment_end - 1, 3600000000)
  )) AS hour_index
),
hourly_usage AS (
  SELECT
    hour_index,
    collection_type,
    priority_tier,
    SUM(IF(
      missing_cpu_variants = 0,
      average_cpu_lower * overlap_us,
      NULL
    )) / 3600000000 AS observed_cpu_ncu_lower,
    SUM(IF(
      missing_cpu_variants = 0,
      average_cpu_upper * overlap_us,
      NULL
    )) / 3600000000 AS observed_cpu_ncu_upper,
    SUM(IF(
      missing_cpu_variants = 0,
      average_cpu_lower * overlap_us,
      NULL
    )) / 1000000 AS observed_cpu_time_ncu_seconds_lower,
    SUM(IF(
      missing_cpu_variants = 0,
      average_cpu_upper * overlap_us,
      NULL
    )) / 1000000 AS observed_cpu_time_ncu_seconds_upper,
    SUM(IF(missing_cpu_variants = 0, overlap_us, 0)) / 1000000
      AS observed_cpu_overlap_seconds,
    SUM(IF(missing_cpu_variants > 0, overlap_us, 0)) / 1000000
      AS missing_cpu_overlap_seconds,
    SUM(IF(
      missing_cpu_variants = 0 AND cpu_variant_groups > 1,
      overlap_us,
      0
    )) / 1000000 AS cpu_conflict_overlap_seconds,
    COUNT(*) AS fragment_piece_count,
    COUNT(DISTINCT usage_identity_id) AS usage_group_count,
    COUNT(DISTINCT IF(
      cpu_variant_groups > 1,
      usage_identity_id,
      NULL
    )) AS cpu_conflict_usage_group_count,
    COUNT(DISTINCT IF(
      maximum_exact_duplicate_count > 1,
      usage_identity_id,
      NULL
    )) AS exact_duplicate_usage_group_count,
    SUM(IF(
      priority_synthesized AND missing_cpu_variants = 0,
      average_cpu_lower * overlap_us,
      0
    )) / 1000000 AS synthesized_cpu_time_ncu_seconds_lower,
    SUM(IF(
      priority_synthesized AND missing_cpu_variants = 0,
      average_cpu_upper * overlap_us,
      0
    )) / 1000000 AS synthesized_cpu_time_ncu_seconds_upper
  FROM hour_fragments
  WHERE overlap_us > 0
  GROUP BY hour_index, collection_type, priority_tier
),
hours AS (
  SELECT hour_index
  FROM UNNEST(GENERATE_ARRAY(0, 23)) AS hour_index
),
collection_types AS (
  SELECT collection_type
  FROM UNNEST([0, 1]) AS collection_type
),
priority_tiers AS (
  SELECT priority_tier
  FROM UNNEST([
    '1_free',
    '2_beb',
    '3_mid',
    '4_production',
    '5_monitoring',
    'ambiguous',
    'unknown'
  ]) AS priority_tier
),
hourly_complete AS (
  SELECT
    hour.hour_index,
    collection.collection_type,
    tier.priority_tier,
    COALESCE(usage.observed_cpu_ncu_lower, 0.0) AS observed_cpu_ncu_lower,
    COALESCE(usage.observed_cpu_ncu_upper, 0.0) AS observed_cpu_ncu_upper,
    COALESCE(usage.observed_cpu_time_ncu_seconds_lower, 0.0)
      AS observed_cpu_time_ncu_seconds_lower,
    COALESCE(usage.observed_cpu_time_ncu_seconds_upper, 0.0)
      AS observed_cpu_time_ncu_seconds_upper,
    COALESCE(usage.observed_cpu_overlap_seconds, 0)
      AS observed_cpu_overlap_seconds,
    COALESCE(usage.missing_cpu_overlap_seconds, 0)
      AS missing_cpu_overlap_seconds,
    COALESCE(usage.cpu_conflict_overlap_seconds, 0)
      AS cpu_conflict_overlap_seconds,
    COALESCE(usage.fragment_piece_count, 0) AS fragment_piece_count,
    COALESCE(usage.usage_group_count, 0) AS usage_group_count,
    COALESCE(usage.cpu_conflict_usage_group_count, 0)
      AS cpu_conflict_usage_group_count,
    COALESCE(usage.exact_duplicate_usage_group_count, 0)
      AS exact_duplicate_usage_group_count,
    COALESCE(usage.synthesized_cpu_time_ncu_seconds_lower, 0.0)
      AS synthesized_cpu_time_ncu_seconds_lower,
    COALESCE(usage.synthesized_cpu_time_ncu_seconds_upper, 0.0)
      AS synthesized_cpu_time_ncu_seconds_upper
  FROM hours AS hour
  CROSS JOIN collection_types AS collection
  CROSS JOIN priority_tiers AS tier
  LEFT JOIN hourly_usage AS usage
    USING (hour_index, collection_type, priority_tier)
),
machine_quality AS (
  SELECT
    COUNT(*) AS machine_event_rows,
    COUNT(DISTINCT machine_id) AS machines_with_day0_events,
    COUNTIF(COALESCE(machine_missing_data_reason, 0) != 0)
      AS machine_events_with_missing_data
  FROM compact_extract
  WHERE record_type = 'machine_event'
)
SELECT
  'hourly_usage' AS record_type,
  hour_index,
  collection_type,
  priority_tier,
  observed_cpu_ncu_lower,
  observed_cpu_ncu_upper,
  observed_cpu_time_ncu_seconds_lower,
  observed_cpu_time_ncu_seconds_upper,
  observed_cpu_overlap_seconds,
  missing_cpu_overlap_seconds,
  cpu_conflict_overlap_seconds,
  fragment_piece_count,
  usage_group_count,
  cpu_conflict_usage_group_count,
  exact_duplicate_usage_group_count,
  synthesized_cpu_time_ncu_seconds_lower,
  synthesized_cpu_time_ncu_seconds_upper,
  CAST(NULL AS INT64) AS machine_event_time,
  CAST(NULL AS INT64) AS machine_id,
  CAST(NULL AS INT64) AS machine_event_type,
  CAST(NULL AS FLOAT64) AS capacity_cpus,
  CAST(NULL AS INT64) AS machine_missing_data_reason,
  CAST(NULL AS STRING) AS audit_json
FROM hourly_complete

UNION ALL

SELECT
  'machine_event' AS record_type,
  CAST(NULL AS INT64) AS hour_index,
  CAST(NULL AS INT64) AS collection_type,
  CAST(NULL AS STRING) AS priority_tier,
  CAST(NULL AS FLOAT64) AS observed_cpu_ncu_lower,
  CAST(NULL AS FLOAT64) AS observed_cpu_ncu_upper,
  CAST(NULL AS FLOAT64) AS observed_cpu_time_ncu_seconds_lower,
  CAST(NULL AS FLOAT64) AS observed_cpu_time_ncu_seconds_upper,
  CAST(NULL AS INT64) AS observed_cpu_overlap_seconds,
  CAST(NULL AS INT64) AS missing_cpu_overlap_seconds,
  CAST(NULL AS INT64) AS cpu_conflict_overlap_seconds,
  CAST(NULL AS INT64) AS fragment_piece_count,
  CAST(NULL AS INT64) AS usage_group_count,
  CAST(NULL AS INT64) AS cpu_conflict_usage_group_count,
  CAST(NULL AS INT64) AS exact_duplicate_usage_group_count,
  CAST(NULL AS FLOAT64) AS synthesized_cpu_time_ncu_seconds_lower,
  CAST(NULL AS FLOAT64) AS synthesized_cpu_time_ncu_seconds_upper,
  machine_event_time,
  machine_id,
  machine_event_type,
  capacity_cpus,
  machine_missing_data_reason,
  CAST(NULL AS STRING) AS audit_json
FROM compact_extract
CROSS JOIN quality_checked
WHERE record_type = 'machine_event'

UNION ALL

SELECT
  'audit' AS record_type,
  CAST(NULL AS INT64) AS hour_index,
  CAST(NULL AS INT64) AS collection_type,
  CAST(NULL AS STRING) AS priority_tier,
  CAST(NULL AS FLOAT64) AS observed_cpu_ncu_lower,
  CAST(NULL AS FLOAT64) AS observed_cpu_ncu_upper,
  CAST(NULL AS FLOAT64) AS observed_cpu_time_ncu_seconds_lower,
  CAST(NULL AS FLOAT64) AS observed_cpu_time_ncu_seconds_upper,
  CAST(NULL AS INT64) AS observed_cpu_overlap_seconds,
  CAST(NULL AS INT64) AS missing_cpu_overlap_seconds,
  CAST(NULL AS INT64) AS cpu_conflict_overlap_seconds,
  CAST(NULL AS INT64) AS fragment_piece_count,
  CAST(NULL AS INT64) AS usage_group_count,
  CAST(NULL AS INT64) AS cpu_conflict_usage_group_count,
  CAST(NULL AS INT64) AS exact_duplicate_usage_group_count,
  CAST(NULL AS FLOAT64) AS synthesized_cpu_time_ncu_seconds_lower,
  CAST(NULL AS FLOAT64) AS synthesized_cpu_time_ncu_seconds_upper,
  CAST(NULL AS INT64) AS machine_event_time,
  CAST(NULL AS INT64) AS machine_id,
  CAST(NULL AS INT64) AS machine_event_type,
  CAST(NULL AS FLOAT64) AS capacity_cpus,
  CAST(NULL AS INT64) AS machine_missing_data_reason,
  TO_JSON_STRING(STRUCT(
    quality_checked AS usage_quality,
    identity_quality AS cpu_variant_quality,
    machine_quality AS machine_quality
  )) AS audit_json
FROM quality_checked
CROSS JOIN identity_quality
CROSS JOIN machine_quality

ORDER BY
  record_type,
  hour_index,
  collection_type,
  priority_tier,
  machine_event_time,
  machine_id,
  machine_event_type,
  capacity_cpus,
  machine_missing_data_reason,
  audit_json
