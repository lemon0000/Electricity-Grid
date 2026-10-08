WITH
pdu_machines AS (
  SELECT DISTINCT machine_id
  FROM `google.com:google-cluster-data.powerdata_2019.machine_to_pdu_mapping`
  WHERE cell = @cell AND pdu = @pdu
),
usage_prefilter AS (
  SELECT
    usage.start_time,
    usage.end_time,
    usage.collection_type,
    usage.collection_id,
    usage.instance_index,
    usage.machine_id,
    usage.average_usage.cpus AS average_usage_cpus_float
  FROM `google.com:google-cluster-data.clusterdata_2019_f.instance_usage` AS usage
  JOIN pdu_machines USING (machine_id)
  WHERE usage.alloc_collection_id IS NULL OR usage.alloc_collection_id = 0
),
usage_prefilter_audit AS (
  SELECT
    COUNTIF(
      start_time IS NULL
      OR end_time IS NULL
      OR end_time <= start_time
      OR collection_type IS NULL
      OR collection_id IS NULL
      OR instance_index IS NULL
      OR machine_id IS NULL
    ) AS incomplete_or_invalid_key_rows,
    COUNTIF(
      average_usage_cpus_float IS NOT NULL
      AND (
        IS_NAN(average_usage_cpus_float)
        OR IS_INF(average_usage_cpus_float)
        OR average_usage_cpus_float < 0
        OR SAFE_CAST(average_usage_cpus_float AS BIGNUMERIC) IS NULL
      )
    ) AS invalid_cpu_source_rows
  FROM usage_prefilter
),
usage_source AS (
  SELECT
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    SAFE_CAST(average_usage_cpus_float AS BIGNUMERIC) AS average_usage_cpus
  FROM usage_prefilter
  CROSS JOIN usage_prefilter_audit AS audit
  WHERE IF(
    audit.incomplete_or_invalid_key_rows = 0
    AND audit.invalid_cpu_source_rows = 0,
    TRUE,
    ERROR(FORMAT(
      'Usage prefilter failed: invalid_key_or_time=%d invalid_cpu=%d',
      audit.incomplete_or_invalid_key_rows,
      audit.invalid_cpu_source_rows
    ))
  )
    AND end_time > @window_start_us
    AND start_time < @window_end_us
),
usage_value_groups AS (
  SELECT
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    average_usage_cpus,
    COUNT(*) AS exact_duplicate_count,
    TO_HEX(SHA256(TO_JSON_STRING(STRUCT(
      start_time,
      end_time,
      collection_type,
      collection_id,
      instance_index,
      machine_id,
      average_usage_cpus
    )))) AS usage_group_id
  FROM usage_source
  GROUP BY
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    average_usage_cpus
),
usage_rows AS (
  SELECT
    *,
    COUNT(*) OVER (
      PARTITION BY
        start_time,
        end_time,
        collection_type,
        collection_id,
        instance_index,
        machine_id
    ) AS cpu_value_conflict_count
  FROM usage_value_groups
),
priority_event_prefilter AS (
  SELECT
    event.collection_type,
    event.collection_id,
    event.instance_index,
    event.machine_id,
    event.time AS event_time,
    event.priority,
    event.missing_type
  FROM `google.com:google-cluster-data.clusterdata_2019_f.instance_events` AS event
  JOIN pdu_machines USING (machine_id)
  WHERE event.alloc_collection_id IS NULL OR event.alloc_collection_id = 0
),
priority_event_source AS (
  SELECT *
  FROM priority_event_prefilter
  WHERE event_time IS NOT NULL
    AND event_time < @window_end_us
    AND collection_type IS NOT NULL
    AND collection_id IS NOT NULL
    AND instance_index IS NOT NULL
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
    COUNT(DISTINCT priority) + IF(COUNTIF(priority IS NULL) > 0, 1, 0)
      AS priority_conflict_count,
    COUNTIF(priority IS NULL) > 0 AS priority_missing_at_point,
    LOGICAL_OR(COALESCE(missing_type, 0) != 0) AS priority_synthesized
  FROM priority_event_source
  GROUP BY collection_type, collection_id, instance_index, machine_id, event_time
),
ordered_priority_intervals AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    event_time AS interval_start,
    LEAD(event_time, 1, @window_end_us) OVER (
      PARTITION BY collection_type, collection_id, instance_index, machine_id
      ORDER BY event_time
    ) AS interval_end,
    event_time AS priority_event_time,
    priority,
    priority_conflict_count,
    priority_missing_at_point,
    priority_synthesized
  FROM priority_points
),
initial_priority_intervals AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    @window_start_us AS interval_start,
    MIN(event_time) AS interval_end,
    CAST(NULL AS INT64) AS priority_event_time,
    CAST(NULL AS INT64) AS priority,
    0 AS priority_conflict_count,
    TRUE AS priority_missing_at_point,
    FALSE AS priority_synthesized
  FROM priority_points
  GROUP BY collection_type, collection_id, instance_index, machine_id
  HAVING interval_end > @window_start_us
),
priority_intervals AS (
  SELECT * FROM initial_priority_intervals
  UNION ALL
  SELECT * FROM ordered_priority_intervals
  WHERE interval_end > interval_start
),
usage_fragments AS (
  SELECT
    usage.start_time,
    usage.end_time,
    usage.collection_type,
    usage.collection_id,
    usage.instance_index,
    usage.machine_id,
    usage.average_usage_cpus,
    GREATEST(
      usage.start_time,
      COALESCE(priority_interval.interval_start, @window_start_us),
      @window_start_us
    ) AS fragment_start,
    LEAST(
      usage.end_time,
      COALESCE(priority_interval.interval_end, @window_end_us),
      @window_end_us
    ) AS fragment_end,
    priority_interval.priority_event_time,
    priority_interval.priority,
    COALESCE(priority_interval.priority_conflict_count, 0) AS priority_conflict_count,
    COALESCE(priority_interval.priority_missing_at_point, TRUE) AS priority_missing_at_point,
    COALESCE(priority_interval.priority_synthesized, FALSE) AS priority_synthesized,
    usage.exact_duplicate_count,
    usage.cpu_value_conflict_count,
    usage.usage_group_id
  FROM usage_rows AS usage
  LEFT JOIN priority_intervals AS priority_interval
    ON usage.collection_type = priority_interval.collection_type
    AND usage.collection_id = priority_interval.collection_id
    AND usage.instance_index = priority_interval.instance_index
    AND usage.machine_id = priority_interval.machine_id
    AND priority_interval.interval_end > usage.start_time
    AND priority_interval.interval_start < usage.end_time
    AND priority_interval.interval_end > @window_start_us
    AND priority_interval.interval_start < @window_end_us
),
usage_fragments_with_previous AS (
  SELECT
    *,
    LAG(fragment_end) OVER (
      PARTITION BY usage_group_id
      ORDER BY fragment_start, fragment_end, priority_event_time, priority
    ) AS previous_fragment_end
  FROM usage_fragments
  WHERE fragment_end > fragment_start
),
usage_fragments_audited AS (
  SELECT
    *,
    SUM(fragment_end - fragment_start) OVER (
      PARTITION BY usage_group_id
    ) AS fragment_covered_us,
    LEAST(end_time, @window_end_us) - GREATEST(start_time, @window_start_us) AS expected_covered_us,
    COALESCE(previous_fragment_end > fragment_start, FALSE) AS fragment_overlap
  FROM usage_fragments_with_previous
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
    priority_missing_at_point,
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
  FROM usage_fragments_audited
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
    priority_missing_at_point,
    priority_synthesized
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
      LEAST(usage.fragment_end, @window_start_us + (hour_index + 1) * 3600000000)
        - GREATEST(usage.fragment_start, @window_start_us + hour_index * 3600000000)
    ) AS overlap_us
  FROM usage_identity_fragments AS usage
  CROSS JOIN UNNEST(GENERATE_ARRAY(
    DIV(usage.fragment_start - @window_start_us, 3600000000),
    DIV(usage.fragment_end - 1 - @window_start_us, 3600000000)
  )) AS hour_index
),
hourly_usage AS (
  SELECT
    hour_index,
    collection_type,
    priority_tier,
    SUM(IF(missing_cpu_variants = 0, average_cpu_lower * overlap_us, NULL))
      / CAST(3600000000 AS BIGNUMERIC)
      AS observed_cpu_ncu_lower,
    SUM(IF(missing_cpu_variants = 0, average_cpu_upper * overlap_us, NULL))
      / CAST(3600000000 AS BIGNUMERIC)
      AS observed_cpu_ncu_upper,
    SUM(IF(missing_cpu_variants = 0, average_cpu_lower * overlap_us, NULL))
      / CAST(1000000 AS BIGNUMERIC)
      AS observed_cpu_time_ncu_seconds_lower,
    SUM(IF(missing_cpu_variants = 0, average_cpu_upper * overlap_us, NULL))
      / CAST(1000000 AS BIGNUMERIC)
      AS observed_cpu_time_ncu_seconds_upper,
    CAST(SUM(IF(missing_cpu_variants = 0, overlap_us, 0)) AS BIGNUMERIC)
      / CAST(1000000 AS BIGNUMERIC) AS observed_cpu_overlap_seconds,
    CAST(SUM(IF(missing_cpu_variants > 0, overlap_us, 0)) AS BIGNUMERIC)
      / CAST(1000000 AS BIGNUMERIC) AS missing_cpu_overlap_seconds,
    CAST(SUM(IF(missing_cpu_variants = 0 AND cpu_variant_groups > 1, overlap_us, 0)) AS BIGNUMERIC)
      / CAST(1000000 AS BIGNUMERIC)
      AS cpu_conflict_overlap_seconds,
    COUNT(*) AS fragment_piece_count,
    COUNT(DISTINCT usage_identity_id) AS usage_group_count,
    COUNT(DISTINCT IF(cpu_variant_groups > 1, usage_identity_id, NULL)) AS cpu_conflict_usage_group_count,
    COUNT(DISTINCT IF(maximum_exact_duplicate_count > 1, usage_identity_id, NULL))
      AS exact_duplicate_usage_group_count,
    SUM(IF(
      priority_synthesized AND missing_cpu_variants = 0,
      average_cpu_lower * overlap_us,
      CAST(0 AS BIGNUMERIC)
    )) / CAST(1000000 AS BIGNUMERIC)
      AS synthesized_cpu_time_ncu_seconds_lower,
    SUM(IF(
      priority_synthesized AND missing_cpu_variants = 0,
      average_cpu_upper * overlap_us,
      CAST(0 AS BIGNUMERIC)
    )) / CAST(1000000 AS BIGNUMERIC)
      AS synthesized_cpu_time_ncu_seconds_upper
  FROM hour_fragments
  WHERE overlap_us > 0
  GROUP BY hour_index, collection_type, priority_tier
),
hours AS (
  SELECT hour_index
  FROM UNNEST(GENERATE_ARRAY(0, DIV(@window_end_us - @window_start_us, 3600000000) - 1)) AS hour_index
),
collection_types AS (
  SELECT collection_type FROM UNNEST([0, 1]) AS collection_type
),
priority_tiers AS (
  SELECT priority_tier
  FROM UNNEST(['1_free', '2_beb', '3_mid', '4_production', '5_monitoring', 'ambiguous', 'unknown'])
    AS priority_tier
),
hourly_complete AS (
  SELECT
    hour.hour_index,
    collection.collection_type,
    tier.priority_tier,
    COALESCE(usage.observed_cpu_ncu_lower, CAST(0 AS BIGNUMERIC)) AS observed_cpu_ncu_lower,
    COALESCE(usage.observed_cpu_ncu_upper, CAST(0 AS BIGNUMERIC)) AS observed_cpu_ncu_upper,
    COALESCE(usage.observed_cpu_time_ncu_seconds_lower, CAST(0 AS BIGNUMERIC))
      AS observed_cpu_time_ncu_seconds_lower,
    COALESCE(usage.observed_cpu_time_ncu_seconds_upper, CAST(0 AS BIGNUMERIC))
      AS observed_cpu_time_ncu_seconds_upper,
    COALESCE(usage.observed_cpu_overlap_seconds, CAST(0 AS BIGNUMERIC)) AS observed_cpu_overlap_seconds,
    COALESCE(usage.missing_cpu_overlap_seconds, CAST(0 AS BIGNUMERIC)) AS missing_cpu_overlap_seconds,
    COALESCE(usage.cpu_conflict_overlap_seconds, CAST(0 AS BIGNUMERIC)) AS cpu_conflict_overlap_seconds,
    COALESCE(usage.fragment_piece_count, 0) AS fragment_piece_count,
    COALESCE(usage.usage_group_count, 0) AS usage_group_count,
    COALESCE(usage.cpu_conflict_usage_group_count, 0) AS cpu_conflict_usage_group_count,
    COALESCE(usage.exact_duplicate_usage_group_count, 0) AS exact_duplicate_usage_group_count,
    COALESCE(usage.synthesized_cpu_time_ncu_seconds_lower, CAST(0 AS BIGNUMERIC))
      AS synthesized_cpu_time_ncu_seconds_lower,
    COALESCE(usage.synthesized_cpu_time_ncu_seconds_upper, CAST(0 AS BIGNUMERIC))
      AS synthesized_cpu_time_ncu_seconds_upper
  FROM hours AS hour
  CROSS JOIN collection_types AS collection
  CROSS JOIN priority_tiers AS tier
  LEFT JOIN hourly_usage AS usage USING (hour_index, collection_type, priority_tier)
),
source_audit AS (
  SELECT
    (SELECT COUNT(*) FROM pdu_machines) AS pdu_machine_count,
    (SELECT COUNT(*) FROM usage_source) AS usage_source_rows,
    (SELECT COUNT(*) FROM usage_value_groups) AS distinct_usage_value_groups,
    (SELECT COUNTIF(exact_duplicate_count > 1) FROM usage_value_groups) AS exact_duplicate_value_groups,
    (SELECT COUNT(*) FROM priority_event_source) AS selected_priority_event_rows,
    (SELECT COUNTIF(
      event_time IS NULL
      OR collection_type IS NULL
      OR collection_id IS NULL
      OR instance_index IS NULL
    ) FROM priority_event_prefilter) AS unusable_priority_event_rows,
    (SELECT COUNTIF(priority_conflict_count > 1) FROM priority_points) AS conflicting_priority_points,
    (SELECT COUNTIF(priority_missing_at_point) FROM priority_points) AS priority_points_with_missing_value,
    (SELECT incomplete_or_invalid_key_rows FROM usage_prefilter_audit) AS incomplete_or_invalid_key_rows,
    (SELECT invalid_cpu_source_rows FROM usage_prefilter_audit) AS invalid_cpu_source_rows
),
fragment_audit AS (
  SELECT
    COUNT(*) AS usage_fragment_rows,
    COUNT(DISTINCT usage_group_id) AS usage_groups,
    COUNT(DISTINCT IF(fragment_covered_us != expected_covered_us, usage_group_id, NULL))
      AS coverage_mismatch_groups,
    COUNTIF(fragment_overlap) AS overlapping_fragments,
    COUNTIF(priority_event_time IS NOT NULL AND priority_event_time > fragment_start) AS future_priority_rows,
    COUNTIF(fragment_start < @window_start_us OR fragment_end > @window_end_us OR fragment_end <= fragment_start)
      AS out_of_window_fragment_rows,
    COUNT(DISTINCT IF(priority_conflict_count > 1, usage_group_id, NULL)) AS ambiguous_priority_groups,
    COUNT(DISTINCT IF(priority IS NULL AND priority_conflict_count <= 1, usage_group_id, NULL))
      AS unknown_priority_groups,
    COUNT(DISTINCT IF(priority_synthesized, usage_group_id, NULL)) AS synthesized_priority_groups
  FROM usage_fragments_audited
),
identity_audit AS (
  SELECT
    COUNTIF(cpu_variant_groups != declared_cpu_variant_groups) AS inconsistent_cpu_variant_fragments,
    COUNT(DISTINCT IF(cpu_variant_groups > 1, usage_identity_id, NULL)) AS cpu_conflict_usage_groups,
    COUNT(DISTINCT IF(missing_cpu_variants > 0, usage_identity_id, NULL)) AS missing_cpu_usage_groups,
    COUNT(DISTINCT IF(
      average_cpu_lower < 0
      OR average_cpu_upper < 0,
      usage_identity_id,
      NULL
    )) AS invalid_cpu_usage_groups,
    COUNTIF(collection_type NOT IN (0, 1)) AS unexpected_collection_type_fragments,
    COUNTIF(priority IS NOT NULL AND (priority < 0 OR priority > 450)) AS invalid_priority_fragments
  FROM usage_identity_fragments
),
quality_checked AS (
  SELECT source.*, fragment.*, identity.*
  FROM source_audit AS source
  CROSS JOIN fragment_audit AS fragment
  CROSS JOIN identity_audit AS identity
  WHERE IF(
    source.pdu_machine_count = @expected_machine_count
    AND source.usage_source_rows > 0
    AND source.distinct_usage_value_groups > 0
    AND source.incomplete_or_invalid_key_rows = 0
    AND source.invalid_cpu_source_rows = 0
    AND fragment.usage_groups > 0
    AND fragment.coverage_mismatch_groups = 0
    AND fragment.overlapping_fragments = 0
    AND fragment.future_priority_rows = 0
    AND fragment.out_of_window_fragment_rows = 0
    AND identity.inconsistent_cpu_variant_fragments = 0
    AND identity.invalid_cpu_usage_groups = 0
    AND identity.unexpected_collection_type_fragments = 0
    AND identity.invalid_priority_fragments = 0,
    TRUE,
    ERROR(FORMAT(
      'Full-month quality gate failed: machines=%d usage=%d groups=%d invalid_key=%d source_cpu=%d coverage=%d overlap=%d future=%d out_of_window=%d variants=%d invalid_cpu=%d collection_type=%d priority=%d',
      source.pdu_machine_count,
      source.usage_source_rows,
      source.distinct_usage_value_groups,
      source.incomplete_or_invalid_key_rows,
      source.invalid_cpu_source_rows,
      fragment.coverage_mismatch_groups,
      fragment.overlapping_fragments,
      fragment.future_priority_rows,
      fragment.out_of_window_fragment_rows,
      identity.inconsistent_cpu_variant_fragments,
      identity.invalid_cpu_usage_groups,
      identity.unexpected_collection_type_fragments,
      identity.invalid_priority_fragments
    ))
  )
),
audit_payload AS (
  SELECT TO_JSON_STRING(quality_checked) AS audit_json
  FROM quality_checked
)
SELECT
  'hourly_usage' AS record_type,
  hour_index,
  @window_start_us + hour_index * 3600000000 AS raw_interval_start_us,
  @window_start_us + (hour_index + 1) * 3600000000 AS raw_interval_end_us,
  collection_type,
  priority_tier,
  FORMAT('%.12f', observed_cpu_ncu_lower) AS observed_cpu_ncu_lower,
  FORMAT('%.12f', observed_cpu_ncu_upper) AS observed_cpu_ncu_upper,
  FORMAT('%.12f', observed_cpu_time_ncu_seconds_lower) AS observed_cpu_time_ncu_seconds_lower,
  FORMAT('%.12f', observed_cpu_time_ncu_seconds_upper) AS observed_cpu_time_ncu_seconds_upper,
  FORMAT('%.6f', observed_cpu_overlap_seconds) AS observed_cpu_overlap_seconds,
  FORMAT('%.6f', missing_cpu_overlap_seconds) AS missing_cpu_overlap_seconds,
  FORMAT('%.6f', cpu_conflict_overlap_seconds) AS cpu_conflict_overlap_seconds,
  fragment_piece_count,
  usage_group_count,
  cpu_conflict_usage_group_count,
  exact_duplicate_usage_group_count,
  FORMAT('%.12f', synthesized_cpu_time_ncu_seconds_lower) AS synthesized_cpu_time_ncu_seconds_lower,
  FORMAT('%.12f', synthesized_cpu_time_ncu_seconds_upper) AS synthesized_cpu_time_ncu_seconds_upper,
  CAST(NULL AS STRING) AS audit_json
