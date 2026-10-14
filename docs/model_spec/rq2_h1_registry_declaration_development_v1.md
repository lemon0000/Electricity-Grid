# Pre-execution registry declaration

Status: DRAFT_NONAUTHORITATIVE. This metadata declaration binds the expected
outage registry identity before a future bootstrap attempt. It is not an owner
capability, formal authorization or evidence of an accepted current window.

`build(split)` verifies the 983-pin predecessor closure and computes the existing
registry identity formula from its frozen authority/archive/source/cap/catalog
and implementation pins. It includes the selected archive member's metadata and
the explicit split. The registry identity itself is global, so split must remain
a separate binding. No compressed rows are decoded, including holdout rows.

`inspect(path, expected_sha256, split)` requires an externally retained hash,
freshly rebuilds canonical bytes and compares them exactly. Dependency reads and
the declaration file are bookended. The returned dict is detached metadata;
manual construction or a matching caller hash grants no execution authority.

A later bootstrap configuration must pin a pre-existing declaration path/hash
before retaining its attempt. It must use the retained expected registry identity
with the existing `registry.prepare` and phase source preparation to establish
the exact split/seed/start/current prefix and N correspondence. No runtime
discovery fallback, state-chain attachment or bootstrap integration is implemented
in this unit. Synthetic outage and repair assumptions remain mechanism inputs,
not empirical observations or security certification.
