WITH pdu_machines AS (
  SELECT DISTINCT machine_id
  FROM `google.com:google-cluster-data.powerdata_2019.machine_to_pdu_mapping`
  WHERE cell = @cell AND pdu = @pdu
),
usage_rows AS (
  SELECT
    start_time,
    end_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    average_usage.cpus AS average_usage_cpus
  FROM `google.com:google-cluster-data.clusterdata_2019_f.instance_usage`
  JOIN pdu_machines USING (machine_id)
  WHERE start_time IS NOT NULL
    AND end_time IS NOT NULL
    AND end_time > start_time
    AND end_time > @window_start_us
    AND start_time < @window_end_us
    AND (alloc_collection_id IS NULL OR alloc_collection_id = 0)
),
logical_entities AS (
  SELECT DISTINCT collection_type, collection_id, instance_index
  FROM usage_rows
  WHERE collection_type IS NOT NULL
    AND collection_id IS NOT NULL
    AND instance_index IS NOT NULL
),
extract_rows AS (
  SELECT
    'usage' AS record_type,
    start_time,
    end_time,
    CAST(NULL AS INT64) AS event_time,
    collection_type,
    collection_id,
    instance_index,
    machine_id,
    average_usage_cpus,
    CAST(NULL AS INT64) AS priority,
    CAST(NULL AS INT64) AS missing_type,
    CAST(NULL AS INT64) AS machine_event_type,
    CAST(NULL AS FLOAT64) AS capacity_cpus,
    CAST(NULL AS INT64) AS machine_missing_data_reason
  FROM usage_rows

  UNION ALL

  SELECT
    'instance_event' AS record_type,
    CAST(NULL AS INT64) AS start_time,
    CAST(NULL AS INT64) AS end_time,
    event.time AS event_time,
    event.collection_type,
    event.collection_id,
    event.instance_index,
    CAST(NULL AS INT64) AS machine_id,
    CAST(NULL AS FLOAT64) AS average_usage_cpus,
    event.priority,
    event.missing_type,
    CAST(NULL AS INT64) AS machine_event_type,
    CAST(NULL AS FLOAT64) AS capacity_cpus,
    CAST(NULL AS INT64) AS machine_missing_data_reason
  FROM `google.com:google-cluster-data.clusterdata_2019_f.instance_events` AS event
  JOIN logical_entities USING (collection_type, collection_id, instance_index)
  WHERE event.time IS NOT NULL
    AND event.time < @window_end_us
    AND event.priority IS NOT NULL

  UNION ALL

  SELECT
    'machine_event' AS record_type,
    CAST(NULL AS INT64) AS start_time,
    CAST(NULL AS INT64) AS end_time,
    event.time AS event_time,
    CAST(NULL AS INT64) AS collection_type,
    CAST(NULL AS INT64) AS collection_id,
    CAST(NULL AS INT64) AS instance_index,
    event.machine_id,
    CAST(NULL AS FLOAT64) AS average_usage_cpus,
    CAST(NULL AS INT64) AS priority,
    CAST(NULL AS INT64) AS missing_type,
    event.type AS machine_event_type,
    event.capacity.cpus AS capacity_cpus,
    event.missing_data_reason AS machine_missing_data_reason
  FROM `google.com:google-cluster-data.clusterdata_2019_f.machine_events` AS event
  JOIN pdu_machines USING (machine_id)
  WHERE event.time IS NOT NULL
)
SELECT *
FROM extract_rows
ORDER BY
  record_type,
  COALESCE(start_time, event_time),
  collection_type,
  collection_id,
  instance_index,
  machine_id,
  end_time,
  priority,
  machine_event_type
