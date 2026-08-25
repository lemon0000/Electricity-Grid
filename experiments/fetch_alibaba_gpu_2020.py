"""Fetch the source-locked Alibaba PAI GPU v2020 stage-1 archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

import yaml

CHUNK_SIZE = 1024 * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified(path: Path, *, size: int | None, sha256: str) -> bool:
    return (
        path.is_file()
        and (size is None or path.stat().st_size == size)
        and _sha256(path) == sha256
    )


def _download_verified(
    url: str,
    destination: Path,
    *,
    size: int | None,
    sha256: str,
) -> None:
    if _verified(destination, size=size, sha256=sha256):
        return
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Electricity-Grid/1"})
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        partial.open("wb") as target,
    ):
        shutil.copyfileobj(response, target, length=CHUNK_SIZE)
    if not _verified(partial, size=size, sha256=sha256):
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded artifact failed verification: {url}")
    partial.replace(destination)


def _download_atomic(url: str, destination: Path) -> None:
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Electricity-Grid/1"})
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        partial.open("wb") as target,
    ):
        shutil.copyfileobj(response, target, length=CHUNK_SIZE)
    partial.replace(destination)


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    root = Path(source["path"])
    documentation_root = root / "documentation"
    documentation_root.mkdir(parents=True, exist_ok=True)

    archives = []
    for name, expected in config["expected"]["archives"].items():
        _download_verified(
            f"{source['data_base_url']}/{name}",
            root / name,
            size=int(expected["size"]),
            sha256=str(expected["sha256"]),
        )
        header_name = str(expected["header"])
        github_base = (
            "https://raw.githubusercontent.com/alibaba/clusterdata/"
            f"{source['documentation_commit']}/cluster-trace-gpu-v2020"
        )
        _download_verified(
            f"{github_base}/data/{header_name}",
            root / header_name,
            size=None,
            sha256=str(expected["header_sha256"]),
        )
        archives.append(
            {
                "name": name,
                "size": int(expected["size"]),
                "sha256": str(expected["sha256"]),
            }
        )

    github_base = (
        "https://raw.githubusercontent.com/alibaba/clusterdata/"
        f"{source['documentation_commit']}/cluster-trace-gpu-v2020"
    )
    for relative_url, filename in (
        ("README.md", "README.md"),
        ("data/README.md", "DATA_README.md"),
        ("LICENSE", "LICENSE"),
    ):
        _download_atomic(f"{github_base}/{relative_url}", documentation_root / filename)

    metadata = {
        "dataset": source["dataset"],
        "profile": source["profile"],
        "data_base_url": source["data_base_url"],
        "documentation_repository": source["repository"],
        "documentation_commit": source["documentation_commit"],
        "archives": archives,
        "headers": [
            {
                "name": str(expected["header"]),
                "sha256": str(expected["header_sha256"]),
            }
            for expected in config["expected"]["archives"].values()
        ],
    }
    (root / "SOURCE_OBJECTS.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_rows = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.name != "SHA256SUMS"
            and not path.name.endswith(".partial")
        ):
            manifest_rows.append(
                f"{_sha256(path)}  {path.relative_to(root).as_posix()}"
            )
    (root / "SHA256SUMS").write_text(
        "\n".join(manifest_rows) + "\n",
        encoding="ascii",
    )
    return {
        "destination": str(root),
        "archives": len(archives),
        "compressed_bytes": sum(item["size"] for item in archives),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/alibaba_gpu_2020.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
