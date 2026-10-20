from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
LITERATURE_DIR = ROOT / "docs" / "literature"
ROADMAP = ROOT / "docs" / "plan" / "RQ2_论文路线图.md"
MIN_VERIFIED_DATE = date(2026, 8, 25)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_recent_academic_neighbors_are_unique_and_full_text_verified() -> None:
    _, rows = _read_csv(LITERATURE_DIR / "literature_matrix.csv")
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))

    by_id = {row["id"]: row for row in rows}
    expected = {
        "DC14": "https://arxiv.org/html/2602.01508",
        "DC15": "https://arxiv.org/html/2608.19622",
    }
    assert expected.keys() <= by_id.keys()
    for evidence_id, official_url in expected.items():
        row = by_id[evidence_id]
        assert row["核验层级"] == "F-全文筛选"
        assert row["DOI或URL"] == official_url
        assert date.fromisoformat(row["核验日期"]) >= MIN_VERIFIED_DATE
        assert row["与本项目的直接差异"].strip()


def test_contract_evidence_matrix_has_auditable_positive_and_negative_bounds() -> None:
    fields, rows = _read_csv(LITERATURE_DIR / "contract_evidence_matrix.csv")
    required_fields = {
        "id",
        "institutional_domain",
        "instrument",
        "issuer",
        "date",
        "jurisdiction_or_scope",
        "service_or_claim",
        "trigger_or_matching_rule",
        "physical_resource_boundary",
        "what_it_supports",
        "what_it_does_not_support",
        "verification_level",
        "official_url",
        "verified_date",
    }
    assert required_fields.issubset(fields)

    required_sources = {
        "REG01": (
            "Federal Energy Regulatory Commission",
            "https://www.ferc.gov/sites/default/files/2026-06/EL26-69-000.pdf",
        ),
        "CFE01": (
            "EnergyTag Ltd",
            "https://energytag.org/wp-content/uploads/2024/03/Granular-Certificate-Matching-Standard_V1.pdf",
        ),
        "CFE02": (
            "Google",
            "https://sustainability.google/reports/24x7-carbon-free-energy-methodologies-metrics/",
        ),
        "CFE03": (
            "Google",
            "https://sustainability.google/stories/24x7/",
        ),
    }
    ids = [row["id"] for row in rows]
    assert required_sources.keys() <= set(ids)
    assert len(ids) == len(set(ids))

    source_date = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
    verified_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for row in rows:
        support = row["what_it_supports"].strip()
        non_support = row["what_it_does_not_support"].strip()
        assert support
        assert non_support
        assert support != non_support
        assert row["verification_level"].startswith("P-官方")
        assert source_date.fullmatch(row["date"])
        assert verified_date.fullmatch(row["verified_date"])

        parsed = urlparse(row["official_url"])
        assert parsed.scheme == "https"
        assert parsed.netloc
        assert parsed.path not in {"", "/"}

    by_id = {row["id"]: row for row in rows}
    for evidence_id, (issuer, official_url) in required_sources.items():
        assert by_id[evidence_id]["issuer"] == issuer
        assert by_id[evidence_id]["official_url"] == official_url


def test_gap_and_roadmap_keep_hypothesis_and_negative_result_boundaries() -> None:
    gap = (LITERATURE_DIR / "research_gap.md").read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    combined = f"{gap}\n{roadmap}"

    assert "contract-overlap hypothesis" in gap
    assert "contract-overlap hypothesis" in roadmap
    assert "DC14" in gap and "DC15" in gap
    assert "what_it_does_not_support" in (
        LITERATURE_DIR / "search_protocol.md"
    ).read_text(encoding="utf-8")

    phase_map = "R1=0, R2=0, R3=69, mixed=1, unresolved=0"
    assert phase_map in gap
    assert phase_map in roadmap
    assert "original positive H2" in gap
    assert re.search(r"original positive\s+H2", roadmap)
    assert "formal_execution_ready=false" in gap
    assert "formal_execution_ready=false" in roadmap
    for boundary in ("LB_Δ>0", "LB_Δ<=0<UB_Δ", "UB_Δ<=0"):
        assert boundary in gap
        assert boundary in roadmap
    assert "预注册抽样总体" in combined
    assert "单个隔离案例" in combined

    assert "现实中数据中心的两类服务是**分开签约" not in combined
    dangerous_priority_claims = (
        r"(?:本文|本研究|本项目|RQ2).{0,30}(?:首次|率先)"
        r"(?:提出|建立|实现|建模|量化|识别|研究)",
        r"此前(?:没有|未有|无).{0,20}(?:研究|工作|文献)",
        r"RQ2.{0,20}(?:仍是|是).{0,20}(?:研究)?空白",
        r"\b(?:we|this (?:paper|study))\s+(?:are|is)\s+the\s+first\s+to\b",
        r"\bno\s+prior\s+(?:work|study|research)\b",
    )
    for pattern in dangerous_priority_claims:
        assert not re.search(pattern, combined, re.IGNORECASE | re.DOTALL)
