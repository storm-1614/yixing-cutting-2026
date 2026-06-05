#!/usr/bin/env python3
"""三个订单(H01/H02/H03) 对比柱状图 — 思源黑体，中文，高清晰版
每组指标一个分组柱状图，3个订单并排，每个图都有图例
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.font_manager import FontProperties

# ── 思源黑体 ────────────────────────────────────────────
SOURCE_HAN = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf"
)
SOURCE_HAN_BOLD = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Bold.otf"
)
SOURCE_HAN_MEDIUM = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Medium.otf"
)

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Source Han Sans CN"]
plt.rcParams["axes.unicode_minus"] = False

# ── 颜色 ────────────────────────────────────────────────
C_H01 = "#3262A8"   # 蓝
C_H02 = "#D4743E"   # 橙 (最优)
C_H03 = "#3E8A52"   # 绿
COLOR_ORDER = [C_H01, C_H02, C_H03]
LEGEND_LABELS = ["H01", "H02 ★(最优)", "H03"]

DPI = 250
BAR_W = 0.55
x3 = np.arange(3)


def make_fig():
    fig = plt.figure()
    fig.patch.set_facecolor("#FAFAFA")
    return fig


def add_order_legend(ax, loc="lower right"):
    """给每个图添加统一的订单图例"""
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COLOR_ORDER]
    ax.legend(handles, LEGEND_LABELS, loc=loc,
              framealpha=0.92, edgecolor="#BBB", prop=SOURCE_HAN_MEDIUM,
              fontsize=14, title="订单", title_fontproperties=SOURCE_HAN_BOLD)
    return ax


# ═══════════════════════════════════════════════════════════════
# 图1：净利润分组柱状图
# ═══════════════════════════════════════════════════════════════
net_profit = [285620, 295320, 266460]
fig1 = make_fig()
ax1 = fig1.add_subplot(111)

ax1.bar(x3, net_profit, BAR_W, color=COLOR_ORDER,
        edgecolor="white", linewidth=1.5, zorder=2)
for i, v in enumerate(net_profit):
    ax1.text(i, v + 2000, f"¥{v:,}", ha="center", va="bottom",
             fontproperties=SOURCE_HAN_BOLD, fontsize=20, color="#111")

# 差异标注
best = np.argmax(net_profit)
for i in range(3):
    if i != best:
        diff = net_profit[best] - net_profit[i]
        mid_y = (net_profit[i] + net_profit[best]) / 2
        mid_x = (i + best) / 2
        ax1.annotate("", xy=(best, net_profit[best]-15000),
                     xytext=(i, net_profit[i]+15000),
                     arrowprops=dict(arrowstyle="<->", color="#888", lw=2, ls="--"))
        ax1.text(mid_x, mid_y + 10000, f"差额 ¥{diff:,}", ha="center",
                 fontproperties=SOURCE_HAN, fontsize=14, color="#666",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF",
                           edgecolor="#CCC", alpha=0.9))

ax1.set_xticks(x3)
ax1.set_xticklabels(["订单 H01", "订单 H02 ★", "订单 H03"],
                     fontproperties=SOURCE_HAN_BOLD, fontsize=17)
ax1.set_ylabel("净利润 (元)", fontproperties=SOURCE_HAN_MEDIUM, fontsize=17)
ax1.set_title("三个订单净利润对比", fontproperties=SOURCE_HAN_BOLD, fontsize=24, pad=18)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax1.set_ylim(258000, 318000)
ax1.grid(axis="y", alpha=0.2, zorder=1)
ax1.set_axisbelow(True)
ax1.tick_params(axis="both", labelsize=13)
add_order_legend(ax1, loc="lower right")

fig1.tight_layout()
for ext in ["png", "pdf"]:
    fig1.savefig(f"/data/project/yixing-cutting-2026/question3/fig1_netprofit.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig1.get_facecolor())
plt.close(fig1)
print("✅ 图1: 净利润分组柱状图 — fig1_netprofit.png")


# ═══════════════════════════════════════════════════════════════
# 图2：原材料利用率分组柱状图 + 紧急采购标注
# ═══════════════════════════════════════════════════════════════
utilization = [83.40, 94.01, 87.85]
emergency_cnt = [0, 15, 32]

fig2 = make_fig()
ax2 = fig2.add_subplot(111)

bars = ax2.bar(x3, utilization, BAR_W, color=COLOR_ORDER,
               edgecolor="white", linewidth=1.5, zorder=2)
for i, v in enumerate(utilization):
    # 数值标签
    ax2.text(i, v + 0.5, f"{v:.1f}%", ha="center", va="bottom",
             fontproperties=SOURCE_HAN_BOLD, fontsize=22, color="#111")
    # 柱内紧急采购说明
    inner = f"紧急采购 {emergency_cnt[i]}件" if emergency_cnt[i] > 0 else "✓ 零紧急采购"
    ax2.text(i, v - 4.5, inner, ha="center", va="top",
             fontproperties=SOURCE_HAN_MEDIUM, fontsize=13, color="white")

# 最佳标注
best_u = np.argmax(utilization)
ax2.annotate("最高利用率", xy=(best_u, utilization[best_u]),
             xytext=(best_u, utilization[best_u] + 3.5),
             ha="center", fontproperties=SOURCE_HAN_BOLD, fontsize=13,
             color=C_H02,
             arrowprops=dict(arrowstyle="->", color=C_H02, lw=2))

ax2.set_xticks(x3)
ax2.set_xticklabels(["订单 H01", "订单 H02 ★", "订单 H03"],
                     fontproperties=SOURCE_HAN_BOLD, fontsize=17)
ax2.set_ylabel("原材料利用率 (%)", fontproperties=SOURCE_HAN_MEDIUM, fontsize=17)
ax2.set_title("三个订单原材料利用率对比", fontproperties=SOURCE_HAN_BOLD, fontsize=24, pad=18)
ax2.set_ylim(78, 101)
ax2.grid(axis="y", alpha=0.2, zorder=1)
ax2.set_axisbelow(True)
ax2.tick_params(axis="both", labelsize=13)
add_order_legend(ax2, loc="lower right")

fig2.tight_layout()
for ext in ["png", "pdf"]:
    fig2.savefig(f"/data/project/yixing-cutting-2026/question3/fig2_utilization.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig2.get_facecolor())
plt.close(fig2)
print("✅ 图2: 利用率分组柱状图 — fig2_utilization.png")


# ═══════════════════════════════════════════════════════════════
# 图3：自产工件总量分组柱状图
# ═══════════════════════════════════════════════════════════════
total_wp = [178, 352, 191]

fig3 = make_fig()
ax3 = fig3.add_subplot(111)

ax3.bar(x3, total_wp, BAR_W, color=COLOR_ORDER,
        edgecolor="white", linewidth=1.5, zorder=2)
for i, v in enumerate(total_wp):
    ax3.text(i, v + 4, f"{v} 件", ha="center", va="bottom",
             fontproperties=SOURCE_HAN_BOLD, fontsize=22, color="#111")

ax3.set_xticks(x3)
ax3.set_xticklabels(["订单 H01", "订单 H02 ★", "订单 H03"],
                     fontproperties=SOURCE_HAN_BOLD, fontsize=17)
ax3.set_ylabel("自产工件数量 (件)", fontproperties=SOURCE_HAN_MEDIUM, fontsize=17)
ax3.set_title("三个订单自产工件总量对比", fontproperties=SOURCE_HAN_BOLD, fontsize=24, pad=18)
ax3.set_ylim(0, 410)
ax3.grid(axis="y", alpha=0.2, zorder=1)
ax3.set_axisbelow(True)
ax3.tick_params(axis="both", labelsize=13)
add_order_legend(ax3, loc="upper left")

fig3.tight_layout()
for ext in ["png", "pdf"]:
    fig3.savefig(f"/data/project/yixing-cutting-2026/question3/fig3_workpiece_total.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig3.get_facecolor())
plt.close(fig3)
print("✅ 图3: 自产工件总量分组柱状图 — fig3_workpiece_total.png")


# ═══════════════════════════════════════════════════════════════
# 图4：各工件生产满足情况 (每个订单一个子图，每个子图有图例)
# ═══════════════════════════════════════════════════════════════
workpiece_types = ["J01", "J02", "J03", "J04", "J05", "J06", "J07"]
needs = [
    [0, 0, 4, 54, 22, 69, 21],
    [48, 200, 50, 0, 8, 0, 37],
    [0, 0, 7, 54, 24, 104, 25],
]
prods = [
    [0, 0, 4, 54, 22, 69, 21],
    [48, 190, 50, 0, 8, 0, 32],
    [0, 0, 7, 54, 24, 72, 25],
]
ems = [
    [0, 0, 0, 0, 0, 0, 0],
    [0, 10, 0, 0, 0, 0, 5],
    [0, 0, 0, 0, 0, 32, 0],
]
sub_titles = ["订单 H01 ", "订单 H02 ★", "订单 H03 "]

fig4, axes = plt.subplots(1, 3, figsize=(20, 6.5))
fig4.patch.set_facecolor("#FAFAFA")
xw = np.arange(len(workpiece_types))
ww = 0.22

for i, ax in enumerate(axes):
    ax.bar(xw - ww, needs[i], ww, color="#BDCCE0", edgecolor="white",
           linewidth=0.4, label="净需求", zorder=2)
    ax.bar(xw, prods[i], ww, color=COLOR_ORDER[i], edgecolor="white",
           linewidth=0.4, label="自产数量", zorder=2)
    if sum(ems[i]) > 0:
        ax.bar(xw + ww, ems[i], ww, color="#E31A1C", edgecolor="white",
               linewidth=0.4, label="紧急采购", zorder=2)

    ax.set_xticks(xw)
    ax.set_xticklabels(workpiece_types, fontproperties=SOURCE_HAN_BOLD, fontsize=13)
    ax.set_title(sub_titles[i], fontproperties=SOURCE_HAN_BOLD, fontsize=16, pad=12)
    ax.grid(axis="y", alpha=0.2, zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=11)
    if i == 0:
        ax.set_ylabel("数量 (件)", fontproperties=SOURCE_HAN_MEDIUM, fontsize=15)
    # 每个子图都有图例
    ax.legend(loc="upper right", framealpha=0.9, edgecolor="#CCC",
              prop=SOURCE_HAN, fontsize=11.5)

fig4.suptitle("", fontproperties=SOURCE_HAN_BOLD,
              fontsize=23, y=1.02)
fig4.tight_layout()
for ext in ["png", "pdf"]:
    fig4.savefig(f"/data/project/yixing-cutting-2026/question3/fig4_workpiece_detail.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig4.get_facecolor())
plt.close(fig4)
print("✅ 图4: 各工件生产满足情况 — fig4_workpiece_detail.png")


# ═══════════════════════════════════════════════════════════════
# 图5：综合仪表盘 (四合一，每个子图有图例)
# ═══════════════════════════════════════════════════════════════
fig5 = plt.figure(figsize=(20, 12))
fig5.patch.set_facecolor("#F5F5F5")
gs = fig5.add_gridspec(2, 2, hspace=0.28, wspace=0.18)

# (a) 净利润
ax_a = fig5.add_subplot(gs[0, 0])
ax_a.bar(x3, net_profit, 0.45, color=COLOR_ORDER,
         edgecolor="white", linewidth=1.2, zorder=2)
for i, v in enumerate(net_profit):
    ax_a.text(i, v + 2000, f"¥{v:,}", ha="center",
              fontproperties=SOURCE_HAN_BOLD, fontsize=15, color="#111")
ax_a.set_xticks(x3)
ax_a.set_xticklabels(["H01", "H02★", "H03"], fontproperties=SOURCE_HAN_BOLD, fontsize=15)
ax_a.set_title("(a) 净利润", fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_a.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
ax_a.set_ylim(258000, 310000)
ax_a.grid(axis="y", alpha=0.2); ax_a.set_axisbelow(True)
ax_a.tick_params(axis="both", labelsize=12)
add_order_legend(ax_a, loc="lower right")

# (b) 利用率
ax_b = fig5.add_subplot(gs[0, 1])
ax_b.bar(x3, utilization, 0.45, color=COLOR_ORDER,
         edgecolor="white", linewidth=1.2, zorder=2)
for i, v in enumerate(utilization):
    ax_b.text(i, v + 0.4, f"{v:.1f}%", ha="center",
              fontproperties=SOURCE_HAN_BOLD, fontsize=16, color="#111")
ax_b.set_xticks(x3)
ax_b.set_xticklabels(["H01", "H02★", "H03"], fontproperties=SOURCE_HAN_BOLD, fontsize=15)
ax_b.set_title("(b) 原材料利用率", fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_b.set_ylim(80, 99)
ax_b.grid(axis="y", alpha=0.2); ax_b.set_axisbelow(True)
ax_b.tick_params(axis="both", labelsize=12)
add_order_legend(ax_b, loc="lower right")

# (c) 自产件数
ax_c = fig5.add_subplot(gs[1, 0])
ax_c.bar(x3, total_wp, 0.45, color=COLOR_ORDER,
         edgecolor="white", linewidth=1.2, zorder=2)
for i, v in enumerate(total_wp):
    ax_c.text(i, v + 3, f"{v} 件", ha="center",
              fontproperties=SOURCE_HAN_BOLD, fontsize=16, color="#111")
ax_c.set_xticks(x3)
ax_c.set_xticklabels(["H01", "H02★", "H03"], fontproperties=SOURCE_HAN_BOLD, fontsize=15)
ax_c.set_title("(c) 自产工件总量", fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_c.set_ylim(0, 410)
ax_c.grid(axis="y", alpha=0.2); ax_c.set_axisbelow(True)
ax_c.tick_params(axis="both", labelsize=12)
add_order_legend(ax_c, loc="upper left")

# (d) 紧急采购件数
ax_d = fig5.add_subplot(gs[1, 1])
ax_d.bar(x3, emergency_cnt, 0.45, color=COLOR_ORDER,
         edgecolor="white", linewidth=1.2, zorder=2)
for i, v in enumerate(emergency_cnt):
    label = "0 件 (无)" if v == 0 else f"{v} 件"
    ax_d.text(i, v + 0.5, label, ha="center",
              fontproperties=SOURCE_HAN_BOLD, fontsize=16, color="#111")
ax_d.set_xticks(x3)
ax_d.set_xticklabels(["H01", "H02★", "H03"], fontproperties=SOURCE_HAN_BOLD, fontsize=15)
ax_d.set_title("(d) 紧急采购件数", fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_d.set_ylim(0, 44)
ax_d.grid(axis="y", alpha=0.2); ax_d.set_axisbelow(True)
ax_d.tick_params(axis="both", labelsize=12)
add_order_legend(ax_d, loc="upper left")

fig5.suptitle("三个订单综合对比分析", fontproperties=SOURCE_HAN_BOLD,
              fontsize=25, y=1.01, color="#111")
for ext in ["png", "pdf"]:
    fig5.savefig(f"/data/project/yixing-cutting-2026/question3/fig5_dashboard.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig5.get_facecolor())
plt.close(fig5)
print("✅ 图5: 综合仪表盘 — fig5_dashboard.png")

print("\n🎉 全部 5 组图表生成完毕!")
print("  图1: fig1_netprofit.png          — 净利润分组柱状图")
print("  图2: fig2_utilization.png        — 利用率分组柱状图")
print("  图3: fig3_workpiece_total.png    — 自产工件总量分组柱状图")
print("  图4: fig4_workpiece_detail.png   — 各工件生产满足情况")
print("  图5: fig5_dashboard.png          — 四合一综合仪表盘")
