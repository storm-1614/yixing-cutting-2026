"""
子问题2利润上界分析 - 最终3D饼图
展示实际利润与理论上界的差距分析
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 数据准备 ==========
labels = ['已实现利润', '几何约束损耗', '工件组合效率损耗', '块间不可转移废料']
sizes = [86.27, 8.5, 6.0, 2.5]
colors = ['#4CAF50', '#FF9800', '#2196F3', '#9C27B0']
explode = (0.05, 0.08, 0.08, 0.08)

# 计算角度
total = sum(sizes)
angles = []
start = 90  # 起始角度（度）
for size in sizes:
    end = start + 360 * size / total
    angles.append((start, end))
    start = end

def draw_3d_pie(ax, sizes, colors, explode, angles, height=0.3):
    """绘制3D饼图"""
    # 绘制底部
    for i, (size, color, ang) in enumerate(zip(sizes, colors, angles)):
        theta = np.linspace(np.radians(ang[0]), np.radians(ang[1]), 100)
        x = np.cos(theta)
        y = np.sin(theta)
        ax.plot(x, y, zs=0, zdir='z', color=color, linewidth=2)
        z_bottom = np.zeros_like(x)
        ax.plot_trisurf(x, y, z_bottom, alpha=0.5, color=color)

    # 绘制顶部
    for i, (size, color, ang) in enumerate(zip(sizes, colors, angles)):
        theta = np.linspace(np.radians(ang[0]), np.radians(ang[1]), 100)
        x = np.cos(theta)
        y = np.sin(theta)
        ax.plot(x, y, zs=height, zdir='z', color=color, linewidth=2)
        z_top = np.full_like(x, height)
        ax.plot_trisurf(x, y, z_top, alpha=0.9, color=color)

    # 绘制侧面
    for i, (size, color, ang) in enumerate(zip(sizes, colors, angles)):
        theta = np.linspace(np.radians(ang[0]), np.radians(ang[1]), 50)
        x = np.cos(theta)
        y = np.sin(theta)

        for j in range(len(x)-1):
            # 底部到顶部的线
            ax.plot([x[j], x[j]], [y[j], y[j]], [0, height],
                   color=color, linewidth=1, alpha=0.7)

# ========== 主函数 ==========
def main():
    # 创建图形
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')

    # 绘制3D饼图
    draw_3d_pie(ax, sizes, colors, explode, angles, height=0.4)

    # 设置视角
    ax.view_init(elev=25, azim=45)

    # 设置坐标轴范围
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_zlim(0, 0.6)

    # 设置坐标轴比例
    ax.set_box_aspect([1, 1, 0.3])

    # 隐藏坐标轴
    ax.axis('off')

    # ========== 添加标签 ==========
    # 计算每个扇形的中心角度
    label_angles = []
    for ang in angles:
        center_angle = (ang[0] + ang[1]) / 2
        label_angles.append(center_angle)

    # 手动调整标签位置避免重叠
    label_offsets = [
        (1.6, 0.5),   # 已实现利润 - 左上方
        (1.5, 0.3),   # 几何约束损耗 - 右方
        (1.4, 0.3),   # 工件组合效率损耗 - 右下方
        (1.3, 0.3),   # 块间不可转移废料 - 下方
    ]

    # 添加标签
    for i, (label, angle, offset) in enumerate(zip(labels, label_angles, label_offsets)):
        rad = np.radians(angle)
        x = offset[0] * np.cos(rad)
        y = offset[0] * np.sin(rad)

        # 标签线
        ax.plot([1.05*np.cos(rad), x], [1.05*np.sin(rad), y], [0.4, 0.4],
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

        ax.text(x, y, 0.4, text, ha='center', va='center', fontsize=9,
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

if __name__ == '__main__':
    main()