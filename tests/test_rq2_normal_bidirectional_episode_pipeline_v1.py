from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from tests.test_rq2_normal_bidirectional_episode_transport_v1 import (
    packet, bound, supplied, legacy_request, declared_source, prepared_source,
    bound_source, original_bound_source, base_bound_source, source_supplied, original_source_supplied)
from src.rq2_joint_deliverability_boundary_v1 import normal_bidirectional_episode_controller as api


@pytest.fixture
def pipeline(packet, bound, bound_source, tmp_path_factory, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_worker as codec
    parent = tmp_path_factory.mktemp('bound_episode_pipeline')
    context = parent/'synthetic_source.json'
    context.write_text(json.dumps(dict(inputs=codec._encode(bound_source[2].inputs),
        pair=bound_source[3], window=bound_source[4],
        config=api.worker.transport.binding.source_pair.source_window.audit._load_config(None),
        source_root=str(api.worker.transport.binding.source_pair.source_window.audit.ROOT))), encoding='utf-8')
    bootstrap = parent/'synthetic_worker.py'
    repository = Path(__file__).resolve().parents[1]
    bootstrap.write_text('import sys\nsys.path.insert(0, '+repr(str(repository))+')\n'+'''
import json
from copy import deepcopy
from pathlib import Path
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as codec
from src.rq2_joint_deliverability_boundary_v1 import source_normal as source
from src.rq2_joint_deliverability_boundary_v1 import pair_normal_stream as pair
from src.rq2_joint_deliverability_boundary_v1 import normal_bidirectional_episode_worker as worker
context=json.loads(Path(sys.argv.pop(1)).read_text(encoding='utf-8'))
inputs=codec._decode(context['inputs'])
source.RTS_GMLC_MANIFEST_SHA256=inputs.carry.identity.source_sha256
source.verify_sha256_manifest=lambda root: True
source.load_rts_gmlc_chronological_data=lambda root: inputs.data
pair.source_pair.prepare_source_pair=lambda *a,**k:deepcopy(context['pair'])
pair.source_window.load_source_window=lambda *a,**k:deepcopy(context['window'])
pair.source_window.audit._load_config=lambda *a:deepcopy(context['config'])
pair.source_window.audit.ROOT=Path(context['source_root'])
pair.source_window.audit._verify_package=lambda *a:(None,{'grid_source_manifest_sha256':inputs.carry.identity.source_sha256})
pair.source_window.audit._verify_hash=lambda *a:None
worker.main()
''', encoding='utf-8')
    argv = api._argv
    def synthetic_argv(*args):
        actual = argv(*args)
        return actual[:3]+[str(bootstrap), str(context)]+actual[4:]
    monkeypatch.setattr(api, '_argv', synthetic_argv)
    mib = 1024**2
    allocation = api.PipelineBudget(api.process.TaskProcessBudget(240., .05, 1536*mib, 2048*mib, 3.),
        api.process.TaskProcessBudget(120., .05, 1024*mib, 1024*mib, 3.), 120,
        16*mib, 16*mib, 1024*mib, 11014, 1000)
    root = parent/'pipeline_non_authoritative'
    kwargs = dict(allocation=allocation, environment=bound[3])
    kwargs['expected_controller_identity'] = api.controller_identity(root, packet, **kwargs)
    return root, packet, kwargs


def test_real_bound_execute_and_independent_audit(pipeline):
    root, packet, kwargs = pipeline
    result = api.supervise_episode(root, packet, **kwargs)
    assert result['status'] == 'observed_window_replayed'
    assert result['normal_binding']['business_pair_correspondence_verified']
    assert result['normal_binding']['solver_calls_by_binding'] == 0
    for mode in ('execute', 'audit'):
        receipt = json.loads((root/(mode+'_receipt_non_authoritative.json')).read_bytes())
        assert receipt['normal_binding'] == result['normal_binding']
    assert result['audit']['selected_phase_chains_replayed'] == 5
    assert not result['formal_result'] and not result['complete_service_certified']
    with pytest.raises((ValueError, FileExistsError)): api.supervise_episode(root, packet, **kwargs)
