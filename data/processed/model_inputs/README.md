# Processed model inputs

`m6_google_power_shape_no_flex_250mw_v1` maps the pinned Google hourly
normalized shape to a 250 MW peak on a synthetic reference clock. The mapping
is a `derived_benchmark`, not an observed MW trace. The Google values are
realized PDU power proxies, not uncapped requests, and 250 MW is an assumed
project benchmark peak rather than an observed PDU capacity. Because no sourced
flexibility or recovery evidence is available, all flexible, recoverable, and
recovery-headroom fields are fixed to zero.

The generated CSV passes `m6_business_chronology_v1`, but there is no paired
incident chronology or chronological grid solver. Passing the input contract
therefore does not set `chronological_grid_dispatch_coupled` or
`security_certified` to true.

`alibaba_job_execution_envelopes_v1` contains 714,903 job-level observed
execution envelopes derived from 732,318 completed positive-GPU task records.
Release, completion, requested GPU slots, and GPU-seconds are observed proxies.
Deadline, checkpoint, preemptibility, recoverable fraction, and power
conversion remain unavailable.

`alibaba_gpu_telemetry_v1` audits 3,033,232 official instance sensor rows and
joins 1,964,411 rows to completed candidate jobs, yielding 576,724 job-by-GPU
records. `gpu_wrk_util` remains the source-defined lifetime-average
percent-of-one-GPU quantity; dividing it by 100 gives GPU-equivalent
utilization, not electrical power. Nine source rows with machines absent from
the machine catalog remain explicitly `UNMAPPED`.

`rq2_joint_data_v1` places RTS-GMLC Area 1 bus loads, generator-level renewable
availability, and reliability-rate-derived outage samples on the same 8,784
hour benchmark clock. The outage samples are not observed incidents, and an
outage does not become `grid_need_mw` until a chronological network dispatch
computes the required call.

`nlr_genai_power_profiles_v2` catalogs 2,467 source-defined aggregate CPU-plus-
GPU compute-node power profiles measured on four-H100 nodes. Eight
whole-facility profiles are retained separately as DIPLOEE simulations. The
NLR profiles do not share jobs, hardware, or a clock with Alibaba PAI, so they
provide a power-scale sensitivity reference rather than a direct conversion.
The 200 online-rate profiles stored at 0.001 s were interpolated upstream below
the published 0.1/0.2 s measurement resolution and are not independent 1 kHz
measurements or evidence for high-frequency ramp calibration.

`rts_gmlc_hourly_cfe_deficit_250mw_v2` is the current provenance-clean CFE
package. Its hourly CSV is byte-identical to frozen v1, while its summary binds
the current config, builder, and derivation module. V1 remains an immutable
numeric predecessor.

`rq2_data_readiness_v2` verifies source and package manifests plus every live
config, processing implementation, and dependency module declared by the
packages. It currently permits mapping-model development and short validation
only; formal RQ2 experiments remain blocked.

`alibaba_dimensionless_workload_blocks_v2` converts task overlap into hourly
requested-GPU occupancy and 12-hour blocks without treating the quantity as
electrical power or observed flexibility. The training-only peak defines the
normalization. Jobs contributing on both sides of the split boundary are
excluded from both populations; training blocks are only for policy fitting,
while holdout blocks form the workload marginal used by transport bounds and
fixed-policy evaluation. V1 is retained as a rejected predecessor because its
hour-level separation did not guarantee job-level independence.

`alibaba_dimensionless_workload_blocks_v3` is the 24-hour successor used by
the public partial-identification route. It preserves the same job-disjoint
split and training-only normalization, yielding 34 training and 34 holdout
blocks. V2 remains immutable; v3 prevents a 12-hour block boundary from
truncating the registered daily recovery window.

`rts_gmlc_public_power_system_blocks_v4` provides 541 training and 530 holdout
24-hour RTS-GMLC network+CFE blocks across three frozen outage seeds. Its
system-level competing-risk chronology admits at most one active outage per
hour. The reliability scope contains 93 enabled generators and 118
non-islanding AC branches; disabled unit `212_CSP_1` and islanding branches
`B11/C11` are excluded and reported. This package does not yet contain
`grid_need`: `rts_gmlc_public_grid_need_dispatch_v3` must first freeze a normal
24-hour SCUC baseline and solve the registered corrective LP for each sampled
outage hour.

`rq2_public_pairwise_replay_v3` and `rq2_public_identification_grid_v3` are
configured successors, not published data packages. Their execution gates
remain closed until the full grid-need package exists, independent R4 review
passes, and the user separately authorizes the formal long runs.

The v6 route uses new `*_v4_gurobi` grid/pairwise directories and
`rq2_public_identification_grid_v4_gurobi`. It preserves any zero-data-center
endpoint infeasibility as an explicit E0 state rather than a finite
`grid_need`, and conditions contract-risk transport on finite-grid blocks.
These directories must not reuse the existing v3 HiGHS checkpoints and remain
unpublished until the execution-machine pilot and activation gates pass.

`wattgpu_power_reference_v1` adds 4,798 LLM-inference experiments across eight
measured NVIDIA GPU types. Its exact Tesla T4 overlap covers 196,065 Alibaba
candidate tasks, but the sources share neither jobs nor a clock. V100 variants
are retained as non-exact architectural references. The package also exposes
two upstream quality limits rather than hiding them: 200 rows have unequal
prompt/generation request-array lengths, and 266 rows differ by more than 1%
between reported mean power and `energy / duration`. Downstream work must keep
the reported and recomputed quantities separate.
