"""Stdlib-first validate-only bootstrap for the closed Vnext bundle."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.json"
INNER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.OUTER.SHA256SUMS.json"


class BootstrapRejected(RuntimeError):
    """The pre-project-import bundle boundary failed."""


def _stable(path: Path) -> bytes:
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second or not path.is_file() or path.is_symlink():
        raise BootstrapRejected(f"unstable/nonordinary bundle member: {path}")
    return first


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verify_bundle() -> None:
    config = json.loads(_stable(CONFIG))
    inner_raw = _stable(INNER)
    inner = json.loads(inner_raw)
    outer = json.loads(_stable(OUTER))
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if outer != {
        "schema": "rq2_public_grid_evidence_publication_successor_outer_v1",
        "files": {inner_relative: _sha(inner_raw)},
    }:
        raise BootstrapRejected("outer bundle binding drifted")
    expected = set(config["bundle"]["members"].values())
    files = inner.get("files")
    if not isinstance(files, dict) or set(files) != expected:
        raise BootstrapRejected("inner bundle inventory drifted")
    for relative, digest in files.items():
        if _sha(_stable(ROOT / relative)) != digest:
            raise BootstrapRejected(f"bundle member drifted: {relative}")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise BootstrapRejected("bootstrap permits validate-only only")
    _verify_bundle()
    from experiments import rq2_public_grid_evidence_publication_contract_v1 as contract

    contract.StageAwareClosureVerifier().verify("bootstrap_pre_controller_import")
    from experiments import (
        run_rq2_public_grid_evidence_publication_successor_v1 as controller,
    )

    return controller.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
