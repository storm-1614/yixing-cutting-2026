"""用 matplotlib 生成 EMS 算法执行流程实力图"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc
import numpy as np

# ── 全局样式 ──────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Source Han Sans CN", "Noto Sans CJK SC", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 14,
    "axes.labelsize": 11,
    "axes.unicode_minus": False,  # 用 ASCII hyphen 代替 Unicode minus
})

fig, ax = plt.subplots(1, 1, figsize=(24, 32))
ax.set_xlim(0, 24)
ax.set_ylim(0, 32)
ax.set_aspect("equal")
ax.axis("off")

# ── 调色板 ────────────────────────────────────────────────
C = {
    "bg":       "#F5F0E8",   # 暖米色背景
    "title":    "#2C3E50",
    "start":    "#27AE60",
    "end":      "#E74C3C",
    "loop":     "#2980B9",
    "decision": "#E67E22",
    "process":  "#8E44AD",
    "sub":      "#16A085",
    "data":     "#7F8C8D",
    "arrow":    "#555555",
    "box_text": "#FFFFFF",
    "highlight":"#F39C12",
}

def draw_box(ax, x, y, w, h, text, color, fontsize=9, text_color="white",
             bold=False, alpha=1.0, edgecolor=None, lw=1.5, radius=0.15):
    """绘制圆角矩形框"""
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius*10}",
        facecolor=color, edgecolor=edgecolor or color, linewidth=lw,
        alpha=alpha, zorder=3,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, weight=weight, zorder=4)


def draw_arrow(ax, x1, y1, x2, y2, color=None, lw=1.8, style="->"):
    """绘制连接箭头"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color or C["arrow"],
                                lw=lw, connectionstyle="arc3,rad=0"))


def draw_diamond(ax, x, y, w, h, text, color, fontsize=8, text_color="white"):
    """绘制菱形（判断节点）"""
    pts = np.array([
        [x, y + h/2],
        [x + w/2, y],
        [x, y - h/2],
        [x - w/2, y],
    ])
    diamond = plt.Polygon(pts, facecolor=color, edgecolor=color, zorder=3)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, weight="bold", zorder=4)


def draw_label(ax, x, y, text, fontsize=8, color=None, rotation=0):
    """边上的标注文字"""
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=color or C["arrow"], style="italic", rotation=rotation, zorder=2)


# ═══════════════════════════════════════════════════════════
#  标题
# ═══════════════════════════════════════════════════════════
ax.text(12, 31.2, "EMS (Empty Maximal Spaces) 算法流程图",
        ha="center", va="center", fontsize=22, weight="bold", color=C["title"])
ax.text(12, 30.4, "三维矩形装箱 · 贪心构造启发式 · 多策略择优",
        ha="center", va="center", fontsize=12, color="#7F8C8D")

# ── 分隔线 ──
ax.plot([2, 22], [30.0, 30.0], color="#BDC3C7", lw=1, ls="--")

# ═══════════════════════════════════════════════════════════
#  上半部分：solve_subproblem1 外层流程 (y: 24–29.5)
# ═══════════════════════════════════════════════════════════
ax.text(12, 29.5, "外层求解流程 (solve1.py)", ha="center", va="center",
        fontsize=13, weight="bold", color=C["title"])

# 开始
draw_box(ax, 12, 28.6, 3.0, 0.8, "START\n输入: 原材料块 ×100\n      工件类型 ×21", C["start"], fontsize=8)

draw_arrow(ax, 12, 28.2, 12, 27.6)

# 遍历每块原材料
draw_box(ax, 12, 27.3, 3.8, 0.7, "遍历每块原材料 block", C["loop"], fontsize=9)
draw_label(ax, 14.3, 27.3, "100 块", fontsize=7)

draw_arrow(ax, 12, 26.95, 12, 26.4)

# 候选池生成
draw_box(ax, 12, 26.1, 4.2, 0.7, "生成候选池\n21 种工件 × 6 姿态 × 80 份", C["data"], fontsize=8)

draw_arrow(ax, 12, 25.75, 12, 25.2)

# 多策略循环
draw_box(ax, 12, 24.9, 4.5, 0.7, "尝试 3 种排序策略\nvolume / footprint / longest", C["loop"], fontsize=8)

draw_arrow(ax, 12, 24.55, 12, 24.1)

