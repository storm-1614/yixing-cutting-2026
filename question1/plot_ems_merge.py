"""EMS 空间合并示意图 —— 用 matplotlib 绘制三维示意 + 三轴合并示例"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon
import numpy as np

# ── 全局字体 ──────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Source Han Sans CN", "DejaVu Sans"],
    "font.size": 10,
    "axes.unicode_minus": False,
})

# ═══════════════════════════════════════════════════════════
#  颜色方案
# ═══════════════════════════════════════════════════════════
BLUE   = "#3498DB"
ORANGE = "#E67E22"
GREEN  = "#27AE60"
PURPLE = "#8E44AD"
GRAY   = "#7F8C8D"
DARK   = "#2C3E50"
RED    = "#E74C3C"
WHITE  = "#FFFFFF"
BG     = "#F8F9FA"

# ═══════════════════════════════════════════════════════════
#  3D → 2D 投影辅助函数（斜二测投影，即 cabinet projection）
# ═══════════════════════════════════════════════════════════
def project_3d(x, y, z, origin=(0, 0), scale=1.0, angle=np.radians(30)):
    """斜二测投影: (x,y,z) → 2D 画布坐标"""
    ox, oy = origin
    px = ox + scale * (x - y * np.cos(angle))
    py = oy + scale * (z - y * np.sin(angle))
    return px, py


def draw_cuboid_3d(ax, x, y, z, dx, dy, dz, facecolor, edgecolor=None,
                   alpha=0.85, lw=1.5, origin=(0, 0), scale=1.0, label=None,
                   hatch=None, zorder=2):
    """用斜二测投影画一个长方体"""
    # 8 个顶点
    p = {}
    for ix, px in enumerate([x, x + dx]):
        for iy, py in enumerate([y, y + dy]):
            for iz, pz in enumerate([z, z + dz]):
                p[(ix, iy, iz)] = project_3d(px, py, pz, origin, scale)

    # 三个可见面: 顶面, 前面(y面), 右面(x面)
    top   = [p[(0, 0, 1)], p[(1, 0, 1)], p[(1, 1, 1)], p[(0, 1, 1)]]
    front = [p[(0, 0, 0)], p[(1, 0, 0)], p[(1, 0, 1)], p[(0, 0, 1)]]
    right = [p[(1, 0, 0)], p[(1, 1, 0)], p[(1, 1, 1)], p[(1, 0, 1)]]
    left  = [p[(0, 0, 0)], p[(0, 1, 0)], p[(0, 1, 1)], p[(0, 0, 1)]]

    ec = edgecolor or facecolor

    # 顶面 — 最亮
    top_c = lighten(facecolor, 0.25)
    poly = Polygon(top, facecolor=top_c, edgecolor=ec, lw=lw, alpha=alpha,
                   zorder=zorder, hatch=hatch)
    ax.add_patch(poly)

    # 前面
    poly = Polygon(front, facecolor=facecolor, edgecolor=ec, lw=lw, alpha=alpha,
                   zorder=zorder, hatch=hatch)
    ax.add_patch(poly)

    # 右面 — 略暗
    right_c = darken(facecolor, 0.2)
    poly = Polygon(right, facecolor=right_c, edgecolor=ec, lw=lw, alpha=alpha,
                   zorder=zorder, hatch=hatch)
    ax.add_patch(poly)

    # 左面 — 暗
    left_c = darken(facecolor, 0.35)
    if x > 0.01:
        poly = Polygon(left, facecolor=left_c, edgecolor=ec, lw=lw, alpha=alpha,
                       zorder=zorder, hatch=hatch)
    else:
        # 左面是和别人的贴合面时不画左面
        pass

    # 标注
    if label:
        cx, cy = project_3d(x + dx/2, y + dy/2, z + dz/2, origin, scale)
        ax.text(cx, cy, label, ha="center", va="center", fontsize=8,
                color="white", weight="bold", zorder=zorder + 1)


def lighten(color, amount=0.2):
    """颜色变亮"""
    import matplotlib.colors as mc
    rgb = mc.to_rgb(color)
    return tuple(min(1, c + amount) for c in rgb)


def darken(color, amount=0.2):
    """颜色变暗"""
    import matplotlib.colors as mc
    rgb = mc.to_rgb(color)
    return tuple(max(0, c - amount) for c in rgb)


def draw_space_box(ax, x, y, dx, dy, facecolor, label="", origin=(0, 0),
                   alpha=0.85, lw=2):
    """画 2D 俯视空间块（用于 X-Y 合并示意）"""
    rect = FancyBboxPatch(
        (x, y), dx, dy,
        boxstyle="round,pad=0,rounding_size=0.08",
        facecolor=facecolor, edgecolor=darken(facecolor, 0.3),
        lw=lw, alpha=alpha, zorder=3,
    )
    ax.add_patch(rect)
    if label:
        cx, cy = x + dx/2, y + dy/2
        ax.text(cx, cy, label, ha="center", va="center", fontsize=9,
                color="white", weight="bold", zorder=4)


def draw_arrow_seg(ax, x1, y1, x2, y2, color=GRAY, lw=1.8):
    """画箭头"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=lw))


