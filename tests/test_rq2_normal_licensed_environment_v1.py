from pathlib import Path

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_licensed_environment as api


def environment(tmp_path):
    path = tmp_path/'synthetic.lic'
    path.write_text('synthetic path fixture; not a license', encoding='ascii')
    return dict(api.legacy.development_environment(), GRB_LICENSE_FILE=str(path))


def test_explicit_path_does_not_read_or_copy_license(tmp_path, monkeypatch):
    env = environment(tmp_path)
    monkeypatch.setattr(Path, 'read_bytes', lambda *_: pytest.fail('license content must not be read'))
    monkeypatch.setattr(Path, 'read_text', lambda *_a, **_k: pytest.fail('license content must not be read'))
    api._environment(env)


@pytest.mark.parametrize('mode', ['missing', 'relative', 'nonexistent', 'directory', 'extra', 'alias'])
def test_invalid_environment(tmp_path, mode):
    env = environment(tmp_path)
    if mode == 'missing': env.pop('GRB_LICENSE_FILE')
    elif mode == 'relative': env['GRB_LICENSE_FILE'] = 'synthetic.lic'
    elif mode == 'nonexistent': env['GRB_LICENSE_FILE'] = str(tmp_path/'absent.lic')
    elif mode == 'directory': env['GRB_LICENSE_FILE'] = str(tmp_path)
    elif mode == 'extra': env['GUROBI_HOME'] = str(tmp_path)
    elif mode == 'alias': env['grb_license_file'] = env['GRB_LICENSE_FILE']
    with pytest.raises(ValueError): api._environment(env)


def test_legacy_environment_rejects_licensed_mapping(tmp_path):
    with pytest.raises(ValueError): api.legacy._environment(environment(tmp_path))
