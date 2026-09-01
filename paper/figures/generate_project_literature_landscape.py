# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a) literature-stream landscape -> cross-type inherit -> Sankey visual language/param inherit (no semantic production-script match)
# (b) bounded positioning matrix -> cross-type inherit -> Sankey visual language/param inherit (no semantic production-script match)
# (c) institutional-to-identification evidence chain -> cross-type inherit -> Sankey visual language/param inherit (no semantic production-script match)
# RULE: "native run" = load pre-rendered PNG via Image.open().ax.imshow().
#       "param inherit" = drawing function below that copies Class A/B/C values.
#       If a panel says "native run" and you write a drawing function, you broke the contract.

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,         # TrueType font embedding
    "svg.fonttype": "none",     # editable text in SVG
    "savefig.bbox": "tight",    # trim whitespace
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)


import argparse
from collections import OrderedDict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Bbox
from PIL import Image
from PIL.PngImagePlugin import PngInfo

WIDTH_MM = 183
HEIGHT_MM = 138
MM_TO_INCH = 1 / 25.4

# Parameters inherited from the Sankey production asset. Flow width is schematic,
# never proportional to publication counts or evidence strength.
SANKEY_LINK_ALPHA = 0.18
SANKEY_OUTCOME_ALPHA = 0.35
SANKEY_GAP = 0.012
SANKEY_NODE_THICKNESS_PX = 25
SANKEY_NODE_PAD_PX = 80

STREAMS = OrderedDict([
    ("interconnection", (1, 2, 3, 6)),
    ("workload", (5, 7, 13, 14, 15, 16, 17, 18, 19, 20)),
    ("coordination", (4, 26, 27, 28, 29, 30, 31)),
    ("tep", (8, 9, 10, 11, 12)),
    ("cfe", (21, 22, 23, 24, 25)),
])

EXPECTED_REFERENCES = tuple(range(1, 32))
FLAT_REFERENCES = tuple(ref for refs in STREAMS.values() for ref in refs)
assert len(FLAT_REFERENCES) == 31
assert len(set(FLAT_REFERENCES)) == 31
assert tuple(sorted(FLAT_REFERENCES)) == EXPECTED_REFERENCES

MATRIX = OrderedDict([
    ("interconnection", ("P", "S", "O", "O", "O")),
    ("workload", ("S", "P", "S", "O", "O")),
    ("coordination", ("S", "S", "P", "O", "O")),
    ("tep", ("P", "O", "S", "O", "O")),
    ("cfe", ("O", "S", "P", "O", "O")),
    ("project", ("S", "P", "P", "P", "P")),
])

