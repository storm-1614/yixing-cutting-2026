# 子问题1

# 数据
RAW_MATERIALS = [
    ("L01", 300, 200, 150, 5),
    ("L02", 250, 150, 100, 5),
    ("L03", 200, 150, 80, 5),
]

WORKPIECES = [
    ("J01", 40, 40, 40, 620),
    ("J02", 50, 40, 40, 780),
    ("J03", 60, 50, 30, 880),
    ("J04", 75, 60, 40, 1850),
    ("J05", 80, 60, 50, 2520),
    ("J06", 100, 50, 20, 1000),
    ("J07", 120, 20, 20, 540),
]

MIN_QUANTITY_P2 = {f"J{i:02d}": 10 for i in range(1, 8)}

# EMS

import itertools
from dataclasses import dataclass


@dataclass
class Space:
    # 空闲空间
    x: int
    y: int
    z: int
    dx: int
    dy: int
    dz: int

    @property
    def volume(self):
        return self.dx * self.dy * self.dz

    def can_fit(self, dx, dy, dz):
        return self.dx >= dx and self.dy >= dy and self.dz >= dz

    def get_intersection(self, other: "Space") -> "Space | None":
        # 计算交集
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
    perms = set()
    for p in itertools.permutations([l, w, h]):
        perms.add(p)
    return list(perms)


def _split_space(
    space: Space, px: int, py: int, pz: int, dx: int, dy: int, dz: int
) -> list[Space]:
    new_spaces = []
    ex, ey, ez = space.x + space.dx, space.y + space.dy, space.z + space.dz

    candidates = [
        Space(space.x, space.y, space.z, space.dx, space.dy, pz - space.z),  # 下
        Space(space.x, space.y, pz + dz, space.dx, space.dy, ez - (pz + dz)),  # 上
        Space(space.x, space.y, pz, space.dx, py - space.y, dz),  # 前
        Space(space.x, py + dy, pz, space.dx, ey - (py + dy), dz),  # 后
        Space(space.x, py, pz, px - space.x, dy, dz),  # 左
        Space(px + dx, py, pz, ex - (px + dx), dy, dz),  # 右
    ]
    for s in candidates:
        if s.dx > 0 and s.dy > 0 and s.dz > 0:
            new_spaces.append(s)
    return new_spaces


class EMSBin:
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
        new_spaces = []
        for s in self.spaces:
            inter = s.get_intersection(item_space)
            if inter is None:
                new_spaces.append(s)
            else:
                fragments = _split_space(
                    s, inter.x, inter.y, inter.z, inter.dx, inter.dy, inter.dz
                )
                new_spaces.extend(fragments)
        self.spaces = new_spaces

    def try_merge_spaces(self):
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
        # x轴合并
        if (
            abs((a.x + a.dx) - b.x) < 1e-6
            and a.y == b.y
            and a.z == b.z
            and a.dy == b.dy
            and a.dz == b.dz
        ):
            return Space(a.x, a.y, a.z, a.dx + b.dx, a.dy, a.dz)
        if (
            abs((b.x + b.dx) - a.x) < 1e-6
            and a.y == b.y
            and a.z == b.z
            and a.dy == b.dy
            and a.dz == b.dz
        ):
            return Space(b.x, b.y, b.z, a.dx + b.dx, a.dy, a.dz)

        # y轴合并
        if (
            abs((a.y + a.dy) - b.y) < 1e-6
            and a.x == b.x
            and a.z == b.z
            and a.dx == b.dx
            and a.dz == b.dz
        ):
            return Space(a.x, a.y, a.z, a.dx, a.dy + b.dy, a.dz)
        if (
            abs((b.y + b.dy) - a.y) < 1e-6
            and a.x == b.x
            and a.z == b.z
            and a.dx == b.dx
            and a.dz == b.dz
        ):
            return Space(b.x, b.y, b.z, a.dx, a.dy + b.dy, a.dz)

        # z轴合并
        if (
            abs((a.z + a.dz) - b.z) < 1e-6
            and a.x == b.x
            and a.y == b.y
            and a.dx == b.dx
            and a.dy == b.dy
        ):
            return Space(a.x, a.y, a.z, a.dx, a.dy, a.dz + b.dz)
        if (
            abs((b.z + b.dz) - a.z) < 1e-6
            and a.x == b.x
            and a.y == b.y
            and a.dx == b.dx
            and a.dy == b.dy
        ):
            return Space(b.x, b.y, b.z, a.dx, a.dy, a.dz + b.dz)

        return None

    def pack(self, items: list[tuple[str, int, int, int]], sort_key=None) -> list[dict]:
        # 贪心打包
        self.spaces = [Space(0, 0, 0, self.L, self.W, self.H)]
        self.placed = []
        remaining = list(items)

        while remaining:
            best_score = float("inf")
            best_choice = None

            for i, item in enumerate(remaining):
                name, dx, dy, dz = item
                for j, sp in enumerate(self.spaces):
                    if not sp.can_fit(dx, dy, dz):
                        continue
                    # Best-Fit
                    score = (sp.dx - dx) + (sp.dy - dy) + (sp.dz - dz)
                    if score < best_score:
                        best_score = score
                        best_choice = (i, j, sp)

            if best_choice is None:
                break

            i, j, sp = best_choice
            name, dx, dy, dz = remaining.pop(i)

            placed = {
                "type": name,
                "x": sp.x,
                "y": sp.y,
                "z": sp.z,
                "dx": dx,
                "dy": dy,
                "dz": dz,
            }
            self.placed.append(placed)

            item_space = Space(sp.x, sp.y, sp.z, dx, dy, dz)

            self.spaces.pop(j)
            fragments = _split_space(sp, sp.x, sp.y, sp.z, dx, dy, dz)
            self.spaces.extend(fragments)

            self.remove_intersections(item_space)

            self.try_merge_spaces()

        return self.placed

    def gap_fill(self, small_items: list[tuple[str, int, int, int]]):
        return self.pack(small_items)


