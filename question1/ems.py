"""EMS (Empty Maximal Spaces) 算法核心实现"""

import copy
import itertools
from dataclasses import dataclass


@dataclass
class Space:
    """空闲空间: 原点 (x,y,z) + 三轴尺寸 (dx,dy,dz)"""
    x: int; y: int; z: int
    dx: int; dy: int; dz: int

    @property
    def volume(self):
        return self.dx * self.dy * self.dz

    def can_fit(self, dx, dy, dz):
        return self.dx >= dx and self.dy >= dy and self.dz >= dz

    def get_intersection(self, other: "Space") -> "Space | None":
        """计算两个空间的交集"""
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        z1 = max(self.z, other.z)
        x2 = min(self.x + self.dx, other.x + other.dx)
        y2 = min(self.y + self.dy, other.y + other.dy)
        z2 = min(self.z + self.dz, other.z + other.dz)
        if x1 < x2 and y1 < y2 and z1 < z2:
            return Space(x1, y1, z1, x2 - x1, y2 - y1, z2 - z1)
        return None

    def __hash__(self):
        return hash((self.x, self.y, self.z, self.dx, self.dy, self.dz))


def get_orientations(l, w, h):
    """生成工件的 6 种旋转姿态 (去重)"""
    perms = set()
    for p in itertools.permutations([l, w, h]):
        perms.add(p)
    return list(perms)


def _split_space(space: Space, px: int, py: int, pz: int,
                 dx: int, dy: int, dz: int) -> list[Space]:
    """从 space 里切除 (px,py,pz,dx,dy,dz) 区域，返回剩余子空间"""
    new_spaces = []
    ex, ey, ez = space.x + space.dx, space.y + space.dy, space.z + space.dz

    # 六个方向: 下、上、前、后、左、右
    candidates = [
        Space(space.x, space.y, space.z, space.dx, space.dy, pz - space.z),           # 下方
        Space(space.x, space.y, pz + dz, space.dx, space.dy, ez - (pz + dz)),          # 上方
        Space(space.x, space.y, pz, space.dx, py - space.y, dz),                       # 前方(y小)
        Space(space.x, py + dy, pz, space.dx, ey - (py + dy), dz),                     # 后方(y大)
        Space(space.x, py, pz, px - space.x, dy, dz),                                  # 左方(x小)
        Space(px + dx, py, pz, ex - (px + dx), dy, dz),                                # 右方(x大)
    ]
    for s in candidates:
        if s.dx > 0 and s.dy > 0 and s.dz > 0:
            new_spaces.append(s)
    return new_spaces


