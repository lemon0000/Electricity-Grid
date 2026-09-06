# RQ2 joint-deliverability fresh-process activation successor v2

## 1. Status and authority

This R3 successor is the single versioned REWORK of sealed activation v1. It
retains the process-isolation boundary and replaces pathname-based artifact
reads with descriptor- or handle-anchored component traversal. It does not
authorize or expose a write-capable experiment stage.

It binds:

- execution v3 outer
  `b153f0320fe9dfe961575be4836f4bcf4044836be4fa66618119fc08d4cbce80`;
- execution v3 independent review receipt
  `1d8312e1458ce73dc76863a4b5c85f95506272ec53eaa088e523127b6ce0fa41`;
- activation v1 outer
  `7672d1a6f3382e268b5ffa0b22a561e72615bb0b5dc419f0b48916652da860d4`;
- activation v1 official REWORK receipt
  `11363e30bfe497dfb1f6f8f35fbb3c44297300bdcc9fc68b2eae0a3afcd6093a`;
- the complete local Python import closure used by the activation probe.

The activation v2 review receipt remains outside the reviewed outer to avoid a
self-hash cycle. An independent activation PASS closes only the activation
review gate. The receipt must identify `gpt-5.6-sol`, cannot predate the seal,
and binds outer, inner and member count from one sealed-bundle verification.

## 2. Why this successor cannot execute

Execution v3 is immutable and registers the dispatched-grid manifest, runtime
authority and activation authority as `null/ready=false`. Its public planning,
holdout, bootstrap and aggregate entry points remain hard closed.

Activation v2 must not:

1. construct an in-memory overlay that replaces those sealed null values;
2. call execution v3 private `_from_audit` stage helpers;
3. reinterpret missing grid/runtime authority as infeasibility;
4. create an evidence store, lease or formal output root.

A later execution successor must bind non-null grid, runtime and activation
authorities. A separate user instruction must then authorize the exact formal
run.

## 3. Fresh-process boundary

`bootstrap_rq2_joint_deliverability_activation_v2.py` imports only Python
standard-library modules at module load. Validation proceeds in this order:

1. open every required artifact by anchored component traversal: POSIX uses
   `open(..., dir_fd=..., O_NOFOLLOW)` from the filesystem anchor; Windows uses
   `NtCreateFile` with the previously opened directory handle as
   `OBJECT_ATTRIBUTES.RootDirectory` and `FILE_OPEN_REPARSE_POINT`;
2. read each file twice from one descriptor, reopen it by a second anchored
   traversal, and require identical bytes and metadata identity; all ancestor
   descriptors/handles remain owned until leaf validation completes, and close
   failures trigger bounded cleanup plus rejection;
3. verify the activation config;
4. when sealed, verify activation outer, inner and every exact member;
5. recursively verify activation v1 outer and its REWORK receipt;
6. recursively verify execution v3 outer, inner and all 22 members;
7. verify the fixed execution v3 PASS receipt digest;
8. stable-read and hash every member of the registered local Python closure;
9. bind the verified config bytes, activation predecessor, bundle and execution
   identities and all 13
   verified local source files into one canonical parent envelope;
10. create a private empty temporary bytecode-cache directory and start a
   minimal `-c` stage-0 with `-I -B -S -X pycache_prefix=<that directory>`;
   stage-0 accepts only the digest-bound envelope over stdin, extracts the
   verified bootstrap bytes, and compiles them without opening the live
   bootstrap;
11. before project imports, reject site initialization,
   any nonempty or replaced bytecode-cache directory, and any preloaded local
   module other than the bootstrap script itself;
12. install a private in-memory loader for the envelope's verified local source
   bytes, block fallback for every unregistered sibling under a protected
   project package, add only `sysconfig`'s `purelib`/`platlib` paths without
   processing `.pth` files, then import the activation controller and execution
   v3;
13. revalidate activation v1 and execution v3 authority and confirm registered
    inputs remain
   non-ready;
