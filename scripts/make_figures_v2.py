#!/usr/bin/env python3
"""Redraw R12 result figures from the sealed run summary.

The summary is not stored in this public tree. From the repository root it
is the sibling file ../run/v1/results/summary.json. Numbers are read from
that file. Undefined perfect rates and correlations stay undefined.
"""
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_PATH = ROOT / ".." / "run" / "v1" / "results" / "summary.json"
SOURCE = "../run/v1/results/summary.json"
OUT = ROOT / "figures"

NAVY, ORANGE, GREEN, RED, GRAY = "#1f4e79", "#e07b39", "#3a9a5b", "#b23a48", "#6b7280"
C_LIMIT, L1_LIMIT, AUC_CHANGE = 0.02, 0.05, 0.01


def use_cjk():
    from matplotlib import font_manager

    listed = subprocess.check_output(["fc-list", "Noto Sans CJK SC", "file"], text=True)
    paths = [line.split(":")[0].strip() for line in listed.splitlines() if line.strip()]
    if not paths:
        raise SystemExit("Noto Sans CJK SC is not installed")
    for path in paths:
        font_manager.fontManager.addfont(path)
    plt.rcParams.update({
        "font.family": "Noto Sans CJK SC",
        "font.weight": "regular",
        "axes.titleweight": "regular",
        "axes.labelweight": "regular",
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#333333",
        "text.color": "#222222",
        "axes.labelcolor": "#222222",
        "xtick.color": "#222222",
        "ytick.color": "#222222",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 9,
    })


