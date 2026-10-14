# Complete phase dependency verifier with bounded read allocation

Status: DRAFT_NONAUTHORITATIVE; execution and independent review are pending.

The measured old reader requests `cap+1` bytes even after obtaining the exact
initial file size. The successor requests `initial_size+1`, preserving the full
path-stat, opened-fstat, read-length, closing-fstat and final-path-stat checks.
One extra byte detects visible growth, including growth past the declared cap.
Truncation, short reads, replacement and observed metadata changes still reject.
Neither reader proves the absence of byte/metadata ABA that escapes every
observation. The reader retains the predecessor regular-file contract; it does
not add a hardlink or ancestor-reparse safety claim.

`prepare_group` explicitly reconstructs the complete pinned symbolic and group
dependency inventory using the new reader, then invokes the predecessor's pure
projection. It re-reads all files at return and compares both raw bytes and full
file identities. The exact pinned baseline continues to authorize its two
external environment dependencies. No obligation, family, sibling or B6 entry
is removed. Duplicate inventory entries must yield identical views. There are
logical file-count and total-byte bounds, not a physical-memory admission claim.

The result separately names the new verifier's SHA256 and the unchanged
predecessor scientific group projection/identity. It is manually constructible
detached data, not authenticated owner input, execution provenance or a reuse
credential. All formal/resource/native/owner-consumption flags remain false.
The old reader, manifest modules and closed results are unchanged. No global
reader replacement is used, and source, historical, exact-current and durable
journal readers retain their prior implementations.

Acceptance requires small-file read-size regression coverage; stable-file parity
at zero, one and exact-cap sizes; over-cap, append, truncate, short-read and
same-byte replacement refusal; complete projection parity across all four
families and the existing mixed proof/nonzero-capacity group; and complete exit
view byte/stamp checks. Independent review must distinguish this verified group
entrypoint from integration into roster/common operations. The latter remains
open, as does the full three-lane synthetic integration. Further optimization
must be chosen from new measurements, preserving both scientific replay rounds.


F1 draft repair: helper dispatch is captured at import, with entry, pre-projection
and exit reference checks. Flags must have exactly the declared keys and false
values. The separately named verifier implementation identity binds its schema,
own file and explicit predecessor group/symbolic/proof/IO file hashes, all with
exit observations. The predecessor scientific group identity remains unchanged.
This detects ordinary observed helper substitution, not arbitrary Python
reflection, code-object modification or substitution restored between checks.

Nested predecessor protocol constants, file paths, exact flags and proof resolver
are also captured and checked at all three boundaries. Inventory construction
uses captured constants. Entry and exit mutation tests cover this dependency layer.

The direct resolver execution layer is checked as well: Resolver class and its
three used methods, node builder, IO alias, schema/catalog/missing mapping, and
JSON module/decoder references. Unused compiler/build paths and standard-library
internals are outside this bounded substitution check.
