"""Compare the observer against the actual original v3 accounting visitor."""
from dataclasses import dataclass,asdict
from fractions import Fraction
from importlib.util import module_from_spec,spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from experiments.h1_phase_historical_batch_development_v1 import retained_size

HERE=Path(__file__).resolve().parent
spec=spec_from_file_location('M232_accounting_observer',HERE/'packet_worker_v2.py')
worker=module_from_spec(spec);spec.loader.exec_module(worker)
api=SimpleNamespace(retained_size=retained_size)


def test_shared_key_representation_change_keeps_semantics_and_is_observed():
    @dataclass
    class Record:
        name:str
        power:float
        hour:int
    value=Record('fixed',1.0,0);semantics=asdict(value)
    before=worker.observe_accounting(api,value)
    other=[Record('other',2.0,h) for h in range(40)]
    after=worker.observe_accounting(api,value)
    assert len(other)==40 and asdict(value)==semantics
    assert before['original_measure_equals_layout_walk'] and after['original_measure_equals_layout_walk']
    assert before['reachable_object_types_and_sizes']==after['reachable_object_types_and_sizes']
    assert before['observed_recursive_bytes']>after['observed_recursive_bytes']
    assert (before['observed_recursive_bytes']-after['observed_recursive_bytes']
        ==before['instance_dict_bytes']-after['instance_dict_bytes'])


def test_container_aliases_and_fraction_match_actual_visitor():
    shared={'same':(Fraction(3,7),b'payload')}
    pair=(shared,shared)
    observed=worker.observe_accounting(api,pair)
    assert observed['original_measure_equals_layout_walk']
    assert observed['observed_recursive_bytes']==retained_size(pair)
    assert observed['instance_dict_bytes']==0
    fraction,payload=shared['same']
    expected=(pair,shared,next(iter(shared)),shared['same'],fraction,
        fraction.numerator,fraction.denominator,payload)
    assert set(observed['reachable_object_types_and_sizes'])=={str(id(item)) for item in expected}
