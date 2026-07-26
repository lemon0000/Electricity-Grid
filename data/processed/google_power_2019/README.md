# Google PowerData 2019 processed data

Run `python -m experiments.process_google_power_data` in the `compute` Conda
environment to rebuild `v1/hourly_shape.csv` from the pinned raw archives.

The table contains 744 consecutive relative hours. Each PDU is first averaged
only when all twelve five-minute `measured_power_util` samples pass
`bad_measurement_data=false`; incomplete domain-hours are excluded without
imputation. The cross-domain result is an unweighted mean and median across the
55 workload-linkable PDU domains. It is not a power sum because PDU capacities
are unavailable.

`v1/domain_quality.csv` preserves per-domain complete-hour coverage. Thirty-eight
of the 55 linkable domains have all 744 complete measured hours; the aggregate
shape retains every hour and records whether 54 or 55 domains contributed.

`peak_normalized_unweighted_mean` is an observed normalized shape. It has no MW,
flexibility, checkpoint, recovery, contract, or real-calendar semantics. Any
later MW mapping is a separate derived benchmark and must retain that label.
The normalization uses the peak of the complete 744-hour window and is only
valid for fixed replay; it must not be calculated across a train/holdout split.
