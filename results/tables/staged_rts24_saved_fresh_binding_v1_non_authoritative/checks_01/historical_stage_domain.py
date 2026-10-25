"""Reuse only the unchanged generic stage/guard domain, not saved execution."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PRIOR = ROOT/'results/tables/staged_rts24_saved_fresh_entry_v1_non_authoritative/checks_01/stage_reuse_oracle.py'


def verify():
    spec = importlib.util.spec_from_file_location('historical_generic_stage', PRIOR)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    result = value.verify()
    assert result['historical_nodes'] == 87 and result['counted_as_current_epoch_nodes'] is False
    return result


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True))
