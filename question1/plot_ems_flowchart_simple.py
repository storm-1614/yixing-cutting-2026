"""EMS 算法流程图 — 最简洁版"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Source Han Sans CN", "Noto Sans CJK SC", "DejaVu Sans"],
    "font.size": 10,
    "axes.unicode_minus": False,
})

# ── 尺寸 ──
W, H = 12, 20
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.set_aspect("equal")
ax.axis("off")

# ── 调色板 ──
C = {
    "start": "#2ECC71",
    "end": "#E74C3C",
    "loop": "#3498DB",
    "decision": "#E67E22",
    "core": "#8E44AD",
    "arrow": "#2C3E50",
    "bg": "#F8F9FA",
}

# ── 辅助函数 ──
def box(x, y, w, h, text, color, fontsize=9, bold=False, text_color="white", radius=0.12):
    b = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor=color, edgecolor=color, lw=1.5, zorder=3)
    ax.add_patch(b)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, weight=weight, zorder=4, linespacing=1.4)

def diamond(x, y, w, h, text, color, fontsize=8):
    pts = np.array([[x, y+h/2], [x+w/2, y], [x, y-h/2], [x-w/2, y]])
    ax.add_patch(plt.Polygon(pts, facecolor=color, edgecolor=color, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color="white", weight="bold", zorder=4, linespacing=1.3)

def arrow(x1, y1, x2, y2, color=None, lw=1.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color or C["arrow"], lw=lw))

def label(x, y, text, color=None, fontsize=7):
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=color or C["arrow"], style="italic")

# ── 布局参数 ──
cx = 6  # 中心线
gap = 1.8  # 竖向间距
y = 18.5  # 起始 y

# ═══ 标题 ═══
ax.text(cx, 19.5, "EMS 算法流程", ha="center", fontsize=18, weight="bold", color="#2C3E50")

# ═══ START ═══
box(cx, y, 5.5, 0.9, "输入: 原材料块(L×W×H) + 候选工件池", C["start"], fontsize=9, bold=True)
y -= gap * 0.6
arrow(cx, y, cx, y - 0.3)
y -= 0.5

# ═══ 初始化 ═══
box(cx, y, 5.5, 0.9, "初始化: spaces = [整块原材料]\nremaining = 候选工件列表", C["loop"], fontsize=9)
y -= gap * 0.6
arrow(cx, y, cx, y - 0.3)
y -= 0.5

# ═══ WHILE ═══
box(cx, y, 4.0, 0.7, "WHILE remaining != []", C["loop"], fontsize=10, bold=True)
y_start_loop = y
y -= gap * 0.55
arrow(cx, y, cx, y - 0.3)
y -= 0.5

# ═══ Best-Fit ═══
box(cx, y, 6.5, 1.1,
    "Best-Fit 选择\nscore = Σ(space_dim − item_dim) → 最小者\n即: 工件与空间最贴合的(工件, 空间)对",
    C["core"], fontsize=8.5, bold=True)
y_core = y
y -= gap * 0.6
arrow(cx, y, cx, y - 0.3)
y -= 0.5

# ═══ 判断 ═══
diamond(cx, y, 4.5, 1.0, "best_choice\n存在?", C["decision"], fontsize=9)
y_dec = y
y -= gap * 0.6
arrow(cx, y, cx, y - 0.3)
label(cx + 0.3, y + 0.1, "Yes", color="#27AE60", fontsize=8)

# ═══ 放置 ═══
box(cx, y, 5.0, 0.85, "将工件放置于空间原点\n从 remaining 移除", C["core"], fontsize=9)
y -= gap * 0.55
arrow(cx, y, cx, y - 0.3)
y -= 0.5

# ═══ 核心三步 ── 用虚线框包裹 ═══
box_y_top = y + 0.6
box_y_bot = y - 3.6

step_gap = 1.5
# Step 1
box(cx, y, 5.5, 0.75, "① 分裂: _split_space() → 最多 6 个子空间", C["loop"], fontsize=8.5)
y -= step_gap
arrow(cx, y + 0.375, cx, y)
# Step 2
box(cx, y, 5.5, 0.75, "② 切除: 遍历空间求交 → 移除重叠区域", C["loop"], fontsize=8.5)
y -= step_gap
arrow(cx, y + 0.375, cx, y)
# Step 3
box(cx, y, 5.5, 0.75, "③ 合并: 相邻空间共享面 + 对齐 → 合并", C["loop"], fontsize=8.5)

# 虚线框
rect = mpatches.FancyBboxPatch(
    (cx - 3.5, box_y_bot), 7.0, box_y_top - box_y_bot + 0.2,
    boxstyle="round,pad=0.1,rounding_size=0.15",
    facecolor="none", edgecolor="#E74C3C", lw=1.8, ls="--", zorder=1,
)
ax.add_patch(rect)
ax.text(cx - 3.2, box_y_top + 0.15, "核心三步", fontsize=9, color="#E74C3C", weight="bold")

# ═══ 回到 WHILE ═══
arrow(cx, y - 0.375, cx, y - 0.55)
# 循环回线
ax.annotate("", xy=(cx, y_start_loop - 0.35), xytext=(cx, y - 0.55),
            arrowprops=dict(arrowstyle="->", color=C["loop"], lw=1.8,
                           connectionstyle="arc3,rad=0.0"))

# ═══ No 分支 ═══
no_x = cx + 4.0
no_y = y_dec
arrow(cx + 2.25, no_y, no_x, no_y, color="#E74C3C")
label(cx + 3.1, no_y + 0.25, "No", color="#E74C3C", fontsize=8)

# ═══ 输出 ═══
out_y = y_dec - 3.5
box(cx, out_y, 5.5, 0.9, "输出: placed 列表\n{(工件名, x, y, z, dx, dy, dz)}", C["end"], fontsize=9, bold=True)

arrow(no_x, no_y, no_x, out_y)
arrow(no_x, out_y, cx + 2.75, out_y)

# ═══ 右侧注释：Best-Fit 评分 ═══
ann_x = 10.0
ax.text(ann_x, y_core + 0.6, "评分公式", fontsize=9, weight="bold", color="#2C3E50")
ax.text(ann_x, y_core - 0.15,
        "score = (sp.dx − dx)\n       + (sp.dy − dy)\n       + (sp.dz − dz)",
        fontsize=8, color="#555", family="monospace", ha="center")
ax.annotate("", xy=(ann_x - 1.5, y_core),
            xytext=(cx + 3.25, y_core),
            arrowprops=dict(arrowstyle="->", color="#BDC3C7", lw=1.2))

# ═══ 底部标注 ═══
ax.text(cx, 0.5, "EMS (Empty Maximal Spaces) · 贪心构造启发式 · 3D 矩形装箱",
        ha="center", fontsize=8, color="#95A5A6", style="italic")

# ── 保存 ──
fig.tight_layout(pad=0.3)
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_flowchart_simple.png",
            dpi=200, bbox_inches="tight", facecolor="white")
fig.savefig("/data/project/yixing-cutting-2026/question1/ems_flowchart_simple.pdf",
            bbox_inches="tight", facecolor="white")
print("✅ 已生成: ems_flowchart_simple.png / .pdf")
