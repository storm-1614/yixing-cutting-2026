# -*- coding: utf-8 -*-
r"""
================================================================================
子问题 2：每工件 ≥10 件，最大化总收益
求解算法：两阶段 EMS 贪心构造 + 多试次随机搜索
================================================================================

一、数学模型
------------

1. 集合与索引
   M = {L01, L02, L03}             原材料类型
   B_m = {1,2,...,5}                类型 m 的原材料块编号
   B = ∪_m B_m  (|B|=15)           全部原材料块
   J = {J01, J02, ..., J07}        工件类型
   O = {1,2,3,4,5,6}               摆放姿态 (长宽高排列)
   K_j                             工件 j 的实例编号

2. 参数
   (L_m, W_m, H_m)     原材料 m 尺寸        V_m = L_m·W_m·H_m     原材料体积
   (l_j, w_j, h_j)     工件 j 原始尺寸      v_j = l_j·w_j·h_j     工件体积
   (l'_j,w'_j,h'_j)^(o) 姿态 o 下的实际尺寸  p_j                  工件收益

3. 决策变量
   place_{b,j,k,o} ∈ {0,1}    工件 j 的第 k 个实例以姿态 o 是否放入块 b
   x_{b,j,k} ≥ 0              摆放 x 坐标
   y_{b,j,k} ≥ 0              摆放 y 坐标
   z_{b,j,k} ≥ 0              摆放 z 坐标 (刀具进给方向)

4. 约束条件

   (a) 最低产量:   Σ_{b,k,o} place_{b,j,k,o} ≥ 10   ∀j∈J
   (b) 空间边界:   x + l' ≤ L_m,  y + w' ≤ W_m,  z + h' ≤ H_m
   (c) 不重叠 (析取):
       对同一块 b 中任意两个不同工件实例, 至少满足:
         x + l' ≤ x'   ∨  x' + l'' ≤ x   ∨
         y + w' ≤ y'   ∨  y' + w'' ≤ y   ∨
         z + h' ≤ z'   ∨  z' + h'' ≤ z

5. 目标函数

   max  Π = Σ_{b,j,k,o}  p_j · place_{b,j,k,o}

6. 复杂度
   带析取约束的 3D 装箱 MILP, 强 NP-hard. 15 块料 + 数百工件 → 精确算法不可行.

二、求解算法：两阶段 EMS + 多试次

   阶段 1 (必须品):
     - 10×7=70 件必须品, 按体积降序排列 (大件优先), 轮换姿态
     - EMS 顺序打包到 15 块料中 (大块优先)
     - 确保所有必须品都能放入

   阶段 2 (利润填充):
     - 估计剩余空间容量, 生成额外候选工件
     - 按利润密度降序排列, 轮换姿态
     - EMS 顺序填充剩余空间
     - 合并碎片空间 + 二次填充

   多试次 (num_trials=30~50):
     - 变化: 必须品姿态轮换 vs 随机姿态; 利润品姿态策略
     - 保留全局最优解

   EMS 核心规则 (Best-Fit):
     维护互不重叠的空闲空间列表.
     每次放置工件时:
       (1) 在所有可容纳此工件的空间中, 找 (dx-l)+(dy-w)+(dz-h) 最小的
       (2) 在空间原点角落放置
       (3) 从该空间切除工件体积 (最多 6 子空间)
       (4) 检查所有其他空间是否与新工件相交, 若相交则切除
       (5) 周期性合并相邻空间以反碎片化
================================================================================
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from itertools import permutations
import time
import random


# ==============================================================================
# 数据定义
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
    def get_orientations(self) -> List[Tuple[int, int, int]]:
        seen = set()
        res = []
        for p in permutations([self.length, self.width, self.height]):
            if p not in seen:
                seen.add(p); res.append(p)
        return res


MATERIALS = [
    Material("L01", 300, 200, 150, 5),   #  9,000,000 × 5 = 45,000,000
    Material("L02", 250, 150, 100, 5),   #  3,750,000 × 5 = 18,750,000
    Material("L03", 200, 150, 80,  5),   #  2,400,000 × 5 = 12,000,000
]                                        #  Total:          75,750,000

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
TOTAL_RAW_VOL = sum(m.volume * m.quantity for m in MATERIALS)


# ==============================================================================
# EMS 核心数据结构
# ==============================================================================

@dataclass
class Space:
    """三维空闲空间"""
    x: int; y: int; z: int
    dx: int; dy: int; dz: int
    def can_fit(self, dx, dy, dz) -> bool:
        return self.dx >= dx and self.dy >= dy and self.dz >= dz
    @property
    def volume(self) -> int:
        return self.dx * self.dy * self.dz


def get_intersection(sp: Space, ix: int, iy: int, iz: int,
                     idx: int, idy: int, idz: int) -> Optional[Tuple]:
    """空间与工件包围盒的交集, 无交集返回 None."""
    x1, y1, z1 = max(sp.x, ix), max(sp.y, iy), max(sp.z, iz)
    x2 = min(sp.x + sp.dx, ix + idx)
    y2 = min(sp.y + sp.dy, iy + idy)
    z2 = min(sp.z + sp.dz, iz + idz)
    return (x1, y1, z1, x2-x1, y2-y1, z2-z1) if x1<x2 and y1<y2 and z1<z2 else None


def split_space(sp: Space, rx: int, ry: int, rz: int,
                rdx: int, rdy: int, rdz: int) -> List[Space]:
    """切除子体积, 返回最多 6 个剩余空间."""
    res = []
    s = sp
    if rz - s.z > 0:           res.append(Space(s.x, s.y, s.z, s.dx, s.dy, rz-s.z))
    if s.z+s.dz-rz-rdz > 0:    res.append(Space(s.x, s.y, rz+rdz, s.dx, s.dy, s.z+s.dz-rz-rdz))
    if ry - s.y > 0:           res.append(Space(s.x, s.y, rz, s.dx, ry-s.y, rdz))
    if s.y+s.dy-ry-rdy > 0:    res.append(Space(s.x, ry+rdy, rz, s.dx, s.y+s.dy-ry-rdy, rdz))
    if rx - s.x > 0:           res.append(Space(s.x, ry, rz, rx-s.x, rdy, rdz))
    if s.x+s.dx-rx-rdx > 0:    res.append(Space(rx+rdx, ry, rz, s.x+s.dx-rx-rdx, rdy, rdz))
    return res


def merge_spaces(spaces: List[Space]) -> List[Space]:
    """合并相邻空间以减少碎片."""
    if len(spaces) <= 1:
        return spaces
    changed = True
    cur = list(spaces)
    while changed:
        changed = False
        n, mrg, used = len(cur), [], [False] * len(cur)
        for i in range(n):
            if used[i]: continue
            si, found = cur[i], False
            for j in range(n):
                if i == j or used[j]: continue
                sj = cur[j]
                # y 方向合并
                if si.x==sj.x and si.dx==sj.dx and si.z==sj.z and si.dz==sj.dz:
                    if si.y+si.dy==sj.y:
                        mrg.append(Space(si.x,si.y,si.z,si.dx,si.dy+sj.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.y+sj.dy==si.y:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx,sj.dy+si.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
                # x 方向合并
                if si.y==sj.y and si.dy==sj.dy and si.z==sj.z and si.dz==sj.dz:
                    if si.x+si.dx==sj.x:
                        mrg.append(Space(si.x,si.y,si.z,si.dx+sj.dx,si.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.x+sj.dx==si.x:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx+si.dx,sj.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
                # z 方向合并
                if si.x==sj.x and si.dx==sj.dx and si.y==sj.y and si.dy==sj.dy:
                    if si.z+si.dz==sj.z:
                        mrg.append(Space(si.x,si.y,si.z,si.dx,si.dy,si.dz+sj.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.z+sj.dz==si.z:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx,sj.dy,sj.dz+si.dz))
                        used[i]=used[j]=found=changed=True; break
            if not found:
                mrg.append(si); used[i] = True
        cur = mrg
    return cur


# ==============================================================================
# EMS 打包器
# ==============================================================================

class BlockPacker:
    """单块原材料的 EMS 打包器."""

    def __init__(self, dx: int, dy: int, dz: int):
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces: List[Space] = [Space(0, 0, 0, dx, dy, dz)]
        self.placements: List[Tuple] = []

    def find_best_to_place(self, candidates: List[Tuple]
                           ) -> Optional[Tuple[int, str, int, int, int]]:
        """
        从候选列表中找"最紧密贴合"的工件.
        candidates: [(name, dx, dy, dz, priority), ...]
        返回: (index, name, dx, dy, dz) 或 None
        """
        best_idx, best_score = -1, float('inf')
        best_name, best_dims = None, None
        for i, (name, dx, dy, dz, _) in enumerate(candidates):
            fitting = [(j, s) for j, s in enumerate(self.spaces)
                       if s.can_fit(dx, dy, dz)]
            if not fitting: continue
            _, best_s = min(fitting, key=lambda x:
                (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
            score = (best_s.dx-dx)+(best_s.dy-dy)+(best_s.dz-dz)
            if score < best_score:
                best_score = score; best_idx = i
                best_name = name; best_dims = (dx, dy, dz)
        if best_idx < 0: return None
        return (best_idx, best_name, *best_dims)

    def try_place(self, name: str, dx: int, dy: int, dz: int
                  ) -> Optional[Tuple[int, int, int]]:
        """尝试放置工件, 成功返回 (x,y,z), 失败返回 None."""
        fitting = [(i, s) for i, s in enumerate(self.spaces)
                   if s.can_fit(dx, dy, dz)]
        if not fitting: return None
        bi, best_s = min(fitting, key=lambda x:
            (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
        px, py, pz = best_s.x, best_s.y, best_s.z
        used = self.spaces.pop(bi)
        new_sps = split_space(used, px, py, pz, dx, dy, dz)
        cleaned = []
        for s in self.spaces:
            inter = get_intersection(s, px, py, pz, dx, dy, dz)
            if inter is None: cleaned.append(s)
            else: cleaned.extend(split_space(s, *inter))
        self.spaces = cleaned + new_sps
        if len(self.spaces) > 150:
            self.spaces = merge_spaces(self.spaces)
        self.placements.append((name, px, py, pz, dx, dy, dz))
        return (px, py, pz)

    def get_used_volume(self) -> int:
        return sum(dx*dy*dz for _,_,_,_,dx,dy,dz in self.placements)

    def get_waste(self) -> int:
        return self.volume - self.get_used_volume()

    def get_utilization(self) -> float:
        return self.get_used_volume() / self.volume

    def get_placements(self) -> List[Tuple]:
        return self.placements.copy()


# ==============================================================================
# 多块打包引擎
# ==============================================================================

def create_blocks() -> List[Tuple[str, int, int, int]]:
    return [(f"{m.name}_{i+1}", m.length, m.width, m.height)
            for m in MATERIALS for i in range(m.quantity)]


def pack_items_into_blocks(blocks, items, after_pack_hook=None):
    """
    将 items 顺序打包到块中 (大块优先).
    items: [(name, dx, dy, dz, priority), ...]
    返回: {block_name: BlockPacker}
    """
    sorted_blocks = sorted(blocks, key=lambda b: b[1]*b[2]*b[3], reverse=True)
    remaining = list(items)
    packers = {}

    for bname, bx, by, bz in sorted_blocks:
        pk = BlockPacker(bx, by, bz)
        packers[bname] = pk
        while remaining:
            res = pk.find_best_to_place(remaining)
            if res is None: break
            idx, name, dx, dy, dz = res
            pk.try_place(name, dx, dy, dz)
            remaining.pop(idx)
        # 合并 + 重试
        pk.spaces = merge_spaces(pk.spaces)
        changed = True
        while changed and remaining:
            changed = False
            res = pk.find_best_to_place(remaining)
            if res is not None:
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                remaining.pop(idx)
                changed = True

    return packers


# ==============================================================================
# 子问题 2 求解
# ==============================================================================

def evaluate(packers) -> Dict:
    """汇总统计."""
    counts = {}
    total_profit = 0
    total_used = 0
    for pk in packers.values():
        total_used += pk.get_used_volume()
        for name, _,_,_,dx,dy,dz in pk.placements:
            counts[name] = counts.get(name, 0) + 1
            total_profit += WP_MAP[name].profit
    return {
        'counts': counts,
        'total_profit': total_profit,
        'total_used': total_used,
        'total_waste': TOTAL_RAW_VOL - total_used,
        'utilization': total_used / TOTAL_RAW_VOL,
        'total_items': sum(counts.values()),
    }


def solve(num_trials: int = 40):
    """
    两阶段 EMS + 多试次随机搜索.

    阶段 1: 必须品 (10×7=70 件), 按体积降序, 轮换/随机姿态
    阶段 2: 利润填充, 按利润密度降序, 轮换/随机姿态
    变化: 随机种子控制姿态选择和排序微扰
    保留全局最优.
    """
    blocks = create_blocks()
    print(f"原材料总体积: {TOTAL_RAW_VOL:,} (15 块)")
    min_vol = sum(WP_MAP[wp.name].volume*10 for wp in WORKPIECES)
    print(f"必须品体积:   {min_vol:,} ({min_vol/TOTAL_RAW_VOL:.1%})")
    print(f"试次: {num_trials}\n")

    best_solution = None
    best_eval = None
    t0 = time.time()

    for trial in range(num_trials):
        rng = random.Random(trial * 313 + 97)

        # ---- 阶段 1: 必须品 ----
        mandatory = []
        for wp in WORKPIECES:
            oris = wp.get_orientations()
            for i in range(10):
                if trial < 10:
                    ori = oris[i % len(oris)]  # 轮换
                else:
                    ori = rng.choice(oris)      # 随机
                mandatory.append((wp.name, ori[0], ori[1], ori[2], wp.volume))
        mandatory.sort(key=lambda x: x[4], reverse=True)

        packers = pack_items_into_blocks(blocks, mandatory)

        # 检查必须品是否全部放入
        ev = evaluate(packers)
        if any(ev['counts'].get(wp.name, 0) < 10 for wp in WORKPIECES):
            continue  # 本试次失败

        # ---- 阶段 2: 利润填充 ----
        remaining_vol = TOTAL_RAW_VOL - ev['total_used']
        profit_items = []
        for wp in WORKPIECES:
            oris = wp.get_orientations()
            est_max = max(60, int(remaining_vol / wp.volume * 0.6))
            for k in range(est_max):
                if trial < 10:
                    ori = oris[k % len(oris)]
                else:
                    ori = rng.choice(oris)
                profit_items.append(
                    (wp.name, ori[0], ori[1], ori[2], wp.profit_density))
        profit_items.sort(key=lambda x: x[4], reverse=True)

        # 在现有 packers 基础上继续打包
        remaining = list(profit_items)
        for bname in sorted(packers.keys(),
                            key=lambda n: packers[n].get_waste(), reverse=True):
            pk = packers[bname]
            if pk.get_waste() <= 0: continue
            while remaining:
                res = pk.find_best_to_place(remaining)
                if res is None: break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                remaining.pop(idx)
            pk.spaces = merge_spaces(pk.spaces)
            changed = True
            while changed and remaining:
                changed = False
                res = pk.find_best_to_place(remaining)
                if res is not None:
                    idx, name, dx, dy, dz = res
                    pk.try_place(name, dx, dy, dz)
                    remaining.pop(idx)
                    changed = True
            # 缝隙填充 (小尺寸工件)
            small = [(n, dx, dy, dz, pd) for n, dx, dy, dz, pd in remaining
                     if min(dx, dy, dz) <= 30]
            while small:
                res = pk.find_best_to_place(small)
                if res is None: break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                popped = small.pop(idx)
                for ri, (rn, rdx, rdy, rdz, _) in enumerate(remaining):
                    if rn==popped[0] and rdx==popped[1] and rdy==popped[2] and rdz==popped[3]:
                        remaining.pop(ri); break

        # 评估
        ev = evaluate(packers)
        if best_eval is None or ev['total_profit'] > best_eval['total_profit']:
            best_eval = ev
            best_solution = packers
            print(f"  Trial {trial+1:>3}: profit={ev['total_profit']:>10,}  "
                  f"items={ev['total_items']:>4}  util={ev['utilization']:.4%}  "
                  f"*** BEST ***")
        elif (trial+1) % 10 == 0:
            print(f"  Trial {trial+1:>3}: best={best_eval['total_profit']:,}  "
                  f"(trial {trial+1})")

    elapsed = time.time() - t0

    # 组装输出
    results = {}
    for bname, pk in best_solution.items():
        results[bname] = {
            'dims': pk.dims,
            'placements': pk.get_placements(),
            'utilization': pk.get_utilization(),
            'used_volume': pk.get_used_volume(),
            'waste_volume': pk.get_waste(),
        }

    return {
        'results': results,
        'counts': best_eval['counts'],
        'total_profit': best_eval['total_profit'],
        'total_used': best_eval['total_used'],
        'total_waste': best_eval['total_waste'],
        'utilization': best_eval['utilization'],
        'total_items': best_eval['total_items'],
        'elapsed': elapsed,
        'trials': num_trials,
    }


# ==============================================================================
# 输出
# ==============================================================================

def print_solution(sol):
    print("\n" + "=" * 70)
    print("子问题 2: 每工件 ≥10 件 + 最大化利润  (EMS 两阶段贪心)")
    print("=" * 70)

    print(f"\n--- 总体概览 ---")
    print(f"  试次 / 耗时:            {sol['trials']} / {sol['elapsed']:.1f}s")
    print(f"  总利润:                 {sol['total_profit']:>13,}")
    print(f"  原材料总体积:           {TOTAL_RAW_VOL:>13,}")
    print(f"  已用体积:               {sol['total_used']:>13,}")
    print(f"  废料体积:               {sol['total_waste']:>13,}")
    print(f"  材料利用率:             {sol['utilization']:.4%} "
          f"({sol['utilization']*100:.2f}%)")
    print(f"  总工件数:               {sol['total_items']:>8}")

    print(f"\n--- 工件生产统计 ---")
    print(f"  {'型号':<6} {'尺寸':<18} {'数量':<6} {'总体积':<14} "
          f"{'总利润':<14} {'满足?':<6}")
    print(f"  {'-'*6} {'-'*18} {'-'*6} {'-'*14} {'-'*14} {'-'*6}")
    for wp in WORKPIECES:
        c = sol['counts'].get(wp.name, 0)
        tv = c * wp.volume
        tp = c * wp.profit
        ok = "✓" if c >= 10 else f"✗({10-c})"
        print(f"  {wp.name:<6} {wp.length:>3}×{wp.width:>3}×{wp.height:<6} "
              f"{c:<6} {tv:>13,} {tp:>13,} {ok:<6}")

    print(f"\n--- 约束验证 ---")
    all_ok = True
    for wp in WORKPIECES:
        c = sol['counts'].get(wp.name, 0)
        ok = c >= 10
        if not ok: all_ok = False
        print(f"  {wp.name}: {c:>4} {'✓' if ok else '✗ FAIL'}")
    print(f"  全部满足: {'是' if all_ok else '否'}")

    print(f"\n--- 每块原材料 ---")
    print(f"  {'块':<8} {'尺寸':<20} {'工件数':<7} {'已用体积':<14} "
          f"{'利用率':<8}")
    for bname in sorted(sol['results'].keys()):
        d = sol['results'][bname]
        print(f"  {bname:<8} {d['dims'][0]}×{d['dims'][1]}×{d['dims'][2]:<8} "
              f"{len(d['placements']):<7} {d['used_volume']:>13,} "
              f"{d['utilization']:>7.2%}")


if __name__ == "__main__":
    print("=" * 70)
    print("子问题 2 求解: EMS 两阶段贪心 + 多试次")
    print("=" * 70)
    sol = solve(num_trials=40)
    print_solution(sol)
