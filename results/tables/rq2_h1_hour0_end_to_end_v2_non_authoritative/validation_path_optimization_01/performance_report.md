# Path validation optimization: bounded development evidence

2026-10-17. DRAFT_NONAUTHORITATIVE. Full-chain acceptance and all formal/native
resource and execution gates remain open. The original chain_07 is unchanged.

The final candidate passed 34 targeted tests (`monitor_unit_06/terminal.json`).
It retains leaf checks and fresh ancestor reparse/case-sensitivity checks;
directory handles use FILE_LIST_DIRECTORY in addition to READ_ATTRIBUTES.
Partial acquisition, path/binding drift and handle cleanup failures were tested.
Independent read-only PRE_SEAL findings were addressed; no official verdict was
issued.

The final single saved common-arm comparison is `pair_04_io` against
`pair_05_io_path`: 64.2394243 to 54.0645719 seconds, a 15.84% reduction within
that measured scope. Both members exited zero. Full scientific and audit JSON
hashes match exactly; all 461 saved files and the pinned 145-code/604-test
closure remained unchanged. `development_checks_01.json` records the hashes and
terminal locations. This is additional to the existing code-byte/metadata-parse
entry, and is not a full-chain or native runtime forecast.

Two separate tiny three-Actual routing probes stopped at their declared
180-second limits. The second disabled Python per-call profiling and completed
Rref in 137.413 seconds before the limit. Neither probe passed integration.
Their child processes were absent afterward, all four locks could be acquired
and released, and saved-file postchecks were unchanged. See
`integration_probe_stop_01.json` and `integration_probe_stop_02.json`.

`handoff_call_lower_bounds_01.json` derives a static lower bound of 22 common
preparations in one successful consume path: at least 528 full and 528 fresh
saved-N0 numerical audit uses, before nested snapshot/parent/reopen/failure
paths. These are validation operations, not solver calls. This structural
repetition prevents admission of another long chain on the basis of the local
15.84% result. The next development candidate is isolated under
`../validation_selector_incremental_01`; its performance and integration must
be measured separately.
