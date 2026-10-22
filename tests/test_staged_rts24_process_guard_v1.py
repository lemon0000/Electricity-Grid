"""New monitor tests use tiny owned Python children, with no numeric backend."""
import json
import os
from pathlib import Path
import sys

import pytest

from src import staged_rts24_process_guard_v1 as guard


LIMITS = dict(wall_seconds=5, no_progress_seconds=5, rss_bytes=256*1024**2, output_bytes=1024**2, files=20)


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
def test_real_child_rss_and_normal_exit_are_observed(tmp_path):
    result = guard.supervise([sys.executable, "-B", "-c", "import time; time.sleep(.25)"], cwd=tmp_path,
        output=tmp_path, progress=tmp_path/"events", limits=LIMITS)
    assert result["exit_code"] == 0 and result["stop_reason"] is None and result["job_quiet_confirmed"]
    assert result["sampled_tree_peak_rss_bytes"] > 0 and result["peak_job_commit_bytes"] > 0


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
@pytest.mark.parametrize("kind", ["wall", "progress"])
def test_real_timeout_quiesces_whole_job(tmp_path, kind):
    limits = {**LIMITS, "wall_seconds" if kind == "wall" else "no_progress_seconds": .15}
    result = guard.supervise([sys.executable, "-B", "-c", "import time; time.sleep(20)"], cwd=tmp_path,
        output=tmp_path, progress=tmp_path/"events", limits=limits)
    assert result["job_quiet_confirmed"] and result["exit_code"] != 0
    assert result["stop_reason"] in ("wall_limit", "no_progress")


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
def test_worker_exits_with_live_grandchild_whole_job_is_quiesced(tmp_path):
    code = ("import subprocess,sys,json,time; from pathlib import Path; "
            "p=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(20)']); "
            "Path('grand.json').write_text(json.dumps(p.pid)); time.sleep(.5)")
    retained = []
    class ObservedOwner(guard.OwnedChild):
        def sample(self):
            sample = super().sample()
            if not retained and (tmp_path/"grand.json").exists():
                pid = json.loads((tmp_path/"grand.json").read_text())
                handle = self._k.OpenProcess(0x100000 | 0x1000, False, pid)
                assert handle
                retained.append((self._k, handle))
            return sample
    try:
        result = guard.supervise([sys.executable, "-B", "-c", code], cwd=tmp_path,
            output=tmp_path, progress=tmp_path/"events", limits=LIMITS, owner_factory=ObservedOwner)
        assert retained and result["job_quiet_confirmed"]
        assert retained[0][0].WaitForSingleObject(retained[0][1], 0) == 0
        assert result["stop_reason"] == "root_exited_with_descendants"
    finally:
        for kernel, handle in retained: assert kernel.CloseHandle(handle)


class FakeOwner:
    pid, creation_filetime = 123, 456
    def __init__(self, *a, **k): self.released = self.closed = False; self.polls = 0
    def release(self): self.released = True
    def poll(self): self.polls += 1; return None if self.polls == 1 else 0
    def sample(self): return dict(rss_bytes=2, peak_job_commit_bytes=2, processes=0, pids=[])
    def quiesce(self, **kw): pass
    def close(self): self.closed = True


@pytest.mark.parametrize("failure", ["rss", "storage", "sample", "cleanup", "close", "terminal"])
def test_faults_are_recorded_and_cleanup_is_not_assumed(tmp_path, monkeypatch, failure):
    owner = FakeOwner()
    if failure == "sample": monkeypatch.setattr(owner, "sample", lambda: (_ for _ in ()).throw(OSError("sample")))
    if failure == "cleanup": monkeypatch.setattr(owner, "quiesce", lambda **kw: (_ for _ in ()).throw(OSError("cleanup")))
    if failure == "close": monkeypatch.setattr(owner, "close", lambda: (_ for _ in ()).throw(OSError("close")))
    limits = {**LIMITS, "rss_bytes": 1} if failure == "rss" else LIMITS
    if failure in ("storage", "terminal"):
        if failure == "terminal": monkeypatch.setattr(owner, "poll", lambda: 0)
        (tmp_path/"huge").write_bytes(b"x"*LIMITS["output_bytes"])
    result = guard.supervise([sys.executable], cwd=tmp_path, output=tmp_path, progress=tmp_path/"events",
        limits=limits, owner_factory=lambda *a, **k: owner)
    assert result["stop_reason"]
    assert result["job_quiet_confirmed"] is (failure not in ("cleanup", "close"))


