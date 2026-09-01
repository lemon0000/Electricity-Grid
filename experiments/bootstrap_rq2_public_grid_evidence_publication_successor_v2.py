"""Stdlib-first validate-only bootstrap for the closed Vnext-v2 bundle."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v2.json"
INNER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v2.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v2.OUTER.SHA256SUMS.json"


class BootstrapRejected(RuntimeError):
    """The pre-project-import bundle boundary failed closed."""


def _stable(path: Path) -> bytes:
    try:
        before = path.lstat()
        first = path.read_bytes()
        middle = path.lstat()
        second = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise BootstrapRejected(f"bundle member unavailable: {path}") from exc
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if (
        path.is_symlink()
        or not stat.S_ISREG(before.st_mode)
        or getattr(before, "st_file_attributes", 0) & 0x400
        or first != second
        or identity(before) != identity(middle)
        or identity(middle) != identity(after)
    ):
        raise BootstrapRejected(f"unstable/nonordinary bundle member: {path}")
    return first


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verify_bundle() -> None:
    try:
        config = json.loads(_stable(CONFIG))
        inner_raw = _stable(INNER)
        inner = json.loads(inner_raw)
        outer = json.loads(_stable(OUTER))
    except json.JSONDecodeError as exc:
        raise BootstrapRejected("bundle JSON malformed") from exc
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if outer != {
        "schema": "rq2_public_grid_evidence_publication_successor_outer_v2",
        "files": {inner_relative: _sha(inner_raw)},
    }:
        raise BootstrapRejected("outer bundle binding drifted")
    expected = set(config["bundle"]["members"].values())
    files = inner.get("files")
    if (
        inner.get("schema")
        != "rq2_public_grid_evidence_publication_successor_bundle_v2"
        or not isinstance(files, dict)
        or set(files) != expected
        or len(files) != config["bundle"]["exact_member_count"]
    ):
        raise BootstrapRejected("inner bundle inventory drifted")
    for relative, digest in files.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise BootstrapRejected("bundle member binding malformed")
        if _sha(_stable(ROOT / relative)) != digest:
            raise BootstrapRejected(f"bundle member drifted: {relative}")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise BootstrapRejected("bootstrap permits validate-only only")
    if os.getcwd() != str(ROOT):
        raise BootstrapRejected("bootstrap cwd drifted")
    _verify_bundle()
    from experiments import rq2_public_grid_evidence_publication_contract_v2 as contract

    contract.StageAwareClosureVerifier().verify("bootstrap_pre_controller_import")
    from experiments import (
        run_rq2_public_grid_evidence_publication_successor_v2 as controller,
    )

    return controller.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
