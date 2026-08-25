"""Fetch and verify the Alibaba PAI v2020 instance sensor table."""

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


def _download(url: str, destination: Path, *, size: int, sha256: str) -> None:
    if (
        destination.is_file()
        and destination.stat().st_size == size
        and _sha256(destination) == sha256
    ):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Electricity-Grid/1"})
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        partial.open("wb") as output,
    ):
        shutil.copyfileobj(response, output, length=_CHUNK_SIZE)
    if partial.stat().st_size != size or _sha256(partial) != sha256:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded object failed verification: {destination.name}")
    partial.replace(destination)


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    archive = config["archive"]
    target = _path(source["path"], "source.path")
    target.mkdir(parents=True, exist_ok=True)

    archive_name = str(archive["name"])
    archive_url = f"{str(source['data_base_url']).rstrip('/')}/{archive_name}"
    _download(
        archive_url,
        target / archive_name,
        size=int(archive["size"]),
        sha256=str(archive["sha256"]),
    )
    header_name = str(archive["header"])
    documentation_root = (
        "https://raw.githubusercontent.com/alibaba/clusterdata/"
        f"{source['documentation_commit']}/cluster-trace-gpu-v2020"
    )
    _download(
        f"{documentation_root}/data/{header_name}",
        target / header_name,
        size=len(
            ",".join(str(value) for value in archive["columns"]).encode("utf-8")
        )
        + 1,
        sha256=str(archive["header_sha256"]),
    )
    objects = [
        {
            "path": archive_name,
            "size_bytes": int(archive["size"]),
            "sha256": str(archive["sha256"]),
        },
        {
            "path": header_name,
            "size_bytes": (target / header_name).stat().st_size,
            "sha256": str(archive["header_sha256"]),
        },
    ]
    for filename, identity in config["documentation"].items():
        relative = f"documentation/{filename}"
        _download(
            f"{documentation_root}/{filename}",
            target / relative,
            size=int(identity["size"]),
            sha256=str(identity["sha256"]),
        )
        objects.append(
            {
                "path": relative,
                "size_bytes": int(identity["size"]),
                "sha256": str(identity["sha256"]),
            }
        )
    source_record = {
        "dataset": source["dataset"],
        "repository": source["repository"],
        "documentation_commit": source["documentation_commit"],
        "license": source["license"],
        "profile": source["profile"],
        "objects": objects,
    }
    (target / "SOURCE_OBJECTS.json").write_text(
        json.dumps(source_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in objects),
        encoding="ascii",
    )
    return {
        "directory": str(target),
        "archive_size_bytes": int(archive["size"]),
        "objects": len(objects),
        "verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/alibaba_gpu_2020_telemetry_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
