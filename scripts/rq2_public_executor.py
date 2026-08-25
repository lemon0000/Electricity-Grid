"""Single entry point for the RQ2 execution-machine workflow."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from experiments.activate_rq2_public_successor_v1 import activate
from experiments.preflight_rq2_public_executor_v1 import (
    run as run_preflight,
)
from experiments.run_rq2_public_identification_grid_v4 import (
    run as run_identification,
)
from experiments.run_rq2_public_pairwise_replay_v4 import (
    run as run_pairwise,
)
from experiments.run_rq2_public_solver_pilot_v1 import (
    run as run_pilot,
)
from experiments.run_rts_gmlc_public_grid_need_dispatch_v4 import (
    run as run_grid,
)
from src.evaluation.rq2_provenance_v3 import load_json_strict, sha256_file

_HANDOFF = _ROOT / "configs/rq2_public_executor_handoff_v1.yaml"
_ACTIVATION = _ROOT / "configs/rq2_public_successor_activation_v1.yaml"
_PILOT = _ROOT / "configs/rq2_public_solver_pilot_v1.yaml"
_ACTIVATED = _ROOT / "results/execution_configs/rq2_public_successor_v1"


def _verify_result_package(root: Path) -> list[Path]:
    manifest_path = root / "SHA256SUMS.json"
    manifest = load_json_strict(manifest_path)
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"invalid result manifest: {root}")
    files = [manifest_path]
    for name, expected in manifest.items():
        path = root / name
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256_file(path) != expected
        ):
            raise ValueError(f"result package member drifted: {path}")
        files.append(path)
    return files


def _package(complete: bool) -> dict[str, object]:
    roots = [
        _ROOT / "results/tables/rq2_public_executor_preflight_v1",
        _ROOT / "results/tables/rq2_public_solver_pilot_v1",
    ]
    label = "pilot"
    if complete:
        roots.extend(
            (
                _ROOT
                / "data/processed/model_inputs/"
                "rts_gmlc_public_grid_need_dispatch_v4_gurobi",
                _ROOT
                / "data/processed/model_inputs/"
                "rq2_public_pairwise_replay_v4_gurobi",
                _ROOT / "results/tables/rq2_public_identification_grid_v4_gurobi",
            )
        )
        label = "formal_results"
    files = []
    for root in roots:
        files.extend(_verify_result_package(root))
    if complete:
        for path in sorted(_ACTIVATED.glob("*")):
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"invalid activated config artifact: {path}")
            files.append(path)
    transfer_root = _ROOT / "results/transfer"
    transfer_root.mkdir(parents=True, exist_ok=True)
    archive = transfer_root / f"rq2_public_successor_v1_{label}.tar.gz"
    manifest_path = transfer_root / f"rq2_public_successor_v1_{label}.json"
    if archive.exists() or manifest_path.exists():
        raise FileExistsError(f"refusing to overwrite transfer package: {archive}")
    file_hashes = {
        path.relative_to(_ROOT).as_posix(): sha256_file(path)
        for path in sorted(set(files))
    }
    manifest = {
        "schema": "rq2_public_executor_return_package_v1",
        "scope": label,
        "files": file_hashes,
        "formal_result_claimed": complete,
        "security_certified": False,
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=transfer_root,
        prefix=f".{label}.",
        suffix=".json",
        delete=False,
    ) as temporary:
        json.dump(manifest, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_manifest = Path(temporary.name)
    with tempfile.NamedTemporaryFile(
        "wb",
        dir=transfer_root,
        prefix=f".{label}.",
        suffix=".tar.gz",
        delete=False,
    ) as temporary:
        temporary_archive = Path(temporary.name)
    try:
        with tarfile.open(temporary_archive, "w:gz") as bundle:
            for path in sorted(set(files)):
                bundle.add(path, arcname=path.relative_to(_ROOT).as_posix())
            bundle.add(
                temporary_manifest,
                arcname=manifest_path.relative_to(_ROOT).as_posix(),
            )
        temporary_manifest.replace(manifest_path)
        temporary_archive.replace(archive)
    except Exception:
        temporary_manifest.unlink(missing_ok=True)
        temporary_archive.unlink(missing_ok=True)
        raise
    return {
        **manifest,
        "archive": str(archive.relative_to(_ROOT)),
        "archive_sha256": sha256_file(archive),
        "manifest": str(manifest_path.relative_to(_ROOT)),
        "manifest_sha256": sha256_file(manifest_path),
    }


def _dispatch(args: argparse.Namespace) -> dict[str, object]:
    command = args.command
    if command == "verify":
        return run_preflight(_HANDOFF, verify_only=True)
    if command == "preflight":
        return run_preflight(_HANDOFF)
    if command == "pilot":
        return run_pilot(_PILOT)
    if command.startswith("activate-"):
        return activate(
            command.removeprefix("activate-"),
            handoff_path=_HANDOFF,
            activation_path=_ACTIVATION,
        )
    if command in {"grid", "resume-grid"}:
        return run_grid(
            _ACTIVATED / "grid.yaml",
            maximum_blocks=args.maximum_blocks,
        )
    if command in {"pairwise", "resume-pairwise"}:
        return run_pairwise(
            _ACTIVATED / "pairwise.yaml",
            maximum_pairs=args.maximum_pairs,
        )
    if command == "identification":
        return run_identification(_ACTIVATED / "identification.yaml")
    if command == "package-pilot":
        return _package(False)
    if command == "package-results":
        return _package(True)
    raise ValueError(f"unsupported command: {command}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "verify",
            "preflight",
            "pilot",
            "activate-grid",
            "grid",
            "resume-grid",
            "activate-pairwise",
            "pairwise",
            "resume-pairwise",
            "activate-identification",
            "identification",
            "package-pilot",
            "package-results",
        ),
    )
    parser.add_argument("--maximum-blocks", type=int)
    parser.add_argument("--maximum-pairs", type=int)
    args = parser.parse_args()
    os.chdir(_ROOT)
    print(json.dumps(_dispatch(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