TEXT = {
    "en": {
        "stream_labels": {
            "interconnection": "Flexible interconnection / grid capacity",
            "workload": "DR / carbon-aware computing / workload",
            "coordination": "Network-renewable coordination / deliverability",
            "tep": "Multistage TEP / robust planning",
            "cfe": "Annual/hourly CFE / clean computing",
        },
        "stream_refs": {
            "interconnection": "[1, 2, 3, 6]",
            "workload": "[5, 7, 13–20]",
            "coordination": "[4, 26–31]",
            "tep": "[8–12]",
            "cfe": "[21–25]",
        },
        "panel_a": "Reviewed literature landscape",
        "a_note": "n = 31 reviewed academic works · equal-width schematic bands, not bibliometric weights",
        "foundation": "Established\nbuilding blocks\nacross the reviewed set",
        "foundation_note": "All [1–31], once each",
        "panel_b": "Bounded positioning matrix",
        "columns": (
            "Grid access\n/ expansion",
            "24 h within-\nwindow envelope",
            "Network–CFE\ncoordination",
            "Separate\nobligations",
            "Marginal-only\nidentification",
        ),
        "row_labels": {
            "interconnection": "Flexible interconnection",
            "workload": "Workload flexibility",
            "coordination": "Network–renewable",
            "tep": "Multistage TEP",
            "cfe": "Hourly CFE",
            "project": "This project",
        },
        "matrix_note": "P primary   S supporting   ○ outside primary scope (not evidence of absence)",
        "panel_c": "Evidence and identification chain",
        "ferc": "FERC\nnetwork service",
        "cfe_source": "EnergyTag / Google\nhourly CFE",
        "objects_boundary": "Separate objects ≠ observed overlap",
        "hypothesis": "Falsifiable overlap hypothesis",
        "comparison": "Shared 24 h zero-carry-in envelope\ncorrect model  vs  B6",
        "holdout": "Frozen-policy holdout replay",
        "identification": "Conditional sharp bounds\nall-coupling sign · common witness",
        "states": "Current complete blocks: E0 | shortfall | unresolved\nFuture incomplete windows: right-censor",
    },
    "cn": {
        "stream_labels": {
            "interconnection": "灵活接入 / 电网容量",
            "workload": "需求响应 / 碳感知计算 / 工作负荷",
            "coordination": "网络—新能源协同 / 可交付性",
            "tep": "多阶段输电扩展 / 鲁棒规划",
            "cfe": "年度/小时CFE / 清洁计算",
        },
        "stream_refs": {
            "interconnection": "[1, 2, 3, 6]",
            "workload": "[5, 7, 13–20]",
            "coordination": "[4, 26–31]",
            "tep": "[8–12]",
            "cfe": "[21–25]",
        },
        "panel_a": "审阅文献的研究版图",
        "a_note": "n = 31篇审阅学术文献 · 等宽示意带不表示文献计量权重",
        "foundation": "审阅集合中已有的\n基础构件",
        "foundation_note": "[1–31]各出现一次",
        "panel_b": "有界研究定位矩阵",
        "columns": (
            "接入 / 扩建",
            "24h完整窗口内\n时序包络",
            "网络—CFE\n协同",
            "分离的\n制度义务",
            "仅有边缘时的\n部分识别",
        ),
        "row_labels": {
            "interconnection": "灵活接入",
            "workload": "工作负荷柔性",
            "coordination": "网络—新能源",
            "tep": "多阶段输电扩展",
            "cfe": "小时CFE",
            "project": "本项目",
        },
        "matrix_note": "P 主要范围   S 支撑范围   ○ 非主要范围（不表示不存在）",
        "panel_c": "证据与识别链",
        "ferc": "FERC\n网络条件服务",
        "cfe_source": "EnergyTag / Google\n小时CFE核算",
        "objects_boundary": "对象分别存在 ≠ 已观测到现实交叠",
        "hypothesis": "可证伪的 contract-overlap hypothesis",
        "comparison": "同一24h、zero-carry-in窗口内包络\ncorrect model  vs  B6反事实",
        "holdout": "冻结策略的 holdout 回放",
        "identification": "条件 sharp bounds\nall-coupling sign · 共同coupling见证",
        "states": "当前完整块：E0｜服务短缺｜unresolved\n未来不完整窗口：right-censor",
    },
}

STREAM_COLORS = {
    "interconnection": CATEGORICAL[0],
    "workload": CATEGORICAL[2],
    "coordination": CATEGORICAL[3],
    "tep": CATEGORICAL[4],
    "cfe": CATEGORICAL[0],
}

LIGHT = {
    CATEGORICAL[0]: "#E5EFF7",
    CATEGORICAL[2]: "#E7F1E9",
    CATEGORICAL[3]: "#FBEEDC",
    CATEGORICAL[4]: "#EFE6F2",
    ACCENT_RED: "#F7E3E3",
}


