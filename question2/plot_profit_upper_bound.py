"""
子问题2利润上界分析 - 优化版饼图
展示实际利润与理论上界的差距分析
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 数据准备 ==========
labels = ['已实现利润', '几何约束损耗', '工件组合效率损耗', '块间不可转移废料']
sizes = [86.27, 8.5, 6.0, 2.5]
colors = ['#4CAF50', '#FF9800', '#2196F3', '#9C27B0']
explode = (0.05, 0.08, 0.08, 0.08)

# ========== 创建图形 ==========
fig, ax = plt.subplots(figsize=(12, 8))

# ========== 绘制饼图 ==========
wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=None,
                                    colors=colors, autopct='',
                                    shadow=True, startangle=90,
                                    pctdistance=0.75)

# ========== 手动添加标签（避免重叠） ==========
# 计算每个扇形的中心角度
total = sum(sizes)
angles = []
start = 90  # 起始角度
for size in sizes:
    end = start + 360 * size / total
    angles.append((start + end) / 2)
    start = end

# 标签位置和偏移
label_offsets = [
    (1.4, 0.3),   # 已实现利润 - 右上
    (1.3, 0.2),   # 几何约束损耗 - 右
    (1.3, 0.2),   # 工件组合效率损耗 - 右下
    (1.3, 0.2),   # 块间不可转移废料 - 左下
]

# 添加标签
for i, (label, angle, offset) in enumerate(zip(labels, angles, label_offsets)):
    rad = np.radians(angle)
    x = offset[0] * np.cos(rad)
    y = offset[0] * np.sin(rad)

    # 标签线
    ax.plot([0.95*np.cos(rad), x], [0.95*np.sin(rad), y],
            color='gray', linewidth=1, alpha=0.7)

    # 标签文本
    if i == 0:  # 已实现利润
        text = f'{label}\n727,990元 (86.27%)'
    elif i == 1:  # 几何约束损耗
        text = f'{label}\n~8.5% (~9,850元)'
    elif i == 2:  # 工件组合效率损耗
        text = f'{label}\n~6% (~6,950元)'
    else:  # 块间不可转移废料
        text = f'{label}\n~2.5% (~2,900元)'

    ax.text(x, y, text, ha='center', va='center', fontsize=9,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                     alpha=0.9, edgecolor='gray'))

# ========== 标题 ==========
plt.title('子问题2利润上界分析\n理论上界: 843,840元 | 实际利润: 727,990元 (86.27%)',
         fontsize=14, fontweight='bold', pad=20)

# ========== 保存图片 ==========
plt.savefig('/data/project/yixing-cutting-2026/question2/profit_upper_bound_3d.png',
            dpi=200, bbox_inches='tight', facecolor='white')
plt.savefig('/data/project/yixing-cutting-2026/question2/profit_upper_bound_3d.pdf',
            bbox_inches='tight', facecolor='white')

print("Done: profit_upper_bound_3d.png/pdf")