def test_fast_exit_preserves_commit_peak_without_inventing_rss_sample(tmp_path, monkeypatch):
    owner = FakeOwner()
    monkeypatch.setattr(owner, "poll", lambda: 0)
    result = guard.supervise([sys.executable], cwd=tmp_path, output=tmp_path, progress=tmp_path/"events",
        limits=LIMITS, owner_factory=lambda *a, **k: owner)
    assert result["peak_job_commit_bytes"] == 2 and result["samples"] == 0
    assert result["sampled_tree_peak_rss_bytes"] is None and result["rss_observation_available"] is False
    assert result["job_quiet_confirmed"] and result["stop_reason"] is None


@pytest.mark.parametrize("name,value", [("wall_seconds", 301), ("no_progress_seconds", float("inf")),
    ("rss_bytes", True), ("output_bytes", 1.5), ("files", 0)])
def test_invalid_limits_never_construct_owner(tmp_path, name, value):
    def forbidden(*a, **kw): pytest.fail("owner constructed for invalid limits")
    with pytest.raises(ValueError):
        guard.supervise([], cwd=tmp_path, output=tmp_path, progress=tmp_path/"events",
            limits={**LIMITS, name: value}, owner_factory=forbidden)


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
def test_real_nonzero_exit_retains_code_and_quiet_job(tmp_path):
    result = guard.supervise([sys.executable, "-B", "-c", "import time; time.sleep(.3); raise SystemExit(7)"], cwd=tmp_path,
        output=tmp_path, progress=tmp_path/"events", limits=LIMITS)
    assert result["exit_code"] == 7 and result["stop_reason"] == "child_exit_nonzero" and result["job_quiet_confirmed"], result


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
def test_unobserved_short_lived_descendant_forces_unknown(tmp_path):
    code = "import subprocess,sys; subprocess.run([sys.executable,'-B','-c','pass'],check=True)"
    owner = guard.OwnedChild([sys.executable, "-B", "-c", code], cwd=tmp_path,
        max_process_commit_bytes=256*1024**2, max_job_commit_bytes=512*1024**2,
        environment=guard.controlled_environment())
    try:
        owner.release()
        assert owner._k.WaitForSingleObject(owner._process, 5000) == 0
        with pytest.raises(OSError, match="inventory unresolved"): owner.quiesce(max_seconds=2)
        witness = owner.quiescence_witness
        assert witness["all_handles_signaled"] and witness["total_processes"] > witness["observed_unique_member_handles"]
        assert not witness["complete_inventory"]
    finally: owner.close()


@pytest.mark.skipif(os.name != "nt", reason="atomic Windows process ownership")
def test_nested_jobs_both_close_complete_handle_inventories(tmp_path):
    inner = tmp_path/"inner.json"
    code = ("import json,sys; from pathlib import Path; from src.staged_rts24_process_guard_v1 import supervise; "
        f"p=Path({str(tmp_path)!r}); "
        "r=supervise([sys.executable,'-B','-c','import time; time.sleep(.5)'],cwd=p,output=p,progress=p/'events',"
        f"limits={LIMITS!r}); Path({str(inner)!r}).write_text(json.dumps(r))")
    result = guard.supervise([sys.executable, "-B", "-c", code], cwd=Path(guard.__file__).resolve().parents[1],
        output=tmp_path, progress=tmp_path/"events", limits=LIMITS)
    child = json.loads(inner.read_text())
    assert result["job_quiet_confirmed"] and result["stop_reason"] is None, result
    assert child["job_quiet_confirmed"] and child["stop_reason"] is None, child
    for record in (result, child):
        witness = record["quiescence_witness"]
        assert witness["complete_inventory"] and witness["all_handles_signaled"]
        assert witness["total_processes"] == witness["observed_unique_member_handles"]
