"""Zero-solver audit of raw continuation availability in frozen RQ2 margins."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = (
    ROOT / "configs/rq2_joint_deliverability_continuation_audit_v1.DRAFT.yaml"
)
HOUR = timedelta(hours=1)

POWER_FIELDS = (
    "block_id",
    "split",
    "block_probability",
    "outage_seed",
    "hour_offset",
    "source_hour",
    "timestamp",
    "system_load_mw",
    "cfe_call_fraction",
    "active_event_id",
    "active_component_type",
    "active_component_uid",
)
WORKLOAD_FIELDS = (
    "block_id",
    "split",
    "block_probability",
    "hour_offset",
    "source_relative_hour",
    "requested_gpu_occupancy",
    "workload_fraction",
)
EVENT_FIELDS = (
    "outage_seed",
    "event_id",
    "component_type",
    "component_uid",
    "start_hour",
    "end_hour_exclusive",
    "duration_hours",
    "crosses_split",
)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _root_path(value: object, label: str) -> Path:
    path = (ROOT / str(value)).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"{label} escapes repository root")
    return path


def _verify_hash(path: Path, expected: object, label: str) -> None:
    if not path.is_file() or _sha256(path) != str(expected):
        raise ValueError(f"{label} hash mismatch")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def _read_gzip_csv(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != fields:
            raise ValueError(f"{path.name} schema drifted")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name} is empty")
    return rows


def _load_config(config_path: Path) -> dict[str, Any]:
    payload = yaml.load(
        config_path.resolve().read_text(encoding="utf-8"),
        Loader=_UniqueKeyLoader,
    )
    if not isinstance(payload, dict):
        raise TypeError("continuation audit config must be a mapping")
    expected_lifecycle = {
        "status": "DRAFT_NONAUTHORITATIVE",
        "pre_seal_audit_complete": False,
        "sealed_ready_for_independent_review": False,
        "independent_review_passed": False,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }
    if payload.get("lifecycle") != expected_lifecycle:
        raise ValueError("all continuation diagnostic lifecycle gates must stay closed")
    authority = payload.get("authority", {})
    if authority.get("role") != (
        "raw_continuation_availability_and_provenance_diagnostic_only"
    ):
        raise ValueError("continuation diagnostic authority role drifted")
    for key in (
        "may_open_any_execution_gate",
        "may_modify_predecessor_boundary_diagnostic",
        "may_register_continuous_scientific_protocol",
        "may_run_solver_or_formal_execution",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"authority.{key} must remain false")
    audit = payload.get("audit_contract", {})
    required = {
        "evidence_level": "non_authoritative_zero_solver_raw_continuation_diagnostic",
        "source_scope": "frozen_published_predispatch_marginal_packages",
        "same_split_links_only": True,
        "cross_split_links_allowed": False,
        "same_power_outage_seed_required": True,
        "active_event_id_may_change_along_one_power_trajectory": True,
        "workload_trace_identity_basis": "package_source_and_training_normalization",
        "power_and_workload_share_observed_clock": False,
        "potential_pair_adjacency_is_registered_coupling": False,
        "raw_workload_fraction_may_be_clipped": False,
        "v5_workload_occupancy_mapping_is_separate": "min_raw_workload_fraction_and_1",
        "dispatched_grid_continuation_audited": False,
        "full_joint_service_continuation_ready": False,
        "future_contract_parameters_may_be_invented": False,
        "solver_calls_allowed": False,
        "result_contingent_selection_allowed": False,
    }
    if any(audit.get(key) != value for key, value in required.items()):
        raise ValueError("continuation audit contract drifted")
    output = payload.get("output", {})
    if (
        output.get("directory")
        != "results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative"
        or output.get("files") != ["summary.json", "chains.json", "SHA256SUMS.json"]
        or output.get("overwrite_allowed") is not False
    ):
        raise ValueError("continuation diagnostic output contract drifted")
    return payload


def _verify_predecessor(config: dict[str, Any]) -> dict[str, str]:
    predecessor = config["predecessor_boundary_diagnostic"]
    pairs = {
        "config": (predecessor["config_path"], predecessor["config_sha256"]),
        "audit": (predecessor["audit_path"], predecessor["audit_sha256"]),
        "boundary": (predecessor["boundary_path"], predecessor["boundary_sha256"]),
        "runner": (predecessor["runner_path"], predecessor["runner_sha256"]),
    }
    verified: dict[str, str] = {}
    for label, (relative, digest) in pairs.items():
        path = _root_path(relative, f"predecessor.{label}")
        _verify_hash(path, digest, f"predecessor.{label}")
        verified[label] = str(digest)
    result_root = _root_path(
        predecessor["result_directory"], "predecessor.result_directory"
    )
    for name, digest in predecessor["result_files"].items():
        _verify_hash(result_root / name, digest, f"predecessor.result_files.{name}")
        verified[f"result/{name}"] = str(digest)
    manifest = _read_json(result_root / "SHA256SUMS.json")
    if manifest != {
        name: predecessor["result_files"][name]
        for name in ("cells.json", "summary.json")
    }:
        raise ValueError("predecessor result manifest content drifted")
    return verified


def _verify_package(binding: dict[str, Any], label: str) -> tuple[Path, dict[str, Any]]:
    package = _root_path(binding["package"], f"inputs.{label}.package")
    manifest_path = package / "SHA256SUMS.json"
    _verify_hash(manifest_path, binding["manifest_sha256"], f"{label} manifest")
    manifest = _read_json(manifest_path)
    if manifest != binding["members"]:
        raise ValueError(f"{label} manifest members drifted")
    for name, digest in manifest.items():
        _verify_hash(package / name, digest, f"{label}.{name}")
    for prefix in ("builder_config", "builder"):
        path = _root_path(binding[f"{prefix}_path"], f"inputs.{label}.{prefix}_path")
        _verify_hash(path, binding[f"{prefix}_sha256"], f"{label} {prefix}")
    if label == "power":
        chronology = _root_path(binding["chronology_path"], "inputs.power.chronology")
        _verify_hash(chronology, binding["chronology_sha256"], "power chronology")
    return package, _read_json(package / "summary.json")


def _verify_summary(
    binding: dict[str, Any],
    summary: dict[str, Any],
    label: str,
) -> None:
    expected = {
        "schema": binding["expected_schema"],
        "split_hour": binding["expected_split_hour"],
        "block_hours": binding["expected_block_hours"],
        "block_stride_hours": binding["expected_block_stride_hours"],
        "training_block_count": binding["expected_training_blocks"],
        "holdout_block_count": binding["expected_holdout_blocks"],
        "config_sha256": binding["builder_config_sha256"],
        "implementation_sha256": binding["builder_sha256"],
    }
    if label == "power":
        expected.update(
            {
                "hours": binding["expected_hours"],
                "outage_seeds": binding["expected_outage_seeds"],
                "n1_chronology_module_sha256": binding["chronology_sha256"],
                "outage_frequency_semantics": "sampled_from_published_rate",
                "empirical_outage_probability_claimed": False,
                "grid_need_dispatch_completed": False,
                "security_certified": False,
            }
        )
    else:
        expected["hour_count"] = binding["expected_hour_count"]
    if any(summary.get(key) != value for key, value in expected.items()):
        raise ValueError(f"{label} summary contract drifted")


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("power timestamp must carry UTC offset")
    return parsed.astimezone(timezone.utc)


def _boolean(value: str) -> bool:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise ValueError(f"invalid boolean: {value!r}")


def _validate_power_hour_link(
    earlier_source_hour: int,
    later_source_hour: int,
    earlier_timestamp: str,
    later_timestamp: str,
) -> None:
    if (
        later_source_hour != earlier_source_hour + 1
        or _timestamp(later_timestamp) - _timestamp(earlier_timestamp) != HOUR
    ):
        raise ValueError("power source-hour and timestamp link is not consecutive")


def _validate_hourly_outage_state(
    row: dict[str, str],
    active_by_hour: dict[tuple[int, int], dict[str, Any]],
) -> None:
    expected_event = active_by_hour.get(
        (int(row["outage_seed"]), int(row["source_hour"]))
    )
    observed = (
        row["active_event_id"],
        row["active_component_type"],
        row["active_component_uid"],
    )
    expected = (
        (
            expected_event["event_id"],
            expected_event["component_type"],
            expected_event["component_uid"],
        )
        if expected_event is not None
        else ("", "", "")
    )
    if observed != expected:
        raise ValueError("power hourly outage state disagrees with event schedule")


def _validate_workload_normalization(
    requested: Decimal,
    fraction: Decimal,
    peak: Decimal,
) -> None:
    if (
        not requested.is_finite()
        or requested < 0
        or not fraction.is_finite()
        or requested / peak != fraction
    ):
        raise ValueError("workload row does not use the registered training peak")


def _validate_marginal(
    package: Path,
    split: str,
    block_probabilities: dict[str, Decimal],
) -> None:
    rows = _read_gzip_csv(package / f"{split}_marginal.csv.gz", ("id", "probability"))
    probabilities: dict[str, Decimal] = {}
    for row in rows:
        if row["id"] in probabilities:
            raise ValueError(f"duplicate {split} marginal id")
        probabilities[row["id"]] = Decimal(row["probability"])
    if probabilities != block_probabilities:
        raise ValueError(f"{split} marginal and hourly block probabilities differ")


def _missing_intervals(
    low: int,
    high_exclusive: int,
    observed_start: int,
    observed_end: int,
) -> list[dict[str, object]]:
    intervals = []
    if observed_start > low:
        intervals.append(
            {
                "start": low,
                "end_inclusive": observed_start - 1,
                "hour_count": observed_start - low,
                "position": "leading",
            }
        )
    if observed_end + 1 < high_exclusive:
        intervals.append(
            {
                "start": observed_end + 1,
                "end_inclusive": high_exclusive - 1,
                "hour_count": high_exclusive - observed_end - 1,
                "position": "trailing",
            }
        )
    return intervals


def _group_adjacencies(
    blocks: list[dict[str, Any]],
    identity_fields: tuple[str, ...],
) -> list[
    tuple[
        tuple[object, ...],
        list[dict[str, Any]],
        list[tuple[dict[str, Any], dict[str, Any]]],
        list[dict[str, int]],
    ]
]:
    """Classify exact source-hour successors without crossing an identity."""
    grouped: dict[tuple[object, ...], list[dict[str, Any]]] = {}
    for block in blocks:
        key = tuple(block[field] for field in identity_fields)
        grouped.setdefault(key, []).append(block)
    result = []
    for key, members in sorted(grouped.items()):
        members.sort(key=lambda item: item["source_start"])
        starts = [item["source_start"] for item in members]
        if len(starts) != len(set(starts)):
            raise ValueError("duplicate source start makes successor ambiguous")
        links = []
        gaps = []
        for earlier, later in pairwise(members):
            if later["source_start"] <= earlier["source_end"]:
                raise ValueError("overlapping blocks make successor ambiguous")
            if later["source_start"] == earlier["source_end"] + 1:
                links.append((earlier, later))
            else:
                gaps.append(
                    {
                        "start": earlier["source_end"] + 1,
                        "end_inclusive": later["source_start"] - 1,
                        "hour_count": later["source_start"] - earlier["source_end"] - 1,
                    }
                )
        result.append((key, members, links, gaps))
    return result


def _load_outage_events(
    package: Path,
    *,
    split_hour: int,
    expected_seeds: set[int],
) -> tuple[
    dict[tuple[int, int], dict[str, Any]],
    dict[int, dict[str, Any]],
]:
    rows = _read_gzip_csv(package / "n1_outage_events.csv.gz", EVENT_FIELDS)
    identities: set[tuple[int, str]] = set()
    active_by_hour: dict[tuple[int, int], dict[str, Any]] = {}
    cross_split: dict[int, dict[str, Any]] = {}
    for row in rows:
        seed = int(row["outage_seed"])
        event_id = row["event_id"]
        identity = (seed, event_id)
        if identity in identities:
            raise ValueError("duplicate outage event identity")
        identities.add(identity)
        start = int(row["start_hour"])
        end = int(row["end_hour_exclusive"])
        duration = int(row["duration_hours"])
        crosses = _boolean(row["crosses_split"])
        if seed not in expected_seeds or end <= start or duration != end - start:
            raise ValueError("outage event identity or interval drifted")
        if crosses != (start < split_hour < end):
            raise ValueError("cross-split outage event label drifted")
        event = {
            "outage_seed": seed,
            "event_id": event_id,
            "component_type": row["component_type"],
            "component_uid": row["component_uid"],
            "start_hour": start,
            "end_hour_exclusive": end,
            "duration_hours": duration,
        }
        if crosses:
            if seed in cross_split:
                raise ValueError("multiple cross-split events for one outage seed")
            cross_split[seed] = event
        for hour in range(start, end):
            key = (seed, hour)
            if key in active_by_hour:
                raise ValueError("overlapping outage events in one seed trajectory")
            active_by_hour[key] = event
    if set(cross_split) != expected_seeds:
        raise ValueError("each frozen outage seed must expose its cross-split event")
    return active_by_hour, cross_split


def _power_blocks(
    package: Path,
    summary: dict[str, Any],
    binding: dict[str, Any],
    active_by_hour: dict[tuple[int, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = _read_gzip_csv(package / "power_system_blocks.csv.gz", POWER_FIELDS)
    expected_seeds = {int(value) for value in binding["expected_outage_seeds"]}
    grouped: dict[str, list[dict[str, str]]] = {}
    base_by_hour: dict[int, tuple[str, str, str]] = {}
    for row in rows:
        grouped.setdefault(row["block_id"], []).append(row)
        source_hour = int(row["source_hour"])
        base = (row["timestamp"], row["system_load_mw"], row["cfe_call_fraction"])
        if base_by_hour.setdefault(source_hour, base) != base:
            raise ValueError("power base trajectory differs across outage seeds")
        load = Decimal(row["system_load_mw"])
        cfe = Decimal(row["cfe_call_fraction"])
        if (
            not load.is_finite()
            or load <= 0
            or not cfe.is_finite()
            or not 0 <= cfe <= 1
        ):
            raise ValueError("invalid power base value")
        seed = int(row["outage_seed"])
        _validate_hourly_outage_state(row, active_by_hour)

    blocks = []
    probabilities = {"training": {}, "holdout": {}}
    block_hours = int(summary["block_hours"])
    for block_id, block_rows in grouped.items():
        block_rows.sort(key=lambda item: int(item["hour_offset"]))
        if len(block_rows) != block_hours or [
            int(row["hour_offset"]) for row in block_rows
        ] != list(range(block_hours)):
            raise ValueError("power block rows or offsets drifted")
        splits = {row["split"] for row in block_rows}
        seeds = {int(row["outage_seed"]) for row in block_rows}
        probs = {Decimal(row["block_probability"]) for row in block_rows}
        if len(splits) != 1 or len(seeds) != 1 or len(probs) != 1:
            raise ValueError("power block identity is internally inconsistent")
        split, seed, probability = splits.pop(), seeds.pop(), probs.pop()
        if split not in probabilities or seed not in expected_seeds:
            raise ValueError("unknown power split or outage seed")
        hours = [int(row["source_hour"]) for row in block_rows]
        timestamps = [_timestamp(row["timestamp"]) for row in block_rows]
        if hours != list(range(hours[0], hours[0] + block_hours)):
            raise ValueError("power block source clock is not hourly-contiguous")
        for earlier, later in pairwise(block_rows):
            _validate_power_hour_link(
                int(earlier["source_hour"]),
                int(later["source_hour"]),
                earlier["timestamp"],
                later["timestamp"],
            )
        if block_id in probabilities[split]:
            raise ValueError("duplicate power block id")
        probabilities[split][block_id] = probability
        blocks.append(
            {
                "block_id": block_id,
                "split": split,
                "outage_seed": seed,
                "source_start": hours[0],
                "source_end": hours[-1],
                "timestamp_start": timestamps[0],
                "timestamp_end": timestamps[-1],
                "active_event_start": block_rows[0]["active_event_id"],
                "active_event_end": block_rows[-1]["active_event_id"],
                "rows": block_rows,
            }
        )
    for split in ("training", "holdout"):
        _validate_marginal(package, split, probabilities[split])
        expected = int(binding[f"expected_{split}_blocks"])
        if len(probabilities[split]) != expected:
            raise ValueError(f"power {split} block count drifted")
    return blocks


def _power_audit(
    package: Path,
    summary: dict[str, Any],
    binding: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    expected_seeds = {int(value) for value in binding["expected_outage_seeds"]}
    active_by_hour, cross_events = _load_outage_events(
        package,
        split_hour=int(summary["split_hour"]),
        expected_seeds=expected_seeds,
    )
    blocks = _power_blocks(package, summary, binding, active_by_hour)
    groups = _group_adjacencies(blocks, ("split", "outage_seed"))
    links_by_split = {"training": 0, "holdout": 0}
    same_event_boundary = {"training": 0, "holdout": 0}
    hourly_links = 0
    event_changes = 0
    chains = []
    block_hours = int(summary["block_hours"])
    for (split, seed), members, links, internal_gaps in groups:
        if internal_gaps:
            raise ValueError("unexpected internal gap within frozen power split/seed")
        flat_rows = [row for block in members for row in block["rows"]]
        flat_rows.sort(key=lambda item: int(item["source_hour"]))
        for earlier, later in pairwise(flat_rows):
            _validate_power_hour_link(
                int(earlier["source_hour"]),
                int(later["source_hour"]),
                earlier["timestamp"],
                later["timestamp"],
            )
            hourly_links += 1
            event_changes += later["active_event_id"] != earlier["active_event_id"]
        boundary_links = []
        for earlier, later in links:
            if later["timestamp_start"] - earlier["timestamp_end"] != HOUR:
                raise ValueError("power boundary timestamp is not consecutive")
            same = bool(earlier["active_event_end"]) and (
                earlier["active_event_end"] == later["active_event_start"]
            )
            same_event_boundary[split] += same
            boundary_links.append(
                {
                    "predecessor_block_id": earlier["block_id"],
                    "successor_block_id": later["block_id"],
                    "predecessor_source_end": earlier["source_end"],
                    "successor_source_start": later["source_start"],
                    "predecessor_timestamp": earlier["timestamp_end"].isoformat(),
                    "successor_timestamp": later["timestamp_start"].isoformat(),
                    "predecessor_active_event_id": earlier["active_event_end"],
                    "successor_active_event_id": later["active_event_start"],
                    "same_nonempty_active_event": same,
                }
            )
        links_by_split[split] += len(boundary_links)
        low = 0 if split == "training" else int(summary["split_hour"])
        high = int(summary["split_hour"]) if split == "training" else int(
            summary["hours"]
        )
        missing = _missing_intervals(
            low,
            high,
            members[0]["source_start"],
            members[-1]["source_end"],
        )
        expected_starts = set(range(low, high - block_hours + 1, block_hours))
        missing_starts = expected_starts - {item["source_start"] for item in members}
        cross_event = cross_events[seed]
        if any(
            not (
                start < cross_event["end_hour_exclusive"]
                and start + block_hours > cross_event["start_hour"]
            )
            for start in missing_starts
        ):
            raise ValueError("power missing block is not explained by cross-split event")
        chains.append(
            {
                "chain_id": f"power:{split}:outage_seed={seed}",
                "split": split,
                "outage_seed": seed,
                "trajectory_identity_basis": {
                    "package_manifest_sha256": binding["manifest_sha256"],
                    "outage_seed": seed,
                },
                "block_count": len(members),
                "row_count": len(flat_rows),
                "source_start": members[0]["source_start"],
                "source_end": members[-1]["source_end"],
                "timestamp_start": members[0]["timestamp_start"].isoformat(),
                "timestamp_end": members[-1]["timestamp_end"].isoformat(),
                "block_ids": [item["block_id"] for item in members],
                "block_boundary_link_count": len(boundary_links),
                "block_boundary_links": boundary_links,
                "unavailable_in_frozen_margin": missing,
                "unavailable_in_frozen_margin_reason": (
                    "whole_blocks_touching_cross_split_outage_event_excluded"
                ),
            }
        )
    cross_details = []
    for seed, event in sorted(cross_events.items()):
        seed_chains = [chain for chain in chains if chain["outage_seed"] == seed]
        excluded_start = min(
            interval["start"]
            for chain in seed_chains
            for interval in chain["unavailable_in_frozen_margin"]
        )
        excluded_end = max(
            interval["end_inclusive"]
            for chain in seed_chains
            for interval in chain["unavailable_in_frozen_margin"]
        )
        cross_details.append(
            {
                **event,
                "excluded_whole_block_start": excluded_start,
                "excluded_whole_block_end_inclusive": excluded_end,
                "excluded_whole_block_hour_count": excluded_end - excluded_start + 1,
            }
        )
    inventory = {
        "row_count": sum(chain["row_count"] for chain in chains),
        "block_count": len(blocks),
        "chain_count": len(chains),
        "hourly_source_and_timestamp_link_count": hourly_links,
        "active_event_change_link_count": event_changes,
        "block_boundary_links_by_split": links_by_split,
        "same_nonempty_active_event_boundary_links_by_split": same_event_boundary,
        "cross_split_event_count": len(cross_details),
        "outage_schedule_verified_for_every_observed_row": True,
        "base_load_cfe_timestamp_equal_across_seeds": True,
    }
    return inventory, chains, cross_details


def _workload_audit(
    package: Path,
    summary: dict[str, Any],
    binding: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = _read_gzip_csv(package / "workload_blocks.csv.gz", WORKLOAD_FIELDS)
    peak = Decimal(summary["training_peak_requested_gpu_occupancy"])
    grouped: dict[str, list[dict[str, str]]] = {}
    above_hours = {"training": [], "holdout": []}
    above_blocks = {"training": set(), "holdout": set()}
    maximum = {"training": Decimal("-Infinity"), "holdout": Decimal("-Infinity")}
    for row in rows:
        grouped.setdefault(row["block_id"], []).append(row)
        split = row["split"]
        if split not in above_hours:
            raise ValueError("unknown workload split")
        requested = Decimal(row["requested_gpu_occupancy"])
        fraction = Decimal(row["workload_fraction"])
        _validate_workload_normalization(requested, fraction, peak)
        maximum[split] = max(maximum[split], fraction)
        if fraction > 1:
            above_hours[split].append(int(row["source_relative_hour"]))
            above_blocks[split].add(row["block_id"])

    blocks = []
    probabilities = {"training": {}, "holdout": {}}
    block_hours = int(summary["block_hours"])
    for block_id, block_rows in grouped.items():
        block_rows.sort(key=lambda item: int(item["hour_offset"]))
        if len(block_rows) != block_hours or [
            int(row["hour_offset"]) for row in block_rows
        ] != list(range(block_hours)):
            raise ValueError("workload block rows or offsets drifted")
        splits = {row["split"] for row in block_rows}
        probs = {Decimal(row["block_probability"]) for row in block_rows}
        if len(splits) != 1 or len(probs) != 1:
            raise ValueError("workload block identity is internally inconsistent")
        split, probability = splits.pop(), probs.pop()
        hours = [int(row["source_relative_hour"]) for row in block_rows]
        if hours != list(range(hours[0], hours[0] + block_hours)):
            raise ValueError("workload block source clock is not hourly-contiguous")
        if block_id in probabilities[split]:
            raise ValueError("duplicate workload block id")
        probabilities[split][block_id] = probability
        blocks.append(
            {
                "block_id": block_id,
                "split": split,
                "source_start": hours[0],
                "source_end": hours[-1],
            }
        )
    for split in ("training", "holdout"):
        _validate_marginal(package, split, probabilities[split])
        expected = int(binding[f"expected_{split}_blocks"])
        if len(probabilities[split]) != expected:
            raise ValueError(f"workload {split} block count drifted")

    chains = []
    links_by_split = {"training": 0, "holdout": 0}
    hourly_links = 0
    for (split,), members, links, internal_gaps in _group_adjacencies(
        blocks, ("split",)
    ):
        if internal_gaps:
            raise ValueError("unexpected internal gap within frozen workload split")
        boundary_links = [
            {
                "predecessor_block_id": earlier["block_id"],
                "successor_block_id": later["block_id"],
                "predecessor_source_end": earlier["source_end"],
                "successor_source_start": later["source_start"],
            }
            for earlier, later in links
        ]
        links_by_split[split] = len(boundary_links)
        row_count = len(members) * block_hours
        hourly_links += row_count - 1
        low = 0 if split == "training" else int(summary["split_hour"])
        high = int(summary["split_hour"]) if split == "training" else int(
            summary["hour_count"]
        )
        chains.append(
            {
                "chain_id": f"workload:{split}:single_published_trace",
                "split": split,
                "trace_identity_basis": {
                    "source_sha256": summary["source_sha256"],
                    "builder_config_sha256": binding["builder_config_sha256"],
                    "builder_sha256": binding["builder_sha256"],
                    "package_summary_sha256": binding["members"]["summary.json"],
                    "training_peak_requested_gpu_occupancy": str(peak),
                    "normalization_method": (
                        "divide_by_training_segment_peak_occupancy"
                    ),
                },
                "row_trace_id_present": False,
                "block_count": len(members),
                "row_count": row_count,
                "source_start": members[0]["source_start"],
                "source_end": members[-1]["source_end"],
                "block_ids": [item["block_id"] for item in members],
                "block_boundary_link_count": len(boundary_links),
                "block_boundary_links": boundary_links,
                "unavailable_in_frozen_margin": _missing_intervals(
                    low,
                    high,
                    members[0]["source_start"],
                    members[-1]["source_end"],
                ),
                "unavailable_in_frozen_margin_reason": (
                    "incomplete_terminal_block_dropped"
                ),
            }
        )
    inventory = {
        "row_count": len(rows),
        "block_count": len(blocks),
        "chain_count": len(chains),
        "hourly_source_link_count": hourly_links,
        "block_boundary_links_by_split": links_by_split,
        "normalization_identity_verified_for_every_row": True,
        "training_peak_requested_gpu_occupancy": str(peak),
        "raw_fraction_above_one_hour_count_by_split": {
            split: len(hours) for split, hours in above_hours.items()
        },
        "raw_fraction_above_one_block_count_by_split": {
            split: len(block_ids) for split, block_ids in above_blocks.items()
        },
        "raw_fraction_above_one_source_hours": above_hours,
        "maximum_raw_fraction_by_split": {
            split: str(value) for split, value in maximum.items()
        },
        "raw_fraction_was_clipped": False,
        "raw_fraction_above_one_requires_explicit_successor_mapping": True,
    }
    return inventory, chains


def audit_continuation_availability(
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    """Audit source adjacency only; do not infer a registered joint continuation."""
    config_path = config_path.resolve()
    config = _load_config(config_path)
    predecessor = _verify_predecessor(config)
    power_binding = config["inputs"]["power"]
    workload_binding = config["inputs"]["workload"]
    power_package, power_summary = _verify_package(power_binding, "power")
    workload_package, workload_summary = _verify_package(
        workload_binding, "workload"
    )
    _verify_summary(power_binding, power_summary, "power")
    _verify_summary(workload_binding, workload_summary, "workload")
    power_inventory, power_chains, cross_events = _power_audit(
        power_package, power_summary, power_binding
    )
    workload_inventory, workload_chains = _workload_audit(
        workload_package, workload_summary, workload_binding
    )
    power_links = power_inventory["block_boundary_links_by_split"]
    workload_links = workload_inventory["block_boundary_links_by_split"]
    potential: dict[str, object] = {
        split: int(power_links[split]) * int(workload_links[split])
        for split in ("training", "holdout")
    }
    potential["interpretation"] = "unregistered_cartesian_marginal_adjacency_only"
    if (
        power_summary.get("grid_need_dispatch_completed") is not False
        or workload_summary.get("workload_fraction_is_power") is not False
        or workload_summary.get("flexible_fraction_inferred") is not False
        or workload_summary.get("deadline_observed") is not False
        or workload_summary.get("checkpoint_observed") is not False
        or workload_summary.get("recoverability_observed") is not False
    ):
        raise ValueError("frozen contract-evidence status drifted")
    contract_evidence = {
        "cfe_call_fraction_present": True,
        "workload_occupancy_present": True,
        "dispatched_grid_need_present": False,
        "shared_physical_clock_mapping_present": False,
        "absolute_workload_power_present": False,
        "flexible_fraction_observed": False,
        "call_limit_observed": False,
        "track_compatible_recovery_headroom_observed": False,
        "maximum_recovery_power_observed": False,
        "recovery_efficiency_observed": False,
        "flexibility_event_duration_contract_observed": False,
        "flexibility_event_count_contract_observed": False,
        "energy_budget_observed": False,
        "debt_limit_observed": False,
        "accounting_period_id_observed": False,
        "service_deadline_observed": False,
        "checkpoint_observed": False,
        "recoverability_observed": False,
        "missing_contract_interpretation": (
            "unbound_for_future_preregistration_not_permission_to_invent_values"
        ),
    }
    summary = {
        "schema": (
            "rq2_joint_deliverability_continuation_availability_v1_non_authoritative"
        ),
        "evidence_level": config["audit_contract"]["evidence_level"],
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "runner_sha256": _sha256(
            ROOT / "experiments/audit_rq2_joint_deliverability_continuation_v1.py"
        ),
        "power_manifest_sha256": power_binding["manifest_sha256"],
        "workload_manifest_sha256": workload_binding["manifest_sha256"],
        "predecessor_boundary_hashes_verified": predecessor,
        "power_chronology": power_inventory,
        "workload_chronology": workload_inventory,
        "potential_marginal_pair_adjacency": potential,
        "single_margin_successor_is_sufficient_for_joint_continuation": False,
        "power_and_workload_share_observed_clock": False,
        "cross_split_continuation_link_count": 0,
        "contract_evidence": contract_evidence,
        "raw_chronology_candidate_available": True,
        "raw_chronology_candidate_interpretation": (
            "within_each_frozen_margin_only_not_joint_service_readiness"
        ),
        "power_outage_trajectory_semantics": "sampled_from_published_rate_not_observed",
        "dispatched_grid_continuation_audited": False,
        "full_joint_service_continuation_ready": False,
        "continuous_scientific_protocol_registered": False,
        "formal_execution_started": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
        "solver_calls": 0,
    }
    chains = {
        "schema": "rq2_joint_deliverability_continuation_chains_v1_non_authoritative",
        "scope": (
            "source_adjacency_within_each_frozen_margin_not_registered_joint_coupling"
        ),
        "power": power_chains,
        "power_cross_split_events_and_whole_block_exclusions": cross_events,
        "workload": workload_chains,
    }
    return {"summary": summary, "chains": chains}
