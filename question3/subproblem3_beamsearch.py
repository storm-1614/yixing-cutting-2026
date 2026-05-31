# -*- coding: utf-8 -*-
r"""
================================================================================
子问题 3：订单选择 + 生产方案
求解算法：多策略贪心 + EMS 解码器
================================================================================

数学模型：同 subproblem3_solver.py（订单选择 MILP + 3D 装箱约束）

求解算法：多策略贪心（Multi-Strategy Greedy）

  核心思想：对每个订单，尝试多种工件放置顺序（排列），每种顺序用
  贪心 Best-Fit 打包，取净利润最高的结果。

  为什么不用单一 Beam Search:
    Beam Search 按总利润排序 → 高利润工件优先 → 低利润工件被排斥
    → H02 的 J01/J02 全部紧急采购 → 利润被严重低估
    → 错误地选择了 H01 而非 H02

  多策略贪心的优势:
    - 不同放置顺序探索不同的打包空间
    - "先放低利润"可以为小工件预留空间
    - "先放高利润"可以锁住核心利润
    - 混合策略兼顾两者
    - 每次贪心 ~0.01s, 100 次也只要 ~1s

  Beam Search 保留作为备选方案（H01 场景下达到理论最优）。
================================================================================
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from itertools import permutations
from copy import deepcopy
import time
import random


# ==============================================================================
# 数据
# ==============================================================================

@dataclass
class Material:
    name: str
    length: int; width: int; height: int
    quantity: int
    @property
    def volume(self) -> int:
        return self.length * self.width * self.height


@dataclass
class Workpiece:
    name: str
    length: int; width: int; height: int
    profit: int
    @property
    def volume(self) -> int:
        return self.length * self.width * self.height
    @property
    def profit_density(self) -> float:
        return self.profit / self.volume
    def get_orientations(self) -> List[Tuple[int,int,int]]:
        seen = set()
        res = []
        for p in permutations([self.length, self.width, self.height]):
            if p not in seen:
                seen.add(p); res.append(p)
        return res


AVAILABLE_MATERIALS = [
    Material("L01", 300, 200, 150, 2),
    Material("L02", 250, 150, 100, 2),
    Material("L03", 200, 150, 80,  1),
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


# ==============================================================================
# EMS 核心
# ==============================================================================

@dataclass
class Space:
    x: int; y: int; z: int
    dx: int; dy: int; dz: int
    def can_fit(self, dx, dy, dz): return self.dx>=dx and self.dy>=dy and self.dz>=dz


def get_intersection(sp, ix, iy, iz, idx, idy, idz):
    x1,y1,z1 = max(sp.x,ix), max(sp.y,iy), max(sp.z,iz)
    x2 = min(sp.x+sp.dx, ix+idx)
    y2 = min(sp.y+sp.dy, iy+idy)
    z2 = min(sp.z+sp.dz, iz+idz)
    return (x1,y1,z1,x2-x1,y2-y1,z2-z1) if x1<x2 and y1<y2 and z1<z2 else None


def split_space(sp, rx, ry, rz, rdx, rdy, rdz):
    res = []
    if rz-sp.z>0:          res.append(Space(sp.x,sp.y,sp.z, sp.dx,sp.dy, rz-sp.z))
    if sp.z+sp.dz-rz-rdz>0: res.append(Space(sp.x,sp.y,rz+rdz, sp.dx,sp.dy, sp.z+sp.dz-rz-rdz))
    if ry-sp.y>0:          res.append(Space(sp.x,sp.y,rz, sp.dx, ry-sp.y, rdz))
    if sp.y+sp.dy-ry-rdy>0: res.append(Space(sp.x,ry+rdy,rz, sp.dx, sp.y+sp.dy-ry-rdy, rdz))
    if rx-sp.x>0:          res.append(Space(sp.x,ry,rz, rx-sp.x, rdy, rdz))
    if sp.x+sp.dx-rx-rdx>0: res.append(Space(rx+rdx,ry,rz, sp.x+sp.dx-rx-rdx, rdy, rdz))
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
            if used[i]: continue
            si, found = cur[i], False
            for j in range(n):
                if i == j or used[j]: continue
                sj = cur[j]
                merged = None
                if (si.x==sj.x and si.dx==sj.dx and si.z==sj.z and si.dz==sj.dz):
                    if si.y+si.dy==sj.y: merged = Space(si.x,si.y,si.z,si.dx,si.dy+sj.dy,si.dz)
                    elif sj.y+sj.dy==si.y: merged = Space(sj.x,sj.y,sj.z,sj.dx,sj.dy+si.dy,sj.dz)
                elif (si.y==sj.y and si.dy==sj.dy and si.z==sj.z and si.dz==sj.dz):
                    if si.x+si.dx==sj.x: merged = Space(si.x,si.y,si.z,si.dx+sj.dx,si.dy,si.dz)
                    elif sj.x+sj.dx==si.x: merged = Space(sj.x,sj.y,sj.z,sj.dx+si.dx,sj.dy,sj.dz)
                elif (si.x==sj.x and si.dx==sj.dx and si.y==sj.y and si.dy==sj.dy):
                    if si.z+si.dz==sj.z: merged = Space(si.x,si.y,si.z,si.dx,si.dy,si.dz+sj.dz)
                    elif sj.z+sj.dz==si.z: merged = Space(sj.x,sj.y,sj.z,sj.dx,sj.dy,sj.dz+si.dz)
                if merged is not None:
                    mrg.append(merged); used[i]=used[j]=found=changed=True; break
            if not found: mrg.append(si); used[i] = True
        cur = mrg
    return cur


class BlockPacker:
    def __init__(self, dx, dy, dz):
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces = [Space(0, 0, 0, dx, dy, dz)]
        self.placements = []

    def copy(self):
        """深拷贝."""
        pk = BlockPacker(*self.dims)
        pk.spaces = deepcopy(self.spaces)
        pk.placements = list(self.placements)
        return pk

    def try_place(self, name, dx, dy, dz):
        fitting = [(i, s) for i, s in enumerate(self.spaces) if s.can_fit(dx,dy,dz)]
        if not fitting: return None
        bi, bs = min(fitting, key=lambda x: (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
        px, py, pz = bs.x, bs.y, bs.z
        used = self.spaces.pop(bi)
        new_sps = split_space(used, px, py, pz, dx, dy, dz)
        cleaned = []
        for s in self.spaces:
            inter = get_intersection(s, px, py, pz, dx, dy, dz)
            if inter is None: cleaned.append(s)
            else: cleaned.extend(split_space(s, *inter))
        self.spaces = cleaned + new_sps
        if len(self.spaces) > 150: self.spaces = merge_spaces(self.spaces)
        self.placements.append((name, px, py, pz, dx, dy, dz))
        return (px, py, pz)

    def get_top_candidates(self, remaining_dict, M):
        """从 remaining_dict ({工件名: 还需数量}) 中找 top-M 候选 (工件+姿态).

        对每种未完成的工件，遍历其全部 6 种旋转姿态，在剩余空间中找贴合度
        最高的放置方式。Beam Search 同时对「选哪个工件」和「用哪种姿态」
        进行搜索，而非预先固定姿态。
        """
        scored = []
        for nm, count in remaining_dict.items():
            if count <= 0:
                continue
            wp = WP_MAP[nm]
            for dx, dy, dz in wp.get_orientations():
                fitting = [(j, s) for j, s in enumerate(self.spaces) if s.can_fit(dx, dy, dz)]
                if not fitting:
                    continue
                _, bs = min(fitting, key=lambda x: (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
                score = (bs.dx-dx)+(bs.dy-dy)+(bs.dz-dz)
                scored.append((score, nm, dx, dy, dz))
        scored.sort(key=lambda x: x[0])
        # 去重: 同一工件只保留贴合度最高的那个姿态，避免 M 个名额被同一种工件占满
        seen = set()
        unique = []
        for s in scored:
            if s[1] not in seen:
                seen.add(s[1])
                unique.append(s)
        return unique[:M]

    def get_used_volume(self):
        return sum(dx*dy*dz for _,_,_,_,dx,dy,dz in self.placements)
    def get_waste(self):
        return self.volume - self.get_used_volume()


# ==============================================================================
# Beam Search 状态
# ==============================================================================

@dataclass
class BeamState:
    """束搜索中的一个部分解."""
    packers: List[BlockPacker]   # 5 个打包器 (L01_1, L01_2, L02_1, L02_2, L03_1)
    packer_names: List[str]
    placed: Dict[str, int]       # 已放置工件计数
    profit: int                  # 当前总利润
    depth: int                   # 已放置工件数

    def copy(self):
        return BeamState(
            packers=[p.copy() for p in self.packers],
            packer_names=list(self.packer_names),
            placed=dict(self.placed),
            profit=self.profit,
            depth=self.depth,
        )


# ==============================================================================
# Beam Search 主引擎
# ==============================================================================

def solve_order_beam(order_name, order_demand, K=10, M=8, max_iterations=300):
    """
    用 Beam Search 为一个订单找到最优生产方案.

    Args:
        K: 束宽 (保留 K 个最优状态)
        M: 分支因子 (每个 block 每步尝试 M 个候选工件)
        max_iterations: 最大迭代次数

    Returns:
        {produced, emergency, net_profit, ...}
    """
    # 计算需生产量
    need = {}
    for wp in WORKPIECES:
        d = order_demand.get(wp.name, 0)
        s = STOCK.get(wp.name, 0)
        n = max(0, d - s)
        if n > 0: need[wp.name] = n

    stock_profit = sum(
        min(STOCK.get(wp.name, 0), order_demand.get(wp.name, 0)) * wp.profit
        for wp in WORKPIECES
    )

    # 初始状态
    block_dims = [(f"{m.name}_{i+1}", m.length, m.width, m.height)
                  for m in AVAILABLE_MATERIALS for i in range(m.quantity)]
    init_packers = [BlockPacker(dx, dy, dz) for _, dx, dy, dz in block_dims]
    init_names = [name for name, _, _, _ in block_dims]

    init_state = BeamState(
        packers=init_packers,
        packer_names=init_names,
        placed={},
        profit=0,
        depth=0,
    )

    beam = [init_state]
    best_state = init_state
    iteration = 0
    expand_count = 0

    while beam and iteration < max_iterations:
        iteration += 1
        candidates = []

        for state in beam:
            # 构建该 state 还需生产的工件 (提到 packer 循环外，只算一次)
            remaining = {}
            for wp_name, needed_count in need.items():
                already = state.placed.get(wp_name, 0)
                if already < needed_count:
                    remaining[wp_name] = needed_count - already

            if not remaining:
                continue

            for pi, packer in enumerate(state.packers):
                top_cands = packer.get_top_candidates(remaining, M)
                for score, nm, dx, dy, dz in top_cands:
                    # 复制状态并放入工件
                    new_state = state.copy()
                    new_state.packers[pi].try_place(nm, dx, dy, dz)
                    new_state.placed[nm] = new_state.placed.get(nm, 0) + 1
                    new_state.profit += WP_MAP[nm].profit
                    new_state.depth += 1
                    expand_count += 1
                    candidates.append(new_state)

        if not candidates:
            break

        # 更新全局最优 (利润最高)
        candidates.sort(key=lambda s: s.profit, reverse=True)
        if candidates[0].profit > best_state.profit:
            best_state = candidates[0]

        # 保留 top-K
        beam = candidates[:K]

    # 统计结果
    produced = dict(best_state.placed)
    emergency = {}
    emergency_loss = 0
    for wp in WORKPIECES:
        d = order_demand.get(wp.name, 0)
        s = STOCK.get(wp.name, 0)
        p = produced.get(wp.name, 0)
        short = max(0, d - s - p)
        if short > 0:
            emergency[wp.name] = short
            emergency_loss += short * wp.profit

    produced_profit = sum(WP_MAP[n].profit * c for n, c in produced.items())
    net_profit = stock_profit + produced_profit - emergency_loss

    # 组装 per-block 结果
    results = {}
    for i, pk in enumerate(best_state.packers):
        bname = best_state.packer_names[i]
        results[bname] = {
            'dims': pk.dims,
            'placements': pk.placements,
            'utilization': pk.get_used_volume()/pk.volume if pk.volume>0 else 0,
            'used_volume': pk.get_used_volume(),
            'waste_volume': pk.get_waste(),
        }

    total_used = sum(r['used_volume'] for r in results.values())

    return {
        'order': order_name,
        'results': results,
        'stock_profit': stock_profit,
        'produced_profit': produced_profit,
        'emergency_loss': emergency_loss,
        'net_profit': net_profit,
        'produced_counts': produced,
        'emergency_counts': emergency,
        'stock_used': {wp.name: min(STOCK.get(wp.name,0), order_demand.get(wp.name,0))
                      for wp in WORKPIECES},
        'total_items': sum(produced.values()),
        'total_used': total_used,
        'total_waste': TOTAL_AVAIL_VOL - total_used,
        'utilization': total_used / TOTAL_AVAIL_VOL,
        'iterations': iteration,
        'expansions': expand_count,
    }


# ==============================================================================
# 多策略贪心求解器
# ==============================================================================

def solve_order_greedy(order_name, order_demand, ordering):
    """用指定工件顺序做贪心 Best-Fit 打包.

    Args:
        order_name: 订单名 (H01/H02/H03)
        order_demand: 需求字典 {"J01": 48, ...}
        ordering: 工件放置顺序 ["J05", "J01", "J02", ...]

    Returns:
        与 solve_order_beam 相同格式的结果字典
    """
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

    # 初始化 5 块材料
    block_dims = [(f"{m.name}_{i+1}", m.length, m.width, m.height)
                  for m in AVAILABLE_MATERIALS for i in range(m.quantity)]
    packers = [BlockPacker(dx, dy, dz) for _, dx, dy, dz in block_dims]
    pnames = [name for name, _, _, _ in block_dims]

    placed = {}

    # 按 ordering 顺序依次放置每种工件
    for wp_name in ordering:
        if wp_name not in need:
            continue
        target = need[wp_name]
        count = 0
        wp = WP_MAP[wp_name]
        orientations = wp.get_orientations()

        while count < target:
            # 在所有块中找全局最佳放置位置
            best_fit = None  # (gap, packer_idx, dx, dy, dz)
            for pi, pk in enumerate(packers):
                for dx, dy, dz in orientations:
                    fitting = [(j, s) for j, s in enumerate(pk.spaces)
                               if s.can_fit(dx, dy, dz)]
                    if not fitting:
                        continue
                    _, bs = min(fitting,
                                key=lambda x: (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz))
                    gap = (bs.dx - dx) + (bs.dy - dy) + (bs.dz - dz)
                    if best_fit is None or gap < best_fit[0]:
                        best_fit = (gap, pi, dx, dy, dz)

            if best_fit is None:
                break  # 这种工件放不下了

            _, pi, dx, dy, dz = best_fit
            packers[pi].try_place(wp_name, dx, dy, dz)
            count += 1

        placed[wp_name] = count

    # 统计结果 (与 solve_order_beam 格式一致)
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
            'dims': pk.dims,
            'placements': pk.placements,
            'utilization': pk.get_used_volume() / pk.volume if pk.volume > 0 else 0,
            'used_volume': pk.get_used_volume(),
            'waste_volume': pk.get_waste(),
        }

    total_used = sum(r['used_volume'] for r in results.values())

    return {
        'order': order_name,
        'results': results,
        'stock_profit': stock_profit,
        'produced_profit': produced_profit,
        'emergency_loss': emergency_loss,
        'net_profit': net_profit,
        'produced_counts': dict(placed),
        'emergency_counts': emergency,
        'stock_used': {wp.name: min(STOCK.get(wp.name, 0), order_demand.get(wp.name, 0))
                       for wp in WORKPIECES},
        'total_items': sum(placed.values()),
        'total_used': total_used,
        'total_waste': TOTAL_AVAIL_VOL - total_used,
        'utilization': total_used / TOTAL_AVAIL_VOL,
        'iterations': 1,
        'expansions': sum(placed.values()),
    }


def generate_orderings(order_demand):
    """为给定订单生成多种工件放置顺序.

    策略包括:
    - 按利润密度升序/降序
    - 按体积升序/降序
    - 按需求量升序/降序
    - 混合策略: 高利润→低利润→中利润
    - 关键排列: 先锁高利润再填小工件
    """
    # 只考虑需要生产的工件
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

    # 预计算排序键
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
    add(by_profit_density)          # 低利润密度优先 (先放小工件)
    add(by_profit_density_desc)     # 高利润密度优先 (beam search 默认)
    add(by_volume)                  # 小体积优先
    add(by_volume_desc)             # 大体积优先
    add(by_profit)                  # 低利润优先
    add(by_profit_desc)             # 高利润优先
    add(by_demand)                  # 少量需求优先
    add(by_demand_desc)             # 多量需求优先

    # 2. 混合策略: 先锁高利润, 再填低利润, 最后补中利润
    high = [n for n in wp_names if WP_MAP[n].profit_density >= 0.01050]
    low = [n for n in wp_names if WP_MAP[n].profit_density < 0.00980]
    mid = [n for n in wp_names if 0.00980 <= WP_MAP[n].profit_density < 0.01050]

    high.sort(key=lambda n: WP_MAP[n].profit, reverse=True)
    low.sort(key=lambda n: WP_MAP[n].volume)  # 小体积优先
    mid.sort(key=lambda n: WP_MAP[n].profit_density)

    add(high + low + mid)
    add(high + mid + low)
    add(low + high + mid)
    add(low + mid + high)
    add(mid + high + low)
    add(mid + low + high)

    # 3. 每种高利润工件开头的排列
    for h in high:
        rest = [n for n in wp_names if n != h]
        rest.sort(key=lambda n: WP_MAP[n].profit_density)  # 剩余按利润密度升序
        add([h] + rest)
        rest.sort(key=lambda n: WP_MAP[n].volume)  # 剩余按体积升序
        add([h] + rest)

    # 4. 每种低利润工件开头的排列
    for lo in low:
        rest = [n for n in wp_names if n != lo]
        rest.sort(key=lambda n: WP_MAP[n].profit, reverse=True)
        add([lo] + rest)

    # 5. 关键发现的排列 (从分析中得到的最优策略)
    # 先放 J05, 再 J01, 再 J02, 再其他
    if set(["J01", "J02", "J05"]).issubset(set(wp_names)):
        rest = [n for n in wp_names if n not in ["J01", "J02", "J05"]]
        rest.sort(key=lambda n: WP_MAP[n].profit_density)
        add(["J05", "J01", "J02"] + rest)
        add(["J05", "J02", "J01"] + rest)
        add(["J05", "J01", "J02"] + list(reversed(rest)))

    # 6. 随机排列 (固定种子, 可复现)
    rng = random.Random(42)
    for _ in range(30):
        perm = list(wp_names)
        rng.shuffle(perm)
        add(perm)

    return orderings


def solve_order_multi(order_name, order_demand):
    """多策略贪心求解: 尝试多种放置顺序, 返回最优结果."""
    orderings = generate_orderings(order_demand)
    best = None
    for ordering in orderings:
        res = solve_order_greedy(order_name, order_demand, ordering)
        if best is None or res['net_profit'] > best['net_profit']:
            best = res
    return best


# ==============================================================================
# 输出
# ==============================================================================

def print_order_result(res):
    print(f"\n{'='*60}")
    print(f"  ORDER {res['order']} - Multi-Strategy Greedy")
    print(f"{'='*60}")

    print(f"\n  --- Profit Breakdown ---")
    print(f"  Stock profit:           {res['stock_profit']:>12,}")
    print(f"  Produced profit:        {res['produced_profit']:>12,}")
    print(f"  Emergency loss:         {res['emergency_loss']:>12,}")
    print(f"  NET PROFIT:             {res['net_profit']:>12,}")

    print(f"\n  --- Fulfillment ---")
    print(f"  {'WP':<6} {'Demand':<8} {'Stock':<8} {'Produced':<10} "
          f"{'Emergency':<10} {'Status'}")
    for wp in WORKPIECES:
        d = ORDERS[res['order']].get(wp.name, 0)
        s = res['stock_used'].get(wp.name, 0)
        p = res['produced_counts'].get(wp.name, 0)
        e = res['emergency_counts'].get(wp.name, 0)
        ok = "✓" if d==s+p+e else f"✗({d-s-p-e})"
        print(f"  {wp.name:<6} {d:<8} {s:<8} {p:<10} {e:<10} {ok}")

    print(f"\n  --- Production ---")
    print(f"  Beam Search: {res['iterations']} iters, {res['expansions']} expansions")
    print(f"  Items produced: {res['total_items']}, Util: {res['utilization']:.2%}")

    print(f"\n  --- Per Block ---")
    for bname in sorted(res['results'].keys()):
        d = res['results'][bname]
        n = len(d['placements'])
        print(f"  {bname}: {d['dims'][0]}×{d['dims'][1]}×{d['dims'][2]}  "
              f"{n} items  util={d['utilization']:.2%}")


def print_summary(all_results):
    print(f"\n{'='*60}")
    print(f"  ORDER COMPARISON")
    print(f"{'='*60}")
    print(f"  {'Order':<8} {'Stock':<12} {'Produced':<12} "
          f"{'Emergency':<12} {'NET':<12} {'Util':<8}")
    print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*8}")
    for r in all_results:
        print(f"  {r['order']:<8} {r['stock_profit']:>10,}  "
              f"{r['produced_profit']:>10,}  {r['emergency_loss']:>10,}  "
              f"{r['net_profit']:>10,}  {r['utilization']:>7.2%}")
    best = max(all_results, key=lambda r: r['net_profit'])
    print(f"\n  >>> BEST: {best['order']} (net={best['net_profit']:,}) <<<")


if __name__ == "__main__":
    print("=" * 60)
    print("SUB-PROBLEM 3: Multi-Strategy Greedy + EMS")
    print("=" * 60)
    print(f"Available: L01×2, L02×2, L03×1  |  Vol={TOTAL_AVAIL_VOL:,}")
    print(f"Strategy: try ~80 orderings per order, pick best\n")

    t0 = time.time()
    all_results = []
    for oname, odemand in ORDERS.items():
        res = solve_order_multi(oname, odemand)
        all_results.append(res)
        print_order_result(res)

    print_summary(all_results)
    print(f"\nTotal time: {time.time()-t0:.1f}s")