def _font_path(language):
    if language != "cn":
        return None
    candidates = (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for family in ("Source Han Sans CN", "Microsoft YaHei", "SimHei"):
        resolved = Path(fm.findfont(family, fallback_to_default=False))
        if resolved.exists():
            return resolved
    raise RuntimeError("No explicit CJK font is available for the Chinese figure.")


def _font(language, size=6, weight="normal"):
    path = _font_path(language)
    if path is not None:
        resolved_family = fm.FontProperties(fname=str(path)).get_name()
        return fm.FontProperties(family=resolved_family, fname=str(path), size=size, weight=weight)
    return fm.FontProperties(family="Arial", size=size, weight=weight)


def _text(ax, language, x, y, content, *, size=6, weight="normal", **kwargs):
    assert size >= 5
    return ax.text(
        x,
        y,
        content,
        fontproperties=_font(language, size=size, weight=weight),
        **kwargs,
    )


def _rounded_box(ax, x, y, width, height, *, face, edge, linewidth=0.65, radius=0.015):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=face,
        edgecolor=edge,
        linewidth=linewidth,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def _arrow(ax, start, end, *, color=GREY, linewidth=0.75, style="-|>"):
    arrow = FancyArrowPatch(
        start,
        end,
        transform=ax.transAxes,
        arrowstyle=style,
        mutation_scale=7,
        linewidth=linewidth,
        color=color,
        shrinkA=2,
        shrinkB=2,
        clip_on=False,
    )
    ax.add_patch(arrow)
    return arrow


def _routed_arrow(ax, points, *, color):
    """Route an evidence arrow around the central boundary annotation."""
    x_values = [point[0] for point in points[:-1]]
    y_values = [point[1] for point in points[:-1]]
    ax.plot(
        x_values,
        y_values,
        transform=ax.transAxes,
        color=color,
        linewidth=0.75,
        solid_capstyle="round",
        zorder=2,
        clip_on=False,
    )
    arrow = _arrow(ax, points[-2], points[-1], color=color)
    arrow.set_zorder(2)
    return arrow


def _flow(ax, start, end, *, color):
    x0, y0 = start
    x1, y1 = end
    dx = (x1 - x0) * 0.48
    path = MplPath(
        [(x0, y0), (x0 + dx, y0), (x1 - dx, y1), (x1, y1)],
        [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4],
    )
    patch = PathPatch(
        path,
        transform=ax.transAxes,
        fill=False,
        edgecolor=color,
        linewidth=8.0,
        alpha=SANKEY_LINK_ALPHA,
        capstyle="round",
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def _panel_header(ax, language, label, title):
    _text(ax, language, 0.002, 0.985, label, size=8.5, weight="bold", va="top")
    _text(ax, language, 0.065, 0.985, title, size=7.2, weight="bold", va="top")


def draw_literature_landscape(ax, language):
    strings = TEXT[language]
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _panel_header(ax, language, "(a)", strings["panel_a"])
    _text(ax, language, 0.040, 0.895, strings["a_note"], size=5.2, color="#555555", va="top")

    y_positions = (0.715, 0.570, 0.425, 0.280, 0.135)
    destination_y = (0.685, 0.565, 0.445, 0.325, 0.205)
    for (key, _refs), y, y_destination in zip(STREAMS.items(), y_positions, destination_y):
        color = STREAM_COLORS[key]
        _flow(ax, (0.602, y + 0.045), (0.735, y_destination), color=color)
        _rounded_box(ax, 0.025, y, 0.575, 0.095, face=LIGHT[color], edge=color)
        ax.add_patch(Rectangle(
            (0.025, y),
            0.010,
            0.095,
            transform=ax.transAxes,
            facecolor=color,
            edgecolor="none",
            clip_on=False,
        ))
        _text(
            ax,
            language,
            0.050,
            y + 0.061,
            strings["stream_labels"][key],
            size=6.0,
            weight="bold",
            va="center",
        )
        _text(
            ax,
            language,
            0.050,
            y + 0.025,
            strings["stream_refs"][key],
            size=5.3,
            color="#4A4A4A",
            va="center",
        )

    _rounded_box(ax, 0.740, 0.135, 0.235, 0.645, face="#F2F4F5", edge="#666666", linewidth=0.8)
    _text(
        ax,
        language,
        0.858,
        0.505,
        strings["foundation"],
        size=6.6,
        weight="bold",
        ha="center",
        va="center",
        linespacing=1.35,
    )
    _text(
        ax,
        language,
        0.858,
        0.235,
        strings["foundation_note"],
        size=5.2,
        color="#555555",
        ha="center",
        va="center",
    )


def draw_positioning_matrix(ax, language):
    strings = TEXT[language]
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _panel_header(ax, language, "(b)", strings["panel_b"])

    x0 = 0.335
    matrix_width = 0.655
    column_width = matrix_width / 5
    header_bottom = 0.745
    header_height = 0.135
    row_top = 0.720
    row_height = 0.095

    for column, label in enumerate(strings["columns"]):
        x = x0 + column * column_width
        _rounded_box(
            ax,
            x + 0.003,
            header_bottom,
            column_width - 0.006,
            header_height,
            face="#F1F3F5",
            edge="#B8BDC2",
            linewidth=0.5,
            radius=0.006,
        )
        _text(
            ax,
            language,
            x + column_width / 2,
            header_bottom + header_height / 2,
            label,
            size=5.0,
            weight="bold",
            ha="center",
            va="center",
            linespacing=1.12,
        )

    for row_index, (row_key, statuses) in enumerate(MATRIX.items()):
        y = row_top - (row_index + 1) * row_height
        is_project = row_key == "project"
        row_face = "#FFF9F9" if is_project else ("#FAFAFA" if row_index % 2 == 0 else "#FFFFFF")
        ax.add_patch(Rectangle(
            (0.005, y),
            0.985,
            row_height,
            transform=ax.transAxes,
            facecolor=row_face,
            edgecolor=ACCENT_RED if is_project else "#D2D5D8",
            linewidth=0.85 if is_project else 0.35,
            clip_on=False,
        ))
        _text(
            ax,
            language,
            0.020,
            y + row_height / 2,
            strings["row_labels"][row_key],
            size=5.5,
            weight="bold" if is_project else "normal",
            color=ACCENT_RED if is_project else BLACK,
            va="center",
        )
        for column, status in enumerate(statuses):
            cell_x = x0 + column * column_width
            accent_cell = is_project and column >= 3
            if accent_cell:
                face = LIGHT[ACCENT_RED]
                edge = ACCENT_RED
                text_color = ACCENT_RED
            elif status == "P":
                face = LIGHT[CATEGORICAL[0]]
                edge = CATEGORICAL[0]
                text_color = CATEGORICAL[0]
            elif status == "S":
                face = LIGHT[CATEGORICAL[2]]
                edge = CATEGORICAL[2]
                text_color = CATEGORICAL[2]
            else:
                face = "#F2F2F2"
                edge = "#C7C7C7"
                text_color = "#777777"
            _rounded_box(
                ax,
                cell_x + 0.024,
                y + 0.018,
                column_width - 0.048,
                row_height - 0.036,
                face=face,
                edge=edge,
                linewidth=0.55,
                radius=0.010,
            )
            _text(
                ax,
                language,
                cell_x + column_width / 2,
                y + row_height / 2,
                "○" if status == "O" else status,
                size=5.8,
                weight="bold" if status != "O" else "normal",
                color=text_color,
                ha="center",
                va="center",
            )

    _text(ax, language, 0.010, 0.045, strings["matrix_note"], size=5.0, color="#555555", va="bottom")


def draw_evidence_chain(ax, language):
    strings = TEXT[language]
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    _panel_header(ax, language, "(c)", strings["panel_c"])

    _rounded_box(ax, 0.025, 0.820, 0.455, 0.090, face=LIGHT[CATEGORICAL[0]], edge=CATEGORICAL[0])
    _rounded_box(ax, 0.520, 0.820, 0.455, 0.090, face=LIGHT[CATEGORICAL[3]], edge=CATEGORICAL[3])
    _text(ax, language, 0.252, 0.865, strings["ferc"], size=5.0, weight="bold", ha="center", va="center", linespacing=1.0)
    _text(ax, language, 0.748, 0.865, strings["cfe_source"], size=5.0, weight="bold", ha="center", va="center", linespacing=1.0)

    _rounded_box(ax, 0.140, 0.650, 0.720, 0.090, face=LIGHT[ACCENT_RED], edge=ACCENT_RED, linewidth=0.85)
    _text(ax, language, 0.500, 0.695, strings["hypothesis"], size=5.6, weight="bold", color=ACCENT_RED, ha="center", va="center")
    _routed_arrow(ax, ((0.120, 0.815), (0.120, 0.755), (0.260, 0.742)), color=CATEGORICAL[0])
    _routed_arrow(ax, ((0.880, 0.815), (0.880, 0.755), (0.740, 0.742)), color=CATEGORICAL[3])
    _text(
        ax,
        language,
        0.500,
        0.775,
        strings["objects_boundary"],
        size=5.0,
        color="#555555",
        ha="center",
        va="center",
        zorder=10,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2},
    )

    _arrow(ax, (0.500, 0.645), (0.500, 0.580), color="#666666")
    _rounded_box(ax, 0.100, 0.500, 0.800, 0.095, face=LIGHT[CATEGORICAL[0]], edge=CATEGORICAL[0])
    _text(ax, language, 0.500, 0.548, strings["comparison"], size=5.0, weight="bold", ha="center", va="center", linespacing=1.10)

    _arrow(ax, (0.500, 0.495), (0.500, 0.430), color="#666666")
    _rounded_box(ax, 0.180, 0.365, 0.640, 0.080, face="#F2F4F5", edge="#666666")
    _text(ax, language, 0.500, 0.405, strings["holdout"], size=5.4, weight="bold", ha="center", va="center")

    _arrow(ax, (0.500, 0.360), (0.500, 0.295), color="#666666")
    _rounded_box(ax, 0.100, 0.205, 0.800, 0.105, face=LIGHT[CATEGORICAL[2]], edge=CATEGORICAL[2])
    _text(ax, language, 0.500, 0.258, strings["identification"], size=5.0, weight="bold", ha="center", va="center", linespacing=1.02)

    _rounded_box(ax, 0.040, 0.055, 0.920, 0.085, face="#F3F3F3", edge="#888888", linewidth=0.55)
    _text(ax, language, 0.500, 0.097, strings["states"], size=5.0, color="#444444", ha="center", va="center")


def build_figure(language):
    if language not in TEXT:
        raise ValueError(f"Unsupported language: {language}")
    if language == "cn":
        _font_path(language)

    fig = plt.figure(figsize=(WIDTH_MM * MM_TO_INCH, HEIGHT_MM * MM_TO_INCH), facecolor="white")
    grid = fig.add_gridspec(
        2,
        2,
        left=0.025,
        right=0.985,
        bottom=0.025,
        top=0.985,
        wspace=0.095,
        hspace=0.125,
        width_ratios=(1.28, 0.92),
        height_ratios=(0.86, 1.04),
    )
    ax_a = fig.add_subplot(grid[0, :])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])

    draw_literature_landscape(ax_a, language)
    draw_positioning_matrix(ax_b, language)
    draw_evidence_chain(ax_c, language)
    return fig


