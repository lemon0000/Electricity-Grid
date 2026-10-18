"""Isolated zero-solver saved-report worker; creates no native authority."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from experiments import h1_saved_job_development_v1 as api

if __name__=='__main__':
    try:
        if len(sys.argv)!=3:raise ValueError('exact saved request path and pin required')
        api.execute_saved_worker(*sys.argv[1:])
    except BaseException as error:
        with (Path.cwd()/'saved_job_worker_error.txt').open('xb') as stream:
            stream.write((type(error).__name__+': '+str(error)).encode('utf-8','backslashreplace')[:4096])
            stream.flush()
            api.os.fsync(stream.fileno())
        raise SystemExit(2)
