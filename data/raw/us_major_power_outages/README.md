# U.S. major power outage events source data

This project uses the supplementary dataset from Mukherjee et al., "Data on
major power outage events in the continental U.S.," Data in Brief 19 (2018),
2079-2083, DOI `10.1016/j.dib.2018.06.067`, PMCID `PMC6141375`.

Fetch the Europe PMC article XML and supplementary archive with:

```powershell
conda activate compute
powershell -ExecutionPolicy Bypass -File scripts/fetch_us_major_power_outages.ps1
python -m experiments.validate_us_major_power_outages_data --config configs/us_major_power_outages.yaml
```

Downloaded files are stored under `v1/upstream/` and excluded from Git. The
Europe PMC endpoint dynamically repackages its ZIP, so the container SHA changes
between requests. The fetch script instead verifies the byte length and SHA-256
of both stable members (`mmc1.docx` and `mmc2.xlsx`) before accepting the ZIP,
then writes a local `SHA256SUMS` manifest for the acquired container and article
XML.

The workbook contains 1,534 source rows representing state-level major-outage
reports from January 2000 through July 2016. It combines public sources
including DOE OE-417 Schedule 1, EIA, NOAA/NCDC, labor, and census data.
Relevant fields include reported event start/restoration time, outage duration,
cause, demand loss MW, and customers affected. The rows span 50 postal
jurisdictions (49 states plus DC); the workbook includes AK and HI and has no
RI. Despite the source article's title, the workbook must therefore not be
described as covering 50 states or strictly the continental United States.

The article and its supplements are CC BY 4.0. Publications must attribute the
authors, cite the DOI, link the license, and indicate modifications.

The source has material missingness: 58 rows lack restoration/duration, 705
lack demand-loss MW, and 443 lack customers affected. Among the 1,476 rows with
complete temporal fields, 31 reported durations differ from the timestamp
difference by exactly one hour. Another 78 rows report zero duration. These
rows remain unchanged and are explicitly reported.

These are observed source reports, not an identified set of independent
incidents and not an asset outage chronology. Candidate identity, duplicate
aggregation, cause inclusion, loss, and duration rules are now preregistered in
`us_major_power_outages_candidate_cohorts_v1`; the resulting descriptive
cohorts are under `data/processed/us_major_power_outages/v1/`. Preregistration
does not establish independent events, so the rows and candidate groups still
cannot estimate incident frequency or an unconditional duration distribution.
The source also has no branch/generator identifiers, network topology,
SCUC/SCED decisions, or same-clock data-center workload. It must not be mapped
to RTS components or labeled as an RTS observed incident trace.
