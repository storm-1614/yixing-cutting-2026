# 子问题 3

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from itertools import permutations
from copy import deepcopy
import time
import random


# 数据
@dataclass
class Material:
    name: str
    length: int
    width: int
    height: int
    quantity: int

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class Workpiece:
    name: str
    length: int
    width: int
    height: int
    profit: int

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    @property
    def profit_density(self) -> float:
        return self.profit / self.volume

    def get_orientations(self) -> List[Tuple[int, int, int]]:
        seen = set()
        res = []
        for p in permutations([self.length, self.width, self.height]):
            if p not in seen:
                seen.add(p)
                res.append(p)
        return res


AVAILABLE_MATERIALS = [
    Material("L01", 300, 200, 150, 2),
    Material("L02", 250, 150, 100, 2),
    Material("L03", 200, 150, 80, 1),
]
TOTAL_AVAIL_VOL = sum(m.volume * m.quantity for m in AVAILABLE_MATERIALS)

WORKPIECES = [
    Workpiece("J01", 40, 40, 40, 620),
    Workpiece("J02", 50, 40, 40, 780),
    Workpiece("J03", 60, 50, 30, 880),
    Workpiece("J04", 75, 60, 40, 1850),
    Workpiece("J05", 80, 60, 50, 2520),
    Workpiece("J06", 100, 50, 20, 1000),
    Workpiece("J07", 120, 20, 20, 540),
]
WP_MAP = {wp.name: wp for wp in WORKPIECES}

STOCK = {"J01": 0, "J02": 0, "J03": 20, "J04": 0, "J05": 3, "J06": 11, "J07": 19}

ORDERS = {
    "H01": {"J03": 24, "J04": 54, "J05": 25, "J06": 80, "J07": 40},
    "H02": {"J01": 48, "J02": 200, "J03": 70, "J05": 11, "J06": 11, "J07": 56},
    "H03": {"J03": 27, "J04": 54, "J05": 27, "J06": 115, "J07": 44},
}


# EMS
@dataclass
class Space:
    x: int
    y: int
    z: int
    dx: int
    dy: int
    dz: int

    def can_fit(self, dx, dy, dz):
        return self.dx >= dx and self.dy >= dy and self.dz >= dz


def get_intersection(sp, ix, iy, iz, idx, idy, idz):
    x1, y1, z1 = max(sp.x, ix), max(sp.y, iy), max(sp.z, iz)
    x2 = min(sp.x + sp.dx, ix + idx)
    y2 = min(sp.y + sp.dy, iy + idy)
    z2 = min(sp.z + sp.dz, iz + idz)
    return (
        (x1, y1, z1, x2 - x1, y2 - y1, z2 - z1)
        if x1 < x2 and y1 < y2 and z1 < z2
        else None
    )


def split_space(sp, rx, ry, rz, rdx, rdy, rdz):
    res = []
    if rz - sp.z > 0:
        res.append(Space(sp.x, sp.y, sp.z, sp.dx, sp.dy, rz - sp.z))
    if sp.z + sp.dz - rz - rdz > 0:
        res.append(Space(sp.x, sp.y, rz + rdz, sp.dx, sp.dy, sp.z + sp.dz - rz - rdz))
    if ry - sp.y > 0:
        res.append(Space(sp.x, sp.y, rz, sp.dx, ry - sp.y, rdz))
    if sp.y + sp.dy - ry - rdy > 0:
        res.append(Space(sp.x, ry + rdy, rz, sp.dx, sp.y + sp.dy - ry - rdy, rdz))
    if rx - sp.x > 0:
        res.append(Space(sp.x, ry, rz, rx - sp.x, rdy, rdz))
    if sp.x + sp.dx - rx - rdx > 0:
        res.append(Space(rx + rdx, ry, rz, sp.x + sp.dx - rx - rdx, rdy, rdz))
    return res