14. require the isolated bytecode-cache directory to remain empty, map every
    imported repository-local module back to its resolved `__file__`, and
    require the final executed set to equal the registered eager closure;
15. have the parent require exact `13/11/11` verified/observed/executed
    inventories, the full 13-member source hash map and the exact runtime
    schema/static authority, independently confirm the cache stayed empty, and
    replay the config, bundle, execution authority and source snapshot after
    child exit.

The probe reports zero solver calls and zero formal result writes. It neither
creates nor consumes execution authority.

## 4. Closure

The production closure is derived independently from Python AST imports,
including function-local imports and package `__init__.py` files. Its roots are:

- activation bootstrap;
- activation imported controller;
- execution v3 core;
- implementation v2 reference runner.

The discovered set must exactly equal the config inventory. Runtime observation
may be a subset because the implementation runner is imported lazily, but every
observed local module must be registered and rehashed.

## 5. Failure semantics

Duplicate JSON keys, non-finite values, exponent overflow, path traversal,
symlink/reparse aliases, ancestor-directory replacement, unstable reads, digest
drift, a preloaded local module,
an existing project bytecode cache in the isolated prefix, an unregistered
post-import module or a changed execution authority all fail closed.
Sealed manifest verification rereads outer, inner and every member after the
first complete pass. Runtime project imports compile only the verified in-memory
source bytes, so changing a repository source after its verified read cannot
change the bytes executed by the probe.
Presence checks require two complete anchored traversals to agree. Only a
stable missing component is accepted as absence; aliases, absent-to-present
ancestor swaps, type mismatches and indeterminate errors fail closed. A
dangling Windows junction therefore cannot satisfy an authority-absence or
draft-manifest-absence gate.

`--execute` is intentionally hard closed before config reads, project imports,
subprocess creation or filesystem mutation. This prevents an activation review
PASS from being mistaken for formal-run authority.

## 6. Tests

Focused tests cover:

- independent AST closure equality;
- closure digest drift at bootstrap, controller and execution core;
- a valid but malicious timestamp-based `.pyc` displaced by the fresh empty
  cache prefix;
- a live-bootstrap replacement after parent verification and an unregistered
  live sibling import with a body-side-effect sentinel;
- forged child inventory/count output and parent-envelope source drift;
- missing, extra or altered child source hashes and runtime fields;
- unregistered post-import modules;
- execution outer and review digest drift;
- exact ordered execution predecessor inventory;
- activation receipt absent, valid, tampered and dangling-symlink states;
- mixed-generation outer/inner, reviewer-model and pre-seal-date receipt faults;
- manifest-generation changes during member replay and synchronized
  config/receipt contract tampering;
- live-source changes after verified bytes are captured by the in-memory
  source loader;
- any unexpected grid, runtime, execution-activation or formal-run authority;
- deterministic reparse evidence and a Windows-native dangling-junction probe
  for closed authorities and draft manifests;
- duplicate/non-finite JSON;
- dangling-symlink authority paths;
- descriptor-open path-swap detection;
- ancestor-directory replacement during descriptor-anchored traversal;
- absent-to-present ancestor replacement during authority presence checks;
- descriptor/HANDLE close failures and child-resource ownership cleanup;
- activation v1 outer and official REWORK receipt binding;
- POSIX relative-descriptor and Windows relative-handle traversal contracts;
- terminate, wait and kill exception cleanup with explicit reap failure;
- sealed lifecycle exact keys and ISO date validation;
- fresh-process validation with zero solver/write effects;
- unconditional rejection of `--execute`;
- direct prohibition of execution v3 private stage helpers.

## 7. Remaining blockers

Independent activation review does not resolve:

1. complete 1,071-file dispatched-grid package;
2. Windows x86-64 runtime receipt;
3. Gurobi 13.0.2 native replay with four threads;
4. registered-scale peak-memory evidence;
5. measured transport runtime projection;
6. a new execution successor binding all non-null authorities;
7. separate user formal-run authorization.

No formal result, paper claim or security certification follows from this
successor.
