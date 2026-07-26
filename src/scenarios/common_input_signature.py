"""Canonical content signatures for shared deterministic/stochastic inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import fields, is_dataclass
from enum import Enum
from math import isfinite
from numbers import Integral, Real


COMMON_INPUT_SIGNATURE_SCHEMA = "rts24_common_fair_inputs_v2"


def _mapping_key(value: object) -> str:
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, (str, Integral)) and not isinstance(value, bool):
        return str(value)
    raise TypeError("Common-input signature mapping keys must be strings or integers")


def normalize_common_input_signature(value: object) -> object:
    """Return a JSON-safe, order-stable representation of ``value``."""

    if isinstance(value, Enum):
        return normalize_common_input_signature(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return normalize_common_input_signature(
            {field.name: getattr(value, field.name) for field in fields(value)}
        )
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            normalized_key = _mapping_key(key)
            if normalized_key in normalized:
                raise ValueError(
                    "Common-input signature mapping keys collide after normalization"
                )
            normalized[normalized_key] = normalize_common_input_signature(item)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, Set) and not isinstance(value, (str, bytes)):
        normalized_items = [normalize_common_input_signature(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(
                item,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [normalize_common_input_signature(item) for item in value]
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if not isfinite(number):
            raise ValueError("Common-input signatures require finite numbers")
        return number
    raise TypeError(
        f"Unsupported common-input signature value: {type(value).__name__}"
    )


def build_common_input_signature(
    *,
    case: Mapping[object, object],
    source_package: str,
    source_version: str,
    demand_path_source: str,
    quarters: Iterable[object],
    poi: object,
    project: object,
    service_envelope: object,
    service_configuration: Mapping[object, object],
    branch_indices: Iterable[int],
    generator_indices: Iterable[int],
    immediate_rating: str,
    sustained_rating: str,
    security_configuration: Mapping[object, object],
    security_states: Iterable[object],
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    objective: Mapping[object, object],
    solver: Mapping[object, object],
) -> dict[str, object]:
    """Build the complete common-input payload used by M4 and M5."""

    normalized_objective = normalize_common_input_signature(objective)
    normalized_solver = normalize_common_input_signature(solver)
    if not isinstance(normalized_objective, dict) or not isinstance(
        normalized_solver, dict
    ):
        raise TypeError("Objective and solver common inputs must be mappings")

    payload = {
        "schema": COMMON_INPUT_SIGNATURE_SCHEMA,
        "case": {
            "configuration": case,
            "source_package": source_package,
            "source_version": source_version,
        },
        "demand_path_source": demand_path_source,
        "quarters": list(quarters),
        "poi": poi,
        "project": project,
        "service_envelope": service_envelope,
        "service_configuration": service_configuration,
        "branch_indices": list(branch_indices),
        "generator_indices": list(generator_indices),
        "immediate_rating": immediate_rating,
        "sustained_rating": sustained_rating,
        "security_configuration": security_configuration,
        "security_states": list(security_states),
        "redispatch_up_mw": redispatch_up_mw,
        "redispatch_down_mw": redispatch_down_mw,
        # Retain these legacy scalar fields for existing result consumers.
        "access_shortfall_cost_per_mwh": normalized_objective[
            "access_shortfall_cost_per_mwh"
        ],
        "solver_name": normalized_solver["name"],
        "objective": normalized_objective,
        "solver": normalized_solver,
    }
    normalized_payload = normalize_common_input_signature(payload)
    if not isinstance(normalized_payload, dict):
        raise TypeError("Common-input signature payload must be a mapping")
    return normalized_payload


def common_input_signature_sha256(signature: object) -> str:
    """Hash a signature using canonical compact JSON encoded as UTF-8."""

    canonical_json = json.dumps(
        normalize_common_input_signature(signature),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


__all__ = [
    "COMMON_INPUT_SIGNATURE_SCHEMA",
    "build_common_input_signature",
    "common_input_signature_sha256",
    "normalize_common_input_signature",
]