def draw_box_legend(ax, x, y, w, h, accent_color, text):
    """绘制带左侧色条的说明框"""
    # 背景
    rect = FancyBboxPatch(
        (x, y - h), w, h,
        boxstyle="round,pad=0,rounding_size=0.12",
        facecolor="white", edgecolor="#DDD", lw=1, alpha=0.95, zorder=2,
    )
    ax.add_patch(rect)
    # 左侧色条
    bar = mpatches.Rectangle(
        (x, y - h), 0.12, h,
        facecolor=accent_color, edgecolor="none", alpha=0.9, zorder=3,
    )
    ax.add_patch(bar)
    ax.text(x + 0.35, y - h/2, text, ha="left", va="center",
            fontsize=7.5, color=DARK, zorder=4, linespacing=1.35)


# ═══════════════════════════════════════════════════════════
#  主画布 24×18 inches
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(1, 1, figsize=(24, 18))
ax.set_xlim(0, 24)
ax.set_ylim(0, 18)
ax.set_aspect("equal")
ax.axis("off")
ax.set_facecolor(BG)

# ── 标题 ──
ax.text(12, 17.4, "EMS 空间合并 (try_merge_spaces) 示意图",
        ha="center", va="center", fontsize=22, weight="bold", color=DARK)
ax.text(12, 16.8, "相邻空间共享完整面 + 另两轴完全对齐 → 合并为一个大空间，防止空间碎片化",
        ha="center", va="center", fontsize=11, color=GRAY)

# ═══════════════════════════════════════════════════════════
#  第 1 行：X 轴合并 (3D 斜二测投影)
# ═══════════════════════════════════════════════════════════
ROW1_Y = 15.5
ax.text(6.5, ROW1_Y, "X 轴合并", ha="center", fontsize=14, weight="bold", color=BLUE)
ax.text(6.5, ROW1_Y - 0.35, "A 右面 == B 左面  ∧  y,z 对齐  ∧  dy,dz 相等",
        ha="center", fontsize=9, color=GRAY)

ORIGIN1 = (4.3, 14.2)
S = 1.3  # scale

# --- Before: 两个空间 A, B ---
ax.text(5.2, 13.3, "合并前", ha="center", fontsize=10, weight="bold", color=DARK)

# 空间 A: (0,0,0, 2, 2, 1)
draw_cuboid_3d(ax, 0, 0, 0, 2.0, 2.0, 1.0, BLUE, origin=ORIGIN1, scale=S, label="A")
# 空间 B: (2,0,0, 1.5, 2, 1)  — 紧贴 A 右面
draw_cuboid_3d(ax, 2.0, 0, 0, 1.5, 2.0, 1.0, ORANGE, origin=ORIGIN1, scale=S, label="B")

