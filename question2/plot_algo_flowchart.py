"""
子问题2算法流程图 - 多策略两阶段EMS贪心 + ILS混合求解
风格参考：圆角矩形框 + 箭头连接，简洁有力
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# 中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(1, 1, figsize=(14, 7))
ax.set_xlim(0, 14)
ax.set_ylim(0, 7)
ax.axis('off')

def draw_box(ax, x, y, w, h, text, fontsize=9, color='#E8F0FE', edge_color='#4A90D9',
             linewidth=1.5, bold=False, alpha=1.0):
    """绘制圆角矩形框"""
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle="round,pad=0.05",
                         facecolor=color, edgecolor=edge_color,
                         linewidth=linewidth, alpha=alpha, zorder=2)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            fontweight=weight, zorder=3, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color='#666666', lw=1.2, style='->', shrinkA=0, shrinkB=0):
    """绘制箭头"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                               shrinkA=shrinkA, shrinkB=shrinkB),
                zorder=1)

# ========== 布局参数 ==========
# 左侧输入列
input_x = 1.5
# 构造阶段
construct_x = 5.0
# ILS阶段
ils_x = 9.0
# 输出
output_x = 12.5

# ========== 左侧：输入 ==========
y_input = [5.8, 4.5, 3.2]
draw_box(ax, input_x, y_input[0], 2.2, 0.7, '70件必须品\n(每种10件)', fontsize=9,
         color='#FFF3E0', edge_color='#E65100', linewidth=1.5)
draw_box(ax, input_x, y_input[1], 2.2, 0.7, '~3,700件候选工件\n(利润密度降序)', fontsize=9,
         color='#FFF3E0', edge_color='#E65100', linewidth=1.5)
draw_box(ax, input_x, y_input[2], 2.2, 0.7, '15块原材料\n(3000×2100×300mm)', fontsize=9,
         color='#FFF3E0', edge_color='#E65100', linewidth=1.5)

# ========== 中间：48次多策略构造 ==========
# 大框
draw_box(ax, construct_x, 4.5, 4.5, 3.5, '', fontsize=10,
         color='#F5F5F5', edge_color='#888888', linewidth=2, alpha=0.5)
ax.text(construct_x, 6.1, '48次多策略构造', ha='center', va='center',
        fontsize=11, fontweight='bold', color='#333333', zorder=3)

# Phase 1
draw_box(ax, construct_x, 5.1, 3.8, 0.65, 'Phase 1: 必须品保证 — 5种排序策略轮换', fontsize=9,
         color='#E3F2FD', edge_color='#1565C0', linewidth=1.5, bold=True)
ax.text(construct_x, 4.55, '体积降序 / 最长边降序 / 利润密度降序 / 混合排序 / 随机排序',
        ha='center', va='center', fontsize=7.5, color='#555555', zorder=3)

# Phase 2
draw_box(ax, construct_x, 3.7, 3.8, 0.65, 'Phase 2: 利润填充 — 利润密度降序Best-Fit', fontsize=9,
         color='#E8F5E9', edge_color='#2E7D32', linewidth=1.5, bold=True)
ax.text(construct_x, 3.15, '预生成填充池 + 小件缝隙填充',
        ha='center', va='center', fontsize=7.5, color='#555555', zorder=3)

# 验证
draw_box(ax, construct_x, 2.5, 3.0, 0.5, '验证 ≥10约束 → 保留全局最优', fontsize=8,
         color='#F3E5F5', edge_color='#7B1FA2', linewidth=1.2)

# ========== 右侧：ILS迭代 ==========
# 大框
draw_box(ax, ils_x, 4.5, 3.8, 3.5, '', fontsize=10,
         color='#F5F5F5', edge_color='#888888', linewidth=2, alpha=0.5)
ax.text(ils_x, 6.1, 'ILS 800轮迭代', ha='center', va='center',
        fontsize=11, fontweight='bold', color='#333333', zorder=3)

# Destroy
draw_box(ax, ils_x, 5.1, 3.2, 0.65, 'Destroy: 移除15%非必须品', fontsize=9,
         color='#FFEBEE', edge_color='#C62828', linewidth=1.5, bold=True)
