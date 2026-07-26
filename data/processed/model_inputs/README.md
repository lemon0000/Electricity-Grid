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
