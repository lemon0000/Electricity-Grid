"""Validate the downloaded Alibaba PAI GPU v2020 stage-1 archives."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import tarfile
from pathlib import Path

import yaml


def _verify_local_manifest(root: Path) -> bool:
    manifest_path = root / "SHA256SUMS"
    if not manifest_path.exists():
        return False
    expected_paths = set()
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        expected_paths.add(relative)
        path = root / Path(relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return False
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != "SHA256SUMS"
        and not path.name.endswith(".partial")
    }
    return expected_paths == actual_paths


def _validate_archive(
    root: Path,
    archive_name: str,
    expected: dict[str, object],
) -> dict[str, object]:
    archive_path = root / archive_name
    if archive_path.stat().st_size != expected["size"]:
        raise ValueError(f"Unexpected archive size: {archive_name}")
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if digest != expected["sha256"]:
        raise ValueError(f"Official SHA256 mismatch: {archive_name}")

    header_path = root / str(expected["header"])
    header_digest = hashlib.sha256(header_path.read_bytes()).hexdigest()
    if header_digest != expected["header_sha256"]:
        raise ValueError(f"Official header SHA256 mismatch: {header_path.name}")
    header = next(csv.reader([header_path.read_text(encoding="utf-8").strip()]))
    if header != expected["columns"]:
        raise ValueError(f"Header mismatch: {header_path.name}")

    expected_member = str(expected["member"])
    sample_rows = 0
    with tarfile.open(archive_path, "r:gz") as archive:
        file_members = [member for member in archive.getmembers() if member.isfile()]
        if [member.name for member in file_members] != [expected_member]:
            raise ValueError(f"Unexpected tar members in {archive_name}")
        raw_source = archive.extractfile(file_members[0])
        if raw_source is None:
            raise ValueError(f"Cannot read {expected_member}")
        with io.TextIOWrapper(raw_source, encoding="utf-8", newline="") as source:
            reader = csv.reader(source)
            for row in reader:
                if len(row) != len(header):
                    raise ValueError(f"Column-count mismatch in {expected_member}")
                sample_rows += 1
                if sample_rows == 100:
                    break
    if sample_rows == 0:
        raise ValueError(f"Empty table: {expected_member}")
    return {
        "archive": archive_name,
        "member": expected_member,
        "compressed_bytes": archive_path.stat().st_size,
        "columns": header,
        "sample_rows_validated": sample_rows,
    }


def run(
    config_path: Path,
    *,
    write_output: bool = True,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = Path(config["source"]["path"])
    expected_archives = config["expected"]["archives"]
    source_metadata = json.loads(
        (root / "SOURCE_OBJECTS.json").read_text(encoding="utf-8-sig")
    )
    tables = [
        _validate_archive(root, name, expected)
        for name, expected in expected_archives.items()
    ]
    checks = {
        "sha256_manifest": _verify_local_manifest(root),
        "source_profile": source_metadata["profile"] == config["source"]["profile"],
        "documentation_commit": source_metadata["documentation_commit"]
        == config["source"]["documentation_commit"],
        "archive_set": {entry["name"] for entry in source_metadata["archives"]}
        == set(expected_archives),
        "all_table_samples_valid": all(
            table["sample_rows_validated"] > 0 for table in tables
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"Alibaba GPU v2020 validation failed: {checks}")

    summary = {
        "dataset": config["source"]["dataset"],
        "profile": config["source"]["profile"],
        "documentation_commit": config["source"]["documentation_commit"],
        "license": config["source"]["license"],
        "checks": checks,
        "archives": len(tables),
        "compressed_bytes": sum(table["compressed_bytes"] for table in tables),
        "tables": tables,
        "evidence": config["evidence"],
    }
    if write_output:
        output_path = Path(config["output"]["summary_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


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
