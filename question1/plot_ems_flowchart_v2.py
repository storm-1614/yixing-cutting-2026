"""生成 EMS 算法迭代优化流程图 (基于用户图片结构)"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ── 全局样式 ──────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Source Han Sans CN", "Noto Sans CJK SC", "DejaVu Sans"],
    "font.size": 10,
    "axes.unicode_minus": False,
})

fig, ax = plt.subplots(1, 1, figsize=(18, 28))
ax.set_xlim(0, 18)
ax.set_ylim(0, 28)
ax.set_aspect("equal")
ax.axis("off")

# ── 调色板 ────────────────────────────────────────────────
C = {
    "bg":       "#F5F0E8",
    "start":    "#27AE60",
    "process":  "#3498DB",
    "decision": "#E67E22",
    "data":     "#9B59B6",
    "loop":     "#E74C3C",
    "sub":      "#16A085",
    "arrow":    "#555555",
    "highlight": "#F39C12",
}


def draw_rounded_box(ax, x, y, w, h, text, color, fontsize=10,
                     text_color="white", bold=False, radius=0.3, lw=1.5, alpha=1.0):
    """绘制圆角矩形"""
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius*10}",
        facecolor=color, edgecolor=color, linewidth=lw,
        alpha=alpha, zorder=3,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, weight=weight, zorder=4, linespacing=1.4)


def draw_arrow(ax, x1, y1, x2, y2, color=None, lw=1.8, style="->"):
    """绘制连接箭头"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color or C["arrow"],
                                lw=lw, connectionstyle="arc3,rad=0"))


def draw_diamond(ax, x, y, w, h, text, color, fontsize=9, text_color="white"):
    """绘制菱形判断节点"""
    pts = np.array([
        [x, y + h/2],
        [x + w/2, y],
        [x, y - h/2],
        [x - w/2, y],
    ])
    diamond = plt.Polygon(pts, facecolor=color, edgecolor=color, zorder=3)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, weight="bold", zorder=4, linespacing=1.3)


def draw_label(ax, x, y, text, fontsize=8, color=None, rotation=0, ha="center"):
    """边上标注"""
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize,
            color=color or C["arrow"], style="italic", rotation=rotation, zorder=5)


# ═══════════════════════════════════════════════════════════
#  标题
# ═══════════════════════════════════════════════════════════
ax.text(9, 27.2, "EMS (Empty Maximal Spaces) 算法流程图",
        ha="center", va="center", fontsize=20, weight="bold", color="#2C3E50")
ax.text(9, 26.6, "三维矩形装箱 · 贪心构造启发式 · 多策略迭代优化",
        ha="center", va="center", fontsize=11, color="#7F8C8D")

# 分隔线
ax.plot([2, 16], [26.2, 26.2], color="#BDC3C7", lw=1, ls="--")

# ═══════════════════════════════════════════════════════════
#  主流程 (y: 3.5 ~ 25.8)
# ═══════════════════════════════════════════════════════════

cx = 9  # 中心 x 坐标

# ── 开始 ──
draw_rounded_box(ax, cx, 25.6, 4.0, 0.7,
                 "START\n输入: 原材料块 ×100  工件类型 ×21",
                 C["start"], fontsize=9, bold=True)

draw_arrow(ax, cx, 25.25, cx, 24.6)

# ── Step 1: 零件体积排序 ──
draw_rounded_box(ax, cx, 24.2, 4.5, 0.7,
                 "零件体积排序\n按体积/底面积/最长边 降序排列",
                 C["process"], fontsize=9, bold=True)

draw_arrow(ax, cx, 23.85, cx, 23.2)

# ── Step 2: 排序后零件清单 ──
draw_rounded_box(ax, cx, 22.85, 5.0, 0.7,
                 "排序后零件清单\n21种工件 × 6姿态 × 80份 → 候选池",
                 C["data"], fontsize=8)

draw_arrow(ax, cx, 22.5, cx, 21.9)