# 标注尺寸
bx, by = project_3d(0, -0.3, 0, ORIGIN1, S)
ex, ey = project_3d(3.5, -0.3, 0, ORIGIN1, S)
ax.annotate("", xy=(ex, ey), xytext=(bx, by),
            arrowprops=dict(arrowstyle="<->", color=GRAY, lw=1.2))
ax.text((bx + ex) / 2, ey - 0.35, "dx_A + dx_B = 3.5", ha="center", fontsize=8, color=GRAY)

# 贴合面标注
fx, fy = project_3d(2.0, 1.0, 0.5, ORIGIN1, S)
ax.annotate("贴合面", xy=(fx + 0.1, fy - 0.2), fontsize=8, color=RED, weight="bold",
            ha="center")
ax.plot(fx, fy, 'o', color=RED, markersize=4, zorder=5)

# → 箭头
arrow_x = 9.0
ax.annotate("", xy=(10.5, 14.2), xytext=(arrow_x, 14.2),
            arrowprops=dict(arrowstyle="->", color=DARK, lw=2.5))
ax.text(9.75, 14.6, "合并", ha="center", fontsize=10, weight="bold", color=RED)

# --- After: 一个大空间 ---
ax.text(14.0, 13.3, "合并后", ha="center", fontsize=10, weight="bold", color=GREEN)

ORIGIN1B = (13.5, 14.2)
draw_cuboid_3d(ax, 0, 0, 0, 3.5, 2.0, 1.0, GREEN, origin=ORIGIN1B, scale=S,
               label="A+B", lw=2.5)

# 标注
bx2, by2 = project_3d(0, -0.3, 0, ORIGIN1B, S)
ex2, ey2 = project_3d(3.5, -0.3, 0, ORIGIN1B, S)
ax.annotate("", xy=(ex2, ey2), xytext=(bx2, by2),
            arrowprops=dict(arrowstyle="<->", color=GRAY, lw=1.2))
ax.text((bx2 + ex2) / 2, ey2 - 0.35, "dx = 3.5", ha="center", fontsize=8, color=GRAY)

# 合并条件框
draw_box_legend(ax, 18.5, 15.2, 4.2, 2.2, BLUE,
    "X轴合并条件 (代码 117-123 行):\n"
    "- A.x + A.dx == B.x\n"
    "- A.y == B.y, A.z == B.z\n"
    "- A.dy == B.dy, A.dz == B.dz\n"
    "→ 新空间: (A.x, A.y, A.z,\n"
    "           A.dx+B.dx, A.dy, A.dz)")


# ═══════════════════════════════════════════════════════════
#  第 2 行：Y 轴合并 (俯视图 2D)
# ═══════════════════════════════════════════════════════════
ROW2 = 10.0
ax.text(6.5, ROW2 + 1.0, "Y 轴合并 (俯视图)", ha="center", fontsize=14, weight="bold",
        color=ORANGE)
ax.text(6.5, ROW2 + 1.0 - 0.35, "A 后-面 == B 前-面  ∧  x,z 对齐  ∧  dx,dz 相等",
        ha="center", fontsize=9, color=GRAY)

# --- Before ---
ax.text(4.5, ROW2 - 0.2, "合并前", ha="center", fontsize=10, weight="bold", color=DARK)

# 俯视图原点偏移
ox2, oy2 = 2.5, 8.3
draw_space_box(ax, ox2, oy2, 2.5, 1.5, BLUE, label="A", alpha=0.85)
draw_space_box(ax, ox2, oy2 + 1.5, 2.5, 1.0, ORANGE, label="B", alpha=0.85)

# 贴合面标注
ax.plot([ox2, ox2 + 2.5], [oy2 + 1.5, oy2 + 1.5], color=RED, lw=2.5, ls="--", zorder=5)
ax.text(ox2 + 2.5 + 0.2, oy2 + 0.75, "Y 贴合面", fontsize=8, color=RED, weight="bold")

