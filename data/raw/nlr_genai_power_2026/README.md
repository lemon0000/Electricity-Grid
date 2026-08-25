# NLR GenAI Power Profiles

The ignored `v2/upstream/` directory is populated by:

```bash
PYTHONPATH=. conda run -n compute python \
  experiments/fetch_nlr_genai_power_2026.py
```

Source identity, version, license, expected byte count, and SHA-256 are frozen in
`configs/nlr_genai_power_profiles_v2.yaml`.

The archive contains two distinct evidence classes:

- measured aggregate CPU-plus-GPU compute-node power profiles under
  `00_raw_datasets/` and `01_aggregated_datasets/`;
- simulated whole-facility examples under `03_whole-facility_profiles/`.

They must remain distinct in downstream analysis. The dataset is not paired
with Alibaba PAI jobs and does not identify deadline, checkpoint,
preemptibility, or recoverable-work fractions.
