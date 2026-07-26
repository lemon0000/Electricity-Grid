# RTS-GMLC source data

The project uses the official GridMod/RTS-GMLC release `v0.2.3`, pinned to
commit `3ece0d3725c844056132393ee252b3083dd4eab4`.

Fetch the canonical SourceData tables and day-ahead hourly series with:

```powershell
conda activate compute
powershell -ExecutionPolicy Bypass -File scripts/fetch_rts_gmlc.ps1
```

Downloaded files are stored under `v0.2.3/upstream/` and excluded from Git.
The fetch script also writes `SHA256SUMS` for reproducibility.

The upstream README contains the NREL Data Use Disclaimer. Data may be used,
copied, and distributed only with the complete notice retained. Publications
must credit DOE, NREL, and ALLIANCE as required by that notice.

Reference: Barrows et al., "The IEEE Reliability Test System: A Proposed 2019
Update," IEEE Transactions on Power Systems 35(1), 119-127, 2020,
DOI `10.1109/TPWRS.2019.2925557`.

RTS-GMLC is an independent 73-bus validation system. Its ramp rates must not be
silently copied into the current 24-bus PYPOWER case: only 22 of the 33 legacy
units have plausible bus-and-capacity counterparts and their minimum outputs
still differ.
