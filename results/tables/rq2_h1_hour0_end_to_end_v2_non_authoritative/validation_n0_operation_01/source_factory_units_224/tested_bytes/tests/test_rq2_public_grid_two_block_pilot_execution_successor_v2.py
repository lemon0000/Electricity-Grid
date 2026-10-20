"""Focused tests for execution-successor v2 fail-closed OS boundaries."""

from __future__ import annotations

import ast
import errno
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v2 as bootstrap,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / bootstrap.CONFIG_REL).read_text(encoding="utf-8"))


def _runtime() -> dict[str, object]:
    contract = CONFIG["bootstrap_contract"]
    return {
        "executable": contract["locked_python_executable"],
        "executable_sha256": contract["locked_python_sha256"],
        "version": contract["locked_python_version"],
        "orig_argv": [
            contract["locked_python_executable"],
            *contract["exact_argv_suffix"],
        ],
        "cwd": contract["exact_cwd"],
        "hostname": contract["host"]["hostname"],
        "system": contract["host"]["system"],
        "release": contract["host"]["release"],
        "machine": contract["host"]["machine"],
        "environment": contract["exact_environment"],
        "process_age_seconds": 1.0,
        "processes": [(os.getpid(), "python.exe")],
        "available_virtual_bytes": 10 * 1024**3,
    }


def _root_map() -> dict[str, bool]:
    paths = [
        *CONFIG["fresh_roots"],
        *CONFIG["formal_invariants"]["protected_roots_clean_absent"],
    ]
    return dict.fromkeys(paths, False)


class _FakeToolhelp:
    def __init__(
        self,
        rows: list[tuple[int, str]],
        *,
        first_fails: bool = False,
        mid_failure_index: int | None = None,
    ) -> None:
        self.rows = rows
        self.first_fails = first_fails
        self.mid_failure_index = mid_failure_index
        self.index = 0
        self.error = 0
        self.closed = False

    @staticmethod
    def _assign(entry: Any, row: tuple[int, str]) -> None:
        entry.th32ProcessID = row[0]
        entry.szExeFile = row[1]

    def create_snapshot(self) -> object:
        return object()

    def first(self, _snapshot: object, entry: Any) -> bool:
        if self.first_fails or not self.rows:
            self.error = 5
            return False
        self._assign(entry, self.rows[0])
        self.index = 1
        return True

    def next(self, _snapshot: object, entry: Any) -> bool:
        if self.mid_failure_index == self.index:
            self.error = 5
            return False
        if self.index >= len(self.rows):
            self.error = 18
            return False
        self._assign(entry, self.rows[self.index])
        self.index += 1
        return True

    def last_error(self) -> int:
        return self.error

    def close(self, _snapshot: object) -> None:
        self.closed = True


class _FakeScandir:
    def __init__(self, entries: list[Any], *, mid_error: bool = False) -> None:
        self.entries = entries
        self.index = 0
        self.mid_error = mid_error

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self) -> _FakeScandir:
        return self

    def __next__(self) -> Any:
        if self.mid_error and self.index == 1:
            raise PermissionError("mid-enumeration failure")
        if self.index >= len(self.entries):
            raise StopIteration
        entry = self.entries[self.index]
        self.index += 1
        return entry


class _FakeEntry:
    def __init__(
        self,
        name: str,
        path: Path,
        info: Any | None = None,
        error: OSError | None = None,
    ) -> None:
        self.name = name
        self.path = str(path)
        self.info = info
        self.error = error

    def stat(self, *, follow_symlinks: bool) -> Any:
        assert follow_symlinks is False
        if self.error is not None:
            raise self.error
        return self.info


def _checkpoint_fixture(tmp_path: Path) -> tuple[dict[str, str], list[Path]]:
    paths: list[Path] = []
    expected: dict[str, str] = {}
    for index in range(9):
        path = tmp_path / f"holdout_{index:04d}.json"
        path.write_bytes(f"checkpoint-{index}".encode())
        paths.append(path)
        expected[path.name] = bootstrap._sha256(path)
    return expected, paths