def merge_spaces(spaces):
    if len(spaces) <= 1:
        return spaces
    changed = True
    cur = list(spaces)
    while changed:
        changed = False
        n = len(cur)
        mrg, used = [], [False] * n
        for i in range(n):
            if used[i]:
                continue
            si, found = cur[i], False
            for j in range(n):
                if i == j or used[j]:
                    continue
                sj = cur[j]
                merged = None
                if si.x == sj.x and si.dx == sj.dx and si.z == sj.z and si.dz == sj.dz:
                    if si.y + si.dy == sj.y:
                        merged = Space(si.x, si.y, si.z, si.dx, si.dy + sj.dy, si.dz)
                    elif sj.y + sj.dy == si.y:
                        merged = Space(sj.x, sj.y, sj.z, sj.dx, sj.dy + si.dy, sj.dz)
                elif (
                    si.y == sj.y and si.dy == sj.dy and si.z == sj.z and si.dz == sj.dz
                ):
                    if si.x + si.dx == sj.x:
                        merged = Space(si.x, si.y, si.z, si.dx + sj.dx, si.dy, si.dz)
                    elif sj.x + sj.dx == si.x:
                        merged = Space(sj.x, sj.y, sj.z, sj.dx + si.dx, sj.dy, sj.dz)
                elif (
                    si.x == sj.x and si.dx == sj.dx and si.y == sj.y and si.dy == sj.dy
                ):
                    if si.z + si.dz == sj.z:
                        merged = Space(si.x, si.y, si.z, si.dx, si.dy, si.dz + sj.dz)
                    elif sj.z + sj.dz == si.z:
                        merged = Space(sj.x, sj.y, sj.z, sj.dx, sj.dy, sj.dz + si.dz)
                if merged is not None:
                    mrg.append(merged)
                    used[i] = used[j] = found = changed = True
                    break
            if not found:
                mrg.append(si)
                used[i] = True
        cur = mrg
    return cur


class BlockPacker:
    def __init__(self, dx, dy, dz):
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces = [Space(0, 0, 0, dx, dy, dz)]
        self.placements = []

    def copy(self):
        # 深拷贝（浪费时间的东西
        pk = BlockPacker(*self.dims)
        pk.spaces = deepcopy(self.spaces)
        pk.placements = list(self.placements)
        return pk

    def try_place(self, name, dx, dy, dz):
        fitting = [(i, s) for i, s in enumerate(self.spaces) if s.can_fit(dx, dy, dz)]
        if not fitting:
            return None
        bi, bs = min(
            fitting, key=lambda x: (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz)
        )
        px, py, pz = bs.x, bs.y, bs.z
        used = self.spaces.pop(bi)
        new_sps = split_space(used, px, py, pz, dx, dy, dz)
        cleaned = []
        for s in self.spaces:
            inter = get_intersection(s, px, py, pz, dx, dy, dz)
            if inter is None:
                cleaned.append(s)
            else:
                cleaned.extend(split_space(s, *inter))
        self.spaces = cleaned + new_sps
        if len(self.spaces) > 150:
            self.spaces = merge_spaces(self.spaces)
        self.placements.append((name, px, py, pz, dx, dy, dz))
        return (px, py, pz)

    def get_top_candidates(self, remaining_dict, M):
        # 遍历面
        scored = []
        for nm, count in remaining_dict.items():
            if count <= 0:
                continue
            wp = WP_MAP[nm]
            for dx, dy, dz in wp.get_orientations():
                fitting = [
                    (j, s) for j, s in enumerate(self.spaces) if s.can_fit(dx, dy, dz)
                ]
                if not fitting:
                    continue
                _, bs = min(
                    fitting,
                    key=lambda x: (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz),
                )
                score = (bs.dx - dx) + (bs.dy - dy) + (bs.dz - dz)
                scored.append((score, nm, dx, dy, dz))
        scored.sort(key=lambda x: x[0])
        # 去重
        seen = set()
        unique = []
        for s in scored:
            if s[1] not in seen:
                seen.add(s[1])
                unique.append(s)
        return unique[:M]

    def get_used_volume(self):
        return sum(dx * dy * dz for _, _, _, _, dx, dy, dz in self.placements)

    def get_waste(self):
        return self.volume - self.get_used_volume()


