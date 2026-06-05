"""EMS 空间分割 —— 论文用三维示意图"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Source Han Sans CN", "SimHei", "DejaVu Sans"],
    "font.size": 10,
    "axes.unicode_minus": False,
})

# ── 斜二测投影 ──
A = np.radians(30)
def proj(x, y, z, ox=0, oy=0, s=1.0):
    return ox + s*(x - y*np.cos(A)), oy + s*(z - y*np.sin(A))

def cuboid(ax, x, y, z, dx, dy, dz, color, ox=0, oy=0, s=1.0,
           alpha=0.8, lw=1.2, zorder=2):
    """画长方体 (顶/前/右三面)"""
    def p(ix, iy, iz):
        return proj(x + dx*ix, y + dy*iy, z + dz*iz, ox, oy, s)

    def lighten(c, amt=0.15):
        import matplotlib.colors as mc
        r, g, b = mc.to_rgb(c)
        return (min(1, r+amt), min(1, g+amt), min(1, b+amt))

    def darken(c, amt=0.15):
        import matplotlib.colors as mc
        r, g, b = mc.to_rgb(c)
        return (max(0, r-amt), max(0, g-amt), max(0, b-amt))

    ec = darken(color, 0.2)
    # 顶面
    ax.add_patch(Polygon([p(0,0,1), p(1,0,1), p(1,1,1), p(0,1,1)],
                 fc=lighten(color), ec=ec, lw=lw, alpha=alpha, zorder=zorder))
    # 前面 (y=const面)
    ax.add_patch(Polygon([p(0,0,0), p(1,0,0), p(1,0,1), p(0,0,1)],
                 fc=color, ec=ec, lw=lw, alpha=alpha, zorder=zorder))
    # 右面
    ax.add_patch(Polygon([p(1,0,0), p(1,1,0), p(1,1,1), p(1,0,1)],
                 fc=darken(color, 0.12), ec=ec, lw=lw, alpha=alpha, zorder=zorder))

def wireframe(ax, x, y, z, dx, dy, dz, ox=0, oy=0, s=1.0,
              color="#AAA", lw=0.8, zorder=1):
    """线框"""
    def p(ix, iy, iz):
        return proj(x + dx*ix, y + dy*iy, z + dz*iz, ox, oy, s)
    for ix in [0, 1]:
        for iy in [0, 1]:
            a, b = p(ix, iy, 0), p(ix, iy, 1)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=zorder)
    for iz in [0, 1]:
        for ix in [0, 1]:
            a, b = p(ix, 0, iz), p(ix, 1, iz)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=zorder)
        for iy in [0, 1]:
            a, b = p(0, iy, iz), p(1, iy, iz)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=zorder)

def label3d(ax, x, y, z, text, ox=0, oy=0, s=1.0, **kw):
    px, py = proj(x, y, z, ox, oy, s)
    ax.text(px, py, text, **kw)

# ── 画布 ──
fig, ax = plt.subplots(figsize=(10, 8))
ax.set_xlim(-1, 14)
ax.set_ylim(-1, 11)
ax.set_aspect("equal")
ax.axis("off")

# 空间 6×5×4，工件 2×1.5×1.5 贴原点角
SX, SY, SZ = 6, 5, 4
IX, IY, IZ = 2, 1.5, 1.5
OX, OY, SC = 2, 3.5, 1.3

# 空间线框
wireframe(ax, 0, 0, 0, SX, SY, SZ, OX, OY, SC)

# 三个子空间
cuboid(ax, 0, 0, IZ, SX, SY, SZ-IZ, "#3498DB", OX, OY, SC, alpha=0.55)   # 上
cuboid(ax, 0, IY, 0, SX, SY-IY, SZ, "#E67E22", OX, OY, SC, alpha=0.55)   # 后
cuboid(ax, IX, 0, 0, SX-IX, SY, SZ, "#27AE60", OX, OY, SC, alpha=0.55)   # 右

# 工件
cuboid(ax, 0, 0, 0, IX, IY, IZ, "#E74C3C", OX, OY, SC, alpha=0.92, lw=1.8, zorder=5)

# 标签
label3d(ax, SX/2, 0, IZ+(SZ-IZ)/2, "上方", OX, OY, SC, fontsize=12, color="#2471A3", weight="bold", ha="center")
label3d(ax, 0, IY+(SY-IY)/2, SZ/2, "后方", OX, OY, SC, fontsize=12, color="#B9770E", weight="bold", ha="center", va="center")
label3d(ax, IX+(SX-IX)/2, SY/2, 0, "右方", OX, OY, SC, fontsize=12, color="#1E7E34", weight="bold", ha="center")

# 坐标
label3d(ax, SX+0.4, 0, 0, "x", OX, OY, SC, fontsize=10, weight="bold")
label3d(ax, 0, SY+0.4, 0, "y", OX, OY, SC, fontsize=10, weight="bold")
label3d(ax, 0, 0, SZ+0.4, "z", OX, OY, SC, fontsize=10, weight="bold")

fig.tight_layout(pad=0.3)
out = "/data/project/yixing-cutting-2026/question1/ems_space_split"
fig.savefig(out + ".png", dpi=200, bbox_inches="tight", facecolor="white")
fig.savefig(out + ".pdf", bbox_inches="tight", facecolor="white")
print(f"✅ {out}.png/.pdf")
