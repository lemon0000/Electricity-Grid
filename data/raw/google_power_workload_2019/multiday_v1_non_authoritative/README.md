# Google PDU17 full-month hourly CPU acquisition (non-authoritative)

This directory contains a bounded local aggregate acquired from the public Google ClusterData 2019 BigQuery tables.
The 7.7-billion-row `instance_usage` source remains in BigQuery; it was not downloaded to this repository.

`upstream/records.csv.gz` contains 10,416 hourly rows plus one audit row over raw clock
`[600000000,2679000000000)`: 744 hours, two collection types, and seven priority tiers. `upstream/query.sql`,
`upstream/oracle_query.sql`, `upstream/config.yaml`, `upstream/SOURCE_METADATA.json`, and `upstream/SHA256SUMS`
bind the SQL, parameters, fixed BigQuery job, source snapshots, billed bytes, result, and file hashes.

The acquisition is `DRAFT_NONAUTHORITATIVE`. CPU values use normalized compute units for the selected root-allocation
population. They are not physical cores, MW, a complete PDU workload population, observed flexibility, deadlines,
or recovery parameters. The package is not a continuous-model input, formal result, paper claim, or security certificate.

Fixed main job: `google_pdu17_multiday_v1_5f0ddc384afe27ac`  
Processed bytes: `554760728186`  
Billed bytes: `554761715712`  
Local result SHA-256: `3c204c39cc099fb344a663801e2977adcc063ab988de465e8069a62ccd987ca0`
