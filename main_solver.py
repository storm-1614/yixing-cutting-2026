#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
方形材料的切割加工优化问题 — 主要计算程序
数学建模竞赛 A 题（亿星软件题目）
================================================================================

本程序整合三个子问题的核心求解算法：

  子问题 1: EMS (Empty Maximal Spaces) 三维装箱 — 最大化体积利用率
  子问题 2: 多策略两阶段 EMS + 迭代局部搜索 (ILS) — 利润最大化
  子问题 3: 多策略贪心订单选择 — 净利润最大化

算法核心: Global Best-Fit 贪心策略 + 空间分裂/合并机制

使用方法:
  python main_solver.py                 # 运行所有子问题 (快速模式)
  python main_solver.py --full           # 完整求解 (论文级精度)
  python main_solver.py --question 1     # 仅运行子问题 1
================================================================================
"""

import itertools
import time
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from collections import Counter


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          第 1 部分: 全局数据定义                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# --- 原材料规格 ---
# 字段: (型号, 长mm, 宽mm, 高mm, 数量)
RAW_MATERIALS = [
    ("L01", 300, 200, 150, 5),   #  9,000,000 mm³ × 5 = 45,000,000 mm³
    ("L02", 250, 150, 100, 5),   #  3,750,000 mm³ × 5 = 18,750,000 mm³
    ("L03", 200, 150,  80, 5),   #  2,400,000 mm³ × 5 = 12,000,000 mm³
]                                #  总计:                 75,750,000 mm³

# --- 工件规格 ---
# 字段: (型号, 长mm, 宽mm, 高mm, 利润元)
WORKPIECES = [
    ("J01",  40, 40, 40,  620),   # 体积 64,000 mm³,  利润密度 0.00969
    ("J02",  50, 40, 40,  780),   # 体积 80,000 mm³,  利润密度 0.00975
    ("J03",  60, 50, 30,  880),   # 体积 90,000 mm³,  利润密度 0.00978
    ("J04",  75, 60, 40, 1850),   # 体积 180,000 mm³, 利润密度 0.01028
    ("J05",  80, 60, 50, 2520),   # 体积 240,000 mm³, 利润密度 0.01050
    ("J06", 100, 50, 20, 1000),   # 体积 100,000 mm³, 利润密度 0.01000
    ("J07", 120, 20, 20,  540),   # 体积 48,000 mm³,  利润密度 0.01125
]

WP_MAP = {wp[0]: wp for wp in WORKPIECES}
TOTAL_RAW_VOL = sum(L * W * H * q for _, L, W, H, q in RAW_MATERIALS)

# --- 子问题 2 约束 ---
MIN_COUNT_P2 = {f"J{i:02d}": 10 for i in range(1, 8)}

# --- 子问题 3 数据 ---
AVAILABLE_P3 = [
    ("L01", 300, 200, 150, 2),
    ("L02", 250, 150, 100, 2),
    ("L03", 200, 150,  80, 1),
]
TOTAL_AVAIL_VOL_P3 = sum(L * W * H * q for _, L, W, H, q in AVAILABLE_P3)

STOCK_P3 = {"J01": 0, "J02": 0, "J03": 20, "J04": 0, "J05": 3, "J06": 11, "J07": 19}

ORDERS_P3 = {
    "H01": {"J03": 24, "J04": 54, "J05": 25, "J06": 80, "J07": 40},
    "H02": {"J01": 48, "J02": 200, "J03": 70, "J05": 11, "J06": 11, "J07": 56},
    "H03": {"J03": 27, "J04": 54, "J05": 27, "J06": 115, "J07": 44},
}


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                       第 2 部分: EMS 核心数据结构                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@dataclass
class Space:
    """三维空闲空间: 原点 (x,y,z) + 三轴尺寸 (dx,dy,dz)

    EMS 算法的核心数据结构。每个 Space 对象记录原材料块中一段
    尚未被占用的长方体区域。所有 Space 之间互不重叠（不变量）。
    """
    x: int; y: int; z: int
    dx: int; dy: int; dz: int

    def can_fit(self, dx, dy, dz) -> bool:
        """判断工件 (dx,dy,dz) 能否放入本空间"""
        return self.dx >= dx and self.dy >= dy and self.dz >= dz

    @property
    def volume(self) -> int:
        return self.dx * self.dy * self.dz


def get_orientations(l: int, w: int, h: int) -> List[Tuple[int, int, int]]:
    """生成长方体工件的全部旋转姿态（去重）

    长方体有至多 6 种不同的旋转姿态，对应 3! = 6 种轴排列。
    当某些维度相等时，实际姿态数减少（如正方体仅 1 种）。
    """
    return list(set(itertools.permutations([l, w, h])))


def get_intersection(sp: Space, ix: int, iy: int, iz: int,
                     idx: int, idy: int, idz: int) -> Optional[Tuple]:
    """计算空间 sp 与工件包围盒的交集

    Returns:
        若相交则返回 (x1,y1,z1,dx,dy,dz)，否则返回 None
    """
    x1, y1, z1 = max(sp.x, ix), max(sp.y, iy), max(sp.z, iz)
    x2 = min(sp.x + sp.dx, ix + idx)
    y2 = min(sp.y + sp.dy, iy + idy)
    z2 = min(sp.z + sp.dz, iz + idz)
    if x1 < x2 and y1 < y2 and z1 < z2:
        return (x1, y1, z1, x2 - x1, y2 - y1, z2 - z1)
    return None


def split_space(sp: Space, rx: int, ry: int, rz: int,
                rdx: int, rdy: int, rdz: int) -> List[Space]:
    """从空间 sp 中切除子体积 (rx,ry,rz,rdx,rdy,rdz)

    返回至多 6 个剩余子空间（对应 6 个方向）。
    当工件放置在空间原点角落时，仅上、后、右三个方向产生非零子空间。

    示意图（工件放置在空间原点角落）:
        ┌─────────┐
        │  上方    │  ← z+ 方向
        ├─────┬───┤
        │后方 │工件│  ← y+ 方向
        │     │   │
        ├─────┴───┤
        │  右方    │  ← x+ 方向
        └─────────┘
    """
    res = []
    s = sp
    # 六个切除方向: 下(z-)、上(z+)、前(y-)、后(y+)、左(x-)、右(x+)
    if rz - s.z > 0:
        res.append(Space(s.x, s.y, s.z, s.dx, s.dy, rz - s.z))
    if s.z + s.dz - rz - rdz > 0:
        res.append(Space(s.x, s.y, rz + rdz, s.dx, s.dy, s.z + s.dz - rz - rdz))
    if ry - s.y > 0:
        res.append(Space(s.x, s.y, rz, s.dx, ry - s.y, rdz))
    if s.y + s.dy - ry - rdy > 0:
        res.append(Space(s.x, ry + rdy, rz, s.dx, s.y + s.dy - ry - rdy, rdz))
    if rx - s.x > 0:
        res.append(Space(s.x, ry, rz, rx - s.x, rdy, rdz))
    if s.x + s.dx - rx - rdx > 0:
        res.append(Space(rx + rdx, ry, rz, s.x + s.dx - rx - rdx, rdy, rdz))
    return res


def merge_spaces(spaces: List[Space]) -> List[Space]:
    """空间合并（反碎片化）

    检查是否存在两个相邻空间共享完整面且另外两轴对齐，
    若是则将其合并为一个更大的空间。合并沿 x/y/z 三轴分别进行。
    反复迭代直至无可合并的空间对。

    时间复杂度: O(S²)，其中 S 为当前空间数（通常 20-100）。
    """
    if len(spaces) <= 1:
        return spaces
    changed = True
    cur = list(spaces)
    while changed:
        changed = False
        n, mrg, used = len(cur), [], [False] * len(cur)
        for i in range(n):
            if used[i]:
                continue
            si, found = cur[i], False
            for j in range(n):
                if i == j or used[j]:
                    continue
                sj, merged = cur[j], None
                # y 方向合并
                if (si.x == sj.x and si.dx == sj.dx and
                        si.z == sj.z and si.dz == sj.dz):
                    if si.y + si.dy == sj.y:
                        merged = Space(si.x, si.y, si.z, si.dx, si.dy + sj.dy, si.dz)
                    elif sj.y + sj.dy == si.y:
                        merged = Space(sj.x, sj.y, sj.z, sj.dx, sj.dy + si.dy, sj.dz)
                # x 方向合并
                elif (si.y == sj.y and si.dy == sj.dy and
                      si.z == sj.z and si.dz == sj.dz):
                    if si.x + si.dx == sj.x:
                        merged = Space(si.x, si.y, si.z, si.dx + sj.dx, si.dy, si.dz)
                    elif sj.x + sj.dx == si.x:
                        merged = Space(sj.x, sj.y, sj.z, sj.dx + si.dx, sj.dy, sj.dz)
                # z 方向合并
                elif (si.x == sj.x and si.dx == sj.dx and
                      si.y == sj.y and si.dy == sj.dy):
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


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                     第 3 部分: EMS 打包器 (单块原材料)                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class BlockPacker:
    """单块原材料 EMS (Empty Maximal Spaces) 打包器

    维护一个互不重叠的空闲空间列表。每次放置工件时采用
    Global Best-Fit 策略：扫描所有 (工件, 空间) 对，选择
    三轴间隙和最小的组合进行放置。

    核心算法:
      gap = (dx_space - dx_item) + (dy_space - dy_item) + (dz_space - dz_item)
      → 选择 gap 最小的 (工件, 空间) 对
      → 在空间原点角落放置工件
      → 从被用空间中切除工件体积（至多 6 子空间）
      → 检查所有其他空间是否与新工件相交，若相交则切除
      → 执行空间合并（反碎片化）
    """

    def __init__(self, dx: int, dy: int, dz: int, name: str = ""):
        self.name = name
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces: List[Space] = [Space(0, 0, 0, dx, dy, dz)]
        self.placements: List[Tuple] = []  # (name, x, y, z, dx, dy, dz)

    def reset(self):
        """重置打包器到初始状态"""
        self.spaces = [Space(0, 0, 0, *self.dims)]
        self.placements = []

    def find_best(self, candidates):
        """Global Best-Fit: 从候选列表中找最紧密贴合的工件

        Args:
            candidates: [(name, dx, dy, dz, priority), ...]
        Returns:
            (index, name, dx, dy, dz) 或 None（无工件可放置）
        """
        best_idx, best_score = -1, float('inf')
        best_name, best_dims = None, None

        for i, item in enumerate(candidates):
            name, dx, dy, dz = item[0], item[1], item[2], item[3]
            # 在全部空闲空间中找此工件的最佳放置位置
            fitting = [(j, s) for j, s in enumerate(self.spaces)
                       if s.can_fit(dx, dy, dz)]
            if not fitting:
                continue
            _, best_s = min(fitting, key=lambda x:
                (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz))
            score = (best_s.dx - dx) + (best_s.dy - dy) + (best_s.dz - dz)
            if score < best_score:
                best_score = score
                best_idx = i
                best_name = name
                best_dims = (dx, dy, dz)
                if best_score == 0:  # 完美贴合，提前终止
                    break

        if best_idx < 0:
            return None
        return (best_idx, best_name, *best_dims)

    def try_place(self, name, dx, dy, dz):
        """尝试放置工件

        具体步骤:
          1. 在所有可容纳该工件的空间中找 Best-Fit 空间
          2. 在空间原点角落放置工件
          3. 从被占用空间中切除工件体积
          4. 检查所有其他空间是否与工件相交
          5. 相交空间 → 切除相交部分
          6. 如果空间数超过 150 → 触发合并（防碎片爆炸）

        Returns:
            成功返回 (x, y, z) 放置坐标，失败返回 None
        """
        # 步骤 1: 找 Best-Fit 空间
        fitting = [(i, s) for i, s in enumerate(self.spaces)
                   if s.can_fit(dx, dy, dz)]
        if not fitting:
            return None
        bi, best_s = min(fitting, key=lambda x:
            (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz))

        px, py, pz = best_s.x, best_s.y, best_s.z

        # 步骤 2-3: 切出被使用的空间，分裂为子空间
        used = self.spaces.pop(bi)
        new_sps = split_space(used, px, py, pz, dx, dy, dz)

        # 步骤 4-5: 处理与其他空间的相交
        cleaned = []
        for s in self.spaces:
            inter = get_intersection(s, px, py, pz, dx, dy, dz)
            if inter is None:
                cleaned.append(s)
            else:
                cleaned.extend(split_space(s, *inter))

        self.spaces = cleaned + new_sps

        # 步骤 6: 防碎片爆炸
        if len(self.spaces) > 150:
            self.spaces = merge_spaces(self.spaces)

        self.placements.append((name, px, py, pz, dx, dy, dz))
        return (px, py, pz)

    # --- 统计属性 ---
    def get_used_volume(self) -> int:
        return sum(dx * dy * dz for _, _, _, _, dx, dy, dz in self.placements)

    def get_waste(self) -> int:
        return self.volume - self.get_used_volume()

    def get_utilization(self) -> float:
        return self.get_used_volume() / self.volume if self.volume > 0 else 0


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    第 4 部分: 子问题 1 — 体积利用率最大化                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# 问题描述: 无限产量约束下，在 15 块原材料中放置尽可能多的工件，
#          使原材料总体积利用率最大。
#
# 求解方法: EMS 贪心 + 多策略选择
#   - 对每块原材料独立求解（块间无耦合）
#   - 候选池: 每种工件×6 姿态，各复制 80 份 → ~3360 候选
#   - 尝试 3 种排序策略（体积降序/底面积降序/最长边降序），选最优
#   - Global Best-Fit 贪心放置
#
# 复杂度: O(K × N × S), K≈50 件/块, N≈3360 候选, S≈50 空间
#         单块 ~0.1s, 15 块总计 ~2s
# ==============================================================================

def solve_subproblem1():
    """求解子问题 1: 最大化体积利用率"""
    blocks = [(f"{n}_{i+1}", L, W, H)
              for n, L, W, H, q in RAW_MATERIALS for i in range(q)]
    total_vol = sum(L * W * H for _, L, W, H in blocks)

    # 候选工件池生成
    candidates = []
    for name, l, w, h, _ in WORKPIECES:
        for dx, dy, dz in get_orientations(l, w, h):
            candidates.append((f"{name}_{dx}x{dy}x{dz}", dx, dy, dz))

    pool = [c for c in candidates for _ in range(80)]  # 每种复制 80 份

    # 排序策略
    sort_strategies = [
        ("体积降序", lambda items: sorted(items, key=lambda x: x[1]*x[2]*x[3], reverse=True)),
        ("底面积降序", lambda items: sorted(items, key=lambda x: x[1]*x[2], reverse=True)),
        ("最长边降序", lambda items: sorted(items, key=lambda x: max(x[1],x[2],x[3]), reverse=True)),
    ]

    results, all_placed = [], []

    for bname, L, W, H in blocks:
        best_placed, best_vol, best_strat = [], 0, ""

        for strat_name, sort_fn in sort_strategies:
            bin_ = BlockPacker(L, W, H, bname)
            sorted_items = sort_fn(list(pool))

            # Global Best-Fit 贪心放置
            remaining = sorted_items
            while remaining:
                res = bin_.find_best(remaining)
                if res is None:
                    break
                idx, nm, dx, dy, dz = res
                bin_.try_place(nm, dx, dy, dz)
                remaining.pop(idx)
            # 合并空间后重试
            bin_.spaces = merge_spaces(bin_.spaces)
            changed = True
            while changed and remaining:
                changed = False
                res = bin_.find_best(remaining)
                if res is not None:
                    idx, nm, dx, dy, dz = res
                    bin_.try_place(nm, dx, dy, dz)
                    remaining.pop(idx)
                    changed = True

            used = bin_.get_used_volume()
            if used > best_vol:
                best_vol = used
                best_placed = bin_.placements
                best_strat = strat_name

        results.append({
            "block": bname, "L": L, "W": W, "H": H,
            "count": len(best_placed), "used_vol": best_vol,
            "total_vol": L * W * H, "strategy": best_strat,
            "utilization": best_vol / (L * W * H),
        })
        all_placed.extend(best_placed)

    total_used = sum(r["used_vol"] for r in results)
    utilization = total_used / total_vol

    # 按工件类型统计
    type_counts = Counter()
    for p in all_placed:
        base_type = p[0].split("_")[0]
        type_counts[base_type] += 1

    return results, type_counts, total_vol, total_used, utilization


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                 第 5 部分: 子问题 2 — 利润最大化 (有产量约束)              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# 问题描述: 每种工件至少生产 10 件，在 15 块原材料中放置工件，
#          使总利润最大化。
#
# 求解方法: 多策略两阶段 EMS + 迭代局部搜索 (ILS)
#
#   阶段 1 (必须品保证):
#     - 10×7=70 件必须品，按多种策略排序后 EMS 贪心放置
#     - 5 种排序策略: 体积降序/最长边降序/利润密度降序/混合/随机
#
#   阶段 2 (利润填充):
#     - 在剩余空间中按利润密度降序填充候选工件
#     - 合并碎片空间 + 缝隙填充（≤30mm 工件优先）
#
#   阶段 3 (ILS 破坏-重建):
#     - 每轮: 移出 ~15% 非必须品 → 重新打包保留工件 → 填充池补位
#     - 低利润密度偏见采样 (70%) + 随机采样 (30%)
#     - 仅接受改进（爬山策略）
#     - 共 800 轮迭代
#
#   多试次: 48 次构造（5 策略 × 不同参数组合），取全局最优
# ==============================================================================

def solve_subproblem2(num_trials: int = 48, ils_iterations: int = 800,
                      verbose: bool = True):
    """求解子问题 2: 多策略两阶段 EMS + ILS"""

    blocks = [(f"{n}_{i+1}", L, W, H)
              for n, L, W, H, q in RAW_MATERIALS for i in range(q)]
    sorted_blocks = sorted(blocks, key=lambda b: b[1]*b[2]*b[3], reverse=True)

    MANDATORY_VOL = sum(
        WP_MAP[f"J{i:02d}"][1] * WP_MAP[f"J{i:02d}"][2] * WP_MAP[f"J{i:02d}"][3] * 10
        for i in range(1, 8)
    )

    if verbose:
        print(f"  原材料总体积: {TOTAL_RAW_VOL:,} (15 块)")
        print(f"  必须品体积:   {MANDATORY_VOL:,} ({MANDATORY_VOL/TOTAL_RAW_VOL:.1%})")

    # --- 多策略排序 ---
    strategies = ['two_phase_volume', 'two_phase_ld', 'two_phase_pd',
                  'two_phase_hybrid', 'two_phase_random']
    trial_strategies = (strategies * (num_trials // len(strategies) + 1))[:num_trials]
    random.Random(42).shuffle(trial_strategies)

    best_packers = None
    best_profit = 0
    t0 = time.time()

    for trial in range(num_trials):
        rng = random.Random(trial * 67 + 313)
        strategy = trial_strategies[trial]

        # --- 生成工件池 ---
        mandatory_items = []
        for name, l, w, h, _ in WORKPIECES:
            oris = get_orientations(l, w, h)
            for i in range(10):
                ori = oris[i % len(oris)]
                mandatory_items.append((name, ori[0], ori[1], ori[2], l * w * h, True))
        mandatory_items.sort(key=lambda x: x[4], reverse=True)

        rem_vol = TOTAL_RAW_VOL - sum(x[4] for x in mandatory_items)
        profit_items = []
        for name, l, w, h, profit in WORKPIECES:
            oris = get_orientations(l, w, h)
            est_max = max(60, int(rem_vol / (l * w * h) * 0.7))
            for k in range(est_max):
                ori = oris[k % len(oris)]
                profit_items.append((name, ori[0], ori[1], ori[2], profit / (l * w * h), False))

        # --- 两阶段打包 ---
        packers = {}
        p1_strat = strategy.replace('two_phase_', '')
        if p1_strat == 'two_phase': p1_strat = 'volume'

        # Phase 1: 必须品
        remaining = list(mandatory_items)
        if p1_strat == 'volume':
            remaining.sort(key=lambda x: x[4], reverse=True)
        elif p1_strat == 'ld':
            remaining.sort(key=lambda x: max(x[1], x[2], x[3]), reverse=True)
        elif p1_strat == 'pd':
            remaining.sort(key=lambda x: WP_MAP[x[0]][4] / (WP_MAP[x[0]][1] * WP_MAP[x[0]][2] * WP_MAP[x[0]][3]), reverse=True)
        elif p1_strat == 'hybrid':
            remaining.sort(key=lambda x: x[4] * (WP_MAP[x[0]][4] / (WP_MAP[x[0]][1] * WP_MAP[x[0]][2] * WP_MAP[x[0]][3])) ** 0.333, reverse=True)
        # random: 不排序

        for bname, bx, by, bz in sorted_blocks:
            pk = BlockPacker(bx, by, bz, bname)
            packers[bname] = pk
            while remaining:
                res = pk.find_best(remaining)
                if res is None: break
                pk.try_place(res[1], res[2], res[3], res[4])
                remaining.pop(res[0])
            pk.spaces = merge_spaces(pk.spaces)

        # Phase 2: 利润填充
        profit_items.sort(key=lambda x: x[4], reverse=True)
        remaining2 = list(profit_items)

        for bname, _, _, _ in sorted_blocks:
            pk = packers[bname]
            pk.spaces = merge_spaces(pk.spaces)
            while remaining2:
                res = pk.find_best(remaining2)
                if res is None: break
                pk.try_place(res[1], res[2], res[3], res[4])
                remaining2.pop(res[0])

            # 缝隙填充
            small = [(item[0], item[1], item[2], item[3], item[4])
                     for item in remaining2 if min(item[1], item[2], item[3]) <= 30]
            while small:
                res = pk.find_best(small)
                if res is None: break
                pk.try_place(res[1], res[2], res[3], res[4])
                popped = small.pop(res[0])
                for ri, item_r in enumerate(remaining2):
                    if (item_r[0] == popped[0] and item_r[1] == popped[1] and
                        item_r[2] == popped[2] and item_r[3] == popped[3]):
                        remaining2.pop(ri); break

        # --- 验证约束 ---
        counts = {}
        for pk in packers.values():
            for nm, _, _, _, _, _, _ in pk.placements:
                counts[nm] = counts.get(nm, 0) + 1
        if any(counts.get(f"J{i:02d}", 0) < 10 for i in range(1, 8)):
            continue

        profit = sum(counts.get(nm, 0) * WP_MAP[nm][4]
                     for nm in set(n for n, _, _, _, _ in WORKPIECES))
        if profit > best_profit:
            best_profit = profit
            best_packers = packers
            if verbose:
                used = sum(pk.get_used_volume() for pk in packers.values())
                items = sum(len(pk.placements) for pk in packers.values())
                print(f"  Trial {trial+1:>3}: profit={profit:>10,}  "
                      f"items={items:>4}  util={used/TOTAL_RAW_VOL:.4%}  *** BEST ***")

    # --- ILS 迭代改进 ---
    if ils_iterations > 0 and best_packers is not None:
        if verbose:
            print(f"\n  ILS 改进 ({ils_iterations} 次迭代)...")
        best_packers, best_profit = _ils_improve(
            best_packers, best_profit, ils_iterations, sorted_blocks, verbose)

    elapsed = time.time() - t0

    # 汇总
    counts = {}
    block_details = {}
    for bname, pk in best_packers.items():
        for nm, _, _, _, _, _, _ in pk.placements:
            counts[nm] = counts.get(nm, 0) + 1
        block_details[bname] = {
            "dims": pk.dims, "items": len(pk.placements),
            "used": pk.get_used_volume(), "waste": pk.get_waste(),
            "util": pk.get_utilization(),
        }
    total_used = sum(d["used"] for d in block_details.values())
    total_waste = TOTAL_RAW_VOL - total_used

    # 利润上界
    mand_profit = sum(WP_MAP[f"J{i:02d}"][4] * 10 for i in range(1, 8))
    rem_vol = TOTAL_RAW_VOL - MANDATORY_VOL
    sorted_wp = sorted(WORKPIECES, key=lambda w: w[4] / (w[1] * w[2] * w[3]), reverse=True)
    extra, rv = 0, rem_vol
    for name, l, w, h, profit in sorted_wp:
        cnt = rv // (l * w * h)
        extra += cnt * profit
        rv -= cnt * (l * w * h)
    ub = mand_profit + extra

    return {
        "counts": counts, "total_profit": best_profit,
        "total_used": total_used, "total_waste": total_waste,
        "utilization": total_used / TOTAL_RAW_VOL,
        "total_items": sum(counts.values()),
        "block_details": block_details,
        "upper_bound": ub, "elapsed": elapsed,
        "trials": num_trials, "ils_iterations": ils_iterations,
    }


def _ils_improve(best_packers, best_profit, iterations, sorted_blocks, verbose):
    """ILS 破坏-重建局部搜索"""
    rng = random.Random(12345)

    # 重建 blocks 列表
    ils_blocks = [(f"{n}_{i+1}", L, W, H)
                  for n, L, W, H, q in RAW_MATERIALS for i in range(q)]

    # 提取工件
    def extract_items(packers):
        items = []
        for pk in packers.values():
            for nm, _, _, _, dx, dy, dz in pk.placements:
                items.append((nm, dx, dy, dz, WP_MAP[nm][4] / (WP_MAP[nm][1] * WP_MAP[nm][2] * WP_MAP[nm][3])))
        return items

    # 预生成填充池
    filling_pool = []
    rem_vol_est = TOTAL_RAW_VOL - sum(
        pk.get_used_volume() for pk in best_packers.values())
    for name, l, w, h, profit in WORKPIECES:
        oris = get_orientations(l, w, h)
        est_max = min(300, max(50, int(rem_vol_est / (l * w * h) * 0.5)))
        for k in range(est_max):
            ori = rng.choice(oris)
            filling_pool.append((name, ori[0], ori[1], ori[2], profit / (l * w * h)))
    filling_pool.sort(key=lambda x: x[4], reverse=True)

    best_items = extract_items(best_packers)

    for it in range(iterations):
        # Destroy
        current_items = list(best_items)
        mandatory, optional = [], []
        cnts = {}
        for item in current_items:
            name = item[0]
            c = cnts.get(name, 0)
            if c < 10: mandatory.append(item)
            else: optional.append(item)
            cnts[name] = c + 1

        n_destroy = max(1, int(len(optional) * 0.15))
        if len(optional) == 0: continue

        if rng.random() < 0.3:
            destroy_idx = set(rng.sample(range(len(optional)),
                                         min(n_destroy, len(optional))))
        else:
            optional_ranked = sorted(enumerate(optional), key=lambda x: x[1][4])
            weights = [1.0 / (i + 1) for i in range(len(optional_ranked))]
            total_w = sum(weights)
            probs = [w / total_w for w in weights]
            chosen = set()
            while len(chosen) < n_destroy:
                pick = rng.choices(range(len(optional_ranked)), weights=probs, k=1)[0]
                chosen.add(pick)
            destroy_idx = {optional_ranked[i][0] for i in chosen}

        kept = mandatory + [item for i, item in enumerate(optional) if i not in destroy_idx]

        # Repair: 重新打包保留工件
        new_packers = {}
        for bname, bx, by, bz in ils_blocks:
            new_packers[bname] = BlockPacker(bx, by, bz, bname)
        kept.sort(key=lambda x: x[4], reverse=True)
        remaining_k = list(kept)
        for bname, bx, by, bz in sorted_blocks:
            pk = new_packers[bname]
            while remaining_k:
                res = pk.find_best(remaining_k)
                if res is None: break
                pk.try_place(res[1], res[2], res[3], res[4])
                remaining_k.pop(res[0])
            pk.spaces = merge_spaces(pk.spaces)

        # Fill
        remaining_f = list(filling_pool)
        for bname in sorted(new_packers.keys(),
                            key=lambda n: new_packers[n].get_waste(), reverse=True):
            pk = new_packers[bname]
            if pk.get_waste() <= 0: continue
            pk.spaces = merge_spaces(pk.spaces)
            while remaining_f:
                res = pk.find_best(remaining_f)
                if res is None: break
                pk.try_place(res[1], res[2], res[3], res[4])
                remaining_f.pop(res[0])

        # 验证
        cnts_new = {}
        for pk in new_packers.values():
            for nm, _, _, _, _, _, _ in pk.placements:
                cnts_new[nm] = cnts_new.get(nm, 0) + 1
        if any(cnts_new.get(f"J{i:02d}", 0) < 10 for i in range(1, 8)):
            continue

        profit_new = sum(cnts_new.get(nm, 0) * WP_MAP[nm][4]
                        for nm in set(n for n, _, _, _, _ in WORKPIECES))
        if profit_new > best_profit:
            best_profit = profit_new
            best_packers = new_packers
            best_items = extract_items(new_packers)

    if verbose:
        print(f"  ILS 完成: 最终利润 {best_profit:,}")
    return best_packers, best_profit


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                 第 6 部分: 子问题 3 — 订单选择 + 生产方案                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# 问题描述: 从 3 份备选订单中选 1 份，利用剩余 5 块原材料和库存工件，
#          最大化净利润 = 库存利润 + 自产利润 - 紧急采购损失。
#
# 求解方法: 多策略贪心 (Multi-Strategy Greedy)
#
#   对每个备选订单:
#     1. 生成 ~80 种工件放置顺序（按利润密度、体积、需求量等排序，含随机）
#     2. 每种顺序: 按此顺序依次将每种工件用 Global Best-Fit 填满目标数量
#     3. 计算净利润（含紧急采购损失）
#     4. 取净利润最高的顺序作为该订单的最优方案
#
#   选择净利润最大的订单
#
#  Why Multi-Strategy Greedy (not Beam Search):
#   Beam Search 按总利润排序 → 高利润工件优先 → 低利润工件被排斥
#   → H02 的 J01/J02 全部紧急采购 → 利润被严重低估
#   → 错误选择 H01 而非 H02
#   "先放低利润工件"策略为小工件预留空间 → H02 胜出
# ==============================================================================

def solve_subproblem3():
    """求解子问题 3: 多策略贪心订单选择"""

    def solve_one_order(order_name, order_demand, ordering):
        """用指定顺序做贪心 Best-Fit 打包"""
        # 计算需要生产的工件
        need = {}
        for name, l, w, h, profit in WORKPIECES:
            d = order_demand.get(name, 0)
            s = STOCK_P3.get(name, 0)
            n = max(0, d - s)
            if n > 0: need[name] = n

        stock_profit = sum(
            min(STOCK_P3.get(name, 0), order_demand.get(name, 0)) * profit
            for name, l, w, h, profit in WORKPIECES
        )

        # 初始化 5 块原材料
        block_dims = [(f"{n}_{i+1}", L, W, H)
                      for n, L, W, H, q in AVAILABLE_P3 for i in range(q)]
        packers = [BlockPacker(dx, dy, dz, name) for name, dx, dy, dz in block_dims]
        pnames = [name for name, _, _, _ in block_dims]

        placed = {}

        # 按 ordering 顺序依次放置每种工件
        for wp_name in ordering:
            if wp_name not in need: continue
            target = need[wp_name]
            count = 0
            name, l, w, h, profit = WP_MAP[wp_name]
            oris = get_orientations(l, w, h)

            while count < target:
                # 在所有 5 块中找全局最佳放置位置
                best_fit = None  # (gap, packer_idx, dx, dy, dz)
                for pi, pk in enumerate(packers):
                    for dx, dy, dz in oris:
                        fitting = [(j, s) for j, s in enumerate(pk.spaces)
                                   if s.can_fit(dx, dy, dz)]
                        if not fitting: continue
                        _, bs = min(fitting, key=lambda x:
                            (x[1].dx - dx) + (x[1].dy - dy) + (x[1].dz - dz))
                        gap = (bs.dx - dx) + (bs.dy - dy) + (bs.dz - dz)
                        if best_fit is None or gap < best_fit[0]:
                            best_fit = (gap, pi, dx, dy, dz)

                if best_fit is None: break
                _, pi, dx, dy, dz = best_fit
                packers[pi].try_place(wp_name, dx, dy, dz)
                count += 1

            placed[wp_name] = count

        # 统计结果
        emergency, emergency_loss = {}, 0
        for name, l, w, h, profit in WORKPIECES:
            d = order_demand.get(name, 0)
            s = STOCK_P3.get(name, 0)
            p = placed.get(name, 0)
            short = max(0, d - s - p)
            if short > 0:
                emergency[name] = short
                emergency_loss += short * profit

        produced_profit = sum(placed.get(name, 0) * WP_MAP[name][4]
                             for name, l, w, h, _ in WORKPIECES)
        net_profit = stock_profit + produced_profit - emergency_loss

        total_used = sum(pk.get_used_volume() for pk in packers)

        return {
            "order": order_name, "stock_profit": stock_profit,
            "produced_profit": produced_profit, "emergency_loss": emergency_loss,
            "net_profit": net_profit, "produced": placed, "emergency": emergency,
            "stock_used": {name: min(STOCK_P3.get(name, 0), order_demand.get(name, 0))
                          for name, _, _, _, _ in WORKPIECES},
            "total_used": total_used,
            "results": {pnames[i]: {"dims": pk.dims, "placements": pk.placements,
                                    "used_volume": pk.get_used_volume(),
                                    "utilization": pk.get_utilization()}
                        for i, pk in enumerate(packers)},
        }

    def generate_orderings(order_demand):
        """为订单生成 ~80 种工件放置顺序"""
        need = {}
        for name, l, w, h, profit in WORKPIECES:
            d = order_demand.get(name, 0)
            s = STOCK_P3.get(name, 0)
            n = max(0, d - s)
            if n > 0: need[name] = n

        wp_names = list(need.keys())
        if len(wp_names) <= 1: return [wp_names]

        orderings, seen = [], set()

        def add(ordering):
            key = tuple(ordering)
            if key not in seen:
                seen.add(key)
                orderings.append(ordering)

        # 基础排序策略
        add(sorted(wp_names, key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3])))
        add(sorted(wp_names, key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]), reverse=True))
        add(sorted(wp_names, key=lambda n: WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]))
        add(sorted(wp_names, key=lambda n: WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3], reverse=True))
        add(sorted(wp_names, key=lambda n: WP_MAP[n][4]))
        add(sorted(wp_names, key=lambda n: WP_MAP[n][4], reverse=True))
        add(sorted(wp_names, key=lambda n: need[n]))
        add(sorted(wp_names, key=lambda n: need[n], reverse=True))

        # 混合策略
        high = [n for n in wp_names if WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]) >= 0.01050]
        low = [n for n in wp_names if WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]) < 0.00980]
        mid = [n for n in wp_names if 0.00980 <= WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]) < 0.01050]
        high.sort(key=lambda n: WP_MAP[n][4], reverse=True)
        low.sort(key=lambda n: WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3])
        mid.sort(key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]))
        for perm in [high + low + mid, high + mid + low, low + high + mid,
                     low + mid + high, mid + high + low, mid + low + high]:
            add(perm)

        # 每种高利润工件开头的排列
        for h in high:
            rest = [n for n in wp_names if n != h]
            rest.sort(key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]))
            add([h] + rest)
            rest.sort(key=lambda n: WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3])
            add([h] + rest)

        # 针对 H02 的关键策略: 先放低利润密度工件为小工件预留空间
        if set(["J01", "J02", "J05"]).issubset(set(wp_names)):
            rest = [n for n in wp_names if n not in ["J01", "J02", "J05"]]
            rest.sort(key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]))
            add(["J05", "J01", "J02"] + rest)
            add(["J05", "J02", "J01"] + rest)
            add(["J01", "J02", "J05"] + rest)
            add(["J01", "J05", "J02"] + rest)
            add(["J02", "J01", "J05"] + rest)
            add(["J02", "J05", "J01"] + rest)
            # H02 关键: 先放低利润工件 J01/J02 填位，再锁高利润
            rest2 = [n for n in wp_names if n not in ["J01", "J02", "J05"]]
            rest2.sort(key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]), reverse=True)
            add(["J01", "J02"] + rest2 + ["J05"])
            add(["J01", "J02", "J05"] + rest2)
            add(["J02", "J01", "J05"] + rest2)
            # 先利润密度升序，后降序 (H02 关键策略)
            rest3 = sorted([n for n in wp_names if n not in ["J01", "J02"]],
                          key=lambda n: WP_MAP[n][4] / (WP_MAP[n][1] * WP_MAP[n][2] * WP_MAP[n][3]))
            add(["J01", "J02"] + rest3)
            add(["J02", "J01"] + rest3)
            # 需求量大的优先
            rest4 = sorted([n for n in wp_names if n not in ["J01", "J02"]],
                          key=lambda n: need[n], reverse=True)
            add(["J01", "J02"] + rest4)

        # 随机排列 (增加至 60 次以覆盖更多策略空间)
        rng = random.Random(42)
        for _ in range(60):
            perm = list(wp_names)
            rng.shuffle(perm)
            add(perm)

        return orderings

    # 对每个订单多策略求解
    all_results = []
    for oname, odemand in ORDERS_P3.items():
        best = None
        for ordering in generate_orderings(odemand):
            res = solve_one_order(oname, odemand, ordering)
            if best is None or res["net_profit"] > best["net_profit"]:
                best = res
        all_results.append(best)

    return all_results


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                            第 7 部分: 主入口                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def print_solution_p1(results, type_counts, total_vol, total_used, utilization):
    """打印子问题 1 结果"""
    print("\n" + "=" * 60)
    print("子问题 1 — 体积利用率最大化")
    print("=" * 60)
    print(f"  原材料总体积:  {total_vol:>15,} mm³")
    print(f"  已使用体积:    {total_used:>15,} mm³")
    print(f"  废料体积:      {total_vol - total_used:>15,} mm³")
    print(f"  总体积利用率:  {utilization * 100:>14.2f}%")
    print(f"  总工件数:      {sum(type_counts.values()):>15}")
    print(f"\n  各工件生产数量:")
    for name in sorted(type_counts):
        print(f"    {name}: {type_counts[name]}")


def print_solution_p2(sol):
    """打印子问题 2 结果"""
    print("\n" + "=" * 60)
    print("子问题 2 — 利润最大化（每工件 ≥10 件）")
    print("=" * 60)
    if sol is None:
        print("  ⚠ 未找到可行解!")
        return
    print(f"  总利润:        {sol['total_profit']:>15,} 元")
    print(f"  利润上界:      {sol['upper_bound']:>15,} 元 ({sol['total_profit']/sol['upper_bound']*100:.2f}%)")
    print(f"  材料利用率:    {sol['utilization'] * 100:>14.2f}%")
    print(f"  总工件数:      {sol['total_items']:>15}")
    print(f"  总耗时:        {sol['elapsed']:>14.1f}s")
    print(f"\n  工件产量:")
    for name, l, w, h, profit in WORKPIECES:
        cnt = sol["counts"].get(name, 0)
        ok = "✓" if cnt >= 10 else "✗"
        print(f"    {name} ({l}×{w}×{h}): {cnt:>4}  利润={cnt*profit:>8,}  {ok}")


def print_solution_p3(all_results):
    """打印子问题 3 结果"""
    print("\n" + "=" * 60)
    print("子问题 3 — 订单选择 + 生产方案")
    print("=" * 60)
    best = max(all_results, key=lambda r: r["net_profit"])
    print(f"\n  订单比较:")
    for r in all_results:
        marker = " ★ 最优" if r["order"] == best["order"] else ""
        print(f"    {r['order']}: 净利润={r['net_profit']:>10,} 元"
              f"  (生产={r['produced_profit']:>10,}  采购损失={r['emergency_loss']:>10,}){marker}")
    print(f"\n  选择订单: {best['order']}")
    print(f"  紧急采购工件: {dict(best['emergency'])}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="方形材料切割加工优化 — 主计算程序")
    parser.add_argument("--full", action="store_true", help="完整求解 (论文级精度)")
    parser.add_argument("--question", type=int, choices=[1, 2, 3], help="仅运行指定子问题")
    args = parser.parse_args()

    p2_trials = 48 if args.full else 12
    p2_ils = 800 if args.full else 100

    print("=" * 60)
    print("方形材料的切割加工优化问题 — 主计算程序")
    print("数学建模竞赛 A 题（亿星软件题目）")
    print("=" * 60)

    t_start = time.time()

    if args.question:
        if args.question == 1:
            results, tc, tv, tu, util = solve_subproblem1()
            print_solution_p1(results, tc, tv, tu, util)
        elif args.question == 2:
            sol = solve_subproblem2(num_trials=p2_trials, ils_iterations=p2_ils)
            print_solution_p2(sol)
        elif args.question == 3:
            all_r = solve_subproblem3()
            print_solution_p3(all_r)
    else:
        # 子问题 1
        t1 = time.time()
        results, tc, tv, tu, util = solve_subproblem1()
        print_solution_p1(results, tc, tv, tu, util)
        print(f"  耗时: {time.time() - t1:.1f}s")

        # 子问题 2
        t2 = time.time()
        sol = solve_subproblem2(num_trials=p2_trials, ils_iterations=p2_ils)
        print_solution_p2(sol)
        print(f"  耗时: {time.time() - t2:.1f}s")

        # 子问题 3
        t3 = time.time()
        all_r = solve_subproblem3()
        print_solution_p3(all_r)
        print(f"  耗时: {time.time() - t3:.1f}s")

    print(f"\n总耗时: {time.time() - t_start:.1f}s")