# 多策略贪心求解器
def solve_order_greedy(order_name, order_demand, ordering):
    need = {}
    for wp in WORKPIECES:
        d = order_demand.get(wp.name, 0)
        s = STOCK.get(wp.name, 0)
        n = max(0, d - s)
        if n > 0:
            need[wp.name] = n

    stock_profit = sum(
        min(STOCK.get(wp.name, 0), order_demand.get(wp.name, 0)) * wp.profit
        for wp in WORKPIECES
    )

    block_dims = [
        (f"{m.name}_{i + 1}", m.length, m.width, m.height)
        for m in AVAILABLE_MATERIALS
        for i in range(m.quantity)
    ]
    packers = [BlockPacker(dx, dy, dz) for _, dx, dy, dz in block_dims]
    pnames = [name for name, _, _, _ in block_dims]

    placed = {}

    for wp_name in ordering:
        if wp_name not in need:
            continue
        target = need[wp_name]
        count = 0
        wp = WP_MAP[wp_name]
        orientations = wp.get_orientations()

        while count < target:
            best_fit = None
            for pi, pk in enumerate(packers):
                for dx, dy, dz in orientations:
                    fitting = [
                        (j, s) for j, s in enumerate(pk.spaces) if s.can_fit(dx, dy, dz)
                    ]
                    if not fitting:
                        continue
                    _, bs = min(
                        fitting,
                        key=lambda x: (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz),
                    )
                    gap = (bs.dx - dx) + (bs.dy - dy) + (bs.dz - dz)
                    if best_fit is None or gap < best_fit[0]:
                        best_fit = (gap, pi, dx, dy, dz)

            if best_fit is None:
                break  # 工件放不下了

            _, pi, dx, dy, dz = best_fit
            packers[pi].try_place(wp_name, dx, dy, dz)
            count += 1

        placed[wp_name] = count

    # 统计结果
    emergency = {}
    emergency_loss = 0
    for wp in WORKPIECES:
        d = order_demand.get(wp.name, 0)
        s = STOCK.get(wp.name, 0)
        p = placed.get(wp.name, 0)
        short = max(0, d - s - p)
        if short > 0:
            emergency[wp.name] = short
            emergency_loss += short * wp.profit

    produced_profit = sum(WP_MAP[n].profit * c for n, c in placed.items())
    net_profit = stock_profit + produced_profit - emergency_loss

    results = {}
    for i, pk in enumerate(packers):
        bname = pnames[i]
        results[bname] = {
            "dims": pk.dims,
            "placements": pk.placements,
            "utilization": pk.get_used_volume() / pk.volume if pk.volume > 0 else 0,
            "used_volume": pk.get_used_volume(),
            "waste_volume": pk.get_waste(),
        }

    total_used = sum(r["used_volume"] for r in results.values())

    return {
        "order": order_name,
        "results": results,
        "stock_profit": stock_profit,
        "produced_profit": produced_profit,
        "emergency_loss": emergency_loss,
        "net_profit": net_profit,
        "produced_counts": dict(placed),
        "emergency_counts": emergency,
        "stock_used": {
            wp.name: min(STOCK.get(wp.name, 0), order_demand.get(wp.name, 0))
            for wp in WORKPIECES
        },
        "total_items": sum(placed.values()),
        "total_used": total_used,
        "total_waste": TOTAL_AVAIL_VOL - total_used,
        "utilization": total_used / TOTAL_AVAIL_VOL,
        "iterations": 1,
        "expansions": sum(placed.values()),
    }


def generate_orderings(order_demand):
    # 为给定订单生成多种工件放置顺序
    need = {}
    for wp in WORKPIECES:
        d = order_demand.get(wp.name, 0)
        s = STOCK.get(wp.name, 0)
        n = max(0, d - s)
        if n > 0:
            need[wp.name] = n

    wp_names = list(need.keys())
    if len(wp_names) <= 1:
        return [wp_names]

    # 预计算排序
    by_profit_density = sorted(wp_names, key=lambda n: WP_MAP[n].profit_density)
    by_profit_density_desc = list(reversed(by_profit_density))
    by_volume = sorted(wp_names, key=lambda n: WP_MAP[n].volume)
    by_volume_desc = list(reversed(by_volume))
    by_profit = sorted(wp_names, key=lambda n: WP_MAP[n].profit)
    by_profit_desc = list(reversed(by_profit))
    by_demand = sorted(wp_names, key=lambda n: need[n])
    by_demand_desc = list(reversed(by_demand))

    orderings = []
    seen = set()

    def add(ordering):
        key = tuple(ordering)
        if key not in seen:
            seen.add(key)
            orderings.append(ordering)

    # 1. 基础排序策略
    add(by_profit_density)  # 低利润密度优先
    add(by_profit_density_desc)  # 高利润密度优先
    add(by_volume)  # 小体积优先
    add(by_volume_desc)  # 大体积优先
    add(by_profit)  # 低利润优先
    add(by_profit_desc)  # 高利润优先
    add(by_demand)  # 少量需求优先
    add(by_demand_desc)  # 多量需求优先

    # 2. 混合策略
    high = [n for n in wp_names if WP_MAP[n].profit_density >= 0.01050]
    low = [n for n in wp_names if WP_MAP[n].profit_density < 0.00980]
    mid = [n for n in wp_names if 0.00980 <= WP_MAP[n].profit_density < 0.01050]

    high.sort(key=lambda n: WP_MAP[n].profit, reverse=True)
    low.sort(key=lambda n: WP_MAP[n].volume)
    mid.sort(key=lambda n: WP_MAP[n].profit_density)

    add(high + low + mid)
    add(high + mid + low)
    add(low + high + mid)
    add(low + mid + high)
    add(mid + high + low)
    add(mid + low + high)

    for h in high:
        rest = [n for n in wp_names if n != h]
        rest.sort(key=lambda n: WP_MAP[n].profit_density)
        add([h] + rest)
        rest.sort(key=lambda n: WP_MAP[n].volume)
        add([h] + rest)

    for lo in low:
        rest = [n for n in wp_names if n != lo]
        rest.sort(key=lambda n: WP_MAP[n].profit, reverse=True)
        add([lo] + rest)

    if set(["J01", "J02", "J05"]).issubset(set(wp_names)):
        rest = [n for n in wp_names if n not in ["J01", "J02", "J05"]]
        rest.sort(key=lambda n: WP_MAP[n].profit_density)
        add(["J05", "J01", "J02"] + rest)
        add(["J05", "J02", "J01"] + rest)
        add(["J05", "J01", "J02"] + list(reversed(rest)))

    # 6. 随机排列
    rng = random.Random(42)
    for _ in range(30):
        perm = list(wp_names)
        rng.shuffle(perm)
        add(perm)

    return orderings


