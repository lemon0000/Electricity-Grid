WITH raw_extract AS (
  SELECT *
  FROM `__SOURCE_TABLE__`
),
usage_source AS (
  SELECT
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    average_usage_cpus
  FROM raw_extract
  WHERE record_type = 'usage'
),
usage_key_audit AS (
  SELECT COUNTIF(
    start_time IS NULL
    OR end_time IS NULL
    OR collection_type IS NULL
    OR collection_id IS NULL
    OR instance_index IS NULL
    OR machine_id IS NULL
  ) AS incomplete_key_rows
  FROM usage_source
),
usage_complete AS (
  SELECT usage.*
  FROM usage_source AS usage
  CROSS JOIN usage_key_audit AS audit
  WHERE IF(
    audit.incomplete_key_rows = 0,
    TRUE,
    ERROR('Compact extract contains incomplete usage keys')
  )
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
  FROM usage_complete
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
logical_entities AS (
  SELECT DISTINCT collection_type, collection_id, instance_index
  FROM usage_rows
),
priority_points AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    event_time,
    IF(
      COUNT(DISTINCT priority) = 1,
      MIN(priority),
      CAST(NULL AS INT64)
    ) AS priority,
    COUNT(DISTINCT priority) AS priority_conflict_count,
    LOGICAL_OR(COALESCE(missing_type, 0) != 0) AS priority_synthesized
  FROM raw_extract
  WHERE record_type = 'instance_event'
  GROUP BY collection_type, collection_id, instance_index, event_time
),
ordered_priority_intervals AS (
  SELECT
    collection_type,
    collection_id,
    instance_index,
    event_time AS interval_start,
    LEAD(event_time, 1, @window_end_us) OVER (
      PARTITION BY collection_type, collection_id, instance_index
      ORDER BY event_time
    ) AS interval_end,
    event_time AS priority_event_time,
    priority,
    priority_conflict_count,
    priority_synthesized
  FROM priority_points
),
initial_priority_intervals AS (
  SELECT
    entity.collection_type,
    entity.collection_id,
    entity.instance_index,
    @window_start_us AS interval_start,
    COALESCE(MIN(point.event_time), @window_end_us) AS interval_end,
    CAST(NULL AS INT64) AS priority_event_time,
    CAST(NULL AS INT64) AS priority,
    0 AS priority_conflict_count,
    FALSE AS priority_synthesized
  FROM logical_entities AS entity
  LEFT JOIN priority_points AS point
    USING (collection_type, collection_id, instance_index)
  GROUP BY entity.collection_type, entity.collection_id, entity.instance_index
  HAVING interval_end > @window_start_us
),
priority_intervals AS (
  SELECT * FROM initial_priority_intervals
  UNION ALL
  SELECT * FROM ordered_priority_intervals
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
      priority_interval.interval_start,
      @window_start_us
    ) AS fragment_start,
    LEAST(
      usage.end_time,
      priority_interval.interval_end,
      @window_end_us
    ) AS fragment_end,
    priority_interval.priority_event_time,
    priority_interval.priority,
    priority_interval.priority_conflict_count,
    priority_interval.priority_synthesized,
    usage.exact_duplicate_count,
    usage.cpu_value_conflict_count,
    usage.usage_group_id
  FROM usage_rows AS usage
  JOIN priority_intervals AS priority_interval
    USING (collection_type, collection_id, instance_index)
  WHERE priority_interval.interval_end > usage.start_time
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
    LEAST(end_time, @window_end_us)
      - GREATEST(start_time, @window_start_us) AS expected_covered_us,
    COALESCE(previous_fragment_end > fragment_start, FALSE) AS fragment_overlap
  FROM usage_fragments_with_previous
)
SELECT
  'usage_fragment' AS record_type,
  start_time,
  end_time,
  collection_type,
  collection_id,
  instance_index,
  machine_id,
  average_usage_cpus,
  fragment_start,
  fragment_end,
  priority_event_time,
  priority,
  priority_conflict_count,
  priority_synthesized,
  exact_duplicate_count,
  cpu_value_conflict_count,
  usage_group_id,
  fragment_covered_us,
  expected_covered_us,
  fragment_overlap,
  CAST(NULL AS INT64) AS machine_event_time,
  CAST(NULL AS INT64) AS machine_event_type,
  CAST(NULL AS FLOAT64) AS capacity_cpus,
  CAST(NULL AS INT64) AS machine_missing_data_reason
FROM usage_fragments_audited

UNION ALL

SELECT
  'machine_event' AS record_type,
  CAST(NULL AS INT64) AS start_time,
  CAST(NULL AS INT64) AS end_time,
  CAST(NULL AS INT64) AS collection_type,
  CAST(NULL AS INT64) AS collection_id,
  CAST(NULL AS INT64) AS instance_index,
  machine_id,
  CAST(NULL AS FLOAT64) AS average_usage_cpus,
  CAST(NULL AS INT64) AS fragment_start,
  CAST(NULL AS INT64) AS fragment_end,
  CAST(NULL AS INT64) AS priority_event_time,
  CAST(NULL AS INT64) AS priority,
  CAST(NULL AS INT64) AS priority_conflict_count,
  CAST(NULL AS BOOL) AS priority_synthesized,
  CAST(NULL AS INT64) AS exact_duplicate_count,
  CAST(NULL AS INT64) AS cpu_value_conflict_count,
  CAST(NULL AS STRING) AS usage_group_id,
  CAST(NULL AS INT64) AS fragment_covered_us,
  CAST(NULL AS INT64) AS expected_covered_us,
  CAST(NULL AS BOOL) AS fragment_overlap,
  event_time AS machine_event_time,
  machine_event_type,
  capacity_cpus,
  machine_missing_data_reason
FROM raw_extract
WHERE record_type = 'machine_event'
  AND event_time < @window_end_us

ORDER BY
  record_type,
  start_time,
  end_time,
  collection_type,
  collection_id,
  instance_index,
  machine_id,
  average_usage_cpus,
  fragment_start,
  fragment_end,
  priority_event_time,
  priority,
  priority_conflict_count,
  priority_synthesized,
  exact_duplicate_count,
  cpu_value_conflict_count,
  usage_group_id,
  fragment_covered_us,
  expected_covered_us,
  fragment_overlap,
  machine_event_time,
  machine_event_type,
  capacity_cpus,
  machine_missing_data_reason
