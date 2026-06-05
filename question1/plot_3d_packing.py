"""子问题1: 3D装箱结果可视化 - 类似EMS.png风格"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
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


# 工件颜色映射 (按类型)
COLORS = {
    "J01": "#FF6B6B",   # 红
    "J02": "#4ECDC4",   # 青
    "J03": "#45B7D1",   # 蓝
    "J04": "#96CEB4",   # 绿
    "J05": "#FFEAA7",   # 黄
    "J06": "#DDA0DD",   # 紫
    "J07": "#98D8C8",   # 浅绿
}


def draw_box_3d(ax, x, y, z, dx, dy, dz, color, alpha=0.7, edgecolor="#333333"):
    """绘制3D长方体"""
    # 6个面的顶点
    vertices = [
        [[x, y, z], [x+dx, y, z], [x+dx, y+dy, z], [x, y+dy, z]],           # 底面
        [[x, y, z+dz], [x+dx, y, z+dz], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]], # 顶面
        [[x, y, z], [x+dx, y, z], [x+dx, y, z+dz], [x, y, z+dz]],           # 前面
        [[x, y+dy, z], [x+dx, y+dy, z], [x+dx, y+dy, z+dz], [x, y+dy, z+dz]], # 后面
        [[x, y, z], [x, y+dy, z], [x, y+dy, z+dz], [x, y, z+dz]],           # 左面
        [[x+dx, y, z], [x+dx, y+dy, z], [x+dx, y+dy, z+dz], [x+dx, y, z+dz]], # 右面
    ]
    faces = Poly3DCollection(vertices, alpha=alpha, facecolor=color,
                              edgecolor=edgecolor, linewidths=0.5)
    ax.add_collection3d(faces)


def solve_and_pack(block_name, L, W, H):
    """对单个原材料块进行打包"""
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

    return best_placed


def plot_single_block(block_idx, block_name, L, W, H, placed):
    """绘制单个原材料块的3D装箱图"""
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')

    # 绘制原材料边界框 (透明)
    draw_box_3d(ax, 0, 0, 0, L, W, H, "white", alpha=0.05, edgecolor="#333333")

    # 绘制所有工件
    for item in placed:
        base_type = item["type"].split("_")[0]
        color = COLORS.get(base_type, "#888888")
        draw_box_3d(ax, item["x"], item["y"], item["z"],
                    item["dx"], item["dy"], item["dz"],
                    color, alpha=0.85)

    # 设置坐标轴
    ax.set_xlabel("X (mm)", fontsize=10, labelpad=10)
    ax.set_ylabel("Y (mm)", fontsize=10, labelpad=10)
    ax.set_zlabel("Z - 切割深度 (mm)", fontsize=10, labelpad=10)
    ax.set_title(f"{block_name} ({L}×{W}×{H})\n{len(placed)} 件, 利用率: {sum(p['dx']*p['dy']*p['dz'] for p in placed)/(L*W*H)*100:.1f}%",
                 fontsize=12, fontweight='bold', pad=20)

    # 设置视角
    ax.view_init(elev=25, azim=-60)

    # 设置坐标范围
    ax.set_xlim(0, L)
    ax.set_ylim(0, W)
    ax.set_zlim(0, H)

    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = []
    used_types = set(item["type"].split("_")[0] for item in placed)
    for t in sorted(used_types):
        legend_elements.append(Patch(facecolor=COLORS.get(t, "#888888"),
                                     edgecolor="#333333", label=t))
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9)

    plt.tight_layout()
    return fig


def plot_multiple_blocks(blocks_data, figsize=(20, 12)):
    """绘制多个原材料块的组合图"""
    n = len(blocks_data)
    cols = min(3, n)
    rows = (n + cols - 1) // cols

    fig = plt.figure(figsize=figsize)

    for idx, (block_name, L, W, H, placed) in enumerate(blocks_data):
        ax = fig.add_subplot(rows, cols, idx + 1, projection='3d')

        # 绘制原材料边界框
        draw_box_3d(ax, 0, 0, 0, L, W, H, "white", alpha=0.05, edgecolor="#333333")

        # 绘制工件
        for item in placed:
            base_type = item["type"].split("_")[0]
            color = COLORS.get(base_type, "#888888")
            draw_box_3d(ax, item["x"], item["y"], item["z"],
                        item["dx"], item["dy"], item["dz"],
                        color, alpha=0.85)

        # 设置坐标轴
        ax.set_xlabel("X", fontsize=8, labelpad=5)
        ax.set_ylabel("Y", fontsize=8, labelpad=5)
        ax.set_zlabel("Z", fontsize=8, labelpad=5)
        util = sum(p['dx']*p['dy']*p['dz'] for p in placed)/(L*W*H)*100
        ax.set_title(f"{block_name}\n{len(placed)} 件, {util:.1f}%", fontsize=9, fontweight='bold')

        ax.view_init(elev=25, azim=-60)
        ax.set_xlim(0, L)
        ax.set_ylim(0, W)
        ax.set_zlim(0, H)
        ax.tick_params(labelsize=7)

    # 全局图例
    from matplotlib.patches import Patch
    all_types = set()
    for _, _, _, _, placed in blocks_data:
        for item in placed:
            all_types.add(item["type"].split("_")[0])
    legend_elements = [Patch(facecolor=COLORS.get(t, "#888888"),
                             edgecolor="#333333", label=t) for t in sorted(all_types)]
    fig.legend(handles=legend_elements, loc='lower center', ncol=len(all_types),
              fontsize=10, bbox_to_anchor=(0.5, 0.02))

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    return fig


def main():
    """主函数: 生成子问题1的3D装箱可视化"""
    print("正在求解子问题1...")

    # 求解所有原材料块
    blocks_data = []
    for name, L, W, H, qty in RAW_MATERIALS:
        for i in range(qty):
            block_name = f"{name}_{i+1}"
            placed = solve_and_pack(block_name, L, W, H)
            blocks_data.append((block_name, L, W, H, placed))
            print(f"  {block_name}: {len(placed)} 件")

    # 1. 绘制每种原材料类型的代表块
    print("\n生成单块3D图...")
    type_examples = {}
    for block_name, L, W, H, placed in blocks_data:
        base_type = block_name.split("_")[0]
        if base_type not in type_examples:
            type_examples[base_type] = (block_name, L, W, H, placed)

    for base_type, (block_name, L, W, H, placed) in type_examples.items():
        fig = plot_single_block(0, block_name, L, W, H, placed)
        fig.savefig(f"/data/project/yixing-cutting-2026/question1/packing_3d_{base_type}.png",
                    dpi=200, bbox_inches='tight', facecolor='white')
        fig.savefig(f"/data/project/yixing-cutting-2026/question1/packing_3d_{base_type}.pdf",
                    bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"  已保存: packing_3d_{base_type}.png/pdf")

    # 2. 绘制组合图 (每种类型选一块)
    print("\n生成组合3D图...")
    combo_data = [type_examples[t] for t in sorted(type_examples.keys())]
    fig = plot_multiple_blocks(combo_data, figsize=(18, 8))
    fig.savefig("/data/project/yixing-cutting-2026/question1/packing_3d_combined.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    fig.savefig("/data/project/yixing-cutting-2026/question1/packing_3d_combined.pdf",
                bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: packing_3d_combined.png/pdf")

    # 3. 绘制L01详细图 (100%利用率的特殊案例)
    print("\n生成L01详细3D图 (100%利用率)...")
    l01_data = [d for d in blocks_data if d[0].startswith("L01")]
    fig = plot_multiple_blocks(l01_data[:3], figsize=(18, 7))
    fig.suptitle("L01型原材料 (300×200×150) - 100%利用率", fontsize=14, fontweight='bold', y=1.02)
    fig.savefig("/data/project/yixing-cutting-2026/question1/packing_3d_L01_detail.png",
                dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print("  已保存: packing_3d_L01_detail.png")

    print("\n✅ 所有3D可视化图表已生成!")


if __name__ == "__main__":
    main()
