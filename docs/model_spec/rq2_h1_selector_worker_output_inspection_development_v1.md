# Selector worker output inspection development

DRAFT_NONAUTHORITATIVE. This read-only unit is the complete conditional reader
for the selector controller's future `on_quiescent` callback. The controller must
first validate its owned live Job wait and complete cleanup. This reader accepts
no TaskProcessObservation and issues no execution credential.

`inspect` requires exactly six parent-produced input pins, explicit environment,
and expected process identity/PID/creation. Fresh mode (`expected_output_pins=None`)
performs the first bounded stable read of consumed/result/timing outputs and
derives their pins itself. Retained mode requires exactly those three output pins
in addition to the six inputs. Fresh derived hashes are bookends, not external
authentication. Both modes return all nine pins inside the lifecycle's bounded,
detached JSON diagnostic envelope.

The reader checks exact namespaces, plain single-link non-reparse files, canonical
encoding and individual byte caps. Scratch is an opaque plain directory with fixed
identity. The fresh source snapshot is rebuilt and the entire request projection
is independently reconstructed from typed context/configuration; worker `_match`
and `_projection` are not used as the parent oracle. Launch argv/cwd/environment,
host/budget and implementation reconstruct process identity. Initial headroom,
child/release/consume links and exact expected PID/creation must agree.

Full scientific and timing sequence replay determines request, record hashes,
terminal pins, native aggregate and full archive-view fingerprint. Result and
worker timing terminal must have exactly the reconstructed fields and all-false
authority flags. Eight prescribed phases are integer, ordered, contiguous and
have the exact entry-to-result delta. Every replayed stage/native window lies
within the run phase and shares PID/thread. The current fixed clock profile must
match, but no cross-process clock bridge or non-solver allowance is proved.

Source is rebuilt again before return. Metadata full stamps, root identities,
complete science/timing archive view and imported validator/reader/codec identities
are bookended around callbacks. Worker caps/phase names/namespaces/flags retain
their initial values. The whole public operation forbids solver calls.

Output is fresh conditional replay only: no historical native execution, whole-
Job quiescence, persistent lane transaction, live Rref capability or formal result
is authenticated. Actual's source rebuilding covers science and business mapping;
the future parent must separately bind Rref Job provenance before Actual release.
It must jointly bind the live lifecycle observation and this diagnostic in its own
parent terminal. All production/resource/formal gates remain false.
