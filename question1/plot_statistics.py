"""子问题1: 统计图表生成 - 适合论文使用"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from data import RAW_MATERIALS, WORKPIECES
from ems import EMSBin, create_candidates, SORT_STRATEGIES


# 全局样式 - 思源黑体
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Source Han Sans CN", "思源黑体 CN", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "axes.unicode_minus": False,
})

# 颜色方案
COLORS = {
    "L01": "#3498DB",  # 蓝
    "L02": "#2ECC71",  # 绿
    "L03": "#E74C3C",  # 红
}
WORKPIECE_COLORS = ["#3498DB", "#2ECC71", "#E74C3C", "#F39C12", "#9B59B6", "#1ABC9C", "#34495E"]


def solve_subproblem1():
    """求解子问题1并返回详细结果"""
    blocks = []
    for name, L, W, H, qty in RAW_MATERIALS:
        for i in range(qty):
            blocks.append((f"{name}_{i + 1}", L, W, H))

    results = []
    all_placed = []

    for block_name, L, W, H in blocks:
        candidates = create_candidates(
            [(name, l, w, h, _) for name, l, w, h, _ in WORKPIECES],
            with_orientations=True,
        )
        pool = []
        for c in candidates:
            pool.extend([c] * 80)

        best_placed = []
        best_vol = 0

        for strat_name, sort_fn in SORT_STRATEGIES:
            bin_ = EMSBin(block_name, L, W, H)
            sorted_items = sort_fn(list(pool))
            placed = bin_.pack(sorted_items)
            used = sum(p["dx"] * p["dy"] * p["dz"] for p in placed)
            if used > best_vol:
                best_vol = used
                best_placed = placed

        results.append({
            "block": block_name,
            "type": block_name.split("_")[0],
            "L": L, "W": W, "H": H,
            "placed": best_placed,
            "count": len(best_placed),
            "used_vol": best_vol,
            "total_vol": L * W * H,
        })
        all_placed.extend(best_placed)

    return results, all_placed


def plot_utilization_comparison(results):
    """各原材料块利用率对比柱状图"""
    fig, ax = plt.subplots(figsize=(10, 6))

    block_names = [r["block"] for r in results]
    utilizations = [r["used_vol"] / r["total_vol"] * 100 for r in results]
    types = [r["type"] for r in results]
    colors = [COLORS[t] for t in types]

    bars = ax.bar(range(len(block_names)), utilizations, color=colors, edgecolor='white', linewidth=0.5)

    # 添加数值标签
    for bar, util in zip(bars, utilizations):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{util:.1f}%', ha='center', va='bottom', fontsize=8)

    ax.set_xlabel("原材料块", fontsize=11)
    ax.set_ylabel("利用率 (%)", fontsize=11)
    ax.set_title("各原材料块利用率对比", fontsize=13, fontweight='bold')
    ax.set_xticks(range(len(block_names)))
    ax.set_xticklabels(block_names, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(90, 102)
    ax.axhline(y=98.28, color='red', linestyle='--', linewidth=1, label='总体: 98.28%')
    ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_utilization_comparison.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_utilization_comparison.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: fig_utilization_comparison.png/pdf")


def plot_type_utilization(results):
    """按原材料类型的平均利用率"""
    fig, ax = plt.subplots(figsize=(8, 6))

    type_data = {}
    for r in results:
        t = r["type"]
        if t not in type_data:
            type_data[t] = {"utils": [], "dims": []}
        type_data[t]["utils"].append(r["used_vol"] / r["total_vol"] * 100)
        type_data[t]["dims"].append(f"{r['L']}×{r['W']}×{r['H']}")

    types = sorted(type_data.keys())
    avg_utils = [np.mean(type_data[t]["utils"]) for t in types]
    dims = [type_data[t]["dims"][0] for t in types]
    colors = [COLORS[t] for t in types]

    bars = ax.bar(types, avg_utils, color=colors, edgecolor='white', linewidth=0.5, width=0.6)

    for bar, util, dim in zip(bars, avg_utils, dims):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{util:.2f}%\n({dim})', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel("原材料类型", fontsize=11)
    ax.set_ylabel("平均利用率 (%)", fontsize=11)
    ax.set_title("按原材料类型的平均利用率", fontsize=13, fontweight='bold')
    ax.set_ylim(94, 102)

    plt.tight_layout()
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_type_utilization.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_type_utilization.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: fig_type_utilization.png/pdf")


def plot_workpiece_distribution(all_placed):
    """工件类型分布饼图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 左: 数量分布
    type_counts = Counter()
    for p in all_placed:
        base_type = p["type"].split("_")[0]
        type_counts[base_type] += 1

    types = sorted(type_counts.keys())
    counts = [type_counts[t] for t in types]

    wedges, texts, autotexts = ax1.pie(counts, labels=types, autopct='%1.1f%%',
                                        colors=WORKPIECE_COLORS[:len(types)],
                                        startangle=90, pctdistance=0.85)
    ax1.set_title("工件数量分布", fontsize=12, fontweight='bold')

    # 右: 体积分布
    type_volumes = {}
    for p in all_placed:
        base_type = p["type"].split("_")[0]
        vol = p["dx"] * p["dy"] * p["dz"]
        type_volumes[base_type] = type_volumes.get(base_type, 0) + vol

    vol_types = sorted(type_volumes.keys())
    volumes = [type_volumes[t] for t in vol_types]

    wedges2, texts2, autotexts2 = ax2.pie(volumes, labels=vol_types, autopct='%1.1f%%',
                                           colors=WORKPIECE_COLORS[:len(vol_types)],
                                           startangle=90, pctdistance=0.85)
    ax2.set_title("工件体积分布", fontsize=12, fontweight='bold')

    plt.tight_layout()
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_workpiece_distribution.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_workpiece_distribution.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: fig_workpiece_distribution.png/pdf")