FROM hourly_complete

UNION ALL

SELECT
  'audit' AS record_type,
  CAST(NULL AS INT64) AS hour_index,
  CAST(NULL AS INT64) AS raw_interval_start_us,
  CAST(NULL AS INT64) AS raw_interval_end_us,
  CAST(NULL AS INT64) AS collection_type,
  CAST(NULL AS STRING) AS priority_tier,
  CAST(NULL AS STRING) AS observed_cpu_ncu_lower,
  CAST(NULL AS STRING) AS observed_cpu_ncu_upper,
  CAST(NULL AS STRING) AS observed_cpu_time_ncu_seconds_lower,
  CAST(NULL AS STRING) AS observed_cpu_time_ncu_seconds_upper,
  CAST(NULL AS STRING) AS observed_cpu_overlap_seconds,
  CAST(NULL AS STRING) AS missing_cpu_overlap_seconds,
  CAST(NULL AS STRING) AS cpu_conflict_overlap_seconds,
  CAST(NULL AS INT64) AS fragment_piece_count,
  CAST(NULL AS INT64) AS usage_group_count,
  CAST(NULL AS INT64) AS cpu_conflict_usage_group_count,
  CAST(NULL AS INT64) AS exact_duplicate_usage_group_count,
  CAST(NULL AS STRING) AS synthesized_cpu_time_ncu_seconds_lower,
  CAST(NULL AS STRING) AS synthesized_cpu_time_ncu_seconds_upper,
  audit_json
FROM audit_payload

ORDER BY record_type, hour_index, collection_type, priority_tier