def test_v2_is_standard_library_only_and_closed() -> None:
    assert bootstrap.PROJECT_IMPORTS_PERMITTED is False
    tree = ast.parse((ROOT / bootstrap.SELF_REL).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported.intersection({"src", "experiments", "pyomo", "pandas"})
    assert CONFIG["gates"]["successor_execution_ready"] is False
    assert CONFIG["gates"]["formal_execution_ready"] is False


def test_sealed_v2_static_authority_and_checkpoint_tree_are_live() -> None:
    config = bootstrap._verify_static_authority()
    assert config["status"] == "execution_successor_v2_candidate_closed"
    assert config["gates"]["successor_independent_review_passed"] is False
    assert config["gates"]["successor_execution_ready"] is False
    assert config["gates"]["formal_execution_ready"] is False


def test_project_preimport_fails_before_static_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def forbidden() -> dict[str, Any]:
        nonlocal called
        called = True
        return CONFIG

    monkeypatch.setattr(bootstrap, "_verify_static_authority", forbidden)
    with pytest.raises(bootstrap.BootstrapRejected, match="preimport"):
        bootstrap.validate(preimport_modules=["src.attack"])
    assert called is False


def test_toolhelp_initial_failure_rejected_and_closed() -> None:
    fake = _FakeToolhelp([], first_fails=True)
    with pytest.raises(bootstrap.BootstrapRejected, match="Process32FirstW"):
        bootstrap._windows_processes(fake)
    assert fake.closed is True


def test_toolhelp_mid_enumeration_failure_rejected_and_closed() -> None:
    fake = _FakeToolhelp(
        [(os.getpid(), "python.exe"), (12345, "other.exe")],
        mid_failure_index=1,
    )
    with pytest.raises(bootstrap.BootstrapRejected, match="error 5"):
        bootstrap._windows_processes(fake)
    assert fake.closed is True


def test_toolhelp_error_18_is_only_normal_eof() -> None:
    fake = _FakeToolhelp([(os.getpid(), "python.exe"), (12345, "other.exe")])
    assert bootstrap._windows_processes(fake) == [
        (os.getpid(), "python.exe"),
        (12345, "other.exe"),
    ]
    assert fake.closed is True


def test_toolhelp_inventory_must_contain_current_pid() -> None:
    fake = _FakeToolhelp([(os.getpid() + 10, "python.exe")])
    with pytest.raises(bootstrap.BootstrapRejected, match="current PID"):
        bootstrap._windows_processes(fake)


def test_checkpoint_exact_nine_ordinary_files_pass(tmp_path: Path) -> None:
    expected, _paths = _checkpoint_fixture(tmp_path)
    bootstrap._audit_checkpoint_inventory(tmp_path, expected)


def test_checkpoint_extra_directory_and_type_swap_rejected(tmp_path: Path) -> None:
    expected, paths = _checkpoint_fixture(tmp_path)
    (tmp_path / "extra").mkdir()
    with pytest.raises(bootstrap.BootstrapRejected, match="ordinary file"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)
    (tmp_path / "extra").rmdir()
    paths[0].unlink()
    paths[0].mkdir()
    with pytest.raises(bootstrap.BootstrapRejected, match="ordinary file"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)


@pytest.mark.parametrize(
    "info",
    [
        SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0),
        SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0x400),
        SimpleNamespace(st_mode=stat.S_IFIFO, st_file_attributes=0),
    ],
    ids=["broken-alias", "junction-reparse", "special"],
)
def test_checkpoint_alias_reparse_or_special_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, info: Any
) -> None:
    expected, paths = _checkpoint_fixture(tmp_path)
    fake = _FakeEntry(paths[0].name, paths[0], info=info)
    monkeypatch.setattr(os, "scandir", lambda _path: _FakeScandir([fake]))
    with pytest.raises(bootstrap.BootstrapRejected, match="ordinary file"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)


def test_checkpoint_unreadable_entry_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected, paths = _checkpoint_fixture(tmp_path)
    fake = _FakeEntry(
        paths[0].name, paths[0], error=PermissionError("entry unreadable")
    )
    monkeypatch.setattr(os, "scandir", lambda _path: _FakeScandir([fake]))
    with pytest.raises(bootstrap.BootstrapRejected, match="inaccessible"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)


def test_checkpoint_unreadable_file_bytes_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected, paths = _checkpoint_fixture(tmp_path)
    unreadable = paths[0]
    real_open = Path.open

    def open_path(path: Path, *args: object, **kwargs: object) -> Any:
        if path == unreadable:
            raise PermissionError("checkpoint bytes unreadable")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_path)
    with pytest.raises(bootstrap.BootstrapRejected, match="unreadable"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)


@pytest.mark.parametrize("mid_error", [False, True], ids=["open", "mid-iteration"])
def test_checkpoint_enumeration_errors_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mid_error: bool
) -> None:
    expected, paths = _checkpoint_fixture(tmp_path)
    if not mid_error:
        monkeypatch.setattr(
            os, "scandir", lambda _path: (_ for _ in ()).throw(PermissionError("open"))
        )
    else:
        real_info = os.lstat(paths[0])
        first = _FakeEntry(paths[0].name, paths[0], info=real_info)
        monkeypatch.setattr(
            os, "scandir", lambda _path: _FakeScandir([first], mid_error=True)
        )
    with pytest.raises(bootstrap.BootstrapRejected, match="enumeration"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)


