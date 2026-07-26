# Processed data

All files below are deterministic derivatives of pinned inputs under
`data/raw/`. Rebuild them from the repository root in the `compute` Conda
environment:

```powershell
python -m experiments.process_google_power_data --config configs/google_power_2019.yaml
python -m experiments.process_google_power_workload_day0 --config configs/google_power_workload_day0.yaml
python -m experiments.process_alibaba_gpu_2020_data --config configs/alibaba_gpu_2020.yaml
python -m experiments.process_us_major_power_outages_data --config configs/us_major_power_outages.yaml
python -m experiments.build_m6_google_power_shape_benchmark --config configs/m6_google_power_shape_benchmark.yaml
python -m experiments.build_m6_google_power_workload_day0_benchmark --config configs/m6_google_power_workload_day0_benchmark.yaml
```

The Google, Alibaba, and outage products retain separate evidence identities
and clocks. They must not be joined as one observed chronology. The two
model-native Google business artifacts pass the M6 business input schema only
as no-flexibility derived benchmarks. Their standalone summaries retain
`chronological_dispatch_request_built=false` and
`chronological_grid_dispatch_coupled=false`: these directories are model
inputs, not grid-solve outputs, and neither provides incidents.

`google_power_workload_2019/v1/` is a narrower same-system evidence product:
24 hourly rows pair normalized `pdu17` measured power with bounded NCU usage,
and 168 rows retain the seven priority tiers. The processor reconstructs
machine-event capacity without backfilling later UPDATE values;
`hour_index=18/19` retain 44.908767 unknown-capacity machine-seconds. Priority 0-119 usage is
marked only as a flexibility candidate proxy. The product is not an MW demand
series, a complete PDU workload census, a recovery trace, or an M6-ready input.

`model_inputs/m6_google_power_shape_no_flex_250mw_v1/` is the 744-hour
peak-normalized fixed-replay baseline. The independent
`model_inputs/m6_google_power_workload_day0_no_flex_250mw_v1/` baseline maps the
24 paired power-utilization hours directly to an assumed 250 MW reference
capacity, without day-0 peak renormalization. Its flexibility, recoverable load,
and recovery headroom are all zero. `candidate_proxy_audit.csv` preserves the
priority/NCU candidate evidence and the incomplete capacity audit at hours 18
and 19, but none of those fields is used as model flexibility.

The downstream result
`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1` consumes only the first
six continuous rows of the day-0 business artifact and, in that named result
alone, sets `chronological_dispatch_request_built=true` and
`chronological_grid_dispatch_coupled=true`. Reproduce it from the repository
root with:

```powershell
conda activate compute
python -m experiments.run_rts_gmlc_day0_scuc --config configs/rts_gmlc_google_day0_scuc.yaml
```

That solve publishes outside `data/processed/`, under
`results/tables/rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1/`.
The directory contains nine payload files plus `SHA256SUMS`, which pins all
nine:

```text
generator_dispatch.csv
hourly_dispatch.csv
incident_chronology.csv
initial_state.csv
normal_branch_flows.csv
security_audit.csv
security_branch_flows.csv
security_generator_dispatch.csv
summary.json
SHA256SUMS
```

It is a six-hour, selected-N-1 day-ahead DC benchmark, not a claim that the
input itself contains observed MW, flexibility, recovery behavior, or observed
incidents. Its empty incident chronology and optimization-derived initial state
also do not establish full M6 readiness, real-time operation, full N-1, AC
security, or engineering certification. Scaling the native solve to 24 hours
remains compute-blocked.
