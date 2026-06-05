#!/usr/bin/env python3
"""收敛性曲线 — 思源黑体，中文，高清晰版
展示算法迭代过程中gap的变化
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
C_BLUE = "#3262A8"    # 蓝
C_ORANGE = "#D4743E"  # 橙
C_GREEN = "#3E8A52"   # 绿
C_RED = "#E31A1C"     # 红
DPI = 250

# ── 示例收敛数据（实际使用时替换为真实数据）─────────────
# 迭代次数
iterations = np.arange(0, 51)

# gap% 随迭代次数的变化（模拟指数下降）
np.random.seed(42)
gap_initial = 85.0
gap_curve = gap_initial * np.exp(-0.12 * iterations) + np.random.normal(0, 0.8, len(iterations))
gap_curve = np.maximum(gap_curve, 0.5)  # 设置下限
gap_curve[0] = gap_initial  # 初始值

# 目标函数值随迭代的变化
obj_initial = 1500000
obj_curve = obj_initial - (obj_initial - 2850000) * (1 - np.exp(-0.1 * iterations))
obj_curve += np.random.normal(0, 5000, len(iterations))
obj_curve = np.minimum(obj_curve, 2850000)
obj_curve[0] = obj_initial

# ═══════════════════════════════════════════════════════════════
# 图1：Gap收敛曲线（单条线）
# ═══════════════════════════════════════════════════════════════
fig1, ax1 = plt.subplots(figsize=(12, 7))
fig1.patch.set_facecolor("#FAFAFA")

ax1.plot(iterations, gap_curve, color=C_BLUE, linewidth=2.5, marker='o',
         markersize=4, markerfacecolor='white', markeredgewidth=1.5,
         markeredgecolor=C_BLUE, label='Gap%', zorder=3)

# 填充曲线下方
ax1.fill_between(iterations, gap_curve, alpha=0.15, color=C_BLUE)

# 标注关键点
key_iters = [0, 10, 20, 30, 40, 50]
for it in key_iters:
    if it < len(gap_curve):
        ax1.annotate(f'{gap_curve[it]:.1f}%',
                     xy=(it, gap_curve[it]),
                     xytext=(0, 15), textcoords='offset points',
                     ha='center', fontproperties=SOURCE_HAN_MEDIUM,
                     fontsize=11, color='#333',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF',
                               edgecolor='#CCC', alpha=0.9))

# 添加收敛阈值线
threshold = 5.0
ax1.axhline(y=threshold, color=C_RED, linestyle='--', linewidth=1.5, alpha=0.7)
ax1.text(51, threshold + 1, f'收敛阈值 {threshold}%', fontproperties=SOURCE_HAN,
         fontsize=11, color=C_RED, ha='right')

ax1.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax1.set_ylabel('Gap (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax1.set_title('算法收敛曲线 — Gap随迭代次数变化', fontproperties=SOURCE_HAN_BOLD,
              fontsize=22, pad=15)
ax1.set_xlim(-1, 52)
ax1.set_ylim(0, 100)
ax1.grid(True, alpha=0.25, zorder=1)
ax1.set_axisbelow(True)
ax1.tick_params(axis='both', labelsize=12)
ax1.legend(prop=SOURCE_HAN_MEDIUM, fontsize=13, loc='upper right',
           framealpha=0.9, edgecolor='#BBB')

fig1.tight_layout()
for ext in ["png", "pdf"]:
    fig1.savefig(f"/data/project/yixing-cutting-2026/question2/fig_convergence_gap.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig1.get_facecolor())
plt.close(fig1)
print("✅ 图1: Gap收敛曲线 — fig_convergence_gap.png")


# ═══════════════════════════════════════════════════════════════
# 图2：目标函数值收敛曲线
# ═══════════════════════════════════════════════════════════════
fig2, ax2 = plt.subplots(figsize=(12, 7))
fig2.patch.set_facecolor("#FAFAFA")

ax2.plot(iterations, obj_curve, color=C_GREEN, linewidth=2.5, marker='s',
         markersize=4, markerfacecolor='white', markeredgewidth=1.5,
         markeredgecolor=C_GREEN, label='目标函数值', zorder=3)

# 填充曲线下方
ax2.fill_between(iterations, obj_curve, alpha=0.12, color=C_GREEN)

# 标注关键点
for it in key_iters:
    if it < len(obj_curve):
        val = obj_curve[it]
        label = f'¥{val/10000:.1f}万'
        ax2.annotate(label, xy=(it, val),
                     xytext=(0, 15), textcoords='offset points',
                     ha='center', fontproperties=SOURCE_HAN_MEDIUM,
                     fontsize=11, color='#333',
                     bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF',
                               edgecolor='#CCC', alpha=0.9))

# 添加最优解参考线
best_obj = obj_curve[-1]
ax2.axhline(y=best_obj, color=C_ORANGE, linestyle='--', linewidth=1.5, alpha=0.7)
ax2.text(51, best_obj + 15000, f'最优解 ≈¥{best_obj/10000:.1f}万',
         fontproperties=SOURCE_HAN, fontsize=11, color=C_ORANGE, ha='right')

ax2.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax2.set_ylabel('目标函数值 (元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax2.set_title('算法收敛曲线 — 目标函数值变化', fontproperties=SOURCE_HAN_BOLD,
              fontsize=22, pad=15)
ax2.set_xlim(-1, 52)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{int(v/10000)}万'))
ax2.grid(True, alpha=0.25, zorder=1)
ax2.set_axisbelow(True)
ax2.tick_params(axis='both', labelsize=12)
ax2.legend(prop=SOURCE_HAN_MEDIUM, fontsize=13, loc='lower right',
           framealpha=0.9, edgecolor='#BBB')

fig2.tight_layout()
for ext in ["png", "pdf"]:
    fig2.savefig(f"/data/project/yixing-cutting-2026/question2/fig_convergence_obj.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig2.get_facecolor())
plt.close(fig2)
print("✅ 图2: 目标函数值收敛曲线 — fig_convergence_obj.png")


# ═══════════════════════════════════════════════════════════════
# 图3：双Y轴综合收敛图（Gap + 目标函数值）
# ═══════════════════════════════════════════════════════════════
fig3, ax3a = plt.subplots(figsize=(14, 7))
fig3.patch.set_facecolor("#FAFAFA")

# 左Y轴：Gap%
color_gap = C_BLUE
ax3a.plot(iterations, gap_curve, color=color_gap, linewidth=2.5, marker='o',
          markersize=5, markerfacecolor='white', markeredgewidth=1.5,
          markeredgecolor=color_gap, label='Gap%', zorder=3)
ax3a.fill_between(iterations, gap_curve, alpha=0.1, color=color_gap)
ax3a.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax3a.set_ylabel('Gap (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16, color=color_gap)
ax3a.tick_params(axis='y', labelcolor=color_gap, labelsize=12)
ax3a.set_xlim(-1, 52)
ax3a.set_ylim(0, 100)

# 右Y轴：目标函数值
ax3b = ax3a.twinx()
color_obj = C_GREEN
ax3b.plot(iterations, obj_curve, color=color_obj, linewidth=2.5, marker='s',
          markersize=5, markerfacecolor='white', markeredgewidth=1.5,
          markeredgecolor=color_obj, label='目标函数值', zorder=3)
ax3b.set_ylabel('目标函数值 (元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16, color=color_obj)
ax3b.tick_params(axis='y', labelcolor=color_obj, labelsize=12)
ax3b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{int(v/10000)}万'))

# 合并图例
lines1, labels1 = ax3a.get_legend_handles_labels()
lines2, labels2 = ax3b.get_legend_handles_labels()
ax3a.legend(lines1 + lines2, labels1 + labels2, prop=SOURCE_HAN_MEDIUM,
            fontsize=13, loc='center right', framealpha=0.9, edgecolor='#BBB')

ax3a.set_title('算法收敛过程 — Gap与目标函数值双轴对比', fontproperties=SOURCE_HAN_BOLD,
               fontsize=22, pad=15)
ax3a.grid(True, alpha=0.2, zorder=1)
ax3a.set_axisbelow(True)
ax3a.tick_params(axis='x', labelsize=12)

fig3.tight_layout()
for ext in ["png", "pdf"]:
    fig3.savefig(f"/data/project/yixing-cutting-2026/question2/fig_convergence_dual.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig3.get_facecolor())
plt.close(fig3)
print("✅ 图3: 双Y轴综合收敛图 — fig_convergence_dual.png")


# ═══════════════════════════════════════════════════════════════
# 图4：四合一综合仪表盘
# ═══════════════════════════════════════════════════════════════
fig4 = plt.figure(figsize=(18, 12))
fig4.patch.set_facecolor("#F5F5F5")
gs = fig4.add_gridspec(2, 2, hspace=0.3, wspace=0.25)

# (a) Gap收敛曲线
ax_a = fig4.add_subplot(gs[0, 0])
ax_a.plot(iterations, gap_curve, color=C_BLUE, linewidth=2, marker='o',
          markersize=3, markerfacecolor='white', markeredgewidth=1,
          markeredgecolor=C_BLUE, zorder=3)
ax_a.fill_between(iterations, gap_curve, alpha=0.15, color=C_BLUE)
ax_a.axhline(y=threshold, color=C_RED, linestyle='--', linewidth=1.2, alpha=0.7)
ax_a.set_title('(a) Gap收敛曲线', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_a.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_a.set_ylabel('Gap (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_a.set_xlim(-1, 52); ax_a.set_ylim(0, 100)
ax_a.grid(True, alpha=0.2); ax_a.set_axisbelow(True)
ax_a.tick_params(axis='both', labelsize=11)

# (b) 目标函数值收敛
ax_b = fig4.add_subplot(gs[0, 1])
ax_b.plot(iterations, obj_curve, color=C_GREEN, linewidth=2, marker='s',
          markersize=3, markerfacecolor='white', markeredgewidth=1,
          markeredgecolor=C_GREEN, zorder=3)
ax_b.fill_between(iterations, obj_curve, alpha=0.12, color=C_GREEN)
ax_b.set_title('(b) 目标函数值收敛', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_b.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_b.set_ylabel('目标函数值 (元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_b.set_xlim(-1, 52)
ax_b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{int(v/10000)}万'))
ax_b.grid(True, alpha=0.2); ax_b.set_axisbelow(True)
ax_b.tick_params(axis='both', labelsize=11)

# (c) 每轮改进量
improvements = np.diff(gap_curve)
improvements = np.insert(improvements, 0, 0)
colors_imp = [C_RED if x < 0 else C_GREEN for x in improvements]
ax_c = fig4.add_subplot(gs[1, 0])
ax_c.bar(iterations, improvements, color=colors_imp, alpha=0.7, edgecolor='white', linewidth=0.5, zorder=2)
ax_c.axhline(y=0, color='#333', linewidth=0.8)
ax_c.set_title('(c) 每轮Gap变化量', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_c.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_c.set_ylabel('ΔGap (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_c.set_xlim(-1, 52)
ax_c.grid(True, alpha=0.2); ax_c.set_axisbelow(True)
ax_c.tick_params(axis='both', labelsize=11)

# (d) 收敛速度（累计改进百分比）
cumulative_improve = (gap_initial - gap_curve) / gap_initial * 100
ax_d = fig4.add_subplot(gs[1, 1])
ax_d.plot(iterations, cumulative_improve, color=C_ORANGE, linewidth=2.5, marker='D',
          markersize=4, markerfacecolor='white', markeredgewidth=1.5,
          markeredgecolor=C_ORANGE, zorder=3)
ax_d.fill_between(iterations, cumulative_improve, alpha=0.15, color=C_ORANGE)
ax_d.axhline(y=95, color=C_RED, linestyle='--', linewidth=1.2, alpha=0.7)
ax_d.text(51, 96, '95%改进线', fontproperties=SOURCE_HAN, fontsize=10, color=C_RED, ha='right')
ax_d.set_title('(d) 累计改进百分比', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_d.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_d.set_ylabel('累计改进 (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_d.set_xlim(-1, 52); ax_d.set_ylim(0, 105)
ax_d.grid(True, alpha=0.2); ax_d.set_axisbelow(True)
ax_d.tick_params(axis='both', labelsize=11)

fig4.suptitle("算法收敛性综合分析", fontproperties=SOURCE_HAN_BOLD,
              fontsize=25, y=1.01, color="#111")
for ext in ["png", "pdf"]:
    fig4.savefig(f"/data/project/yixing-cutting-2026/question2/fig_convergence_dashboard.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig4.get_facecolor())
plt.close(fig4)
print("✅ 图4: 四合一综合仪表盘 — fig_convergence_dashboard.png")


print("\n🎉 全部 4 组收敛性图表生成完毕!")
print("  图1: fig_convergence_gap.png      — Gap收敛曲线")
print("  图2: fig_convergence_obj.png      — 目标函数值收敛曲线")
print("  图3: fig_convergence_dual.png     — 双Y轴综合收敛图")
print("  图4: fig_convergence_dashboard.png — 四合一综合仪表盘")