# 调用 pack → 核心 EMS
draw_box(ax, 12, 23.8, 4.0, 0.7, "EMSBin.pack(sorted_items)\n→ 核心 EMS 打包", C["highlight"], fontsize=9, bold=True)

draw_arrow(ax, 12, 23.45, 12, 23.0)

# 择优
draw_diamond(ax, 12, 22.6, 3.5, 1.0, "利用率\n> 历史最优?", C["decision"], fontsize=8)

# Yes →
draw_label(ax, 14.2, 22.6, "Yes", fontsize=7, color=C["start"])
draw_arrow(ax, 13.75, 22.6, 16.5, 22.6)

draw_box(ax, 18.5, 22.6, 2.8, 0.7, "记录最优方案", C["process"], fontsize=8, alpha=0.85)

# 回到多策略
draw_arrow(ax, 18.5, 22.25, 18.5, 21.0)
draw_arrow(ax, 18.5, 21.0, 12, 21.0)
draw_arrow(ax, 12, 21.0, 12, 22.1)

# No →
draw_label(ax, 12, 22.1, "No / 下一策略", fontsize=7)

draw_arrow(ax, 12, 22.1, 12, 21.0)

# 多策略结束 → 下一块 循环
draw_arrow(ax, 9.5, 22.6, 5.0, 22.6)
draw_arrow(ax, 5.0, 22.6, 5.0, 27.3)
draw_arrow(ax, 5.0, 27.3, 10.1, 27.3)
draw_label(ax, 4.5, 25.0, "下一块", fontsize=8, rotation=90)

# 汇总输出
draw_arrow(ax, 12, 19.5, 12, 19.0)
draw_box(ax, 12, 18.7, 4.5, 0.7, "汇总: 总利用率 / 废料体积\n      各工件生产数量", C["end"], fontsize=8, bold=True)

# ═══════════════════════════════════════════════════════════
#  大括号连接线 (外层 → 核心)
# ═══════════════════════════════════════════════════════════
ax.annotate("", xy=(12, 19.8), xytext=(12, 23.1),
            arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=2.5,
                           connectionstyle="arc3,rad=0"))
ax.text(13.2, 21.5, "每次调用 pack()\n触发核心 EMS 循环",
        fontsize=9, color="#E74C3C", weight="bold")

# ── 分隔线 ──
ax.plot([2, 22], [18.2, 18.2], color="#BDC3C7", lw=1.5, ls="-")
ax.text(12, 17.9, "核心 EMS 算法 —— EMSBin.pack() 单次打包流程",
        ha="center", va="center", fontsize=13, weight="bold", color=C["title"])

# ═══════════════════════════════════════════════════════════
#  下半部分：核心 EMS 算法 (y: 1–17.5)
# ═══════════════════════════════════════════════════════════

# 入参
draw_box(ax, 12, 17.3, 4.5, 0.6, "输入: sorted_items (已排序候选工件列表)", C["data"], fontsize=8)

draw_arrow(ax, 12, 17.0, 12, 16.4)

# 初始化
draw_box(ax, 12, 16.1, 5.5, 0.7,
         "初始化\nspaces = [Space(0,0,0, L,W,H)]  # 整个原材料\nplaced = []  ;  remaining = list(items)",
         C["process"], fontsize=7.5)

draw_arrow(ax, 12, 15.75, 12, 15.1)

# 主循环 While remaining
draw_box(ax, 12, 14.8, 3.5, 0.7, "WHILE remaining\n不为空", C["loop"], fontsize=9, bold=True)

draw_arrow(ax, 12, 14.45, 12, 13.8)

# ── 步骤 1: Best-Fit 选择 ──
draw_box(ax, 12, 13.45, 6.5, 0.8,
         "步骤1: Best-Fit 贪心选择\n遍历 remaining × spaces, 计算 score = Σ(space.d-item.d)\n选 score 最小的 (工件, 空间) 组合",
         C["highlight"], fontsize=8, bold=True, lw=2.5)

draw_arrow(ax, 12, 13.05, 12, 12.5)

# 判断: 找到可行组合?
draw_diamond(ax, 12, 12.0, 4.0, 1.1, "找到\nbest_choice?", C["decision"], fontsize=8)