def create_candidates(workpiece_data: list, with_orientations=True):
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
    # 按体积
    return sorted(items, key=lambda x: x[1] * x[2] * x[3], reverse=True)


def sort_by_footprint(items):
    # 按面积
    return sorted(items, key=lambda x: x[1] * x[2], reverse=True)


def sort_by_longest(items):
    # 按最长边
    return sorted(items, key=lambda x: max(x[1], x[2], x[3]), reverse=True)


SORT_STRATEGIES = [
    ("volume_desc", sort_by_volume),
    ("footprint_desc", sort_by_footprint),
    ("longest_desc", sort_by_longest),
]


from collections import Counter


def solve_subproblem1():
    blocks = []
    for name, L, W, H, qty in RAW_MATERIALS:
        for i in range(qty):
            blocks.append((f"{name}_{i + 1}", L, W, H))

    total_volume = sum(L * W * H for _, L, W, H in blocks)

    results = []
    all_placed = []

    for block_name, L, W, H in blocks:
        candidates = create_candidates(
            [(name, l, w, h, _) for name, l, w, h, _ in WORKPIECES],
            with_orientations=True,
        )
        pool = []
        for c in candidates:
            pool.extend([c] * 80)

        best_placed = []
        best_vol = 0

        for strat_name, sort_fn in SORT_STRATEGIES:
            bin_ = EMSBin(block_name, L, W, H)
            sorted_items = sort_fn(list(pool))
            placed = bin_.pack(sorted_items)
            used = sum(p["dx"] * p["dy"] * p["dz"] for p in placed)
            if used > best_vol:
                best_vol = used
                best_placed = placed

        results.append(
            {
                "block": block_name,
                "L": L,
                "W": W,
                "H": H,
                "placed": best_placed,
                "count": len(best_placed),
                "used_vol": best_vol,
                "total_vol": L * W * H,
            }
        )
        all_placed.extend(best_placed)

        print(
            f"  {block_name}: {len(best_placed)} 件, "
            f"利用率 {best_vol / (L * W * H) * 100:.2f}%"
        )

    # 汇总
    total_used = sum(r["used_vol"] for r in results)
    utilization = total_used / total_volume

    print(f"\n子问题1 结果：")
    print(f"原材料总体积:     {total_volume:,}")
    print(f"已使用体积:       {total_used:,}")
    print(f"废料体积:         {total_volume - total_used:,}")
    print(f"总体积利用率:     {utilization * 100:.2f}%")
    print(f"总工件数:         {len(all_placed)}")

    print(f"\n各块详情:")
    for r in results:
        u = r["used_vol"] / r["total_vol"] * 100
        print(f"  {r['block']}: {r['count']:>4} 件, 利用率 {u:.2f}%")

    type_counts = Counter()
    for p in all_placed:
        base_type = p["type"].split("_")[0]
        type_counts[base_type] += 1
    print(f"\n各工件生产数量:")
    for t in sorted(type_counts):
        print(f"  {t}: {type_counts[t]}")

    return results, all_placed, total_volume, total_used


if __name__ == "__main__":
    solve_subproblem1()
