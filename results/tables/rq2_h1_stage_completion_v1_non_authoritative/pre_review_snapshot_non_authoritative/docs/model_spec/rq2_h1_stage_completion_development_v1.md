# H1 owned stage completion development v1

Status: DRAFT_NONAUTHORITATIVE. This unit joins producer completion and science
completion after an owned call returns. Existing capture and science code are
unchanged. There is no CLI, native authorization, Job supervision or formal gate.

`OwnedStage` holds one PID/thread and a nonblocking guard. It internally builds
the canonical stage, creates StageCapture and fixes science.consume as callback.
It allows one run. After StageCapture.run returns, it checks that the returned
object is the callback object, started/complete/poisoned states, raw closed and
unpoisoned state, stage count, owner and released guard. It then fixes complete
and science terminal hashes and invokes the independent reader. Only after
successful replay and context/implementation checks does it mint an immutable
in-memory Completion. Any escaping exception poisons the owner. No retry or
resume exists. Tests substitute a synthetic adapter; calling run with the real
adapter requires new explicit authority and hard resource/Job supervision.

`inspect` requires independent producer-complete, science-terminal and current
reader-implementation pins. It returns an ordinary conditional projection, never
a Completion. It checks canonical root, plain directories and exact topology
(17 files, three nested directories), caps, full bytes and file identities.
It validates raw ingress completion, producer complete binding/raw/terminal
hashes, science source containment and existing fresh science replay. It brackets
all files and directory listings around replay, and rechecks context/dependency
identity. The metadata uses the existing false flags. The returned
producer_completion_record_checked=true concerns these bytes only;
producer_run_return_observed=false and whole_job_quiescence_checked=false remain
explicit. Completion includes request, implementation, both pins and immutable
false authority flags; it is only an API boundary within trusted Python, not a
security boundary against arbitrary mutation of Python objects or module globals.

Science terminal can precede a failed close, raw finish or complete publication.
Even if raw terminal or complete bytes survive a confirmation error, no live
Completion is returned. The reader cannot recover evidence that a call returned
from disk. Dual hashes identify bytes, not a unique native execution instance;
byte-identical histories are not distinguishable without a future versioned
execution identity. No new durable handshake file is introduced.

Tests borrow installed DirectSolver.solve with a synthetic adapter and derived
saved assignments. They cover successful live return/fresh replay, close and
raw-terminal/complete write-before/write-after failures, post-return poisoned or
inconsistent state, return-object replacement, fresh replay rejection, source
and completion drift, topology growth, mismatched roots/pins/requests, owner and
reentry errors, direct receipt construction and dependency drift. This is not
actual Gurobi or symbol-map postsolve validation, full 232-stage/all-hour coverage,
native authentication, whole-Job quiescence, crash/power-loss durability, resource
admission or official acceptance. Added reader work and memory need successor
timing/storage accounting; this unit adds no output files to the successful
capture-plus-science tree. All formal/resource/coverage flags remain false.