# 尺寸标注
ax.annotate("", xy=(ox2 + 2.5 + 0.6, oy2), xytext=(ox2 + 2.5 + 0.6, oy2 + 2.5),
            arrowprops=dict(arrowstyle="<->", color=GRAY, lw=1.2))
ax.text(ox2 + 2.5 + 1.0, oy2 + 1.25, "dy=2.5", ha="center", fontsize=8, color=GRAY)

# → 箭头
ax.annotate("", xy=(7.3, ROW2 - 0.2), xytext=(5.8, ROW2 - 0.2),
            arrowprops=dict(arrowstyle="->", color=DARK, lw=2.5))
ax.text(6.55, ROW2 + 0.15, "合并", ha="center", fontsize=10, weight="bold", color=RED)

# --- After ---
ax.text(9.5, ROW2 - 0.2, "合并后", ha="center", fontsize=10, weight="bold", color=GREEN)

ox3, oy3 = 8.2, 8.3
draw_space_box(ax, ox3, oy3, 2.5, 2.5, GREEN, label="A+B", alpha=0.85, lw=2.5)

ax.annotate("", xy=(ox3 + 2.5 + 0.6, oy3), xytext=(ox3 + 2.5 + 0.6, oy3 + 2.5),
            arrowprops=dict(arrowstyle="<->", color=GRAY, lw=1.2))
ax.text(ox3 + 2.5 + 1.0, oy3 + 1.25, "dy=2.5", ha="center", fontsize=8, color=GRAY)

# 条件框
draw_box_legend(ax, 13.0, ROW2 + 1.2, 4.2, 2.2, ORANGE,
    "Y轴合并条件 (代码 125-131 行):\n"
    "- A.y + A.dy == B.y\n"
    "- A.x == B.x, A.z == B.z\n"
    "- A.dx == B.dx, A.dz == B.dz\n"
    "→ 新空间: (A.x, A.y, A.z,\n"
    "           A.dx, A.dy+B.dy, A.dz)")

# ═══════════════════════════════════════════════════════════
#  第 3 行：Z 轴合并 (正视图 2D)
# ═══════════════════════════════════════════════════════════
ROW3 = 5.5
ax.text(12, ROW3 + 1.0, "Z 轴合并 (正视图 XZ 平面)", ha="center", fontsize=14,
        weight="bold", color=PURPLE)
ax.text(12, ROW3 + 1.0 - 0.35,
        "A 上-面 == B 下-面  ∧  x,y 对齐  ∧  dx,dy 相等",
        ha="center", fontsize=9, color=GRAY)

# --- Before ---
ax.text(4.5, ROW3 - 0.2, "合并前", ha="center", fontsize=10, weight="bold", color=DARK)

oz1_x, oz1_y = 2.5, 3.0
# 空间 A (下方)
rect_a = FancyBboxPatch(
    (oz1_x, oz1_y), 2.5, 1.0,
    boxstyle="round,pad=0,rounding_size=0.08",
    facecolor=BLUE, edgecolor=darken(BLUE, 0.3), lw=2, alpha=0.85, zorder=3,
)
ax.add_patch(rect_a)
ax.text(oz1_x + 2.5/2, oz1_y + 1.0/2, "A", ha="center", va="center",
        fontsize=9, color="white", weight="bold", zorder=4)

# 空间 B (上方)
rect_b = FancyBboxPatch(
    (oz1_x, oz1_y + 1.0), 2.5, 0.8,
    boxstyle="round,pad=0,rounding_size=0.08",
    facecolor=ORANGE, edgecolor="none", lw=2, alpha=0.85, zorder=3,
)
ax.add_patch(rect_b)
ax.text(oz1_x + 2.5/2, oz1_y + 1.0 + 0.8/2, "B", ha="center", va="center",
        fontsize=9, color="white", weight="bold", zorder=4)

