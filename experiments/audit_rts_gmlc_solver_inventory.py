"""Publish a reproducible solver environment and license-capacity inventory."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from pyomo.environ import SolverFactory

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json


_OUTPUT_ROOT = Path("results/tables/rts_gmlc_solver_inventory_v1")
_SCRIPT_PATH = Path(__file__).resolve()
_PACKAGE_NAMES = (
    "numpy",
    "pyomo",
    "highspy",
    "gurobipy",
    "cplex",
    "xpress",
    "xpresslibs",
)
_INTERFACES = {
    "highs": ("highs", "appsi_highs"),
    "gurobi": ("gurobi", "gurobi_direct", "gurobi_persistent"),
    "cplex": ("cplex", "cplex_direct", "cplex_persistent"),
    "xpress": ("xpress", "xpress_direct", "xpress_persistent"),
}
_MODEL_SIZES = {
    "formal_24h_candidate_proxy_stage": {
        "variables": 215689,
        "constraints": 350615,
    },
    "solver_pilot_6h_candidate_proxy_stage": {
        "variables": 53923,
        "constraints": 87545,
    },
}
_CAPACITY_BOUNDARIES = {
    "highs": {
        "limit_kind": "no_software_license_size_limit_observed",
        "maximum_variables": None,
        "maximum_constraints": None,
        "maximum_rows_plus_columns": None,
        "boundary_source": "unrestricted_open_source_distribution",
        "rejection_error_code": None,
    },
    "gurobi": {
        "limit_kind": "separate_variables_and_linear_constraints",
        "maximum_variables": 2000,
        "maximum_constraints": 2000,
        "maximum_rows_plus_columns": None,
        "tested_feasible": "2000_variables_and_2000_linear_constraints",
        "tested_rejected": "2001_variables_or_2001_linear_constraints",
        "boundary_source": "current_session_native_api_capacity_probe",
        "rejection_error_code": 10010,
    },
    "cplex": {
        "limit_kind": "separate_variables_and_constraints",
        "maximum_variables": 1000,
        "maximum_constraints": 1000,
        "maximum_rows_plus_columns": None,
        "tested_feasible": "1000_variables_and_1000_constraints",
        "tested_rejected": "1001_variables_or_1001_constraints",
        "boundary_source": "current_session_native_api_capacity_probe",
        "rejection_error_code": 1016,
    },
    "xpress": {
        "limit_kind": "combined_rows_plus_columns",
        "maximum_variables": None,
        "maximum_constraints": None,
        "maximum_rows_plus_columns": 5000,
        "tested_feasible": "2500_columns_plus_2500_rows",
        "tested_rejected": "5001_total_rows_plus_columns",
        "boundary_source": "current_session_native_api_capacity_probe",
        "rejection_error_code": 120,
    },
}


def _package_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in _PACKAGE_NAMES}


def _runtime_versions() -> dict[str, str]:
    import cplex
    import gurobipy
    import highspy
    import numpy
    import pyomo
    import xpress

    highs = highspy.Highs()
    cplex_runtime = cplex.Cplex()
    return {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "pyomo": pyomo.version.__version__,
        "highs": highs.version(),
        "gurobi": ".".join(str(item) for item in gurobipy.gurobi.version()),
        "cplex": cplex_runtime.get_version(),
        "xpress_optimizer": xpress.getVersion(),
    }


def _pyomo_interfaces() -> dict[str, list[dict[str, Any]]]:
    observed: dict[str, list[dict[str, Any]]] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for solver, names in _INTERFACES.items():
            rows = []
            for name in names:
                try:
                    interface = SolverFactory(name)
                    rows.append(
                        {
                            "name": name,
                            "available": bool(
                                interface.available(exception_flag=False)
                            ),
                            "implementation": (
                                f"{type(interface).__module__}."
                                f"{type(interface).__name__}"
                            ),
                            "error": None,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            "name": name,
                            "available": False,
                            "implementation": None,
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
            observed[solver] = rows
    return observed


def _distribution_file(package: str, suffix: str) -> Path | None:
    distribution = importlib.metadata.distribution(package)
    for relative in distribution.files or ():
        if str(relative).replace("\\", "/").endswith(suffix):
            return Path(distribution.locate_file(relative)).resolve()
    return None


def _first_existing_license_path(
    environment_name: str, candidates: tuple[Path, ...]
) -> tuple[str | None, str]:
    configured = os.environ.get(environment_name)
    if configured:
        return Path(configured).expanduser().resolve().as_posix(), environment_name
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve().as_posix(), "default_search_path"
    return None, "not_observed"


@lru_cache(maxsize=1)
def _gurobi_license_observation() -> dict[str, Any]:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import gurobipy as gp; model=gp.Model(); model.dispose()",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    banner = (probe.stdout + probe.stderr).strip()
    match = re.search(
        r"Restricted license - for non-production use only - expires "
        r"(\d{4}-\d{2}-\d{2})",
        banner,
    )
    home = Path.home()
    appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
    path, path_source = _first_existing_license_path(
        "GRB_LICENSE_FILE",
        (
            home / "gurobi.lic",
            appdata / "gurobi/gurobi.lic",
            Path("C:/gurobi/gurobi.lic"),
        ),
    )
    return {
        "classification": (
            "restricted_non_production" if match else "unclassified"
        ),
        "observable_evidence": "native_environment_initialization_banner",
        "banner": banner or None,
        "license_path": path,
        "license_path_source": path_source,
        "expiry": match.group(1) if match else None,
        "expiry_observed": bool(match),
        "probe_return_code": probe.returncode,
        "legal_conclusion": False,
    }


def _highs_license_observation() -> dict[str, Any]:
    metadata = importlib.metadata.metadata("highspy")
    license_path = _distribution_file(
        "highspy", "highspy-1.15.1.dist-info/licenses/LICENSE.txt"
    )
    return {
        "classification": "unrestricted_open_source",
        "observable_evidence": "package_metadata_license_expression",
        "license_expression": metadata.get("License-Expression"),
        "license_path": license_path.as_posix() if license_path else None,
        "license_path_source": "installed_distribution",
        "expiry": None,
        "expiry_observed": False,
        "legal_conclusion": False,
    }


def _cplex_license_observation() -> dict[str, Any]:
    metadata = importlib.metadata.metadata("cplex")
    summary = str(metadata.get("Summary", ""))
    home = Path.home()
    path, path_source = _first_existing_license_path(
        "ILOG_LICENSE_FILE", (home / "access.ilm",)
    )
    return {
        "classification": "community" if "Community Edition" in summary else "unclassified",
        "observable_evidence": "installed_package_metadata_summary",
        "package_summary": summary,
        "license_path": path,
        "license_path_source": path_source,
        "expiry": None,
        "expiry_observed": False,
        "legal_conclusion": False,
    }


@lru_cache(maxsize=1)
def _xpress_license_observation() -> dict[str, Any]:
    import xpress

    license_path = _distribution_file(
        "xpresslibs", "xpresslibs/bin/community-xpauth.xpr"
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        problem = xpress.problem()
        del problem
    messages = [str(item.message) for item in caught]
    community_warning = next(
        (message for message in messages if "Community license" in message), None
    )
    return {
        "classification": (
            "community"
            if license_path is not None and "community-xpauth.xpr" in license_path.name
            else "unclassified"
        ),
        "observable_evidence": "bundled_license_filename_and_runtime_warning",
        "runtime_warning": community_warning,
        "license_path": license_path.as_posix() if license_path else None,
        "license_path_source": "installed_xpresslibs_distribution",
        "expiry": None,
        "expiry_observed": False,
        "legal_conclusion": False,
    }


def _license_observations() -> dict[str, dict[str, Any]]:
    return {
        "highs": _highs_license_observation(),
        "gurobi": _gurobi_license_observation(),
        "cplex": _cplex_license_observation(),
        "xpress": _xpress_license_observation(),
    }


def _available(interface_rows: list[Mapping[str, Any]]) -> bool:
    return any(bool(row["available"]) for row in interface_rows)


def _capacity_reasons(solver: str, model_name: str) -> list[str]:
    size = _MODEL_SIZES[model_name]
    boundary = _CAPACITY_BOUNDARIES[solver]
    reasons = []
    if boundary["maximum_variables"] is not None and size["variables"] > int(
        boundary["maximum_variables"]
    ):
        reasons.append(
            f"variables_{size['variables']}_exceed_observed_limit_"
            f"{boundary['maximum_variables']}"
        )
    if boundary["maximum_constraints"] is not None and size["constraints"] > int(
        boundary["maximum_constraints"]
    ):
        reasons.append(
            f"constraints_{size['constraints']}_exceed_observed_limit_"
            f"{boundary['maximum_constraints']}"
        )
    combined_limit = boundary["maximum_rows_plus_columns"]
    if combined_limit is not None:
        combined = int(size["variables"]) + int(size["constraints"])
        if combined > int(combined_limit):
            reasons.append(
                f"rows_plus_columns_{combined}_exceed_observed_limit_"
                f"{combined_limit}"
            )
    return reasons


def _eligibility(
    interfaces: Mapping[str, list[Mapping[str, Any]]],
    licenses: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    result = {}
    for solver in _INTERFACES:
        interface_available = _available(list(interfaces[solver]))
        formal_reasons = _capacity_reasons(
            solver, "formal_24h_candidate_proxy_stage"
        )
        pilot_reasons = _capacity_reasons(
            solver, "solver_pilot_6h_candidate_proxy_stage"
        )
        if not interface_available:
            formal_reasons.append("no_available_pyomo_interface")
            pilot_reasons.append("no_available_pyomo_interface")
        if solver == "highs" and licenses[solver]["classification"] != (
            "unrestricted_open_source"
        ):
            formal_reasons.append("unrestricted_open_source_observation_missing")
            pilot_reasons.append("unrestricted_open_source_observation_missing")
        result[solver] = {
            "eligible_for_formal": not formal_reasons,
            "formal_ineligibility_reasons": formal_reasons,
            "eligible_for_6h_pilot": not pilot_reasons,
            "six_hour_ineligibility_reasons": pilot_reasons,
            "eligibility_scope": (
                "pyomo_interface_and_observed_software_license_capacity_only_"
                "not_runtime_or_legal_guarantee"
            ),
        }
    return result


def _build_inventory_payload() -> dict[str, Any]:
    interfaces = _pyomo_interfaces()
    licenses = _license_observations()
    return {
        "schema": "rts_gmlc_solver_inventory_v1",
        "status": "environment_inventory_completed_without_project_model_solve",
        "implementation_sha256": _sha256(_SCRIPT_PATH),
        "environment": {
            "python_executable": Path(sys.executable).resolve().as_posix(),
            "python_prefix": Path(sys.prefix).resolve().as_posix(),
            "platform": platform.platform(),
        },
        "package_versions": _package_versions(),
        "runtime_versions": _runtime_versions(),
        "pyomo_interfaces": interfaces,
        "license_observations": licenses,
        "license_observation_is_legal_conclusion": False,
        "capacity_boundaries": _CAPACITY_BOUNDARIES,
        "capacity_boundaries_retested_by_this_audit": False,
        "model_sizes": _MODEL_SIZES,
        "eligibility": _eligibility(interfaces, licenses),
        "project_model_built_or_solved": False,
        "formal_candidate_started": False,
    }


def _load_inventory(root: Path) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Solver inventory must contain a JSON object")
    return payload


def run(*, output_directory: Path | None = None) -> dict[str, Any]:
    target = output_directory or _OUTPUT_ROOT
    payload = _build_inventory_payload()
    if target.exists():
        observed = _load_inventory(target)
        if observed != _stable_json(payload):
            raise RuntimeError("Published solver inventory drifted from the environment")
        return observed

    def writer(staging: Path) -> None:
        _write_json(staging / "inventory.json", payload)

    _publish_payload(target, writer)
    return _load_inventory(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    result = run(output_directory=args.output_directory)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
