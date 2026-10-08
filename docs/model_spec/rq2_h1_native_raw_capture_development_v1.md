# H1 raw capture before adapter postprocessing development v1

Status: DRAFT_NONAUTHORITATIVE. `StageCapture.run` is a versioned producer
boundary with one owned direct solver and one stage. It can execute native code
if invoked with the real adapter. The caller must supply a newly authorized
run, admitted resources and hard Job supervision. No CLI, production manifest,
lease, authority or worker integration is supplied here. Development tests
replace the adapter; native calls remain zero.

The old provenance runner loads solutions and computes residuals before
encoding its report. Its implementation identity cannot truthfully label this
new path. The new native raw schema is therefore distinct and is not accepted
as an old v3 report. It does not alter the old source closure, report grammar,
generation conversion rule or scientific acceptance thresholds.

## Order and ownership

1. Create a unique root and raw ingress; bind request, canonical model structure
   and producer implementation. Record the unchanged solver specification/options.
2. Build and check the model; create the exact pinned direct adapter. Replace
   only that instance's `_apply_solver` entry with a one-use capture boundary.
3. The installed `DirectSolver.solve` performs presolve. At the apply boundary,
   reject callbacks, console/file logs, option drift and canonical value/structure
   changes. Update the native model and check complete export correspondence.
   Save the bounded export receipt and recheck the metadata pins.
4. Raw intent precedes the original apply call. After it returns (or raises),
   read native attributes and the complete prechecked variable map. Save raw
   with exclusive creation, fsync, stable readback and receipt. The ingress
   callback here only returns bytes: no scientific audit has run.
5. Rethrow any original apply exception after raw retention. Missing required
   capture channels or no incumbent stop here, with retained raw; no claim of
   mathematical infeasibility is made. Otherwise return to the real Pyomo driver,
   which can now execute `_postsolve` and its result handling.
6. Check canonical structure/values again, repeat complete export comparison,
   and independently recapture native channels to reject postprocessing drift.
   Compare fresh disk raw before calling the downstream consumer. The consumer
   receives bytes, unloaded Pyomo results and the canonical model, not the solver.
   Known solver entry points are forbidden during this callback.
7. Recheck binding, metadata, raw and canonical structure. Close the solver once,
   recheck binding/metadata/raw after close, finish/reinspect raw ingress, then
   write the bounded completion record.

The owner is one process/thread with a nonblocking in-memory guard. A second
run, reentrant run or second apply cannot execute the original apply again.
Every exception escaping the owned run poisons the owner; a rejected reentrant
call leaves the active owner in control. If raw ingress already returned, later errors
explicitly abort it; failures before that remain incomplete/poisoned. Close is
attempted once even on errors; close failure needs the future Job controller to
contain the process and cannot produce completion. No retry, resume, truncation
or cleanup is available. This is application ownership, not an adversarial
security boundary or proof of whole-Job quiescence. The implementation identity
directly binds the inherited objective guard and both grammar modules, as well
as this producer, ingress, linear guard, solver-entry guard and pinned old adapter.

The raw terminal closes only the ingress callback sequence. If raw finish is
already closed, or complete publication fails after writing bytes, abort cannot
necessarily be written. A retained complete.json alone is not a durable acceptance
signal: its write/readback may have failed before the owner acknowledged it.
The future parent requires an external complete pin and an independent fresh
reader, neither of which this unit supplies. Finish/publication failures leave
the StageCapture owner poisoned and unresolved, even when terminal files exist.

## Retention and scope

Raw stores native status/counts/objective bounds/runtime, each variable's native
index/name/type/bounds/X, and objective terms by native index. Floats use their
original binary64 big-endian 16-hex-digit bits, with `float.hex()` as a readable
value. NaN sign/payload and negative zero survive bit-for-bit. NaN/infinity
remain available for downstream rejection. Tiny negative generation is kept
unchanged. Failed getters retain an unavailable channel with bounded exception
class, never fabricated zero; exception messages are not captured. A second
read is a consistency observation, not retrying optimize. Optional unavailable
diagnostic channels do not certify numerical acceptance.

Capture completeness means channels were read, not finite values, acceptable
statuses, feasible assignment, objective gap or audit success. No Pyomo solution
loading, canonical completion, generation projection or numerical audit occurs
before initial raw persistence. A downstream callback return and completion file
are operational records only; scientific/native authentication flags stay false.

Raw uses the existing 16 MiB hard ingress cap. If extraction cannot return bytes,
serialization exceeds that cap, or persistence is interrupted, complete raw is
not guaranteed. Partial files remain. A tighter conditional grammar/content
bound, memory bound, total storage including this additional native raw copy,
full segmented timing and filesystem admission remain outstanding. Fsync and
fresh readback do not establish directory-entry power-loss durability.

Tests borrow the actual installed `DirectSolver.solve` method with a synthetic
adapter and `_save_results=False`. They prove ordering around its postsolve call,
not actual Gurobi export, real `_postsolve` or the `_save_results=True` symbol-map
branch. Failure cases cover original apply errors, missing/no-incumbent output,
postsolve errors, native/model/metadata drift, storage failures, consumer rejection,
close failure/drift, terminal/publication failure and second apply/reentry.
Deliberate external raw replacement is detected, not repaired. Preserved negative/NaN values are not
scientific witnesses. Actual native infinity getter behavior, exact adapter
ownership and full 232-stage/192-hour producer coverage remain unverified.

Next integration requires a versioned scientific consumer/replay for this schema,
the approved generation mapping with all constraints rechecked, complete timing,
and the independent hour Job controller. `collector_integrated`,
`native_export_coverage`, `producer_coverage_proven`, `resource_admission`,
`formal_execution_ready` and `formal_result` remain false. Binding/raw/complete
records share explicit false flags, also covering native authorization and
authentication and scientific acceptance. New native execution
still requires a concrete ready package, gates and explicit authorization.
