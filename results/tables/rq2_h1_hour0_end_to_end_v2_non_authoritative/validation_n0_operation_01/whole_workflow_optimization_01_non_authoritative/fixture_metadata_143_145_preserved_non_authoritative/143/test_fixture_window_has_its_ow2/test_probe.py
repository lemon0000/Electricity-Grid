
import importlib.metadata as metadata
import sys
import pytest
ORIGINAL=metadata.Distribution.from_name.__func__
@pytest.fixture
def setup():
    assert metadata.version('numpy')
    return metadata.Distribution.from_name.__func__
@pytest.fixture
def prepared(tmp_path,request):
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    if 'discovery_drift'=='discovery_drift':sys.path.insert(0,str(tmp_path))
    assert metadata.version('numpy')
    if 'discovery_drift'=='nested':assert request.getfixturevalue('setup') is metadata.Distribution.from_name.__func__
    with pytest.raises(metadata.PackageNotFoundError):metadata.version('electricity_grid_no_such_distribution_139')
    if 'discovery_drift'=='fixture_error':raise RuntimeError('expected fixture setup error')
    return metadata.Distribution.from_name.__func__
def test_flow(prepared):
    assert metadata.Distribution.from_name.__func__ is not ORIGINAL
    assert metadata.Distribution.from_name.__func__ is not prepared
    assert metadata.version('numpy')