class EMSBin:
    """单个原材料块的 EMS 打包器"""

    def __init__(self, name: str, L: int, W: int, H: int):
        self.name = name
        self.L, self.W, self.H = L, W, H
        self.spaces: list[Space] = [Space(0, 0, 0, L, W, H)]
        self.placed: list[dict] = []

    @property
    def used_volume(self):
        return sum(it["dx"] * it["dy"] * it["dz"] for it in self.placed)

    @property
    def utilization(self):
        return self.used_volume / (self.L * self.W * self.H)

    def remove_intersections(self, item_space: Space):
        """移除所有空间中与被放置工件相交的部分"""
        new_spaces = []
        for s in self.spaces:
            inter = s.get_intersection(item_space)
            if inter is None:
                new_spaces.append(s)
            else:
                # 用空间分裂切除相交部分
                fragments = _split_space(s, inter.x, inter.y, inter.z,
                                         inter.dx, inter.dy, inter.dz)
                new_spaces.extend(fragments)
        self.spaces = new_spaces

    def try_merge_spaces(self):
        """合并相邻空间: 共享完整面且另两轴对齐"""
        merged = True
        while merged:
            merged = False
            for i in range(len(self.spaces)):
                for j in range(i + 1, len(self.spaces)):
                    s1, s2 = self.spaces[i], self.spaces[j]
                    m = self._try_merge_pair(s1, s2)
                    if m:
                        self.spaces.pop(j)
                        self.spaces.pop(i)
                        self.spaces.append(m)
                        merged = True
                        break
                if merged:
                    break

    def _try_merge_pair(self, a: Space, b: Space) -> Space | None:
        """尝试合并两个空间，成功返回新空间否则 None"""
        # x轴合并: a右面 == b左面, y和z对齐
        if abs((a.x + a.dx) - b.x) < 1e-6 and a.y == b.y and a.z == b.z \
           and a.dy == b.dy and a.dz == b.dz:
            return Space(a.x, a.y, a.z, a.dx + b.dx, a.dy, a.dz)
        if abs((b.x + b.dx) - a.x) < 1e-6 and a.y == b.y and a.z == b.z \
           and a.dy == b.dy and a.dz == b.dz:
            return Space(b.x, b.y, b.z, a.dx + b.dx, a.dy, a.dz)

        # y轴合并
        if abs((a.y + a.dy) - b.y) < 1e-6 and a.x == b.x and a.z == b.z \
           and a.dx == b.dx and a.dz == b.dz:
            return Space(a.x, a.y, a.z, a.dx, a.dy + b.dy, a.dz)
        if abs((b.y + b.dy) - a.y) < 1e-6 and a.x == b.x and a.z == b.z \
           and a.dx == b.dx and a.dz == b.dz:
            return Space(b.x, b.y, b.z, a.dx, a.dy + b.dy, a.dz)

        # z轴合并
        if abs((a.z + a.dz) - b.z) < 1e-6 and a.x == b.x and a.y == b.y \
           and a.dx == b.dx and a.dy == b.dy:
            return Space(a.x, a.y, a.z, a.dx, a.dy, a.dz + b.dz)
        if abs((b.z + b.dz) - a.z) < 1e-6 and a.x == b.x and a.y == b.y \
           and a.dx == b.dx and a.dy == b.dy:
            return Space(b.x, b.y, b.z, a.dx, a.dy, a.dz + b.dz)

        return None

    def pack(self, items: list[tuple[str, int, int, int]],
             sort_key=None) -> list[dict]:
        """贪心打包

        items: [(type_name, dx, dy, dz), ...]
        sort_key: 排序函数, 决定候选顺序
        """
        self.spaces = [Space(0, 0, 0, self.L, self.W, self.H)]
        self.placed = []
        remaining = list(items)

        while remaining:
            best_score = float("inf")
            best_choice = None  # (item_idx, space_idx, placement)

            for i, item in enumerate(remaining):
                name, dx, dy, dz = item
                for j, sp in enumerate(self.spaces):
                    if not sp.can_fit(dx, dy, dz):
                        continue
                    # Best-Fit: 三轴间隙和最小
                    score = (sp.dx - dx) + (sp.dy - dy) + (sp.dz - dz)
                    if score < best_score:
                        best_score = score
                        best_choice = (i, j, sp)

            if best_choice is None:
                break  # 没有可放置的了

            i, j, sp = best_choice
            name, dx, dy, dz = remaining.pop(i)

            # 放置工件 — 放在空间原点
            placed = {
                "type": name,
                "x": sp.x, "y": sp.y, "z": sp.z,
                "dx": dx, "dy": dy, "dz": dz,
            }
            self.placed.append(placed)

            item_space = Space(sp.x, sp.y, sp.z, dx, dy, dz)

            # 分裂被使用的空间
            self.spaces.pop(j)
            fragments = _split_space(sp, sp.x, sp.y, sp.z, dx, dy, dz)
            self.spaces.extend(fragments)

            # 切除其他空间的相交部分
            self.remove_intersections(item_space)

            # 合并相邻空间
            self.try_merge_spaces()

        return self.placed

    def gap_fill(self, small_items: list[tuple[str, int, int, int]]):
        """缝隙填充: 在主打包后用小块填充剩余空间"""
        return self.pack(small_items)


def create_candidates(workpiece_data: list, with_orientations=True):
    """从工件数据生成候选列表

    workpiece_data: [(name, l, w, h, profit), ...]
    returns: [(name_dx_dy_dz, dx, dy, dz), ...]
    """
    candidates = []
    for name, l, w, h, profit in workpiece_data:
        if with_orientations:
            orients = get_orientations(l, w, h)
            for dx, dy, dz in orients:
                candidates.append((f"{name}_{dx}x{dy}x{dz}", dx, dy, dz))
        else:
            candidates.append((f"{name}_{l}x{w}x{h}", l, w, h))
    return candidates


def sort_by_volume(items):
    """按体积降序排列"""
    return sorted(items, key=lambda x: x[1] * x[2] * x[3], reverse=True)


def sort_by_footprint(items):
    """按底面积降序排列"""
    return sorted(items, key=lambda x: x[1] * x[2], reverse=True)


def sort_by_longest(items):
    """按最长边降序排列"""
    return sorted(items, key=lambda x: max(x[1], x[2], x[3]), reverse=True)


SORT_STRATEGIES = [
    ("volume_desc", sort_by_volume),
    ("footprint_desc", sort_by_footprint),
    ("longest_desc", sort_by_longest),
]
