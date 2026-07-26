# Alibaba PAI GPU v2020 processed stage-1 data

This directory contains deterministic, source-locked derivatives of the four
`stage1_core` archives acquired under `data/raw/alibaba_gpu_2020/`. Build them
from the repository root with:

```powershell
conda activate compute
python -m experiments.process_alibaba_gpu_2020_data --config configs/alibaba_gpu_2020.yaml
```

The processor reads each CSV member directly from its tar archive, verifies the
official archive and header hashes, checks the complete raw manifest, and
publishes outputs only after all frozen full-table audits pass. Gzip timestamps
are fixed, so an unchanged source, configuration, Python CSV behavior, and
processor produce the same output hashes. `v2020/SHA256SUMS` is the publication
manifest.

## Outputs

- `jobs.csv.gz` contains every job and a left join to the unique group-tag row
  on `inst_id`. `join_status` is explicitly `matched` or
  `missing_group_tag`; unmatched jobs are never dropped.
- `tasks.csv.gz` contains every task, its parent-job status, duration, and total
  requested CPU cores, GPU equivalents, and memory across `inst_num`
  instances. Raw fields remain present.
- `successful_gpu_task_candidates.csv.gz` is the strict successful GPU
  candidate queue described below.
- `relative_hourly_workload.csv.gz` is a dense relative-hour aggregation of
  candidate task starts. It reports candidate counts, distinct jobs, requested
  instances and requested resources, plus known-value counts for CPU and
  memory.
- `machine_catalog.csv.gz` preserves the complete machine specification table.
- `summary.json` records rules, full-table quality counts, cohort sizes, output
  sizes, and output hashes.

The task derivations follow the upstream units:

```text
duration_seconds = end_time - start_time
requested_cpu_cores = inst_num * plan_cpu / 100
requested_gpu_equivalents = inst_num * plan_gpu / 100
requested_memory_gb = inst_num * plan_mem
```

Missing source values remain empty. In particular, the 223,965 missing
`plan_gpu` values are not converted to zero. A derived value is empty whenever
one of its required source operands is missing or invalid. Genuine observed
zeros remain zero; the audit finds 11 zero `plan_cpu` values and 83 machines
with zero `cap_gpu`. It finds no zero or negative `inst_num`, no negative
resource requests, and no invalid nonempty numeric values.

## Cohorts

`strict_completed_resource_complete_tasks` requires both parent job and task
status to be `Terminated`, complete numeric `start_time`, `end_time`,
`inst_num`, and `plan_gpu`, nonnegative duration, and positive `inst_num`. It
contains 732,318 tasks from 714,903 jobs.

`successful_gpu_task_candidates` additionally requires positive derived GPU
equivalents. It contains the same 732,318 tasks and 714,903 jobs in this release
because every member of the strict completed cohort has a positive GPU request;
87,007 of those jobs have a nonempty workload tag. This equality is an audited
property of v2020, not a rule that treats missing or zero GPU as positive. The
maximum raw request is 800 percent per instance, and the maximum derived task
request is 400 GPU equivalents.

The hourly table covers 1,642 consecutive relative hours. It describes arrivals
and requested resources at task start, not concurrent active demand, measured
utilization, watts, checkpoint state, deadlines, or recoverable work. Empty
hours have genuine zero arrivals. CPU or memory totals are left empty for an
hour with candidate arrivals but no known value, and the corresponding
known-task count exposes that condition.

## Evidence boundary

All start and end values are anonymized relative seconds. Their time of day and
day of week are preserved upstream, but dates, months, and years are not real.
The data must not be aligned to Google power or grid events by apparent calendar
date. A positive GPU request identifies a successful resource-request trace; it
does not by itself prove preemptibility, checkpointability, recoverability, a
deadline, power consumption, or contract eligibility.

These files support `observed_ai_workload_arrival/resource_request` analyses.
Any conversion to MW, flexibility, recovery headroom, or an M6 business
chronology requires a separately preregistered transformation and must be
marked `derived_benchmark`. The upstream trace is CC BY 4.0; publications must
attribute Alibaba and cite the NSDI 2022 paper identified in the raw source
documentation.