ax.text(ils_x, 4.55, '70%偏向低利润密度 + 30%随机',
        ha='center', va='center', fontsize=7.5, color='#555555', zorder=3)

# Repair
draw_box(ax, ils_x, 3.7, 3.2, 0.65, 'Repair: 利润密度降序重打包', fontsize=9,
         color='#E8F5E9', edge_color='#2E7D32', linewidth=1.5, bold=True)
ax.text(ils_x, 3.15, '15块重置 + ~2000件填充候选池',
        ha='center', va='center', fontsize=7.5, color='#555555', zorder=3)

# Accept
draw_box(ax, ils_x, 2.5, 2.8, 0.5, 'Accept: 仅当利润增加时接受 (爬山策略)', fontsize=8,
         color='#FFF8E1', edge_color='#F57F17', linewidth=1.2)

# ========== 输出 ==========
draw_box(ax, output_x, 4.5, 2.0, 1.2, '全局最优解\n利润: 727,990',
         fontsize=11, color='#E8F5E9', edge_color='#1B5E20', linewidth=2.5, bold=True)

# ========== 箭头连接 ==========
# 输入 → 构造
for y in y_input:
    draw_arrow(ax, input_x + 1.1, y, construct_x - 2.25, 4.5, color='#999999', lw=1.0)

# Phase 1 → Phase 2
draw_arrow(ax, construct_x, 4.77, construct_x, 4.03, color='#1565C0', lw=1.5)

# Phase 2 → 验证
draw_arrow(ax, construct_x, 3.37, construct_x, 2.75, color='#2E7D32', lw=1.5)

# 构造 → ILS
draw_arrow(ax, construct_x + 2.25, 4.5, ils_x - 1.9, 4.5, color='#666666', lw=1.5, style='->')

# ILS内部: Destroy → Repair → Accept
draw_arrow(ax, ils_x, 4.77, ils_x, 4.03, color='#C62828', lw=1.5)
draw_arrow(ax, ils_x, 3.37, ils_x, 2.75, color='#2E7D32', lw=1.5)

# ILS → 输出
draw_arrow(ax, ils_x + 1.9, 4.5, output_x - 1.0, 4.5, color='#1B5E20', lw=2.0, style='->')

# ========== ILS循环箭头 ==========
# 从Accept画回Destroy的循环箭头
from matplotlib.patches import Arc
# 画一个弧形箭头表示循环
theta1, theta2 = 30, 150
arc = Arc((ils_x + 1.8, 3.8), 1.5, 2.5, angle=0, theta1=theta1, theta2=theta2,
          color='#888888', lw=1.2, linestyle='--', zorder=1)
ax.add_patch(arc)
# 箭头头部
ax.annotate('', xy=(ils_x + 1.2, 5.2), xytext=(ils_x + 2.35, 4.6),
            arrowprops=dict(arrowstyle='->', color='#888888', lw=1.2),
            zorder=1)
ax.text(ils_x + 2.3, 3.8, '×800', ha='center', va='center', fontsize=8,
        color='#888888', style='italic', zorder=3)

# ========== 48次构造循环箭头 ==========
arc2 = Arc((construct_x + 2.3, 3.8), 1.2, 2.0, angle=0, theta1=30, theta2=150,
           color='#888888', lw=1.2, linestyle='--', zorder=1)
ax.add_patch(arc2)
ax.annotate('', xy=(construct_x + 1.8, 5.1), xytext=(construct_x + 2.75, 4.5),
            arrowprops=dict(arrowstyle='->', color='#888888', lw=1.2),
            zorder=1)
ax.text(construct_x + 2.7, 3.8, '×48', ha='center', va='center', fontsize=8,
        color='#888888', style='italic', zorder=3)

plt.tight_layout()
plt.savefig('/data/project/yixing-cutting-2026/question2/algorithm_flowchart.png',
            dpi=200, bbox_inches='tight', facecolor='white')
plt.savefig('/data/project/yixing-cutting-2026/question2/algorithm_flowchart.pdf',
            bbox_inches='tight', facecolor='white')
print("Done: algorithm_flowchart.png/pdf")