def solve_order_multi(order_name, order_demand):
    orderings = generate_orderings(order_demand)
    best = None
    for ordering in orderings:
        res = solve_order_greedy(order_name, order_demand, ordering)
        if best is None or res["net_profit"] > best["net_profit"]:
            best = res
    return best


# 输出
def print_order_result(res):
    print(f"\n{'=' * 60}")
    print(f"  订单 {res['order']}")
    print(f"{'=' * 60}")

    print(f"\n  利润明细")
    print(f"  库存利润：              {res['stock_profit']:>12,}")
    print(f"  生产利润：              {res['produced_profit']:>12,}")
    print(f"  紧急采购损失：          {res['emergency_loss']:>12,}")
    print(f"  净利润：                {res['net_profit']:>12,}")

    print(f"\n订单满足情况")
    print(
        f"  {'工件':<6} {'需求':<8} {'库存':<8} {'生产':<10} {'紧急采购':<10} {'状态'}"
    )
    for wp in WORKPIECES:
        d = ORDERS[res["order"]].get(wp.name, 0)
        s = res["stock_used"].get(wp.name, 0)
        p = res["produced_counts"].get(wp.name, 0)
        e = res["emergency_counts"].get(wp.name, 0)
        ok = "✓" if d == s + p + e else f"✗({d - s - p - e})"
        print(f"  {wp.name:<6} {d:<8} {s:<8} {p:<10} {e:<10} {ok}")

    print(f"\n  生产统计")
    print(f"  搜索迭代: {res['iterations']} 次, 展开节点: {res['expansions']} 个")
    print(f"  生产工件数: {res['total_items']}, 利用率: {res['utilization']:.2%}")

    print(f"\n 详情")
    for bname in sorted(res["results"].keys()):
        d = res["results"][bname]
        n = len(d["placements"])
        print(
            f"  {bname}: {d['dims'][0]}×{d['dims'][1]}×{d['dims'][2]}  "
            f"{n} 个工件  利用率={d['utilization']:.2%}"
        )


def print_summary(all_results):
    print(f"\n{'=' * 60}")
    print(f"  订单对比")
    print(f"{'=' * 60}")
    print(
        f"  {'订单':<8} {'库存利润':<12} {'生产利润':<12} "
        f"{'紧急损失':<12} {'净利润':<12} {'利用率':<8}"
    )
    print(f"  {'-' * 8} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 12} {'-' * 8}")
    for r in all_results:
        print(
            f"  {r['order']:<8} {r['stock_profit']:>10,}  "
            f"{r['produced_profit']:>10,}  {r['emergency_loss']:>10,}  "
            f"{r['net_profit']:>10,}  {r['utilization']:>7.2%}"
        )
    best = max(all_results, key=lambda r: r["net_profit"])
    print(f"\n  >>> 最优: {best['order']} (净利润={best['net_profit']:,}) <<<")


if __name__ == "__main__":
    print("=" * 60)
    print("子问题 3:")
    print("=" * 60)
    print(f"可用材料: L01×2, L02×2, L03×1  |  总体积={TOTAL_AVAIL_VOL:,}")
    print(f"策略: 每订单尝试约80种排序，择优输出\n")

    t0 = time.time()
    all_results = []
    for oname, odemand in ORDERS.items():
        res = solve_order_multi(oname, odemand)
        all_results.append(res)
        print_order_result(res)

    print_summary(all_results)
    print(f"\n总耗时: {time.time() - t0:.1f}s")
