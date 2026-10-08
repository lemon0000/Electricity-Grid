from copy import deepcopy
import pytest

from test_rq2_objective_provenance_run_v1 import tiny_report, builder
from experiments import replay_rq2_h25_native_provenance_v1 as api


def test_replay_recomputes_complete_numeric_evidence_without_solver(tiny_report, monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('replay must not solve')
    monkeypatch.setattr(api.entry.run,'solve_once',forbidden)
    monkeypatch.setattr(api.entry.run.provenance.adapter,'create_solver',forbidden)
    report=api.verify_numerical(builder(),tiny_report['numerical'])
    assert report['solver_calls_by_replay']==0
    assert report['objective_algebra_recomputed'] and report['canonical_assignment_recomputed']
    assert not report['native_execution_authenticated'] and not report['normal_accepted']


@pytest.mark.parametrize('fault',['assignment','residual','canonical_term','native_term','ref_inventory','comparison'])
def test_independent_replay_rejects_tamper(tiny_report,fault):
    n=deepcopy(tiny_report['numerical'])
    p=n['provenance']
    if fault=='assignment': n['assignment'][0][1]=0.0.hex()
    if fault=='residual': n['maximum_residual']=1.
    if fault=='canonical_term': p['ordered_objective_terms'][0][1]=3.0.hex()
    if fault=='native_term': p['ordered_native_objective_terms'][0][1]=3.0.hex()
    if fault=='ref_inventory': p['referenced_assignment']=[]
    if fault=='comparison': p['comparisons']['lower_le_exact']=False
    with pytest.raises(ValueError):
        api.verify_numerical(builder(),n)
