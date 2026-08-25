"""Render the RQ2 three-region benchmark as an SVG and Markdown table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from src.evaluation.rq2_phase_regions import (
    REGION_COMMON_INSUFFICIENCY,
    REGION_DOUBLE_COMMITMENT,
    REGION_MIXED,
    REGION_NO_CONFLICT,
    REGION_UNRESOLVED,
)

_ROOT = Path(__file__).resolve().parents[1]
_COLORS = {
    REGION_NO_CONFLICT: "#2E7D32",
    REGION_DOUBLE_COMMITMENT: "#C62828",
    REGION_COMMON_INSUFFICIENCY: "#EF6C00",
    REGION_MIXED: "#6A1B9A",
    REGION_UNRESOLVED: "#616161",
}
_LABELS = {
    REGION_NO_CONFLICT: "R1 No conflict",
    REGION_DOUBLE_COMMITMENT: "R2 Double commitment",
    REGION_COMMON_INSUFFICIENCY: "R3 Common insufficiency",
    REGION_MIXED: "Mixed",
    REGION_UNRESOLVED: "Unresolved",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("phase-map cell table is empty")
    return rows


def _primary_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    result = [
        row for row in rows if "primary_phase_surface" in row["families"].split("|")
    ]
    if not result:
        raise ValueError("primary phase surface is missing")
    return result


def _render_svg(rows: list[dict[str, str]], source_sha256: str) -> str:
    primary = _primary_rows(rows)
    alphas = sorted({float(row["hourly_cfe_target"]) for row in primary})
    thresholds = sorted(
        {
            (row["threshold_label"], float(row["network_activation_threshold"]))
            for row in primary
        },
        key=lambda item: item[1],
    )
    headrooms = sorted({float(row["business_recovery_headroom_mw"]) for row in primary})
    lookup = {
        (
            float(row["business_recovery_headroom_mw"]),
            float(row["hourly_cfe_target"]),
            row["threshold_label"],
        ): row
        for row in primary
    }
    if len(lookup) != len(headrooms) * len(alphas) * len(thresholds):
        raise ValueError("primary phase surface is incomplete or duplicated")

    width = 1160
    height = 550
    left = 95
    top = 100
    panel_width = 300
    cell = 58
    gap = 60
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        (
            '<text x="40" y="38" font-family="Arial" font-size="22" '
            'font-weight="700" fill="#111111">'
            "RQ2 three-region phase map</text>"
        ),
        (
            '<text x="40" y="64" font-family="Arial" font-size="12" '
            'fill="#444444">'
            f"Source cells SHA-256: {escape(source_sha256)}</text>"
        ),
    ]
    for panel_index, headroom in enumerate(headrooms):
        x0 = left + panel_index * (panel_width + gap)
        parts.append(
            f'<text x="{x0 + 115}" y="{top - 22}" text-anchor="middle" '
            'font-family="Arial" font-size="15" font-weight="700" '
            f'fill="#111111">Recovery headroom {headroom:g} MW</text>'
        )
        for row_index, (threshold_label, _) in enumerate(thresholds):
            y = top + row_index * cell
            parts.append(
                f'<text x="{x0 - 10}" y="{y + 35}" text-anchor="end" '
                'font-family="Arial" font-size="12" fill="#222222">'
                f"{escape(threshold_label)}</text>"
            )
            for column_index, alpha in enumerate(alphas):
                x = x0 + column_index * cell
                row = lookup[(headroom, alpha, threshold_label)]
                region = row["region"]
                color = _COLORS.get(region, "#000000")
                parts.extend(
                    [
                        (
                            f'<rect x="{x}" y="{y}" width="{cell - 4}" '
                            f'height="{cell - 4}" fill="{color}" '
                            'stroke="#ffffff" stroke-width="2"/>'
                        ),
                        (
                            f'<text x="{x + (cell - 4) / 2}" y="{y + 33}" '
                            'text-anchor="middle" font-family="Arial" '
                            'font-size="13" font-weight="700" fill="#ffffff">'
                            f"{escape(region.split('_', 1)[0])}</text>"
                        ),
                    ]
                )
        for column_index, alpha in enumerate(alphas):
            x = x0 + column_index * cell + (cell - 4) / 2
            parts.append(
                f'<text x="{x}" y="{top + len(thresholds) * cell + 18}" '
                'text-anchor="middle" font-family="Arial" font-size="12" '
                f'fill="#222222">{alpha:.2f}</text>'
            )
        parts.append(
            f'<text x="{x0 + 115}" '
            f'y="{top + len(thresholds) * cell + 42}" '
            'text-anchor="middle" font-family="Arial" font-size="13" '
            'fill="#222222">Hourly CFE target</text>'
        )
    legend_y = 440
    for index, region in enumerate(
        (
            REGION_NO_CONFLICT,
            REGION_DOUBLE_COMMITMENT,
            REGION_COMMON_INSUFFICIENCY,
            REGION_MIXED,
            REGION_UNRESOLVED,
        )
    ):
        x = 80 + index * 205
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="18" height="18" '
            f'fill="{_COLORS[region]}"/>'
        )
        parts.append(
            f'<text x="{x + 27}" y="{legend_y + 14}" '
            'font-family="Arial" font-size="12" fill="#222222">'
            f"{escape(_LABELS[region])}</text>"
        )
    parts.append(
        '<text x="40" y="515" font-family="Arial" font-size="11" '
        'fill="#555555">Derived benchmark; cell frequencies are not '
        "empirical probabilities or security certification.</text>"
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _render_table(rows: list[dict[str, str]], summary: dict) -> str:
    counts = summary["region_counts"]
    lines = [
        "# RQ2 Three-Region Phase-Map Summary",
        "",
        "| Region | Cells | Interpretation |",
        "|---|---:|---|",
    ]
    descriptions = summary["region_definitions"]
    for region in (
        REGION_NO_CONFLICT,
        REGION_DOUBLE_COMMITMENT,
        REGION_COMMON_INSUFFICIENCY,
        REGION_MIXED,
        REGION_UNRESOLVED,
    ):
        lines.append(
            f"| `{region}` | {counts.get(region, 0)} | {descriptions[region]} |"
        )
    scientific = [row for row in rows if row["scientific_region"] == "True"]
    lines.extend(
        [
            "",
            f"Published cells: {len(rows)}.",
            f"Scientifically classified cells: {len(scientific)}.",
            "",
            (
                "These counts describe the frozen benchmark grid and are not "
                "empirical probabilities."
            ),
        ]
    )
    mixed = [row for row in rows if row["region"] == REGION_MIXED]
    if mixed:
        lines.extend(
            [
                "",
                "## Mixed Cells",
                "",
                "| Cell | Correct MW | B6 MW | Delta failure | Delta shortfall (MWh) |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for row in mixed:
            lines.append(
                f"| `{row['cell_id']}` | "
                f"{float(row['correct_committed_flexibility_mw']):.4f} | "
                f"{float(row['b6_committed_flexibility_mw']):.4f} | "
                f"{float(row['delta_failure_probability']):.4f} | "
                f"{float(row['delta_expected_shortfall_mwh']):.4f} |"
            )
    return "\n".join(lines) + "\n"


def run(
    result_dir: Path,
    *,
    figure_path: Path,
    table_path: Path,
) -> dict[str, str]:
    manifest = json.loads((result_dir / "SHA256SUMS.json").read_text(encoding="utf-8"))
    for name, digest in manifest.items():
        if _sha256(result_dir / name) != digest:
            raise ValueError(f"phase-map result manifest drifted: {name}")
    rows = _load_rows(result_dir / "cells.csv")
    summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    figure_path.write_text(
        _render_svg(rows, _sha256(result_dir / "cells.csv")),
        encoding="utf-8",
    )
    table_path.write_text(_render_table(rows, summary), encoding="utf-8")
    return {
        "figure_sha256": _sha256(figure_path),
        "table_sha256": _sha256(table_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=Path("results/tables/rq2_three_region_phase_map_v1"),
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=Path("paper/figures/rq2_three_region_phase_map.svg"),
    )
    parser.add_argument(
        "--table",
        type=Path,
        default=Path("paper/tables/rq2_three_region_summary.md"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.result_dir,
                figure_path=args.figure,
                table_path=args.table,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
