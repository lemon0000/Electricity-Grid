# H1 selector launch preparation development

This R3 non-authoritative unit implements the fixed launch declaration needed by
the future selector parent. It has two read-only APIs and no launcher, lease,
record publication, live completion or Actual release capability.

`prepare(parent_root, snapshot_bytes, ...)` rebuilds the saved selector source
twice under the solver-call prohibition, derives the role-specific Job budget
from the fresh request, and returns bounded canonical immutable JSON bytes. It
does not create directories or reserve resources. Invalid resource declarations
fail before side effects. Source, implementation and Python executable content
and metadata are bookended. A Conda executable may have multiple hardlinks;
its link count, file identity, size and timestamps are retained. Experiment
record single-link rules are unchanged.

The canonical resolved Python path is captured at module import and current
`sys.executable` must still resolve to it. Reachable project-module references,
callables, and project-class static descriptors are captured at import, including
helpers imported by name through their defining project modules. Replacement or
deletion fails the scope checks. The traversal is sorted and excludes external
library internals and test modules; newly added unrelated attributes are not an
execution route. This guards replacement within a trusted Python process, not
hostile arbitrary code with access to private guard state. Checker and captured
module roots are themselves fixed. Module identity includes its `__name__`.
Public protocol constants in that captured graph are serialized independently:
names containing `SCHEMA`, `CAP`, `LIMIT`, or `MAX`, plus `FLAGS`, input/output
file inventories and `PHASES`. Their field inventories and values must remain
unchanged. Mutable scientific instances are not treated as protocol constants.
Fixed private checker/identity references are retained in each operation before
source callbacks. After the solver prohibition context restores its temporary
entrypoint replacements, the original checker runs before any return identity
comparison. A callback cannot bypass this check by replacing its global name.

The command is always the current canonical Python executable followed by
`-I -B -c` and a fixed script. Checkout root, worker implementation pin, absolute
request path and request digest are separate argv data, never interpolated into
Python source. The script inserts the bound checkout root into `sys.path`, checks
the imported worker path and implementation identity, then calls canonical
`worker.execute`. There is no caller-selected script or alternate worker route.
The environment is the existing explicit runtime allowlist; arbitrary parent
environment variables are not copied.

The host declaration covers Job commit plus explicitly declared parent commit,
the complete worker logical content bound, explicit scratch bytes and parent
metadata of 1 MiB binding + 4 MiB terminal + one lease byte. All reserves are
explicit positive integers. Existing host observation aggregates demands by
volume and uses the maximum reserve on each volume. These are logical content
bounds, not filesystem allocation bounds, hard disk quotas or proof of memory
adequacy. The future parent must enforce its own record caps and evaluate live
headroom. This unit does not establish complete research resource admission.

`bind(declaration, snapshot_bytes)` is called after the future parent has made
the declared directories. It reconstructs the entire declaration from source,
checks existing local directory/resource identity, computes the task process
identity, and repeats both declaration and process checks before returning the
existing worker launch schema as JSON bytes. It does not write `launch.json`.
The returned declaration is constructible data, not a receipt or credential.
Checks are fresh at return; the owning lifecycle must recheck before release.

Development source tests use explicitly distinct test-only alias modules loaded
after synthetic source fixtures, with different module/implementation identity.
Canonical code rejects those replaced source helpers and alias declarations;
restoring dependencies invalidates the alias. These aliases have no launch or
credential API and do not establish a canonical fresh-source success case. The
Actual scientific archive uses fabricated adapters. Separate real isolated
Python import probes use canonical code with no synthetic fixture and
the exact fixed command with a missing request or deliberately wrong worker pin.
They must fail before consumption, including with an import-shadowing package
in scratch. These probes do not cover a successful six-file handshake, a Job,
scientific worker execution, parent completion, or Rref-to-Actual live ownership.
They invoke no real native solver. Existing lifecycle tests cannot fill these
selector integration evidence gaps.

Next integration must persist a create-once parent binding before worker files,
own suspended launch/release and quiescence callbacks, retain all six input pins,
run the fresh output inspector after successful whole-Job observation, and
atomically validate a parent terminal before issuing an exact live completion.
Actual needs that completion as well as its scientific reference. Its reference
terminal maps to `scientific_terminal_sha256`; parent and timing terminals remain
separate. Common provenance needs stable-field matching and a global-journal
ancestor check (or an explicit conservative same-head restriction).

`selector_parent_connected`, `native_execution_authorized`,
`non_solver_allowance_verified`, `resource_admission`, `formal_execution_ready`
and `formal_result` remain false. This development unit does not authorize a
native run, phase consumption, legal reuse, full 192-hour coverage or a formal
scientific result. PRE_SEAL review is distinct from post-seal official review.
