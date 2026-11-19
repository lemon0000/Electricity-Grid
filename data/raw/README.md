# Raw data provenance

- 2026-11-14 2016 Dulles 气象／Dominion IRP 电网加强索引：[`DULLES_DOMINION_INDEX_20261114.md`](DULLES_DOMINION_INDEX_20261114.md)，
  字节级清单 [`dulles_dominion_acquisition_20261114.json`](dulles_dominion_acquisition_20261114.json)。
- 2026-11-13 ICARUS-PJM 全量解包：`icarus_pjm/0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3/` 下已把
  `upstream/icarus-pjm.zip` 内的 5 个嵌套压缩包与说明文件解开到浅目录 —— `nodal/`（基准节点系统）、
  `nodal_scenarios/`（8 个情景）、`zone21/`（21 分区）、`zone9/`（9 分区）、`genx_9zones_base/`、
  `genx_9zones_datacenters/`（GenX 容量扩展模型）、`dataset_docs/`（README/LICENSE/IPM 对照表）。
  共 150 个数据文件、217 MB；各目录的 `SOURCE_OBJECTS.json` 记录外层与内层 archive 的 SHA-256 及成员 CRC。
- 2026-11-13 CAISO 并网与输电升级成本索引：[`CAISO_INTERCONNECTION_COST_INDEX_20261113.md`](CAISO_INTERCONNECTION_COST_INDEX_20261113.md)，
  字节级清单 [`caiso_interconnection_acquisition_20261113.json`](caiso_interconnection_acquisition_20261113.json)。
- 2026-11-13 2020 气象／RTS-GMLC 拓扑／迁移开销／西岸电价索引：[`WECC_WEATHER_PRICE_LIT_INDEX_20261113.md`](WECC_WEATHER_PRICE_LIT_INDEX_20261113.md)，
  字节级清单 [`wecc_weather_price_lit_acquisition_20261113.json`](wecc_weather_price_lit_acquisition_20261113.json)。
- 2026-11-09 电网—任务耦合公开数据获取索引：[`EMPIRICAL_GRID_TASK_DATA_INDEX_20261109.md`](EMPIRICAL_GRID_TASK_DATA_INDEX_20261109.md)。
- 2026-11-11 储能成本／并网与阻塞／算力 trace 获取索引：[`ENERGY_STORAGE_GRID_TASK_DATA_INDEX_20261111.md`](ENERGY_STORAGE_GRID_TASK_DATA_INDEX_20261111.md)，
  字节级清单 [`energy_storage_grid_task_acquisition_20261111.json`](energy_storage_grid_task_acquisition_20261111.json)。

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
