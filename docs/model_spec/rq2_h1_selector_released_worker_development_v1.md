# Source-rebuilt released selector worker

DRAFT_NONAUTHORITATIVE. Root-only writer; independent R3 PRE_SEAL review required.
No launcher or CLI. Real execute needs specific native authority and an enclosing
owned Windows Job. The parent controller remains a separate pending integration.

request_document freshly rebuilds a bounded immutable selector snapshot and binds
its external bytes, role/lane, full SelectorRunConfiguration, both logical archive
caps, exact role budget/allowance, timed sequence configuration/request and new
implementation. Actual power is derived by the snapshot's Rref/business path.

released_input validates canonical fixed namespaces, snapshot pin and size, exact
launch/initial/child/release records, current PID/creation, argv/cwd/environment,
task process identity and declared host headroom. It persists and reads back
consumed.json before source reconstruction. Existing output or a prior attempt
in the same process forbids another attempt, including a first write failure that
left no bytes. Another process cannot match the retained launch PID/creation.
This process-local claim is not a production lease or an authentication token.

execute rebuilds source, checks all redundant declarations, creates and runs the
complete timed selector owner, validates its exact completion, freshly inspects
both journals, then rebuilds source again. Immutable transport views, current
process/environment, callbacks, source projection/configuration, issued receipt
and output archive stamps are bookended before publication. Partial archives and
publication failures are retained, with no retry or phase advancement.

The execution captures original validation, publication and sequence functions.
Their identities are checked before calling retained validators and after source,
runner and inspector returns, including receipt and archive snapshot helpers.
Calls use the captured originals; callback replacement fails before the next
sequence release or result publication. These checks detect mid-execution drift
in the trusted process; they are not isolation against arbitrary Python code.

Result is published and read back first. The final timing terminal pins result
in one direction and includes contiguous default-QPC intervals for handshake,
source-before, preparation, run, owned validation, detached inspection,
source-after and result publication. Native stage windows must fit in the run
phase and match the worker PID/thread. execute entry excludes Python startup;
the terminal's own publication and process exit are excluded from its persisted
window. Parent startup/release-to-quiescence measurement and conservative clock
roundoff accounting remain necessary for any non-solver allowance claim.

The worker does not prove actual Job membership, whole-Job quiescence, full
resource admission, 192-hour coverage, actual RTS integration or native optimality.
Parent must require successful matching exit/quiescence and fresh result/source
inspection before reading/adopting outputs. Actual parent release additionally
requires Rref Job provenance, separate from its scientific snapshot dependency.
All execution, consumption, resource, continuation and formal flags remain false.
