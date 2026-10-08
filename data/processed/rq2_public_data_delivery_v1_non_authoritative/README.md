# RQ2 public data delivery v1

This is the single offline entry point for the repository-local public-data packages used by RQ2. It is a `DRAFT_NONAUTHORITATIVE` delivery artifact, not a model-ready or formal-result bundle.

Validate every bound package, manifest, schema, row count, and delivery hash without network access:

```powershell
D:\Miniconda3\envs\compute\python.exe -B -m experiments.prepare_rq2_public_data_delivery_v1 --verify-existing
```

Load a small exact-value sample. CSV numbers remain strings, empty CSV fields become `None`, JSON numbers retain their JSON type, and no value is clipped or replaced with zero:

```python
from experiments.prepare_rq2_public_data_delivery_v1 import load_records
rows = load_records("alibaba_dimensionless_workload_blocks_v3", limit=3)
```

Files:

- `catalog.json`: paths, hashes, schemas, licenses where locally evidenced, time bases, units, uses, limitations, and preserved historical splits.
- `data_dictionary.json`: one row per primary field with separate evidence provenance and field role.
- `input_status.json`: observed/derived inputs, unidentified null inputs, unregistered protocol choices, and closed scientific gates.
- `google_pdu17_hourly_flat.jsonl.gz`: a convenience projection of the existing 744-hour pair; it preserves CPU endpoints/strata, power flag counts, and capacity unknowns.
- `google_raw_origin_24h_blocks.json`: 31 mechanical raw-origin blocks. They are not identified natural days or a selected split.
- `summary.json` and `FILE_HASHES.json`: delivery-scope status and byte bindings.

The Google power flags are retained without filtering. The official PDF and notebook still conflict on flag direction; the current official files were rechecked on 2026-09-12 with no identified correction, so the filtering rule remains unresolved. Existing Alibaba and RTS train/holdout splits are cataloged unchanged; this delivery makes no new split or cross-source coupling choice. Workload fractions above one remain exact source-derived strings.

All deadline, recovery, shared-budget, headroom, checkpoint, preemptibility, event-contract, and job-to-power inputs listed in `input_status.json` remain `null`. Local delivery completeness does not make the empirical dataset, continuous model, formal result, paper claim, or security certification complete.
