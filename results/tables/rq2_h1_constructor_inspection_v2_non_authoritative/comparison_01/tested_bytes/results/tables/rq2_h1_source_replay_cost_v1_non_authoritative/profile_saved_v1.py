"""One read-only saved-prefix Reader under cProfile; zero Job/native."""
import cProfile
from hashlib import sha256
import json
import os
from pathlib import Path
import pstats
import sqlite3
import sys
import time
import traceback
from contextlib import closing

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO / 'tests'))

import pytest
from experiments import h1_phase_historical_batch_development_v1 as historical
from experiments import h1_phase_exact_source_batch_development_v1 as source_batch
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests import h1_cross_hour_outage_fixture_v1 as case
from tests.h1_cross_hour_identity_fixture_v1 import immutable_code_identities

CASE = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')


def load(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def inventory(root):
    return {str(path): pin(path) for path in root.rglob('*') if path.is_file()}


def install_saved_fixture(patch):
    expected = {CASE / 'upstream/SHA256SUMS': b'synthetic-current-source\n', CASE / 'source.yaml': b'{}'}
    mkdir, write = Path.mkdir, Path.write_bytes
    with pytest.MonkeyPatch.context() as temporary:
        def same_mkdir(path, *args, **kwargs):
            if path == CASE / 'upstream':
                assert path.is_dir()
                return None
            return mkdir(path, *args, **kwargs)
        def same_write(path, raw):
            if path in expected:
                assert path.read_bytes() == raw == expected[path]
                return len(raw)
            return write(path, raw)
        temporary.setattr(Path, 'mkdir', same_mkdir)
        temporary.setattr(Path, 'write_bytes', same_write)
        value = supplied.__wrapped__(CASE, patch)
    value = environment.__wrapped__(value, patch)
    case.install_case(value, patch)
    no_solver.__wrapped__(patch)
    # Reuse the exact pinned manifest, as in the saved-profile predecessor.
    # Rebuilding its real-source audit after installing a three-hour toy source
    # would mix incompatible source scopes.
    manifest_raw = (historical.binding.ROOT / historical.binding.MANIFEST).read_bytes()
    assert sha256(manifest_raw).hexdigest() == historical.binding.MANIFEST_PIN
    resolver = historical.binding.manifest._resolver(manifest_raw)
    patch.setattr(historical.binding, 'open_manifest', lambda: resolver)
    patch.setattr(historical.binding, 'precheck', lambda resolver, declaration, **kw:
                  resolver.resolve(kw['family'], kw['ordinal']))
    patch.setattr(historical.binding, 'prevalidate_enrollment', lambda *a, **kw:
                  dict(test_only_synthetic_source=True))


def main():
    output = Path(sys.argv[1]).resolve()
    assert output.parent == HERE and output.is_dir()
    old = load(REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    before = inventory(CASE)
    assert before == old['diagnostic_case_files_sha256'] and len(before) == 465
    checkpoint = load(CASE / 'external_preclose_checkpoint.json')
    assert all(pin(name) == expected for name, expected in checkpoint['saved_files_sha256'].items())
    assert len(checkpoint['saved_files_sha256']) == 444
    database = CASE / 'owner_non_authoritative/owner.sqlite'
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as db:
        intents = [json.loads(row[0]) for row in db.execute("SELECT body FROM events WHERE kind='intent' ORDER BY seq")]
    assert [row['hour'] for row in intents] == [0, 1, 2]
    directory = CASE / 'normal_non_authoritative/obligation_non_authoritative'
    terminals = {hour: pin(directory / f'{hour:03d}.terminal.json') for hour in range(3)}
    args = dict(expected_binding_sha256=pin(directory / 'binding.json'),
                expected_terminal_sha256=terminals[2], completed_hours=3,
                expected_terminals=terminals, selected_hours=(0, 1, 2))
    (output / 'reader_request.json').write_text(json.dumps(dict(
        root=str(directory.parent), arguments=args, retained_case_files=465,
        synthetic_fixture=True, immutable_code_fixture=True, Jobs=0, real_native_calls=0,
        formal_result=False), indent=2) + '\n', encoding='utf-8')
    case_prefix = os.path.normcase(str(CASE)) + os.sep
    audit_counts = dict(old_case_read_opens=0, rejected_mutations=0)
    def within(value):
        if not isinstance(value, (str, bytes, os.PathLike)):
            return False
        return (os.path.normcase(os.path.abspath(os.fsdecode(value))) + os.sep).startswith(case_prefix)
    def audit(event, values):
        mutation = False
        if event == 'open' and within(values[0]):
            _, mode, flags = values
            mutation = (isinstance(mode, str) and any(letter in mode for letter in 'wax+')) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC)))
            audit_counts['old_case_read_opens'] += not mutation
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime', 'os.truncate'):
            mutation = within(values[0])
        elif event in ('os.rename', 'os.link', 'os.symlink'):
            mutation = any(within(path) for path in values[:2])
        if mutation:
            audit_counts['rejected_mutations'] += 1
            raise RuntimeError('saved-case filesystem mutation denied')
    sys.addaudithook(audit)
    patch = pytest.MonkeyPatch()
    profiler = cProfile.Profile()
    error = None
    result = {}
    started = time.perf_counter()
    try:
        install_saved_fixture(patch)
        with immutable_code_identities(output / 'static_identity_bookends.json'):
            with profiler:
                proofs, captured, header, metric = historical.replay_prefixes(directory.parent, **args)
            assert metric['parent_inspect_traversals'] == 2
            assert set(proofs) == set(captured) == {0, 1, 2}
            audits = []
            for hour in range(3):
                envelope = source_batch.prior._envelope(header, captured[hour], proofs[hour])
                # Existing owner intents bind the corresponding historical normal audit.
                expected = intents[hour]['source_audit']['normal_audit_payload']
                assert historical.io.encode(expected) == envelope.audit_payload
                assert proofs[hour] == intents[hour]['source_audit']['historical_controller']
                audits.append(dict(hour=hour, normal_audit_sha256=sha256(envelope.audit_payload).hexdigest(),
                                   decision_sha256=sha256(envelope.decision.decision_bytes).hexdigest()))
            result.update(metric=metric, saved_normal_audits_equal=True, captured_audits=audits)
    except BaseException:
        error = traceback.format_exc()
        (output / 'error.txt').write_text(error, encoding='utf-8')
    finally:
        patch.undo()
    profiler.dump_stats(str(output / 'profile.pstats'))
    stats = pstats.Stats(profiler) if profiler.getstats() else None
    functions = []
    edges = []
    for (file, line, name), (primitive, calls, self_seconds, cumulative, callers) in (stats.stats.items() if stats else ()):
        functions.append(dict(file=file, line=line, function=name, primitive_calls=primitive,
            calls=calls, self_seconds=self_seconds, cumulative_seconds=cumulative))
        for (caller_file, caller_line, caller_name), counts in callers.items():
            edges.append(dict(caller_file=caller_file, caller_line=caller_line, caller=caller_name,
                callee_file=file, callee_line=line, callee=name, counts=list(counts) if isinstance(counts, tuple) else counts))
    functions.sort(key=lambda row: row['cumulative_seconds'], reverse=True)
    (output / 'profile_functions.json').write_text(json.dumps(functions, indent=2) + '\n', encoding='utf-8')
    (output / 'profile_call_edges.json').write_text(json.dumps(edges, indent=2) + '\n', encoding='utf-8')
    with (output / 'profile.txt').open('w', encoding='utf-8') as stream:
        if stats:
            pstats.Stats(profiler, stream=stream).sort_stats('cumulative').print_stats(60)
        else:
            stream.write('No profiled Reader executed; see error.txt and reader_terminal.json.\n')
    def calls(suffix, name):
        return sum(row['calls'] for row in functions if row['file'].replace('\\', '/').endswith(suffix) and row['function'] == name)
    counts = dict(inspect_job=calls('h1_timed_job_parent_development_v1.py', 'inspect_job'),
                  timed_stage_inspect=calls('h1_timed_stage_development_v1.py', 'inspect'))
    after = inventory(CASE)
    accepted = error is None and before == after and counts == dict(inspect_job=12, timed_stage_inspect=60)
    result.update(status='DRAFT_NONAUTHORITATIVE', exit_code=0 if accepted else 1,
        error=error, elapsed_seconds=time.perf_counter() - started, profile_total_calls=stats.total_calls if stats else 0,
        profile_primitive_calls=stats.prim_calls if stats else 0, call_counts=counts, saved_case_files=len(before),
        saved_case_bytes_unchanged=before == after, audit=audit_counts, cprofile_overhead_included=True,
        complete_dynamic_closure_proved=False, unobserved_ABA_covered=False,
        optimization_implemented=False, complete_owner_chain_profile=False,
        Jobs=0, real_native_calls=0, formal_result=False)
    with (output / 'reader_terminal.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('error', 'captured_audits')}, indent=2), flush=True)
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