# No → break
draw_label(ax, 9.6, 12.0, "No", fontsize=8, color=C["end"])
draw_arrow(ax, 10.0, 12.0, 7.5, 12.0)
draw_arrow(ax, 7.5, 12.0, 7.5, 10.5)
draw_arrow(ax, 7.5, 10.5, 16.3, 10.5)
draw_box(ax, 17.3, 10.5, 1.8, 0.5, "BREAK\n无空间可放", C["end"], fontsize=7.5)

# Yes → 放置
draw_label(ax, 14.4, 12.0, "Yes", fontsize=8, color=C["start"])
draw_arrow(ax, 14.0, 12.0, 16.5, 12.0)

# 放置工件
draw_box(ax, 18.8, 12.0, 3.5, 1.0,
         "放置工件到空间原点\n(sp.x, sp.y, sp.z)\nremaining.pop(i)", C["start"], fontsize=8)

draw_arrow(ax, 18.8, 11.5, 18.8, 10.8)

# ── 步骤 2: 分裂 ──
draw_box(ax, 18.8, 10.4, 4.5, 0.9,
         "步骤2: 分裂被占空间\n_split_space() 生成最多 6 块:\n 下 · 上 · 前 · 后 · 左 · 右",
         C["sub"], fontsize=7.5, bold=True, lw=2)

draw_arrow(ax, 18.8, 9.95, 18.8, 9.3)

# ── 步骤 3a: 切除相交 ──
draw_box(ax, 18.8, 8.95, 4.5, 0.8,
         "步骤3a: 切除相交\n遍历所有 space, 与工件\n求交 → 切除重叠部分",
         C["sub"], fontsize=7.5, bold=True, lw=2)

draw_arrow(ax, 18.8, 8.55, 18.8, 7.9)

# ── 步骤 3b: 合并 ──
draw_box(ax, 18.8, 7.5, 4.5, 0.9,
         "步骤3b: 空间合并\n相邻空间共享整面 + 两轴对齐\n→ 合为一个大空间 (反碎片化)",
         C["sub"], fontsize=7.5, bold=True, lw=2)

# 回到主循环
draw_arrow(ax, 18.8, 7.05, 18.8, 6.3)
draw_arrow(ax, 18.8, 6.3, 12, 6.3)
draw_arrow(ax, 12, 6.3, 12, 14.45)
draw_label(ax, 15.5, 6.1, "下一轮迭代", fontsize=8)

# ── 缝隙填充 (循环结束后) ──
draw_box(ax, 12, 5.6, 4.0, 0.7, "主循环结束\n→ 缝隙填充 gap_fill()", C["process"], fontsize=8)

draw_arrow(ax, 12, 5.25, 12, 4.7)

# 输出
draw_box(ax, 12, 4.35, 4.5, 0.8,
         "输出: placed 列表\n(f'{工件名}_{dx}x{dy}x{dz}',\n x, y, z, dx, dy, dz)",
         C["data"], fontsize=8)

# ═══════════════════════════════════════════════════════════
#  右侧说明框：Step1 Best-Fit 细节
# ═══════════════════════════════════════════════════════════
detail_x = 21.5

# 小标题
ax.text(detail_x + 0.2, 16.8, "Best-Fit 评分细节", fontsize=10,
        weight="bold", color=C["title"])

draw_box(ax, detail_x + 0.2, 15.8, 3.8, 2.2,
         "score = (sp.dx - dx)\n      + (sp.dy - dy)\n      + (sp.dz - dz)\n\n→ 三轴间隙和最小\n= 工件最贴合空间",
         "#34495E", fontsize=7.5, text_color="white", alpha=0.9, radius=0.1)

# ═══════════════════════════════════════════════════════════
#  右侧说明框：空间分裂示意
# ═══════════════════════════════════════════════════════════
ax.text(detail_x + 0.2, 13.0, "空间分裂示意", fontsize=10,
        weight="bold", color=C["title"])

# 画一个 3D 示意方块 (2D 投影)
# 大框
rect = mpatches.Rectangle((20.0, 9.5), 3.5, 2.8, fill=False,
                           edgecolor="#2C3E50", lw=1.5, zorder=2)
ax.add_patch(rect)
ax.text(21.75, 12.5, "原材料空间", fontsize=8, ha="center", color="#2C3E50")

# 工件 (右下角小块)
item = mpatches.Rectangle((21.5, 9.8), 2.0, 1.5, fill=True,
                           facecolor="#E74C3C", alpha=0.35, edgecolor="#C0392B",
                           lw=1.5, zorder=3)