def strip_png_text(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a png: {path.name}")
    out = bytearray(data[:8])
    i = 8
    while i + 8 <= len(data):
        length = int.from_bytes(data[i:i + 4], "big")
        ctype = data[i + 4:i + 8]
        end = i + 12 + length
        if end > len(data):
            raise SystemExit(f"truncated png: {path.name}")
        if ctype not in (b"tEXt", b"iTXt", b"zTXt"):
            out += data[i:end]
        i = end
        if ctype == b"IEND":
            break
    Path(path).write_bytes(out)
    width = int.from_bytes(out[16:20], "big")
    if width != 1600:
        raise SystemExit(f"{path.name} width {width} != 1600")


def save_png(fig, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    strip_png_text(path)


def footer(fig, extra=""):
    text = f"数据来源 Source: {SOURCE}"
    if extra:
        text = extra + "\n" + text
    fig.text(0.01, 0.012, text, fontsize=7, color=GRAY, ha="left", va="bottom")


def load_summary():
    if not SUMMARY_PATH.is_file():
        raise SystemExit(f"missing data file: {SOURCE}")
    import json
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def fig_checks(summary):
    cells = summary["P2"]["cells"]
    by = {}
    for cell in cells:
        ok = (cell["complete"] and cell["C10k"] <= C_LIMIT and cell["C20k"] <= C_LIMIT
              and cell["L1"] <= L1_LIMIT and cell["auroc_change"] <= AUC_CHANGE)
        if ok != cell["passed"]:
            raise SystemExit(f"pass flag mismatch: {cell['model']} {cell['index']}")
        by[(cell["model"], cell["index"])] = cell
    for model in ("regular", "anti"):
        for index in range(16):
            if (model, index) not in by:
                raise SystemExit(f"missing Conf cell {model} {index}")

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.8), gridspec_kw={"height_ratios": [1.25, 1.05]})
    ax = axes[0]
    x = np.arange(16)
    width = 0.38
    regular = [by[("regular", i)]["C20k"] for i in range(16)]
    anti = [by[("anti", i)]["C20k"] for i in range(16)]
    ax.bar(x - width / 2, regular, width, color=NAVY, label="常规 regular")
    ax.bar(x + width / 2, anti, width, color=ORANGE, label="anti-IG")
    ax.axhline(C_LIMIT, color=RED, ls="--", lw=1, label="门槛 Threshold C = 0.02")
    ax.set_yscale("log")
    ax.set_ylim(1e-9, 5e-2)
    ax.set_xticks(x)
    ax.set_xlabel("分子编号 Molecule index")
    ax.set_ylabel("完整性残差 C（20,000 步）\nCompleteness residual C (20,000 steps)")
    ax.grid(axis="y", color="#e5e7eb")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=3, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.02))
    l1_max = max(cell["L1"] for cell in cells)
    da_max = max(cell["auroc_change"] for cell in cells)
    maxima = (f"max C20k 常规 {max(regular):.3g} / anti {max(anti):.3g}；"
              f"max L1 {l1_max:.3g}；max |ΔAUROC| {da_max:.3g}")

    ax2 = axes[1]
    gates = [
        ("C10k", lambda c: c["C10k"] <= C_LIMIT, "C 10k ≤ 0.02"),
        ("C20k", lambda c: c["C20k"] <= C_LIMIT, "C 20k ≤ 0.02"),
        ("L1", lambda c: c["L1"] <= L1_LIMIT, "L1 ≤ 0.05"),
        ("dAUC", lambda c: c["auroc_change"] <= AUC_CHANGE, "|ΔAUROC| ≤ 0.01"),
    ]
    models = (("regular", "常规"), ("anti", "anti"))
    grid = np.ones((8, 16))
    ylabels = []
    for mi, (model, mlabel) in enumerate(models):
        for gi, (_, pred, label) in enumerate(gates):
            row = mi * 4 + gi
            ylabels.append(f"{mlabel}  {label}")
            for index in range(16):
                grid[row, index] = 1.0 if pred(by[(model, index)]) else 0.0
    cmap = matplotlib.colors.ListedColormap([RED, GREEN])
    ax2.imshow(grid, aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
    ax2.set_xticks(range(16))
    ax2.set_yticks(range(8), ylabels, fontsize=7.5)
    ax2.set_xticks(np.arange(-0.5, 16, 1), minor=True)
    ax2.set_yticks(np.arange(-0.5, 8, 1), minor=True)
    ax2.grid(which="minor", color="white", lw=0.8)
    ax2.tick_params(which="minor", bottom=False, left=False)
    ax2.set_xlabel("分子编号 Molecule index")
    ax2.set_title("四个冻结门槛 × 两个模型  Four frozen gates × two models")
    for spine in ax2.spines.values():
        spine.set_visible(False)
    tech = summary["P2"]["technical_configurations"]
    failed_cfg = sum(item["F"] > 0 for item in tech)
    total_f = sum(item["F"] for item in tech)
    fig.suptitle("Conf 十六项技术检查：高步完整性（32/32 通过）\n"
                 "16-molecule technical checks: high-step completeness (32/32 passed)", fontsize=11, y=0.985)
    footer(fig, f"绿色 = 通过 Pass。{maxima}。{len(tech)} 个技术配置中 F>0 的个数 = {failed_cfg}，F 合计 = {total_f}。")
    fig.subplots_adjust(left=0.18, right=0.98, top=0.78, bottom=0.12, hspace=0.55)
    save_png(fig, OUT / "conf16_technical_checks.png")


def fig_alignment(summary):
    items = summary["P4"]
    perm = summary["permutation"]
    molecules = perm["molecules"]
    if len(molecules) != 16:
        raise SystemExit(f"expected 16 permutation rows, got {len(molecules)}")
    undefined = sum(row["rho"] is None for row in molecules)
    if undefined != perm["undefined"]:
        raise SystemExit("undefined rho count does not match the summary")
    agrees = sum(bool(row["classification_agrees"]) for row in molecules)

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 6.4), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    y = np.arange(len(items))
    fractions, colors = [], []
    for item in items:
        stats = item["statistics"]
        fractions.append(stats["finite"] / stats["expected"])
        colors.append(GREEN if item["status"] == "通过" else ORANGE if item["status"] == "队列未对齐" else RED)
    ax.barh(y, fractions, color=colors, height=0.72)
    for i, item in enumerate(items):
        stats = item["statistics"]
        ax.text(0.02, i, f"{stats['finite']}/{stats['expected']}", va="center", ha="left",
                color="white", fontsize=7.5)
    ax.set_yticks(y, [item["item"] for item in items], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("有限结果 / 固定分母 Finite / denominator")
    ax.set_title("八项发表队列 Eight publication cohorts")
    ax.grid(axis="x", color="#e5e7eb")
    ax.set_axisbelow(True)

    ax2 = axes[1]
    ax2.set_xlim(-0.6, 1.6)
    ax2.set_ylim(15.6, -0.6)
    for index, row in enumerate(molecules):
        rho_color = GRAY if row["rho"] is None else NAVY
        cls_color = GREEN if row["classification_agrees"] else RED
        ax2.add_patch(Rectangle((-0.42, index - 0.38), 0.84, 0.76, facecolor=rho_color, edgecolor="white", lw=0.6))
        ax2.add_patch(Rectangle((0.58, index - 0.38), 0.84, 0.76, facecolor=cls_color, edgecolor="white", lw=0.6))
    ax2.set_yticks(range(16), [str(i) for i in range(16)], fontsize=7)
    ax2.set_xticks([0, 1], ["Spearman ρ", "分类一致\nClass agrees"], fontsize=8)
    ax2.set_ylabel("分子编号 Molecule index")
    mean_rho = "未定义 undefined" if perm["mean_rho"] is None else f"{perm['mean_rho']:.3g}"
    ax2.set_title(f"置乱对照 Permutation\n平均 ρ mean ρ: {mean_rho}")
    for spine in ax2.spines.values():
        spine.set_visible(True)
        spine.set_color("#dddddd")
    ax2.tick_params(length=0)
    sentence = summary["permutation_sentence"]
    footer(fig, f"橙 = 队列未对齐 Not aligned；绿 = 通过 Pass。灰 = ρ 未定义 undefined；"
           f"红 = 分类不一致 disagrees。分类一致 {agrees}/16。{sentence}")
    fig.subplots_adjust(left=0.16, right=0.98, top=0.86, bottom=0.16, wspace=0.32)
    save_png(fig, OUT / "alignment_and_permutation.png")


def fig_perfect(summary):
    high = summary["P3"]["high"]
    low = summary["P3"]["low"]
    p5 = summary["P5_statistics"]
    for model in ("regular", "anti"):
        if low[model]["M"] is not None:
            raise SystemExit("low-step perfect rate is defined; this figure must be redrawn")
    if p5["ablation"]["M"] is not None or p5["anti"]["M"] is not None:
        raise SystemExit("P5 perfect rates are defined; this figure must be redrawn")
    if summary["P3"]["d50"] is not None:
        raise SystemExit("low-step gap d50 is defined; this figure must be redrawn")

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 5.8), gridspec_kw={"width_ratios": [1, 1.15]})
    ax = axes[0]
    labels, rates, colors, texts = [], [], [], []
    for model, color, name in (
        ("regular", NAVY, "常规 regular"),
        ("anti", ORANGE, "anti-IG"),
    ):
        block = high[model]["M"]
        labels.append(name)
        rates.append(block["perfect_rate"])
        colors.append(color)
        texts.append(f"{block['perfect_count']}/{block['denominator']}")
    xpos = np.arange(2)
    ax.bar(xpos, rates, color=colors, width=0.62)
    ax.axhline(0.95, color=RED, ls="--", lw=1)
    ax.set_ylim(0, 1.28)
    ax.set_xticks(xpos, labels)
    ax.set_ylabel("完美率 Perfect rate")
    ax.set_title("高步 Conf 轨道 M（N=16）\nHigh-step Conf, track M (N=16)")
    for x, rate, text in zip(xpos, rates, texts):
        ax.text(x, rate + 0.04, f"{rate:.3f}  {text}", ha="center", va="bottom", fontsize=8)
    gap = summary["P3"]["d20k_formatted"]

    def gate_word(value):
        if value is None:
            return "未定义"
        if value is True:
            return "达到"
        if value is False:
            return "未达到"
        return str(value)

    flags = [f"{key} {gate_word(summary['P3'][key])}" for key in ("B", "G", "A", "P3")]
    ax.text(1.0, 0.72, "落差 d20k\n" + gap + "\n" + "\n".join(flags),
            ha="center", va="top", fontsize=7.5, color="#222222")
    ax.text(1.58, 0.97, "门槛 0.95", color=RED, fontsize=7, ha="right", va="bottom")
    ax.set_xlim(-0.6, 1.6)

    ax2 = axes[1]
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")
    ax2.set_title("全队列消融完美率不可计算\nFull-cohort ablation rate is undefined")
    blocks = [
        (0.04, "完整 anti-IG\nFull anti-IG", p5["anti"]),
        (0.52, "消融 Ablation", p5["ablation"]),
    ]
    for x, title, block in blocks:
        ax2.add_patch(FancyBboxPatch((x, 0.46), 0.44, 0.42, boxstyle="round,pad=0.012,rounding_size=0.02",
                                      facecolor="#f7f8fa", edgecolor=NAVY, lw=1.1))
        ax2.text(x + 0.22, 0.82, title, ha="center", va="top", fontsize=9, color=NAVY)
        ax2.text(x + 0.22, 0.66,
                 f"有限调用 Finite calls\n{block['finite']}/{block['expected']}\n\n完美率 Perfect rate\n未定义 undefined",
                 ha="center", va="top", fontsize=8)
    ax2.annotate("", xy=(0.52, 0.67), xytext=(0.48, 0.67),
                 arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 1})
    ax2.text(0.5, 0.40, f"P5 状态 Status: {summary['P5']}", ha="center", va="top", fontsize=9, color=ORANGE)
    ax2.text(0.5, 0.30, "低步完美率与落差 d50 同样未定义。\nLow-step perfect rates and d50 are undefined too.",
             ha="center", va="top", fontsize=8)
    note = summary["P5_statistics"]["note"]
    ax2.text(0.5, 0.16, note, ha="center", va="top", fontsize=7.5, wrap=True)

    footer(fig, "左图不是消融对比。右图有限调用比例不是完美率。 The left panel is not the ablation contrast. "
           "A finite-call count is not a perfect rate.")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.12, wspace=0.18)
    save_png(fig, OUT / "perfect_rate_receptive_field.png")


def main():
    use_cjk()
    summary = load_summary()
    if summary.get("status") != "DONE":
        raise SystemExit(f"summary status is {summary.get('status')}, not DONE")
    fig_checks(summary)
    fig_alignment(summary)
    fig_perfect(summary)
    print("wrote figures/conf16_technical_checks.png")
    print("wrote figures/alignment_and_permutation.png")
    print("wrote figures/perfect_rate_receptive_field.png")


if __name__ == "__main__":
    main()
