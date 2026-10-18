# Selector replay candidate: do not integrate for performance

2026-10-17. DRAFT_NONAUTHORITATIVE. The numerical candidate is consistent with
legacy evidence in the checks below, but failed the practical performance
objective. It is retained as development evidence and is not selected for the
hour-0 integration route. No new long chain was launched.

| Final saved raw audit | Existing v1 | Incremental v2 | Decision |
|---|---:|---:|---|
| Rref, two prior stages | 11.4259613 s | 16.7185467 s | slower; do not integrate |
| Actual, one prior stage | 7.5387376 s | 12.6913475 s | slower; do not integrate |

These are one pair per lane under the same existing fixed code-byte and
METADATA-parse optimization. Identity functions and package discovery remained
real. No per-call profiler or identity memo was active. Four members completed
in a 57.314660-second child process; the monitor exited zero in 57.844 seconds,
with peak sampled RSS 173,432,832 bytes. This is a small saved-capsule diagnostic,
not a full-chain forecast. No repeat was made to seek a favorable timing.

Both pairs produced exactly the saved selector record bytes and the same full
scientific projection after excluding capture-specific raw/postsolve hashes.
All 140 saved capture files and the source/test/package closure were unchanged.
`real_identity_pair_01/request.json`, the four member JSON files and
`terminal.json` record the byte pins, route identities, measurements and outcome.
`real_identity_monitor_01/terminal.json` records the enforced stop conditions.

The new raw path reduces full native-shaped numerical replay calls from
`3*k+1` to `k+1` within an audit with `k` prior stages. Its additional fresh
metadata/context bookends nevertheless cost more than the numerical work saved.
The measured invocation recorded 185,090 held-code read hits and 14,910
METADATA-parse hits. These counts include setup/identity receipts as well as
the measured audits; they are not solver calls or a per-function time profile.
They support investigating repeated dependency identity computation rather
than assuming numerical call count alone predicts speed.

`helper_checks_05` completed 127 tests in 84.79 seconds (monitor 86.093 seconds,
exit zero, source pins unchanged). The suite compares unchanged v1 and v2 raw
selector records at every prefix in both lanes, full legacy ReplayResult bytes,
locks/carry, signed zero, failed records and suffix chronology, numerical call
counts, append/return poisoning, and request/admission drift before directory
allocation. Test-only argument-keyed memoization of three upstream static
identity functions uses real initial values and re-evaluates every parameter
snapshot with the original restored functions at fixture exit. This suite is
mathematical/wiring evidence, not full upstream freshness or runtime evidence.
The real-identity pair separately covers both final-stage helper/raw paths.

Earlier attempts remain intact: helper_checks_01 stopped at 180 seconds;
checks_02 exposed an invalid test perturbation; checks_03 exposed an incorrect
test expectation about suffixes exceeding the total stage limit; checks_04
exposed a fixture bookend that retained mutable argument references. These are
not relabeled as passing. Checks_05 fixes the fixtures and records its own bytes.

Independent read-only PRE_SEAL review found the raw-prefix return/admission
drift window; the candidate now revalidates before returning a request key and
before allocating capture state. The six associated counterexamples passed.
The independent reviewer reported no further issue preventing the bounded pair.
This is not official review and opens no execution gate.

The next performance work must address the real repeated dependency path or a
larger explicitly versioned validation scope. Native discovery remains fresh:
Windows directory notifications alone are change hints, and directory oplocks
allow child-entry changes without waiting for acknowledgment; they do not
provide a namespace writer fence. See the primary
[notification documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirstchangenotificationw)
and [directory oplock semantics](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_request_oplock).
A process-wide identity memo or a discovery cache based only on those signals
is not admitted. Explicit successor callers must keep dynamic source, registry,
clock, package and input observations, and distinguish the legacy scientific
identity from the active validation identity.

Full three-arm N0/common/Rref/Actual/paired-commit/reopen/replay acceptance,
whole-workflow performance admission, 192-hour producer coverage, resource
admission, seal, official review and formal execution remain open. The original
chain_07 continues with its original code and timing records.

An explicit interpreter-path successor subsequently produced a measured local
benefit without changing stock distribution discovery. The standard and
configured saved-capsule audits were each run once: Rref 11.463455 to 9.821175
seconds, Actual 7.658076 to 6.800654 seconds. All scientific projections,
selector records, bridge identities, 140 saved files and 764 source/package pins
matched; 1,883 shared module origins and file hashes were equal. Five Pyomo
module aliases to stdlib files were classified explicitly after baseline byte
equality, rather than mistaken for misplaced SDK modules. The comparison is
`configured_entry_comparison_02.json`; no audit was repeated for that postcheck.

The standard-only modules were pywin32_bootstrap, win32file and win32pipe; no
configured-only module was recorded in that pair. Bare `-I` had failed before
audits because pytest needed user-site Pygments; that attempt remains intact.
The configured route explicitly retains a pinned support root and removes
exact duplicate paths. It leaves the original version/distribution functions
and stock finder active; the existing locked-METADATA parsed-version lease
still operates within each discovery window.

The successful route is now integrated into the sibling fixed
`validation_path_optimization_01/entry_revision_03/` package. Its final exact
e5a789… bytes have a 77-pass/1-skip unit terminal and a 12-pass actual routing
terminal, plus hash, lifecycle and process postchecks. See
`validation_path_optimization_01/configured_entry_03_checks_01.json` and
`docs/model_spec/rq2_h1_configured_validation_entry_development_v1.md`.
The slower numerical incremental helper remains excluded. This is still
development/PRE_SEAL evidence; full-chain performance and all formal gates
remain open.
