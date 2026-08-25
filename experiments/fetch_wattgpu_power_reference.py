"""Fetch and verify the pinned WattGPU data subset and methodology files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CHUNK_SIZE = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified(path: Path, *, size: int, sha256: str) -> bool:
    return path.is_file() and path.stat().st_size == size and _sha256(path) == sha256


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    commit = str(source["commit"])
    target = _path(source["path"], "source.path")
    target.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for relative, identity in config["objects"].items():
        destination = target / relative
        size = int(identity["size"])
        sha256 = str(identity["sha256"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not _verified(destination, size=size, sha256=sha256):
            partial = destination.with_suffix(destination.suffix + ".partial")
            partial.unlink(missing_ok=True)
            url = (
                "https://raw.githubusercontent.com/maufadel/wattgpu/"
                f"{commit}/{relative}"
            )
            request = urllib.request.Request(
                url, headers={"User-Agent": "Electricity-Grid/1"}
            )
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                partial.open("wb") as output,
            ):
                shutil.copyfileobj(response, output, length=_CHUNK_SIZE)
            if not _verified(partial, size=size, sha256=sha256):
                partial.unlink(missing_ok=True)
                raise RuntimeError(f"Downloaded WattGPU object failed: {relative}")
            partial.replace(destination)
        records.append(
            {
                "path": relative,
                "size_bytes": size,
                "sha256": sha256,
                "commit": commit,
            }
        )

    source_record = {
        "repository": source["repository"],
        "commit": commit,
        "release_version": str(source["release_version"]),
        "release_date": str(source["release_date"]),
        "license": str(source["license"]),
        "paper": source["paper"],
        "paper_url": source["paper_url"],
        "objects": records,
    }
    (target / "SOURCE_OBJECTS.json").write_text(
        json.dumps(source_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "SHA256SUMS").write_text(
        "".join(f"{row['sha256']}  {row['path']}\n" for row in records),
        encoding="ascii",
    )
    return {
        "directory": str(target),
        "commit": commit,
        "objects": len(records),
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/wattgpu_power_reference_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
