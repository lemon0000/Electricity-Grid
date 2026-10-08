"""Isolated single-hour calibration worker; seal/review/authority are mandatory."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v2 as api

if __name__ == '__main__':
    try:
        if len(sys.argv) != 5:
            raise ValueError('sealed calibration package and independent review required before execution')
        api._execute_calibration_worker(*sys.argv[1:])
    except BaseException as error:
        # Keep bounded diagnostics; no result or numerical status is synthesized.
        with (Path.cwd()/'full_job_worker_error.txt').open('xb') as stream:
            stream.write((type(error).__name__+': '+str(error)).encode('utf-8', 'backslashreplace')[:4096])
        raise SystemExit(2)