ax.add_patch(item)
ax.text(22.5, 10.55, "工件", fontsize=8, ha="center", color="#C0392B", weight="bold")

# 6 个方向的标注
directions = [
    (21.75, 12.8, "上方 ↑"),
    (23.8, 11.5, "右方 →"),
    (21.0, 8.7, "下方 ↓"),
    (19.0, 11.5, "← 左方"),
    (21.75, 7.8, "前方 ◇"),
    (21.75, 13.8, "后方 ◇"),
]
for dx_, dy_, txt in directions:
    ax.text(dx_, dy_, txt, fontsize=7, color="#7F8C8D", ha="center", va="center")

# ═══════════════════════════════════════════════════════════
#  右侧说明框：合并示意
# ═══════════════════════════════════════════════════════════
ax.text(detail_x + 0.2, 7.0, "空间合并条件", fontsize=10,
        weight="bold", color=C["title"])

draw_box(ax, detail_x + 0.2, 6.0, 3.8, 2.0,
         "A 右面 == B 左面\nAND  y, z 对齐\nAND  dy, dz 相等\n\n→ 合成 A+B 大空间",
         "#34495E", fontsize=7.5, text_color="white", alpha=0.9, radius=0.1)

# ═══════════════════════════════════════════════════════════
#  左下角：多策略示意
# ═══════════════════════════════════════════════════════════
ax.text(3.5, 4.5, "三种排序策略", fontsize=10, weight="bold", color=C["title"])

strategies = [
    ("volume_desc", "体积降序\n大件优先填空", "#2980B9"),
    ("footprint_desc", "底面积降序\n稳底优先", "#27AE60"),
    ("longest_desc", "最长边降序\n长件优先", "#8E44AD"),
]
for i, (name, desc, col) in enumerate(strategies):
    y_pos = 3.5 - i * 1.1
    draw_box(ax, 3.5, y_pos, 3.0, 0.9, f"{name}\n{desc}", col, fontsize=7)

# ═══════════════════════════════════════════════════════════
#  中心虚线框：核心三步循环
# ═══════════════════════════════════════════════════════════
loop_rect = mpatches.FancyBboxPatch(
    (7.2, 5.9), 14.8, 8.8,
    boxstyle="round,pad=0.1,rounding_size=0.3",
    facecolor="none", edgecolor="#E74C3C", lw=2, ls="--", zorder=1,
)
ax.add_patch(loop_rect)
ax.text(8.0, 14.2, "核心贪心循环", fontsize=9, color="#E74C3C", weight="bold")

# ═══════════════════════════════════════════════════════════
#  图例
# ═══════════════════════════════════════════════════════════
legend_y = 2.0
legend_items = [
    (C["loop"], "循环 / 迭代"),
    (C["decision"], "判断分支"),
    (C["highlight"], "核心步骤"),
    (C["start"], "放置 / 输出"),
    (C["process"], "初始化 / 处理"),
    (C["data"], "数据 I/O"),
]
for i, (col, label) in enumerate(legend_items):
    lx = 1.5 + i * 3.6
    rect_leg = mpatches.Rectangle((lx, legend_y), 0.4, 0.4, facecolor=col,
                                   edgecolor=col, zorder=3)
    ax.add_patch(rect_leg)
    ax.text(lx + 0.6, legend_y + 0.2, label, fontsize=8, va="center", color="#555")

# ═══════════════════════════════════════════════════════════
#  底部信息
# ═══════════════════════════════════════════════════════════
ax.text(12, 0.8, "子问题 1 · EMS 贪心构造启发式 · 3D 矩形装箱",
        ha="center", fontsize=9, color="#95A5A6", style="italic")
ax.text(12, 0.4, "Best-Fit 评分 + 空间分裂/切除/合并 + 多策略择优",
        ha="center", fontsize=9, color="#95A5A6", style="italic")

# ── 保存 ──
fig.tight_layout(pad=0.5)
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_algorithm_flowchart.png",
            dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none")
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_algorithm_flowchart.pdf",
            bbox_inches="tight", facecolor="white", edgecolor="none")
print("✅ 已生成:")
print("   PNG: ems_algorithm_flowchart.png")
print("   PDF: ems_algorithm_flowchart.pdf")
