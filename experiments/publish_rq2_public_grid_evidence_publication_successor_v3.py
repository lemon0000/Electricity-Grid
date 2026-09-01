"""Secret-free presence, truth-table, and tree primitives for V3 publication."""

from __future__ import annotations

import dataclasses
import os
import stat
from pathlib import Path

from experiments import rq2_public_grid_evidence_publication_contract_v3 as contract


@dataclasses.dataclass(frozen=True, slots=True)
class PublicationPaths:
    result: Path
    success: Path
    terminal: Path


@dataclasses.dataclass(frozen=True, slots=True)
class PresenceSnapshot:
    result_classification: str
    success_classification: str
    terminal_classification: str
    result_clean_absent: bool
    success_clean_absent: bool
    terminal_clean_absent: bool
    result_ordinary_directory: bool
    success_ordinary_directory: bool
    terminal_ordinary_directory: bool


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewOutcome:
    classification: str
    published: bool
    review_fixture: bool
    nonformal: bool
    claim: bool
    mathematical_infeasibility_inferred: bool
    worker_processes_started: int
    worker_pids: tuple[int, ...]
    pipe_authority_digests: tuple[str, ...]
    pipe_authority_verified: bool
    parent_identity_verified: bool
    raw_handle_roles_verified: bool
    scientific_loader_calls: int
    solver_calls: int
    result_path: str
    success_path: str
    terminal_path: str


def publication_paths(base: Path) -> PublicationPaths:
    return PublicationPaths(
        result=base,
        success=base.with_name(base.name + ".PUBLISHED"),
        terminal=base.with_name(base.name + ".TERMINAL"),
    )


def capture_presence(paths: PublicationPaths) -> PresenceSnapshot:
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as prior

    result = prior._probe_one_path(paths.result, label="v3 result")
    success = prior._probe_one_path(paths.success, label="v3 success")
    terminal = prior._probe_one_path(paths.terminal, label="v3 terminal")
    return PresenceSnapshot(
        result_classification=result.classification,
        success_classification=success.classification,
        terminal_classification=terminal.classification,
        result_clean_absent=result.eligible_clean_absent,
        success_clean_absent=success.eligible_clean_absent,
        terminal_clean_absent=terminal.eligible_clean_absent,
        result_ordinary_directory=result.exact_ordinary_directory,
        success_ordinary_directory=success.exact_ordinary_directory,
        terminal_ordinary_directory=terminal.exact_ordinary_directory,
    )


def classify_publication(
    snapshot: PresenceSnapshot, *, result_exact: bool, success_exact: bool
) -> str:
    """Independent implementation of the frozen three-row V3 truth table."""
    contract.load_config()
    if not snapshot.terminal_clean_absent:
        return "commit_indeterminate"
    if (
        snapshot.result_clean_absent
        and snapshot.success_clean_absent
        and not result_exact
        and not success_exact
    ):
        return "honest_incomplete"
    if (
        snapshot.result_ordinary_directory
        and snapshot.success_ordinary_directory
        and result_exact
        and success_exact
    ):
        return "committed_success"
    return "commit_indeterminate"


def atomic_write(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise contract.ContractRejected("publication member already exists")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise contract.ContractRejected("publication parent is not ordinary")
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def typed_tree(root: Path) -> dict[str, object]:
    directories: list[str] = ["."]
    files: dict[str, str] = {}
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as exc:
            raise contract.ContractRejected("publication tree unreadable") from exc
        for entry in entries:
            relative = Path(entry.path).relative_to(root).as_posix()
            try:
                observed = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise contract.ContractRejected("publication member unreadable") from exc
            if entry.is_symlink() or getattr(observed, "st_file_attributes", 0) & 0x400:
                raise contract.ContractRejected("publication alias/reparse rejected")
            if stat.S_ISDIR(observed.st_mode):
                directories.append(relative)
                stack.append(Path(entry.path))
            elif stat.S_ISREG(observed.st_mode):
                if relative == "SHA256SUMS.json":
                    continue
                files[relative] = contract.sha256_bytes(
                    contract.read_stable(Path(entry.path))
                )
            else:
                raise contract.ContractRejected("publication special member rejected")
    return {
        "schema": "rq2_public_grid_evidence_publication_typed_tree_v3",
        "directories": sorted(directories),
        "files": dict(sorted(files.items())),
    }


def materialize_presence_for_test(
    paths: PublicationPaths,
    *,
    result_kind: str,
    success_kind: str,
    terminal_kind: str,
) -> None:
    for path, kind in (
        (paths.result, result_kind),
        (paths.success, success_kind),
        (paths.terminal, terminal_kind),
    ):
        if kind == "absent":
            continue
        if kind == "directory":
            path.mkdir(parents=True)
        elif kind == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("appearance", encoding="ascii")
        elif kind == "alias":
            path.parent.mkdir(parents=True, exist_ok=True)
            target = path.with_name(path.name + ".target")
            target.mkdir()
            path.symlink_to(target, target_is_directory=True)
        else:
            raise ValueError("unregistered test presence kind")
