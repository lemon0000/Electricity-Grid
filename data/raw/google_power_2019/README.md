# Google PowerData 2019 source data

This project uses the public Google PowerData 2019 bucket together with the
machine-to-PDU mapping. The documentation is pinned to Google cluster-data
commit `3f6a61d380dc4ea847416d5414c5fa499f830b9d`.

Fetch all 57 power-domain traces, the mapping table, and the official
documentation with:

```powershell
conda activate compute
powershell -ExecutionPolicy Bypass -File scripts/fetch_google_power_2019.ps1
python -m experiments.validate_google_power_data --config configs/google_power_2019.yaml
```

Downloaded files are stored under `2019/upstream/` and excluded from Git. The
fetch script verifies each Google Cloud Storage object against its published
size and MD5 digest, rejects changes to the pinned aggregate object-generation
manifest, records the source metadata, and writes `SHA256SUMS`.

The dataset contains 55 PDU traces linkable to the eight ClusterData cells and
two power-only MVPP traces, each with 8,928 five-minute samples, plus a
96,616-row machine-to-PDU mapping. Power values are normalized utilization, not
watts or MW, and PDU capacities are not published. A separate guarded BigQuery
acquisition has retrieved the cell `f` / `pdu17` day-0 task-priority, CPU-usage,
and machine-event extract under
`data/raw/google_power_workload_2019/v1/upstream/`. It does not alter this bucket
download, and every additional cell, PDU, or window still requires a new
dry-run and explicit billing cap.

The acquisition validator records 24 bad-measurement rows and 116,517
bad-production-power rows (22.896% of all power rows), plus per-domain coverage
and longest continuous valid windows. File and hash completeness must not be
interpreted as full-row analytical usability; downstream processing must use
the corresponding quality flag for each selected power field.

Machine identifiers are not globally unique. The downloaded mapping also has
two cell-scoped machine identifiers in cell `c` (`102` and `124`) associated
with two PDUs each. No complete `(cell, pdu, machine_id)` tuple is duplicated.
Later joins must preserve that full key or apply and document an explicit
ambiguity policy; rows must not be silently dropped.

The data and trace documentation are licensed under CC BY 4.0. Publications
must attribute Google and should cite the paper named in the official
PowerData documentation.

This source supports an observed production-shape benchmark. It does not
provide absolute power, deadlines, checkpoint state, recoverable fractions,
recovery efficiency, recovery power, or contract semantics. Any MW scaling or
recovery parameters must remain explicitly marked as derived benchmark inputs.
The current processed 250 MW no-flex baseline follows that rule and does not
upgrade the source to observed MW or observed capacity.
