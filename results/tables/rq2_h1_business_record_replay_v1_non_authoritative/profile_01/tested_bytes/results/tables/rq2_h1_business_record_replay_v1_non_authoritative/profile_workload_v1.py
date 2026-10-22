"""Fixed zero-native total-validator diagnostic; not an owner experiment."""
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import time

from experiments import h1_exact_business_development_v1 as business
from tests import test_h1_exact_business_development_v1 as fixture
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def test_fixed_total_validator_profile(tmp_path):
    # Import after the autouse no_solver guard has denied native entry points.
    from experiments import h1_business_record_replay_operation_development_v1 as replay
    plan = json.loads(Path(__file__).with_name('profile_plan_v1.json').read_bytes())
    assert plan['horizons_business_hours'] == [4, 16, 32]
    assert plan['orders'] == [['original', 'successor'], ['successor', 'original']]
    started = time.perf_counter()
    carries = [fixture.origin()]
    for hour in range(32):
        item = fixture.hour(carries[-1], hour, g=Q(17, 200) if hour == 0 else Q(0),
                            source=Q(1, 2) if hour == 0 else Q(0))
        carry = fixture.advance(carries[-1], item).next_candidate
        assert carry is not None
        carries.append(carry)
    build_seconds = time.perf_counter() - started
    started = time.perf_counter()
    before = [sha256(carry.scientific_payload).hexdigest() for carry in carries]
    hash_seconds = time.perf_counter() - started
    rows = []
    for horizon in plan['horizons_business_hours']:
        selected = carries[:horizon + 1]
        for repeat, order in enumerate(plan['orders']):
            for path in order:
                started = time.perf_counter()
                if path == 'original':
                    for _ in range(2):
                        for carry in selected:
                            assert business._validate(carry) is None
                    observed = None
                else:
                    with replay.RecordReplayOperation() as operation:
                        for _ in range(2):
                            for carry in selected:
                                assert operation.validate(carry) is None
                    observed = operation.observation
                elapsed = time.perf_counter() - started
                if observed is not None:
                    assert observed['validator_calls'] == 2 * (horizon + 1)
                    assert observed['records_observed'] == horizon * (horizon + 1)
                    assert observed['original_record_replays'] == horizon
                    assert observed['record_reuses'] == horizon ** 2
                    assert observed['closed_cleanly'] and observed['cache_cleared']
                    assert not observed['active'] and not observed['poisoned']
                row = dict(horizon=horizon, repeat=repeat, path=path,
                           total_validator_wall_seconds=elapsed,
                           validator_calls=2 * (horizon + 1),
                           original_record_replay_work_units=horizon * (horizon + 1),
                           operation_observation=observed)
                rows.append(row)
                with (tmp_path / 'profile_rows.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(row) + '\n')
                print(json.dumps(row), flush=True)
    started = time.perf_counter()
    after = [sha256(carry.scientific_payload).hexdigest() for carry in carries]
    hash_seconds += time.perf_counter() - started
    assert after == before
    (tmp_path / 'profile_fact.json').write_text(json.dumps(dict(
        status='DRAFT_NONAUTHORITATIVE', business_hours=32, rows=rows,
        fixture_build_wall_seconds=build_seconds, payload_hash_wall_seconds=hash_seconds,
        scientific_payload_sha256=before, scientific_payloads_unchanged=True,
        original_and_successor_acceptance_equal=True,
        complete_owner_chain_profile=False, paired_owner_authenticated=False,
        phase_events_written=0, real_native_calls=0, new_normal_jobs=0,
        formal_result=False), indent=2) + '\n', encoding='utf-8')
