"""One bounded synthetic capacity check in the declared development environment."""
from dataclasses import asdict
from argparse import ArgumentParser
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process

CHILD = '''
import json
from pathlib import Path
from importlib.metadata import version
import gurobipy as gp
assert version('gurobipy') == '13.0.2'
with gp.Env(empty=True) as env:
    env.setParam('OutputFlag', 0)
    env.start()
    with gp.Model(env=env) as model:
        model.Params.Threads = 1
        model.Params.TimeLimit = 5.
        model.Params.Seed = 0
        x = model.addVars(22275, lb=0.)
        model.addConstrs((x[i % 22275] >= 0. for i in range(28004)))
        model.setObjective(gp.quicksum(x.values()))
        model.optimize()
        assert model.NumVars == 22275 and model.NumConstrs == 28004
        result = dict(schema='synthetic_license_capacity_observation_v1',
            variables=model.NumVars, constraints=model.NumConstrs,
            status=model.Status, solution_count=model.SolCount,
            objective=model.ObjVal if model.SolCount else None,
            solver_runtime_seconds=model.Runtime, formal_result=False,
            research_model_solved=False, threads=model.Params.Threads,
            time_limit_seconds=model.Params.TimeLimit, seed=model.Params.Seed)
        with Path('capacity.json').open('x', encoding='utf-8') as f:
            json.dump(result, f, sort_keys=True)
'''


def validate_result(raw):
    body = json.loads(raw)
    keys = {'schema', 'variables', 'constraints', 'status', 'solution_count', 'objective',
        'solver_runtime_seconds', 'formal_result', 'research_model_solved',
        'threads', 'time_limit_seconds', 'seed'}
    if type(body) is not dict or set(body) != keys:
        raise ValueError('exact capacity record required')
    if (body['schema'] != 'synthetic_license_capacity_observation_v1'
            or body['formal_result'] is not False or body['research_model_solved'] is not False):
        raise ValueError('non-authoritative synthetic scope required')
    for key, value in (('variables', 22275), ('constraints', 28004), ('status', 2),
            ('solution_count', 1), ('threads', 1), ('seed', 0)):
        if type(body[key]) is not int or body[key] != value:
            raise ValueError('unexpected capacity count or native status')
    for key in ('objective', 'solver_runtime_seconds', 'time_limit_seconds'):
        if type(body[key]) not in (int, float) or not math.isfinite(body[key]):
            raise ValueError('finite native numeric field required')
    if body['objective'] != 0. or body['time_limit_seconds'] != 5. or body['solver_runtime_seconds'] < 0.:
        raise ValueError('unexpected fixed synthetic result')
    return body


def main():
    import yaml
    parser = ArgumentParser()
    parser.add_argument('--expected-script-sha256', required=True)
    expected = parser.parse_args().expected_script_sha256
    def check():
        if sha256(Path(__file__).read_bytes()).hexdigest() != expected:
            raise ValueError('external script pin mismatch')
    check()
    declaration = ROOT/'configs/rq2_normal_task_gurobi_direct_h25_development_v1.DRAFT.yaml'
    raw = declaration.read_bytes()
    if sha256(raw).hexdigest() != 'bd48dcdd47ac45ef3c667e1bbeada8626d923215b1f3e77e5e32d48199e37c08':
        raise ValueError('pinned predecessor declaration required')
    environment = yaml.safe_load(raw)['environment']
    license_path = Path(os.environ['GRB_LICENSE_FILE'])
    if not license_path.is_absolute() or not license_path.is_file():
        raise ValueError('existing absolute local license file required')
    environment['GRB_LICENSE_FILE'] = str(license_path)
    target = ROOT/'results/tables/rq2_gurobi_license_environment_probe1_non_authoritative'
    target.mkdir(exist_ok=False)
    environment.update(TEMP=str(target), TMP=str(target))
    budget = process.TaskProcessBudget(30., .1, 768*1024**2, 768*1024**2, 3.)
    host = process.resources.HostResourceBudget(768*1024**2, 64*1024**2,
        (process.resources.DirectoryDemand('scratch', str(target), 16*1024**2, 64*1024**2),))
    argv = [sys.executable, '-I', '-B', '-c', CHILD]
    args = dict(cwd=target, environment=environment, budget=budget, host_budget=host,
        expected_host_identity=process.resources.resource_identity(host))
    pin = process.task_process_identity(argv, **args)
    request = dict(argv=argv, environment=environment, budget=asdict(budget),
        host_budget=asdict(host), process_identity=pin,
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), formal_result=False)
    request_raw = json.dumps(request, sort_keys=True).encode('utf-8')
    with (target/'request.json').open('xb') as f:
        f.write(request_raw)
    check()
    with process.normal_task_child(argv, **args, expected_process_identity=pin) as owner:
        owner.release()
        observation = owner.wait()
    process_raw = json.dumps(asdict(observation), sort_keys=True).encode('utf-8')
    with (target/'process.json').open('xb') as f:
        f.write(process_raw)
    print(json.dumps(asdict(observation), sort_keys=True))
    if observation.exit_code != 0 or not observation.whole_job_quiescent:
        raise RuntimeError('capacity child did not complete cleanly')
    check()
    raw = (target/'capacity.json').read_bytes()
    body = validate_result(raw)
    check()
    with (target/'summary.json').open('x', encoding='utf-8') as f:
        json.dump(dict(formal_result=False, research_model_solved=False,
            capacity_bytes=len(raw), capacity_sha256=sha256(raw).hexdigest(),
            request_sha256=sha256(request_raw).hexdigest(),
            process_sha256=sha256(process_raw).hexdigest(), process_identity=pin,
            script_sha256=expected), f, sort_keys=True)
    print(json.dumps(body, sort_keys=True))


if __name__ == '__main__':
    main()