# Z 贴合面
ax.plot([oz1_x - 0.3, oz1_x + 2.5 + 0.3], [oz1_y + 1.0, oz1_y + 1.0],
        color=RED, lw=2.5, ls="--", zorder=5)
ax.text(oz1_x + 2.5 + 0.5, oz1_y + 1.0, "Z 贴合面", fontsize=8, color=RED, weight="bold",
        va="center")

# 箭头
ax.annotate("", xy=(7.3, ROW3), xytext=(5.8, ROW3),
            arrowprops=dict(arrowstyle="->", color=DARK, lw=2.5))
ax.text(6.55, ROW3 + 0.35, "合并", ha="center", fontsize=10, weight="bold", color=RED)

# --- After ---
ax.text(9.5, ROW3 - 0.2, "合并后", ha="center", fontsize=10, weight="bold", color=GREEN)

oz2_x = 8.2
rect_c = FancyBboxPatch(
    (oz2_x, oz1_y), 2.5, 1.8,
    boxstyle="round,pad=0,rounding_size=0.08",
    facecolor=GREEN, edgecolor=darken(GREEN, 0.3), lw=2.5, alpha=0.85, zorder=3,
)
ax.add_patch(rect_c)
ax.text(oz2_x + 2.5/2, oz1_y + 1.8/2, "A+B", ha="center", va="center",
        fontsize=9, color="white", weight="bold", zorder=4)

# 条件框
draw_box_legend(ax, 13.0, ROW3 + 0.8, 4.2, 2.2, PURPLE,
    "Z轴合并条件 (代码 133-139 行):\n"
    "- A.z + A.dz == B.z\n"
    "- A.x == B.x, A.y == B.y\n"
    "- A.dx == B.dx, A.dy == B.dy\n"
    "→ 新空间: (A.x, A.y, A.z,\n"
    "           A.dx, A.dy, A.dz+B.dz)")


# ═══════════════════════════════════════════════════════════
#  底部总结
# ═══════════════════════════════════════════════════════════
ax.text(12, 1.8, "核心思想：放置工件后空间被切成碎片 → 合并相邻且共享整面的空间 → 减少碎片化 → 为后续大工件保留更多连续空间",
        ha="center", fontsize=10, color=GRAY, style="italic")
ax.text(12, 1.3, "合并三要素：共享完整面 (相邻)  +  另两轴坐标完全对齐  +  另两轴尺寸完全相等",
        ha="center", fontsize=10, color=DARK, weight="bold")

# 图例
legend_y = 0.6
items = [
    (BLUE, "空间 A"), (ORANGE, "空间 B"), (GREEN, "合并结果"),
    (RED, "贴合面"), (PURPLE, "不满足条件 (不合并)")
]
for i, (col, label) in enumerate(items):
    lx = 2.5 + i * 4.2
    if label == "贴合面":
        ax.plot([lx, lx + 0.5], [legend_y, legend_y], color=col, lw=2.5, ls="--")
    else:
        rect = mpatches.Rectangle((lx, legend_y - 0.12), 0.5, 0.25,
                                   facecolor=col, edgecolor=darken(col, 0.2), lw=1, zorder=3)
        ax.add_patch(rect)
    ax.text(lx + 0.7, legend_y, label, fontsize=8, va="center", color=DARK)

# ── 保存 ──
fig.tight_layout(pad=0.5)
out_base = "/data/project/yixing-cutting-2026/question1/ems_space_merge"
fig.savefig(out_base + ".png", dpi=200, bbox_inches="tight",
            facecolor="white", edgecolor="none")
fig.savefig(out_base + ".pdf", bbox_inches="tight",
            facecolor="white", edgecolor="none")
print("✅ 已生成:")
print(f"   PNG: {out_base}.png")
print(f"   PDF: {out_base}.pdf")