ROOT_RELATIVES = [
    *CONFIG["fresh_roots"],
    *CONFIG["formal_invariants"]["protected_roots_clean_absent"],
]


@pytest.mark.parametrize("relative", ROOT_RELATIVES)
@pytest.mark.parametrize(
    "hazard", ["inaccessible", "broken-alias", "reparse", "mount"]
)
def test_each_absent_root_hazard_is_indeterminate(
    relative: str, hazard: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = ROOT / relative
    real_lstat = os.lstat
    real_mount = bootstrap._path_is_mount
    drive, tail = os.path.splitdrive(str(root))
    target = Path(drive + os.sep)
    for segment in [part for part in tail.split(os.sep) if part]:
        target /= segment
        try:
            real_lstat(target)
        except FileNotFoundError:
            break

    def lstat(path: os.PathLike[str] | str) -> Any:
        current = Path(path)
        if current != target:
            return real_lstat(path)
        if hazard == "inaccessible":
            raise PermissionError("denied")
        if hazard == "broken-alias":
            return SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        if hazard == "reparse":
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0)

    monkeypatch.setattr(os, "lstat", lstat)
    monkeypatch.setattr(
        bootstrap,
        "_path_is_mount",
        lambda path: Path(path) == target if hazard == "mount" else real_mount(path),
    )
    with pytest.raises(bootstrap.BootstrapRejected):
        bootstrap._strict_absent(root)


def test_only_file_or_path_not_found_is_clean_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = ROOT / "results" / "never-created"
    missing = FileNotFoundError(errno.ENOENT, "missing")
    monkeypatch.setattr(os, "lstat", lambda _path: (_ for _ in ()).throw(missing))
    assert bootstrap._lstat_or_absent(target) is None

    path_missing = FileNotFoundError(errno.EACCES, "path missing")
    path_missing.winerror = 3
    monkeypatch.setattr(
        os, "lstat", lambda _path: (_ for _ in ()).throw(path_missing)
    )
    assert bootstrap._lstat_or_absent(target) is None

    monkeypatch.setattr(
        os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(OSError(errno.EIO, "device error")),
    )
    with pytest.raises(bootstrap.BootstrapRejected, match="indeterminate"):
        bootstrap._lstat_or_absent(target)


@pytest.mark.parametrize(
    ("location", "hazard"),
    [
        ("ancestor", "junction"),
        ("ancestor", "reparse"),
        ("ancestor", "mount"),
        ("ancestor", "unreadable"),
        ("leaf", "directory"),
        ("leaf", "alias"),
    ],
)
def test_locked_python_path_hazards_rejected_before_hash(
    location: str,
    hazard: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = CONFIG["bootstrap_contract"]
    leaf = Path(contract["locked_python_executable"])
    target = leaf.parent if location == "ancestor" else leaf
    real_lstat = os.lstat
    real_mount = bootstrap._path_is_mount
    hash_called = False

    def lstat(path: os.PathLike[str] | str) -> Any:
        current = Path(path)
        if current != target:
            return real_lstat(path)
        if hazard == "unreadable":
            raise PermissionError("denied")
        if hazard in {"junction", "reparse"}:
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        if hazard == "alias":
            return SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0)

    def sha256(_path: Path) -> str:
        nonlocal hash_called
        hash_called = True
        return contract["locked_python_sha256"]

    monkeypatch.setattr(os, "lstat", lstat)
    monkeypatch.setattr(bootstrap, "_sha256", sha256)
    monkeypatch.setattr(
        bootstrap,
        "_path_is_mount",
        lambda path: Path(path) == target if hazard == "mount" else real_mount(path),
    )
    with pytest.raises(bootstrap.BootstrapRejected):
        bootstrap._verify_locked_python(contract)
    assert hash_called is False


def test_locked_python_valid_path_and_hash_pass() -> None:
    bootstrap._verify_locked_python(CONFIG["bootstrap_contract"])


def test_validate_report_is_closed_and_zero_write(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: CONFIG)
    monkeypatch.setattr(bootstrap, "_verify_locked_python", lambda _contract: None)
    report = bootstrap.validate(
        preimport_modules=[], runtime=_runtime(), root_appearances=_root_map()
    )
    assert report["validation_passed"] is True
    assert report["status"] == "READY_FOR_INDEPENDENT_REVIEW"
    assert report["execution_ready"] is False
    assert report["project_modules_imported"] == 0
    assert report["worker_processes_started"] == 0
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0


def test_non_validate_cli_remains_permanently_closed() -> None:
    with pytest.raises(bootstrap.BootstrapRejected, match="validate-only"):
        bootstrap.main([])
