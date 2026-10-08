# Google PDU17 744-hour CPU-power-capacity alignment

This DRAFT_NONAUTHORITATIVE package aligns three existing local sources on raw clock
`[600000000,2679000000000)`. Each JSONL row contains 14 CPU strata, 12-sample unfiltered
measured/production PDU power means with original flag counts, and the matching hourly
normalized-capacity evidence. The 31 coverage blocks start at the raw trace origin and are
not identified as natural calendar days.

CPU and capacity use normalized units. No CPU/capacity ratio, MW conversion, headroom,
flexibility, deadline, recovery parameter, p-value, fit, or train/holdout selection is produced.
The population is incomplete and the power quality-flag direction remains unresolved.