def export_figure(fig, language, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / f"project_literature_landscape_{language}"
    svg_path = base.with_suffix(".svg")
    pdf_path = base.with_suffix(".pdf")
    png_path = base.with_suffix(".png")

    exact_bbox = Bbox.from_bounds(0, 0, WIDTH_MM * MM_TO_INCH, HEIGHT_MM * MM_TO_INCH)
    common = {"bbox_inches": exact_bbox, "pad_inches": 0, "facecolor": "white", "edgecolor": "none"}
    title = f"RQ2 literature landscape and identification chain ({language})"
    description = (
        "Conceptual evidence map generated from the 31-work review inventory; "
        "schematic bands are not bibliometric weights. Source script: "
        "paper/figures/generate_project_literature_landscape.py"
    )
    fig.savefig(
        svg_path,
        format="svg",
        metadata={"Title": title, "Description": description},
        **common,
    )
    fig.savefig(
        pdf_path,
        format="pdf",
        dpi=300,
        metadata={
            "Title": title,
            "Author": "Electricity-grid research project",
            "Subject": description,
            "Keywords": "literature landscape, partial identification, RQ2",
        },
        **common,
    )
    fig.savefig(png_path, format="png", dpi=300, **common)
    plt.close(fig)

    with Image.open(png_path) as image:
        rgb = image.convert("RGB")
        metadata = PngInfo()
        metadata.add_text("Title", title)
        metadata.add_text("Description", description)
        metadata.add_text("Software", "Matplotlib and Pillow")
        rgb.save(png_path, dpi=(300, 300), pnginfo=metadata)

    for path in (svg_path, pdf_path, png_path):
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"Export failed: {path}")
    return svg_path, pdf_path, png_path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate the bilingual RQ2 literature-positioning figure.")
    parser.add_argument("--lang", choices=("cn", "en", "all"), default="all")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    return parser.parse_args()


def main():
    args = parse_args()
    languages = ("cn", "en") if args.lang == "all" else (args.lang,)
    print("Validation: n=31 reviewed academic works; references 1..31 appear once across five streams.")
    print("Grouping source: project introductions section 2; institutional sources are separate.")
    print("Statistics: no sampling, tests, effect estimates, or error bars; this is not bibliometrics.")
    for language in languages:
        outputs = export_figure(build_figure(language), language, args.output_dir)
        print(f"Generated {language}: " + ", ".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