# ── Step 3: 生成切割方案 ──
draw_rounded_box(ax, cx, 21.5, 4.5, 0.7,
                 "切割方案清单\nEMS Bin.pack() 贪心打包",
                 C["sub"], fontsize=9, bold=True)

draw_arrow(ax, cx, 21.15, cx, 20.5)

# ── Step 4: 匹配工件尺寸 ──
draw_rounded_box(ax, cx, 20.1, 5.5, 0.7,
                 "根据工件尺寸匹配零件体积\nBest-Fit: score = dx + dy + dz 最小",
                 C["highlight"], fontsize=8, bold=True)

draw_arrow(ax, cx, 19.75, cx, 19.1)

# ── Step 5: 方案清单 ──
draw_rounded_box(ax, cx, 18.75, 4.0, 0.7,
                 "方案清单\n记录已放置工件列表",
                 C["data"], fontsize=9)

draw_arrow(ax, cx, 18.4, cx, 17.8)

# ── Step 6: 计算体积匹配率 ──
draw_rounded_box(ax, cx, 17.4, 4.5, 0.7,
                 "计算体积匹配率\n利用率 = 已用体积 / 原材料体积",
                 C["process"], fontsize=8)

draw_arrow(ax, cx, 17.05, cx, 16.4)

# ── Step 7: 选择最优方案 ──
draw_rounded_box(ax, cx, 16.05, 4.5, 0.7,
                 "选择最优方案\n3种策略 (volume/footprint/longest) 择优",
                 C["highlight"], fontsize=8, bold=True)

draw_arrow(ax, cx, 15.7, cx, 15.1)

# ── Step 8: 终止条件判断 ──
draw_diamond(ax, cx, 14.5, 4.0, 1.2,
             "是否满足\n终止条件?", C["decision"], fontsize=10)

# ── Yes 分支 (右侧) ──
draw_label(ax, 11.3, 14.5, "Yes", fontsize=9, color=C["start"])
draw_arrow(ax, 11.0, 14.5, 13.5, 14.5)

draw_rounded_box(ax, 14.8, 14.5, 2.2, 0.6,
                 "输出最终方案", C["start"], fontsize=9, bold=True)

# ── No 分支 (下方) ──
draw_label(ax, cx, 13.8, "No", fontsize=9, color=C["loop"])
draw_arrow(ax, cx, 13.9, cx, 13.2)

# ── Step 9: 迭代优化 ──
draw_rounded_box(ax, cx, 12.8, 4.0, 0.7,
                 "迭代优化\n调整排序策略 / 缝隙填充 gap_fill()",
                 C["loop"], fontsize=9, bold=True)

# ── 反馈回路 (左侧回到 Step 1) ──
draw_arrow(ax, cx - 2.0, 12.8, 2.5, 12.8)
draw_arrow(ax, 2.5, 12.8, 2.5, 24.2)
draw_arrow(ax, 2.5, 24.2, cx - 2.25, 24.2)

# 反馈标注
ax.text(1.8, 18.5, "调整排序\n重新打包", fontsize=8, color=C["loop"],
        ha="center", va="center", style="italic", rotation=90, weight="bold")

# ── 最终输出区域 ──
draw_arrow(ax, 14.8, 14.2, 14.8, 13.5)
draw_arrow(ax, 14.8, 13.5, 14.8, 11.5)

draw_rounded_box(ax, cx, 11.0, 6.0, 0.8,
                 "汇总输出\n总利用率 / 废料体积 / 各工件生产数量",
                 "#2C3E50", fontsize=9, bold=True)

# ═══════════════════════════════════════════════════════════
#  左侧：多策略说明
# ═══════════════════════════════════════════════════════════
ax.text(3.0, 9.8, "三种排序策略", fontsize=10, weight="bold", color="#2C3E50")

