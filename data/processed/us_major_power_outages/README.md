# U.S. Major Power Outage Processing

This directory contains deterministic, source-preserving artifacts derived from
the pinned `mmc2.xlsx` workbook in `data/raw/us_major_power_outages/v1/upstream`.
The current artifact version is under `v1/`; the raw archive is never edited.

## Artifacts

- `v1/source_rows_clean.csv`: one row for every source `OBS`, with normalized
  missing values and derived timestamps, durations, loss flags, and cohort flags.
- `v1/candidate_groups.csv`: one row per candidate event key. Source `OBS` values
  are retained in `source_obs_ids`; duplicate loss and customer values are
  summarized by both `max` and `min`. Values are never summed.
- `v1/cohort_membership.csv`: one row per candidate group with the frozen cohort
  membership flags and represented source-row counts.
- `v1/processing_summary.json`: source hash, processing contract, frozen counts,
  intersections, cause counts, and output metadata.
- `v1/SHA256SUMS`: publication hashes written only after every frozen count and
  artifact hash passes.

## Frozen rules

The processing contract is `us_major_power_outages_candidate_cohorts_v1` in
`configs/us_major_power_outages.yaml`. Its event-selection and cohort rules are
now preregistered for deterministic processing; this does not establish that
candidate groups are independent physical events. Candidate details are trimmed, lower
cased, whitespace-collapsed, and missing values use `__MISSING__`. Timestamps
remain naive local source-clock values. The primary duration value is the
reported duration in minutes; timestamp-derived duration and their difference
are retained for sensitivity checks. Missing duration and missing demand loss
are not imputed.

The primary sustained cohort has 1,385 candidate groups (1,398 source rows).
Known-loss and positive-loss sensitivities have 751 and 611 groups. The
zero-duration sensitivity has 1,463 groups. These are source-derived benchmark
cohorts, not independent event counts or probability samples.

The dataset has no component identifiers, topology, SCUC/SCED, or data-center
clock. Do not infer unconditional outage frequency, component outage rates,
RTS contingency mappings, or same-clock business/contract failure from these
artifacts.
