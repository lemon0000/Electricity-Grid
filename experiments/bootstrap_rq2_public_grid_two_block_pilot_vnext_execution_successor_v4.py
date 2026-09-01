"""Stdlib-first bootstrap for review-closed Vnext execution successor v4."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v4.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v4.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v4.OUTER.SHA256SUMS.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v4.json"


class BootstrapRejected(RuntimeError):
    """The pre-project-import V4 bootstrap failed closed."""


def _stable(path: Path) -> bytes:
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise BootstrapRejected(f"ordinary file required: {path}")
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise BootstrapRejected(f"bundle member unavailable: {path}") from exc
    if first != second:
        raise BootstrapRejected(f"bundle member changed while read: {path}")
    return first


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verify_bundle() -> tuple[dict[str, object], str]:
    try:
        outer = json.loads(_stable(OUTER))
        inner_raw = _stable(INNER)
        inner = json.loads(inner_raw)
        config = json.loads(_stable(CONFIG))
    except json.JSONDecodeError as exc:
        raise BootstrapRejected("V4 bundle JSON malformed") from exc
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if (
        outer.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_outer_v4"
        or outer.get("files") != {inner_relative: _sha(inner_raw)}
        or inner.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_bundle_v4"
        or set(inner.get("files", {})) != set(config["bundle"]["members"])
        or len(inner["files"]) != config["bundle"]["exact_member_count"]
    ):
        raise BootstrapRejected("V4 bundle identity/inventory drifted")
    for relative, expected in inner["files"].items():
        if _sha(_stable(ROOT / relative)) != expected:
            raise BootstrapRejected(f"V4 bundle member hash drifted: {relative}")
    return config, _sha(_stable(OUTER))


def _preimport_review(config: dict[str, object], outer_sha256: str) -> None:
    if not REVIEW.exists() or REVIEW.is_symlink():
        raise BootstrapRejected("fixed V4 execution-review PASS receipt is absent")
    try:
        value = json.loads(_stable(REVIEW))
    except json.JSONDecodeError as exc:
        raise BootstrapRejected("V4 execution-review receipt JSON malformed") from exc
    authority = config["fixed_execution_review"]
    predecessor = config["predecessor_v3"]
    controller_auth = config["controller_authentication"]
    expected_keys = {
        "schema",
        "version",
        "reviewed_on",
        "reviewer_role",
        "verdict",
        "reviewed_outer",
        "bound_v3_outer",
        "bound_v3_escalate",
        "bound_v3_public_key",
        "bound_public_key",
        "findings",
        "effect",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != authority["schema"]
        or value.get("version") != 4
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("verdict") != "PASS"
        or value.get("findings") != []
        or value.get("reviewed_outer")
        != {"path": config["bundle"]["outer_path"], "sha256": outer_sha256}
        or value.get("bound_v3_outer")
        != {"path": predecessor["outer_path"], "sha256": predecessor["outer_sha256"]}
        or value.get("bound_v3_escalate")
        != {
            "path": predecessor["review_escalate_path"],
            "sha256": predecessor["review_escalate_sha256"],
        }
        or value.get("bound_v3_public_key")
        != {
            "path": predecessor["public_anchor_path"],
            "sha256": predecessor["public_anchor_sha256"],
            "key_id": predecessor["key_id"],
        }
        or value.get("bound_public_key")
        != {
            "path": controller_auth["public_key_path"],
            "sha256": controller_auth["public_key_file_sha256"],
            "key_id": controller_auth["key_id"],
        }
        or value.get("effect") != authority["effect"]
    ):
        raise BootstrapRejected("V4 execution-review receipt binding/effect drifted")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    config, outer_sha256 = _verify_bundle()
    if arguments == ["--execute"]:
        _preimport_review(config, outer_sha256)
    elif arguments != ["--validate-only"]:
        raise BootstrapRejected("only --validate-only or gated --execute is registered")
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from experiments import (
        run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v4 as controller,
    )

    return controller.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