def plot_volume_breakdown(results):
    """体积分解堆叠图"""
    fig, ax = plt.subplots(figsize=(10, 6))

    block_names = [r["block"] for r in results]
    used_vols = [r["used_vol"] / 1e6 for r in results]  # 转换为 mm³ × 10⁶
    waste_vols = [(r["total_vol"] - r["used_vol"]) / 1e6 for r in results]

    x = np.arange(len(block_names))
    width = 0.7

    bars1 = ax.bar(x, used_vols, width, label='已用体积', color='#2ECC71', edgecolor='white')
    bars2 = ax.bar(x, waste_vols, width, bottom=used_vols, label='废料体积', color='#E74C3C', edgecolor='white')

    ax.set_xlabel("原材料块", fontsize=11)
    ax.set_ylabel("体积 (×10⁶ mm³)", fontsize=11)
    ax.set_title("体积使用与废料分析", fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(block_names, rotation=45, ha='right', fontsize=9)
    ax.legend(fontsize=10)

    # 添加利用率标签
    for i, r in enumerate(results):
        util = r["used_vol"] / r["total_vol"] * 100
        ax.text(i, r["total_vol"] / 1e6 + 0.1, f'{util:.1f}%',
                ha='center', va='bottom', fontsize=8, color='#333')

    plt.tight_layout()
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_volume_breakdown.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_volume_breakdown.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: fig_volume_breakdown.png/pdf")


def plot_efficiency_summary(results, all_placed):
    """综合效率汇总表"""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.axis('off')

    # 准备数据
    total_volume = sum(r["total_vol"] for r in results)
    total_used = sum(r["used_vol"] for r in results)
    total_count = len(all_placed)
    overall_util = total_used / total_volume * 100

    type_counts = Counter()
    type_volumes = {}
    for p in all_placed:
        base_type = p["type"].split("_")[0]
        type_counts[base_type] += 1
        vol = p["dx"] * p["dy"] * p["dz"]
        type_volumes[base_type] = type_volumes.get(base_type, 0) + vol

    # 表格数据
    table_data = [
        ["指标", "数值"],
        ["原材料总体积", f"{total_volume:,} mm³"],
        ["已使用体积", f"{total_used:,} mm³"],
        ["废料体积", f"{total_volume - total_used:,} mm³"],
        ["总体积利用率", f"{overall_util:.2f}%"],
        ["总工件数", f"{total_count}"],
        ["原材料块数", f"{len(results)}"],
    ]

    # 添加各类型工件统计
    for t in sorted(type_counts.keys()):
        table_data.append([f"{t} 数量", f"{type_counts[t]}"])
        table_data.append([f"{t} 体积", f"{type_volumes[t]:,} mm³"])

    table = ax.table(cellText=table_data, colLoc='center', cellLoc='center',
                     loc='center', colWidths=[0.4, 0.4])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # 设置表头样式
    for j in range(2):
        table[0, j].set_facecolor('#3498DB')
        table[0, j].set_text_props(color='white', fontweight='bold')

    # 设置交替行颜色
    for i in range(1, len(table_data)):
        for j in range(2):
            if i % 2 == 0:
                table[i, j].set_facecolor('#F0F0F0')

    ax.set_title("子问题1 - 汇总统计", fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_summary_table.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/fig_summary_table.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: fig_summary_table.png/pdf")


def main():
    """主函数"""
    print("=" * 50)
    print("子问题1 统计图表生成")
    print("=" * 50)

    print("\n正在求解...")
    results, all_placed = solve_subproblem1()

    print("\n生成图表...")
    plot_utilization_comparison(results)
    plot_type_utilization(results)
    plot_workpiece_distribution(all_placed)
    plot_volume_breakdown(results)
    plot_efficiency_summary(results, all_placed)

    print("\n" + "=" * 50)
    print("✅ 所有统计图表已生成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