strategies = [
    ("volume_desc", "体积降序 · 大件优先", "#3498DB"),
    ("footprint_desc", "底面积降序 · 稳底优先", "#27AE60"),
    ("longest_desc", "最长边降序 · 长件优先", "#9B59B6"),
]
for i, (name, desc, col) in enumerate(strategies):
    y_pos = 9.0 - i * 1.0
    draw_rounded_box(ax, 3.0, y_pos, 4.2, 0.8, f"{name}\n{desc}", col, fontsize=7.5)

# ═══════════════════════════════════════════════════════════
#  右侧：Best-Fit 评分细节
# ═══════════════════════════════════════════════════════════
ax.text(14.5, 9.8, "Best-Fit 评分", fontsize=10, weight="bold", color="#2C3E50")

draw_rounded_box(ax, 14.5, 8.4, 4.5, 2.0,
                 "score = (sp.dx - dx)\n      + (sp.dy - dy)\n      + (sp.dz - dz)\n\n三轴间隙和最小\n= 工件最贴合空间",
                 "#34495E", fontsize=8, radius=0.15)

# ═══════════════════════════════════════════════════════════
#  右下角：空间分裂示意
# ═══════════════════════════════════════════════════════════
ax.text(14.5, 6.5, "空间分裂 (Split)", fontsize=10, weight="bold", color="#2C3E50")

# 3D 示意图
rect = mpatches.Rectangle((12.5, 4.2), 4.0, 2.0, fill=False,
                           edgecolor="#2C3E50", lw=1.5, zorder=2)
ax.add_patch(rect)
ax.text(14.5, 6.4, "原材料", fontsize=8, ha="center", color="#2C3E50")

# 工件
item = mpatches.Rectangle((14.5, 4.5), 1.8, 1.2, fill=True,
                           facecolor="#E74C3C", alpha=0.4, edgecolor="#C0392B",
                           lw=1.5, zorder=3)
ax.add_patch(item)
ax.text(15.4, 5.1, "工件", fontsize=8, ha="center", color="#C0392B", weight="bold")

# 分裂方向
directions = [
    (14.5, 6.7, "上 ↑"),
    (16.7, 5.5, "右 →"),
    (14.5, 3.8, "下 ↓"),
    (12.0, 5.5, "← 左"),
]
for dx_, dy_, txt in directions:
    ax.text(dx_, dy_, txt, fontsize=7, color="#7F8C8D", ha="center", va="center")

# ═══════════════════════════════════════════════════════════
#  底部图例
# ═══════════════════════════════════════════════════════════
legend_y = 2.5
legend_items = [
    (C["process"], "流程处理"),
    (C["data"], "数据 I/O"),
    (C["highlight"], "核心步骤"),
    (C["decision"], "判断分支"),
    (C["loop"], "迭代优化"),
    (C["start"], "起止 / 输出"),
]
for i, (col, label) in enumerate(legend_items):
    lx = 2.0 + i * 2.5
    rect_leg = mpatches.Rectangle((lx, legend_y), 0.4, 0.4, facecolor=col,
                                   edgecolor=col, zorder=3)
    ax.add_patch(rect_leg)
    ax.text(lx + 0.55, legend_y + 0.2, label, fontsize=8, va="center", color="#555")

# ── 底部标注 ──
ax.text(9, 1.5, "子问题 1 · EMS 贪心构造启发式 · 3D 矩形装箱",
        ha="center", fontsize=9, color="#95A5A6", style="italic")
ax.text(9, 1.0, "多策略排序 + Best-Fit 评分 + 空间分裂/切除/合并 + 迭代优化",
        ha="center", fontsize=9, color="#95A5A6", style="italic")

# ── 保存 ──
fig.tight_layout(pad=0.5)
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_flowchart_v2.png",
            dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none")
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_flowchart_v2.pdf",
            bbox_inches="tight", facecolor="white", edgecolor="none")
print("✅ 已生成:")
print("   PNG: ems_flowchart_v2.png")
print("   PDF: ems_flowchart_v2.pdf")
