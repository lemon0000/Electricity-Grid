# RTS-24 data provenance

The project loads `case24_ieee_rts` directly from PYPOWER 5.1.19. No local
copy is modified. The upstream case is BSD-licensed and cites:

- IEEE Reliability Test System Task Force, "IEEE Reliability Test System,"
  IEEE Transactions on Power Apparatus and Systems 98(6), 1979, 2047-2054.
- IEEE Reliability Test System Task Force, "IEEE Reliability Test
  System-96," IEEE Transactions on Power Systems 14(3), 1999, 1010-1020.

The case uses a 100 MVA base. Loads, generator limits, branch `RATE_A` (long
term), `RATE_B` (short term), `RATE_C` (emergency), and polynomial generation
costs are consumed without changing the upstream data. Generator `RAMP_10` and
`RAMP_30` are zero for every unit; this project treats those zeros as missing
response data rather than evidence of either zero or unlimited ramp capability.

## Google cell-f / pdu17 day-0 workload extract

The guarded ClusterData acquisition is archived under
`google_power_workload_2019/v1/upstream/`. Reuse the completed extract and
compact jobs without rescanning the public tables with:

```powershell
python -m experiments.fetch_google_power_workload_day0 `
  --config configs/google_power_workload_day0.yaml `
  --execute `
  --extract-job-id cb350a47-cfa1-449e-a4e5-f1cf1ec6a916 `
  --compact-job-id 004b5224-ae3b-40a9-904f-ddf1a4dc2ce3
```

The final hourly Job is `bd85f50f-b628-43bd-a354-23d74ff74eb2`. The three
successful jobs processed 551,002,439,062 bytes and billed 551,004,667,904
bytes, below the frozen 1 TiB budget. Both unsuccessful attempts have null
processed and billed byte fields in the archived audit. The result contains
336 hourly usage cells, 1,328 machine events, and one quality record; all query
parameters, SQL copies, source snapshots, records, metadata, and hashes are
locked by `SHA256SUMS`. The three anonymous query-result tables were not copied
into a permanent project dataset; their exact IDs and expiration timestamps are
archived, and BigQuery removes them automatically at those timestamps.

This is a bounded `alloc_collection_id IS NULL OR 0` population, not proof of
complete PDU workload. CPU is normalized compute usage (NCU), power remains
normalized utilization, and neither quantity supplies absolute MW or observed
flexibility.
