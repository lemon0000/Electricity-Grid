# Alibaba PAI GPU Cluster Trace v2020 source data

This project starts with the `stage1_core` subset of the public Alibaba PAI GPU
Cluster Trace v2020. The official documentation is pinned to commit
`0d0f3f1efdbf1add6a7bcc63676eafbd1eb11f71`.

Fetch the job, task, group-tag, and machine-specification archives with:

```powershell
conda activate compute
powershell -ExecutionPolicy Bypass -File scripts/fetch_alibaba_gpu_2020.ps1
python -m experiments.validate_alibaba_gpu_2020_data --config configs/alibaba_gpu_2020.yaml
```

Downloaded files are stored under `v2020/upstream/` and excluded from Git. The
fetch script supports resuming partial OSS downloads, verifies the four
official SHA-256 digests before promoting files, downloads the matching header
files and pinned documentation, and writes a local `SHA256SUMS` manifest.

The 145.6 MiB `stage1_core` subset supports empirical analysis of job arrival,
launch delay, run duration, status, requested CPU/GPU resources, machine types,
and the workload label available for a subset of jobs. The CSV archives do not
contain headers; the separately verified `.header` files define their schemas.
Dates, months, and years are anonymized; relative intervals, time of day, and
day of week are preserved. The trace cannot be aligned to Google or grid data
by apparent calendar date.

The instance, sensor, and machine-metric archives are deliberately deferred.
They add about 1.2 GiB, and the sensor values are lifetime aggregates rather
than continuous watts or checkpoint progress. They will be fetched only if a
registered analysis requires those fields.

The trace subdirectory is licensed under CC BY 4.0. Publications must provide
attribution, link the license, and indicate modifications. The upstream authors
also recommend citing the NSDI 2022 paper named in the official README.

This source is an observed AI workload trace. It does not observe continuous
power, deadlines, checkpoint state, recoverable fractions, recovery efficiency,
recovery power, or contract semantics. Low-priority or completed work must not
automatically be labeled recoverable without an explicit derived rule.
