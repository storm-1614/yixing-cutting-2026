# -*- coding: utf-8 -*-
r"""
================================================================================
子问题 2：每工件 ≥10 件，最大化总收益
算法 v3: 多策略单阶段池 + 顺序块 Best-Fit + 迭代局部搜索

核心设计:
  1. 保留原版的优秀机制 — 单次排序 + 顺序块 Best-Fit (扫描全部工件取最优)
  2. 两阶段 → 单阶段: 所有工件在同一池中, 按优先级排序
  3. 多策略优先级: 不同试次使用不同排序策略 (最长边/利润密度/混合)
  4. 迭代局部搜索: Destroy 低利润工件 → 重新打包 → 填充
  5. 理论分析: 上界计算 + 几何兼容性矩阵

与 v2 的关键区别:
  - v2 采样 10 件 → 每步选一件, 破坏了 Best-Fit 的全局扫描优势
  - v3 全局排序 → 每块扫描全部剩余工件, 保留原版的紧密贴合效果
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
    @property
    def longest_dim(self) -> int:
        return max(self.length, self.width, self.height)
    def get_orientations(self) -> List[Tuple[int, int, int]]:
        seen = set()
        res = []
        for p in permutations([self.length, self.width, self.height]):
            if p not in seen:
                seen.add(p); res.append(p)
        return res


MATERIALS = [
    Material("L01", 300, 200, 150, 5),
    Material("L02", 250, 150, 100, 5),
    Material("L03", 200, 150,  80, 5),
]

WORKPIECES = [
    Workpiece("J01", 40, 40, 40,  620),
    Workpiece("J02", 50, 40, 40,  780),
    Workpiece("J03", 60, 50, 30,  880),
    Workpiece("J04", 75, 60, 40, 1850),
    Workpiece("J05", 80, 60, 50, 2520),
    Workpiece("J06", 100, 50, 20, 1000),
    Workpiece("J07", 120, 20, 20,  540),
]

WP_MAP = {wp.name: wp for wp in WORKPIECES}
TOTAL_RAW_VOL = sum(m.volume * m.quantity for m in MATERIALS)
MIN_COUNT = 10
MANDATORY_VOL = sum(wp.volume * MIN_COUNT for wp in WORKPIECES)


# ==============================================================================
# EMS 核心 (保留原版实现)
# ==============================================================================

@dataclass
class Space:
    x: int; y: int; z: int
    dx: int; dy: int; dz: int
    def can_fit(self, dx, dy, dz) -> bool:
        return self.dx >= dx and self.dy >= dy and self.dz >= dz
    @property
    def volume(self) -> int:
        return self.dx * self.dy * self.dz


def get_intersection(sp: Space, ix: int, iy: int, iz: int,
                     idx: int, idy: int, idz: int) -> Optional[Tuple]:
    x1, y1, z1 = max(sp.x, ix), max(sp.y, iy), max(sp.z, iz)
    x2 = min(sp.x + sp.dx, ix + idx)
    y2 = min(sp.y + sp.dy, iy + idy)
    z2 = min(sp.z + sp.dz, iz + idz)
    return (x1, y1, z1, x2-x1, y2-y1, z2-z1) if x1<x2 and y1<y2 and z1<z2 else None


def split_space(sp: Space, rx: int, ry: int, rz: int,
                rdx: int, rdy: int, rdz: int) -> List[Space]:
    res = []
    s = sp
    if rz - s.z > 0:
        res.append(Space(s.x, s.y, s.z, s.dx, s.dy, rz-s.z))
    if s.z+s.dz-rz-rdz > 0:
        res.append(Space(s.x, s.y, rz+rdz, s.dx, s.dy, s.z+s.dz-rz-rdz))
    if ry - s.y > 0:
        res.append(Space(s.x, s.y, rz, s.dx, ry-s.y, rdz))
    if s.y+s.dy-ry-rdy > 0:
        res.append(Space(s.x, ry+rdy, rz, s.dx, s.y+s.dy-ry-rdy, rdz))
    if rx - s.x > 0:
        res.append(Space(s.x, ry, rz, rx-s.x, rdy, rdz))
    if s.x+s.dx-rx-rdx > 0:
        res.append(Space(rx+rdx, ry, rz, s.x+s.dx-rx-rdx, rdy, rdz))
    return res


def merge_spaces(spaces: List[Space]) -> List[Space]:
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
                if si.x==sj.x and si.dx==sj.dx and si.z==sj.z and si.dz==sj.dz:
                    if si.y+si.dy==sj.y:
                        mrg.append(Space(si.x,si.y,si.z,si.dx,si.dy+sj.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.y+sj.dy==si.y:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx,sj.dy+si.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
                if si.y==sj.y and si.dy==sj.dy and si.z==sj.z and si.dz==sj.dz:
                    if si.x+si.dx==sj.x:
                        mrg.append(Space(si.x,si.y,si.z,si.dx+sj.dx,si.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.x+sj.dx==si.x:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx+si.dx,sj.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
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
# 块打包器 (保留原版 Best-Fit 逻辑)
# ==============================================================================

class BlockPacker:
    """单块原材料 EMS 打包器."""

    def __init__(self, dx: int, dy: int, dz: int, name: str = ""):
        self.name = name
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces: List[Space] = [Space(0, 0, 0, dx, dy, dz)]
        self.placements: List[Tuple] = []  # (name, x, y, z, dx, dy, dz)

    def reset(self):
        self.spaces = [Space(0, 0, 0, *self.dims)]
        self.placements = []

    def find_best_to_place(self, candidates: List[Tuple]
                           ) -> Optional[Tuple[int, str, int, int, int]]:
        """
        从候选列表中找最紧密贴合的工件 (原版 Best-Fit 逻辑).
        candidates: [(name, dx, dy, dz, priority), ...]
        返回: (index, name, dx, dy, dz) 或 None
        """
        best_idx, best_score = -1, float('inf')
        best_name, best_dims = None, None
        for i, (name, dx, dy, dz, _) in enumerate(candidates):
            fitting = [(j, s) for j, s in enumerate(self.spaces)
                       if s.can_fit(dx, dy, dz)]
            if not fitting:
                continue
            _, best_s = min(fitting, key=lambda x:
                (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
            score = (best_s.dx-dx)+(best_s.dy-dy)+(best_s.dz-dz)
            if score < best_score:
                best_score = score; best_idx = i
                best_name = name; best_dims = (dx, dy, dz)
                if best_score == 0:
                    break  # 完美贴合, 无需继续搜索
        if best_idx < 0:
            return None
        return (best_idx, best_name, *best_dims)

    def try_place(self, name: str, dx: int, dy: int, dz: int
                  ) -> Optional[Tuple[int, int, int]]:
        """尝试放置工件, 成功返回 (x,y,z), 失败返回 None."""
        fitting = [(i, s) for i, s in enumerate(self.spaces)
                   if s.can_fit(dx, dy, dz)]
        if not fitting:
            return None
        bi, best_s = min(fitting, key=lambda x:
            (x[1].dx-dx)+(x[1].dy-dy)+(x[1].dz-dz))
        px, py, pz = best_s.x, best_s.y, best_s.z
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

    def get_used_volume(self) -> int:
        return sum(dx*dy*dz for _,_,_,_,dx,dy,dz in self.placements)

    def get_waste(self) -> int:
        return self.volume - self.get_used_volume()

    def get_utilization(self) -> float:
        return self.get_used_volume() / self.volume if self.volume > 0 else 0


# ==============================================================================
# v3 求解器: 多策略单阶段池 + 顺序块 Best-Fit + ILS
# ==============================================================================

def create_blocks() -> List[Tuple[str, int, int, int]]:
    return [(f"{m.name}_{i+1}", m.length, m.width, m.height)
            for m in MATERIALS for i in range(m.quantity)]


def count_items(packers: Dict[str, BlockPacker]) -> Dict[str, int]:
    counts = {}
    for pk in packers.values():
        for name, _, _, _, _, _, _ in pk.placements:
            counts[name] = counts.get(name, 0) + 1
    return counts


def total_profit(packers: Dict[str, BlockPacker]) -> int:
    profit = 0
    for pk in packers.values():
        for name, _, _, _, _, _, _ in pk.placements:
            profit += WP_MAP[name].profit
    return profit


def total_items(packers: Dict[str, BlockPacker]) -> int:
    return sum(len(pk.placements) for pk in packers.values())


def total_used_vol(packers: Dict[str, BlockPacker]) -> int:
    return sum(pk.get_used_volume() for pk in packers.values())


# ---- 工件池生成 ----
def generate_pool(rng: random.Random, extra_factor: float = 0.7
                  ) -> List[Tuple[str, int, int, int, bool]]:
    """
    生成工件池: 10 件必须品 + 额外候选.

    候选数量: 与原版一致, 按 max(60, remaining_vol/wp.vol × extra_factor) 生成.
    确保 Best-Fit 有足够多样的候选选择.

    返回: [(name, dx, dy, dz, is_mandatory), ...]
    """
    mandatory_vol = sum(wp.volume * MIN_COUNT for wp in WORKPIECES)
    remaining_vol = TOTAL_RAW_VOL - mandatory_vol
    pool = []

    for wp in WORKPIECES:
        oris = wp.get_orientations()
        # 必须品 (轮换姿态)
        for i in range(MIN_COUNT):
            ori = oris[i % len(oris)]
            pool.append((wp.name, ori[0], ori[1], ori[2], True))

        # 额外候选 — 与原版一致的计算公式
        est_max = max(60, int(remaining_vol / wp.volume * extra_factor))
        for k in range(est_max):
            ori = oris[k % len(oris)]  # 轮换姿态而非随机
            pool.append((wp.name, ori[0], ori[1], ori[2], False))

    return pool


# ---- 优先级排序策略 ----
def compute_priority(item: Tuple[str, int, int, int, bool],
                     strategy: str) -> float:
    """
    计算工件在池中的优先级 (越高越先被处理).

    策略:
      'volume'         — 体积优先
      'profit_density' — 利润密度优先
      'longest_dim'    — 最长边优先
      'hybrid_lv'      — 体积 × 利润密度¹/³
      'hybrid_vl'      — 最长边 × √利润密度
      'balanced'       — 体积40% + 最长边30% + 利润密度30%
      'two_phase'      — 必须品按体积降序 → 候选按利润密度降序
    """
    name, dx, dy, dz, is_mandatory = item
    wp = WP_MAP[name]
    ld = wp.longest_dim
    pd = wp.profit_density
    vol = wp.volume

    if strategy == 'two_phase':
        # 必须品在前, 按体积降序; 候选在后, 按利润密度降序
        if is_mandatory:
            return 1e9 + float(vol)  # 必须品: 极大基数 + 体积
        else:
            return pd  # 候选: 利润密度

    elif strategy == 'volume':
        # 必须品加小量修正 (即使是非必须品, 大件也应该优先)
        return float(vol) * (1.0 + pd * 0.0001)

    elif strategy == 'profit_density':
        return pd

    elif strategy == 'longest_dim':
        return float(ld) * (1.0 + pd * 0.0001)

    elif strategy == 'hybrid_lv':
        return float(vol) * (pd ** 0.333)

    elif strategy == 'hybrid_vl':
        return float(ld) * (pd ** 0.5)

    elif strategy == 'balanced':
        max_vol = max(w.volume for w in WORKPIECES)
        max_pd = max(w.profit_density for w in WORKPIECES)
        max_ld = max(w.longest_dim for w in WORKPIECES)
        vol_norm = vol / max_vol
        pd_norm = pd / max_pd
        ld_norm = ld / max_ld
        return 0.4 * vol_norm + 0.3 * ld_norm + 0.3 * pd_norm

    else:
        return pd


# ---- 打包全部块 ----
def pack_all_blocks(pool: List[Tuple[str, int, int, int, bool]],
                    priority_strategy: str,
                    rng: random.Random,
                    blocks: List[Tuple[str, int, int, int]]
                    ) -> Dict[str, BlockPacker]:
    """
    将池中工件打包到所有块中.

    流程:
      1. 按优先级排序池
      2. 按块体积降序处理
      3. 每块: 扫描全部剩余工件 → Best-Fit → 放置
      4. 合并 + 重试 + 缝隙填充
    """
    # 排序池 — 保留 mandatory flag 信息
    pool_with_priority = [
        (name, dx, dy, dz, compute_priority(
            (name, dx, dy, dz, is_mand), priority_strategy))
        for name, dx, dy, dz, is_mand in pool
    ]
    pool_with_priority.sort(key=lambda x: x[4], reverse=True)

    # 块按体积降序
    sorted_blocks = sorted(blocks, key=lambda b: b[1]*b[2]*b[3], reverse=True)

    # 对于 two_phase* 策略, 分两遍打包以确保必须品优先
    if priority_strategy.startswith('two_phase'):
        # Phase 1 策略
        p1 = priority_strategy.replace('two_phase_', '')
        if p1 == 'two_phase':
            p1 = 'volume'

        # 构建必须品列表, 按策略设置权重
        mandatory_pool = []
        for n, dx, dy, dz, is_mand in pool:
            if not is_mand:
                continue
            wp = WP_MAP[n]
            if p1 == 'volume':
                w = float(wp.volume)
            elif p1 == 'ld':
                w = float(wp.longest_dim)
            elif p1 == 'pd':
                w = wp.profit_density
            elif p1 == 'hybrid':
                w = float(wp.volume) * (wp.profit_density ** 0.333)
            elif p1 == 'random':
                w = rng.random()
            else:
                w = float(wp.volume)
            mandatory_pool.append((n, dx, dy, dz, w))

        if p1 != 'random':
            mandatory_pool.sort(key=lambda x: x[4], reverse=True)

        # Phase 1: 放置必须品
        remaining = list(mandatory_pool)
        packers = {}
        for bname, bx, by, bz in sorted_blocks:
            pk = BlockPacker(bx, by, bz, bname)
            packers[bname] = pk
            changed = True
            while changed and remaining:
                changed = False
                res = pk.find_best_to_place(remaining)
                if res is not None:
                    idx, name, dx, dy, dz = res
                    pk.try_place(name, dx, dy, dz)
                    remaining.pop(idx)
                    changed = True
            pk.spaces = merge_spaces(pk.spaces)

        # Phase 2: 放置候选
        optional_pool = [(n, dx, dy, dz, WP_MAP[n].profit_density)
                         for n, dx, dy, dz, is_mand in pool if not is_mand]
        optional_pool.sort(key=lambda x: x[4], reverse=True)
        remaining = list(optional_pool)

        for bname, _, _, _ in sorted_blocks:
            pk = packers[bname]
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

        # 缝隙填充
        for bname in sorted(packers.keys(),
                            key=lambda n: packers[n].get_waste(), reverse=True):
            pk = packers[bname]
            if pk.get_waste() <= 0:
                continue
            pk.spaces = merge_spaces(pk.spaces)
            small = [(n, dx, dy, dz, pr) for n, dx, dy, dz, pr in remaining
                     if min(dx, dy, dz) <= 30]
            while small:
                res = pk.find_best_to_place(small)
                if res is None:
                    break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                popped = small.pop(idx)
                for ri, (rn, rdx, rdy, rdz, _) in enumerate(remaining):
                    if rn==popped[0] and rdx==popped[1] and rdy==popped[2] and rdz==popped[3]:
                        remaining.pop(ri); break
            while remaining:
                res = pk.find_best_to_place(remaining)
                if res is None:
                    break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                remaining.pop(idx)

        return packers

    # 非 two_phase 策略: 单遍打包 (原逻辑)
    remaining = list(pool_with_priority)
    packers = {}

    for bname, bx, by, bz in sorted_blocks:
        pk = BlockPacker(bx, by, bz, bname)
        packers[bname] = pk

        # 主填充
        while remaining:
            res = pk.find_best_to_place(remaining)
            if res is None:
                break
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

    # --- 缝隙填充 (全局) ---
    for bname in sorted(packers.keys(),
                        key=lambda n: packers[n].get_waste(), reverse=True):
        pk = packers[bname]
        if pk.get_waste() <= 0:
            continue
        pk.spaces = merge_spaces(pk.spaces)

        # 小尺寸工件优先
        small = [(n, dx, dy, dz, pr) for n, dx, dy, dz, pr in remaining
                 if min(dx, dy, dz) <= 30]
        while small:
            res = pk.find_best_to_place(small)
            if res is None:
                break
            idx, name, dx, dy, dz = res
            pk.try_place(name, dx, dy, dz)
            popped = small.pop(idx)
            # 从 remaining 中删除对应项
            for ri, (rn, rdx, rdy, rdz, _) in enumerate(remaining):
                if rn == popped[0] and rdx == popped[1] and rdy == popped[2] and rdz == popped[3]:
                    remaining.pop(ri)
                    break

        # 再试更大尺寸
        while remaining:
            res = pk.find_best_to_place(remaining)
            if res is None:
                break
            idx, name, dx, dy, dz = res
            pk.try_place(name, dx, dy, dz)
            remaining.pop(idx)

    return packers


# ---- 破坏-重建局部搜索 ----
def destroy_and_repair(best_packers: Dict[str, BlockPacker],
                       rng: random.Random,
                       iterations: int = 500,
                       destroy_ratio: float = 0.15
                       ) -> Dict[str, BlockPacker]:
    """
    ILS: 破坏-重建.

    优化: 预先生成填充池, 避免每轮重复生成.
    每轮:
      1. 从已放置工件中移出低利润密度的非必须品
      2. 保留的工件重新打包到空块中 (快速)
      3. 用预生成的填充池填充剩余空间
      4. 若改善则接受
    """
    blocks = create_blocks()
    sorted_blocks = sorted(blocks, key=lambda b: b[1]*b[2]*b[3], reverse=True)

    # 从当前解中提取工件列表
    def extract_items(packers):
        items = []
        for pk in packers.values():
            for name, _, _, _, dx, dy, dz in pk.placements:
                items.append((name, dx, dy, dz, WP_MAP[name].profit_density))
        return items

    # 预生成填充池 (只生成一次, 每轮重用)
    filling_pool = []
    remaining_vol_est = TOTAL_RAW_VOL - total_used_vol(best_packers)
    for wp in WORKPIECES:
        oris = wp.get_orientations()
        est_max = max(50, int(remaining_vol_est / wp.volume * 0.5))
        est_max = min(est_max, 300)
        for k in range(est_max):
            ori = rng.choice(oris)
            filling_pool.append(
                (wp.name, ori[0], ori[1], ori[2], wp.profit_density))
    filling_pool.sort(key=lambda x: x[4], reverse=True)

    best_items = extract_items(best_packers)
    best_profit = total_profit(best_packers)

    for it in range(iterations):
        # --- Destroy ---
        current_items = list(best_items)

        # 分离必须品和非必须品
        mandatory = []
        optional = []
        counts = {}
        for item in current_items:
            name = item[0]
            c = counts.get(name, 0)
            if c < MIN_COUNT:
                mandatory.append(item)
            else:
                optional.append(item)
            counts[name] = c + 1

        n_destroy = max(1, int(len(optional) * destroy_ratio))
        if n_destroy == 0 or len(optional) == 0:
            continue

        # 策略切换: 30% 随机破坏, 70% 偏见低利润密度
        if rng.random() < 0.3:
            destroy_idx = set(rng.sample(
                range(len(optional)), min(n_destroy, len(optional))))
        else:
            optional_ranked = sorted(enumerate(optional),
                                     key=lambda x: x[1][4])
            weights = [1.0 / (i + 1) for i in range(len(optional_ranked))]
            total_w = sum(weights)
            probs = [w / total_w for w in weights]
            chosen_indices = set()
            while len(chosen_indices) < n_destroy:
                pick = rng.choices(range(len(optional_ranked)),
                                   weights=probs, k=1)[0]
                chosen_indices.add(pick)
            destroy_idx = {optional_ranked[i][0] for i in chosen_indices}

        kept_optional = [item for i, item in enumerate(optional)
                        if i not in destroy_idx]
        kept_items = mandatory + kept_optional

        # --- Repair: 重新打包保留工件 ---
        new_packers = {}
        for bname, bx, by, bz in blocks:
            new_packers[bname] = BlockPacker(bx, by, bz, bname)

        kept_items.sort(key=lambda x: x[4], reverse=True)
        remaining = [(n, dx, dy, dz, pd) for n, dx, dy, dz, pd in kept_items]

        for bname, bx, by, bz in sorted_blocks:
            pk = new_packers[bname]
            changed = True
            while changed and remaining:
                changed = False
                res = pk.find_best_to_place(remaining)
                if res is not None:
                    idx, name, dx, dy, dz = res
                    pk.try_place(name, dx, dy, dz)
                    remaining.pop(idx)
                    changed = True
            pk.spaces = merge_spaces(pk.spaces)

        # --- Fill: 用预生成池填充剩余空间 ---
        fill_remaining = list(filling_pool)
        for bname in sorted(new_packers.keys(),
                            key=lambda n: new_packers[n].get_waste(),
                            reverse=True):
            pk = new_packers[bname]
            if pk.get_waste() <= 0:
                continue
            pk.spaces = merge_spaces(pk.spaces)
            while fill_remaining:
                res = pk.find_best_to_place(fill_remaining)
                if res is None:
                    break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                fill_remaining.pop(idx)

        # 验证约束
        counts_new = count_items(new_packers)
        if any(counts_new.get(wp.name, 0) < MIN_COUNT for wp in WORKPIECES):
            continue

        profit_new = total_profit(new_packers)
        if profit_new > best_profit:
            best_profit = profit_new
            best_packers = new_packers
            best_items = extract_items(new_packers)

    return best_packers


# ---- 主求解函数 ----
def solve(num_trials: int = 24, ils_iterations: int = 300):
    """
    多策略多样本求解 + ILS.

    策略分布:
      - longest_dim (注重几何):    6 次试验
      - profit_density (注重经济): 6 次试验
      - hybrid_lp (混合):          6 次试验
      - hybrid_lv (混合):          6 次试验
    加上不同随机种子, 共 num_trials 次.
    """
    blocks = create_blocks()
    # 全部使用两阶段变体 (确保可行性), 变化在 Phase 1 的排序策略
    strategies = ['two_phase_volume', 'two_phase_ld', 'two_phase_pd',
                  'two_phase_hybrid', 'two_phase_random']
    # 确保策略均匀分布
    trials_per_strategy = num_trials // len(strategies)
    trial_strategies = []
    for s in strategies:
        trial_strategies.extend([s] * trials_per_strategy)
    # 余数随机
    rng_setup = random.Random(42)
    while len(trial_strategies) < num_trials:
        trial_strategies.append(rng_setup.choice(strategies))
    rng_setup.shuffle(trial_strategies)

    print(f"原材料总体积: {TOTAL_RAW_VOL:,} (15 块)")
    print(f"必须品体积:   {MANDATORY_VOL:,} ({MANDATORY_VOL/TOTAL_RAW_VOL:.1%})")
    print(f"策略: {strategies}")
    print(f"试次: {num_trials}, ILS: {ils_iterations}\n")

    best_packers = None
    best_profit = 0
    t0 = time.time()

    for trial in range(num_trials):
        strategy = trial_strategies[trial]
        trial_seed = trial * 67 + 313
        rng = random.Random(trial_seed)

        # 生成池 (5-元组: name, dx, dy, dz, is_mandatory)
        pool = generate_pool(rng, extra_factor=0.7)

        # 打包
        packers = pack_all_blocks(pool, strategy, rng, blocks)

        # 验证约束
        counts = count_items(packers)
        if any(counts.get(wp.name, 0) < MIN_COUNT for wp in WORKPIECES):
            continue

        profit = total_profit(packers)

        if profit > best_profit:
            best_profit = profit
            best_packers = packers
            print(f"  Trial {trial+1:>3} [{strategy:<16}]: "
                  f"profit={profit:>10,}  "
                  f"items={total_items(packers):>4}  "
                  f"util={total_used_vol(packers)/TOTAL_RAW_VOL:.4%}  "
                  f"*** BEST ***")
        elif (trial + 1) % 8 == 0:
            print(f"  Trial {trial+1:>3} [{strategy:<16}]: "
                  f"best so far = {best_profit:,}")

    construct_time = time.time() - t0

    if best_packers is None:
        print("ERROR: No feasible solution!")
        return None

    print(f"\n构造阶段: {num_trials} 次试验, "
          f"最优 {best_profit:,}, {construct_time:.1f}s")

    # --- ILS ---
    if ils_iterations > 0:
        print(f"\nILS 改进 ({ils_iterations} 次迭代)...")
        t1 = time.time()
        ils_rng = random.Random(12345)
        best_packers = destroy_and_repair(
            best_packers, ils_rng, ils_iterations)
        ils_time = time.time() - t1
        best_profit = total_profit(best_packers)
        print(f"ILS 完成: 最终利润 {best_profit:,}, {ils_time:.1f}s")
    else:
        ils_time = 0

    elapsed = time.time() - t0
    counts = count_items(best_packers)

    # 上界
    sorted_wp = sorted(WORKPIECES, key=lambda w: w.profit_density, reverse=True)
    mand_profit = sum(wp.profit * MIN_COUNT for wp in WORKPIECES)
    rem_vol = TOTAL_RAW_VOL - MANDATORY_VOL
    extra_profit = 0
    for wp in sorted_wp:
        cnt = rem_vol // wp.volume
        extra_profit += cnt * wp.profit
        rem_vol -= cnt * wp.volume
    ub = mand_profit + extra_profit

    # 组装输出
    results = {}
    used_vol = 0
    for bname, pk in best_packers.items():
        used_vol += pk.get_used_volume()
        results[bname] = {
            'dims': pk.dims,
            'placements': pk.placements.copy(),
            'utilization': pk.get_utilization(),
            'used_volume': pk.get_used_volume(),
            'waste_volume': pk.get_waste(),
        }

    return {
        'results': results,
        'counts': counts,
        'total_profit': best_profit,
        'total_used': used_vol,
        'total_waste': TOTAL_RAW_VOL - used_vol,
        'utilization': used_vol / TOTAL_RAW_VOL,
        'total_items': sum(counts.values()),
        'elapsed': elapsed,
        'construct_time': construct_time,
        'ils_time': ils_time,
        'trials': num_trials,
        'ils_iterations': ils_iterations,
        'upper_bound': ub,
        'ub_gap': best_profit / ub if ub > 0 else 0,
    }


# ==============================================================================
# 输出
# ==============================================================================

def print_solution(sol):
    print("\n" + "=" * 70)
    print("子问题 2: 每工件 ≥10 件 + 最大化利润  (v3 多策略单阶段 + ILS)")
    print("=" * 70)

    print(f"\n--- 总体概览 ---")
    print(f"  构造试验 / ILS 迭代:    {sol['trials']} / {sol['ils_iterations']}")
    print(f"  总耗时:                  {sol['elapsed']:.1f}s "
          f"(构造 {sol['construct_time']:.1f}s + ILS {sol['ils_time']:.1f}s)")
    print(f"  总利润:                 {sol['total_profit']:>13,}")
    print(f"  理论利润上界 (体积松弛): {sol['upper_bound']:>13,}")
    print(f"  占上界比例:             {sol['ub_gap']:.4%}")
    print(f"  原材料总体积:           {TOTAL_RAW_VOL:>13,}")
    print(f"  已用体积:               {sol['total_used']:>13,}")
    print(f"  废料体积:               {sol['total_waste']:>13,}")
    print(f"  材料利用率:             {sol['utilization']:.4%} "
          f"({sol['utilization']*100:.2f}%)")
    print(f"  总工件数:               {sol['total_items']:>8}")

    print(f"\n--- 工件生产统计 ---")
    print(f"  {'型号':<6} {'尺寸':<18} {'数量':<6} {'总体积':<14} "
          f"{'总利润':<14} {'满足?'}")
    print(f"  {'-'*6} {'-'*18} {'-'*6} {'-'*14} {'-'*14} {'-'*6}")
    for wp in WORKPIECES:
        c = sol['counts'].get(wp.name, 0)
        tv = c * wp.volume
        tp = c * wp.profit
        ok = "✓" if c >= MIN_COUNT else f"✗({MIN_COUNT-c})"
        print(f"  {wp.name:<6} {wp.length:>3}×{wp.width:>3}×{wp.height:<6} "
              f"{c:<6} {tv:>13,} {tp:>13,} {ok}")

    print(f"\n--- 约束验证 ---")
    all_ok = True
    for wp in WORKPIECES:
        c = sol['counts'].get(wp.name, 0)
        ok = c >= MIN_COUNT
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
    print("子问题 2 求解: v3 多策略单阶段池 + 顺序块 Best-Fit + ILS")
    print("=" * 70)
    sol = solve(num_trials=48, ils_iterations=800)
    print_solution(sol)
