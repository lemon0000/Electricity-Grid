"""Explicit local Gurobi license routing for development children."""
import os
from pathlib import Path

from . import normal_worker as legacy
from .normal_worker import _decode, _write_once, process


def _environment(environment):
    process._environment_block(environment)
    if 'GRB_LICENSE_FILE' not in environment:
        raise ValueError('explicit Gurobi license path required')
    legacy._environment({k: v for k, v in environment.items() if k != 'GRB_LICENSE_FILE'})
    path = Path(environment['GRB_LICENSE_FILE'])
    if (not path.is_absolute() or not path.is_file() or path.is_symlink()
            or str(path).startswith(('\\\\', '//'))):
        raise ValueError('existing absolute local license file required')


def development_environment():
    environment = legacy.development_environment()
    environment['GRB_LICENSE_FILE'] = os.environ.get('GRB_LICENSE_FILE', '')
    _environment(environment)
    return environment
