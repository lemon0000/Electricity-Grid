"""Fetch and verify version 2 of the NLR GenAI power-profile archive."""

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


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


def _verified(path: Path, *, size: int, sha256: str) -> bool:
    return path.is_file() and path.stat().st_size == size and _sha256(path) == sha256


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    archive = _path(source["archive_path"], "source.archive_path")
    size = int(source["archive_size_bytes"])
    sha256 = str(source["archive_sha256"])
    archive.parent.mkdir(parents=True, exist_ok=True)

    if not _verified(archive, size=size, sha256=sha256):
        partial = archive.with_suffix(archive.suffix + ".partial")
        partial.unlink(missing_ok=True)
        request = urllib.request.Request(
            str(source["download_url"]),
            headers={"User-Agent": "Electricity-Grid/1"},
        )
        with (
            urllib.request.urlopen(request, timeout=120) as response,
            partial.open("wb") as target,
        ):
            shutil.copyfileobj(response, target, length=_CHUNK_SIZE)
        if not _verified(partial, size=size, sha256=sha256):
            partial.unlink(missing_ok=True)
            raise RuntimeError("Downloaded NLR archive failed size or SHA-256 check")
        partial.replace(archive)

    source_record = {
        "dataset": source["dataset"],
        "catalog_version": int(source["catalog_version"]),
        "catalog_last_updated": str(source["catalog_last_updated"]),
        "doi": str(source["doi"]),
        "landing_page": str(source["landing_page"]),
        "download_url": str(source["download_url"]),
        "license": str(source["license"]),
        "archive": {
            "name": archive.name,
            "size_bytes": size,
            "sha256": sha256,
        },
    }
    (archive.parent / "SOURCE_OBJECTS.json").write_text(
        json.dumps(source_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive.parent / "SHA256SUMS").write_text(
        f"{sha256}  {archive.name}\n",
        encoding="ascii",
    )
    return {
        "archive": str(archive),
        "size_bytes": size,
        "sha256": sha256,
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/nlr_genai_power_profiles_v2.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
