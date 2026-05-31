# -*- coding: utf-8 -*-
r"""
================================================================================
子问题 2：每工件 ≥10 件，最大化总收益
新算法：自适应单阶段构造 + 迭代局部搜索 (Adaptive Single-Phase + ILS)

设计原则：
  1. 单阶段池 — 所有工件（必须+候选）在同一池中竞争，通过动态评分平衡约束与利润
  2. 约束引导评分 — 低于最低产量的工件获得优先级提升，平滑过渡而非硬切换
  3. 全姿态评估 — 每次放置评估全部 6 种姿态，选择几何最优
  4. 迭代局部搜索 — Destroy-and-Repair 破坏低利润密度工件后重填
  5. 有意义的多样本 — 变化工件排序策略、姿态策略、块处理顺序
  6. 上界计算 — 体积背包松弛给出理论天花板
================================================================================
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set
from itertools import permutations
import time
import random
import copy


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
        """返回所有唯一姿态 (去重)."""
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
MIN_COUNT = 10  # 每种工件最低产量


# ==============================================================================
# EMS 核心数据结构 (保留原版优良设计)
# ==============================================================================

@dataclass
class Space:
    """三维空闲空间."""
    x: int; y: int; z: int
    dx: int; dy: int; dz: int
    def can_fit(self, dx: int, dy: int, dz: int) -> bool:
        return self.dx >= dx and self.dy >= dy and self.dz >= dz
    @property
    def volume(self) -> int:
        return self.dx * self.dy * self.dz


def get_intersection(sp: Space, ix: int, iy: int, iz: int,
                     idx: int, idy: int, idz: int) -> Optional[Tuple]:
    """空间与工件的交集, 无交集返回 None."""
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
                # y-dir merge
                if si.x==sj.x and si.dx==sj.dx and si.z==sj.z and si.dz==sj.dz:
                    if si.y+si.dy==sj.y:
                        mrg.append(Space(si.x,si.y,si.z,si.dx,si.dy+sj.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.y+sj.dy==si.y:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx,sj.dy+si.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
                # x-dir merge
                if si.y==sj.y and si.dy==sj.dy and si.z==sj.z and si.dz==sj.dz:
                    if si.x+si.dx==sj.x:
                        mrg.append(Space(si.x,si.y,si.z,si.dx+sj.dx,si.dy,si.dz))
                        used[i]=used[j]=found=changed=True; break
                    elif sj.x+sj.dx==si.x:
                        mrg.append(Space(sj.x,sj.y,sj.z,sj.dx+si.dx,sj.dy,sj.dz))
                        used[i]=used[j]=found=changed=True; break
                # z-dir merge
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
# 增强版 EMS 打包器
# ==============================================================================

@dataclass
class Placement:
    """一次摆放记录."""
    wp_name: str
    x: int; y: int; z: int
    dx: int; dy: int; dz: int
    profit: int = 0
    profit_density: float = 0.0


class BlockPacker:
    """单块原材料的 EMS 打包器 (增强版)."""

    def __init__(self, dx: int, dy: int, dz: int, name: str = ""):
        self.name = name
        self.dims = (dx, dy, dz)
        self.volume = dx * dy * dz
        self.spaces: List[Space] = [Space(0, 0, 0, dx, dy, dz)]
        self.placements: List[Placement] = []

    def reset(self):
        """重置到空状态 (用于重打包)."""
        self.spaces = [Space(0, 0, 0, *self.dims)]
        self.placements = []

    def evaluate_placement(self, dx: int, dy: int, dz: int,
                           profit: float, profit_density: float,
                           wp_name: str) -> Optional[Tuple[float, int, int, int, int]]:
        """
        评估该工件在所有可用空间中的最佳摆放.

        返回: (score, space_idx, x, y, z) 或 None (放不下)

        score 综合考虑:
          - fit_tightness: 工件体积/空间体积 (越高越好)
          - fragmentation_penalty: 摆放后是否会产生无法利用的碎片
          - profit_density: 工件本身的利润密度
        """
        best_score = -1.0
        best_info = None

        for si, sp in enumerate(self.spaces):
            if not sp.can_fit(dx, dy, dz):
                continue

            # fit_tightness: 工件占空间的体积比
            item_vol = dx * dy * dz
            fit_tightness = item_vol / sp.volume

            # fragmentation_penalty: 模拟放置后评估子空间质量
            # 先快速模拟 split 产生的子空间
            px, py, pz = sp.x, sp.y, sp.z
            new_spaces = split_space(sp, px, py, pz, dx, dy, dz)

            # 评估碎片化: 能够容纳至少一个最小工件的子空间比例
            min_item_dim = 20  # 最小工件的最小维度 (J07 的 20)
            usable_vol = sum(s.volume for s in new_spaces
                           if s.dx >= min_item_dim and s.dy >= min_item_dim
                           and s.dz >= min_item_dim)
            space_quality = usable_vol / max(1, sum(s.volume for s in new_spaces))

            # 综合评分: fit_tightness 和 space_quality 的几何平均
            # 加上利润密度的微小贡献 (用于打破平局)
            placement_score = (fit_tightness * 0.6 + space_quality * 0.4
                             + profit_density * 0.0001)

            if placement_score > best_score:
                best_score = placement_score
                best_info = (si, px, py, pz)

        if best_info is None:
            return None
        si, px, py, pz = best_info
        return (best_score, si, px, py, pz)

    def try_place(self, wp_name: str, dx: int, dy: int, dz: int,
                  profit: int = 0, profit_density: float = 0.0
                  ) -> Optional[Tuple[int, int, int]]:
        """尝试放置工件. 成功返回 (x,y,z), 失败返回 None."""
        result = self.evaluate_placement(dx, dy, dz, profit, profit_density, wp_name)
        if result is None:
            return None

        _, si, px, py, pz = result
        used = self.spaces.pop(si)

        # 切除已用体积
        new_sps = split_space(used, px, py, pz, dx, dy, dz)

        # 检查其他空间是否与新工件相交
        cleaned = []
        for s in self.spaces:
            inter = get_intersection(s, px, py, pz, dx, dy, dz)
            if inter is None:
                cleaned.append(s)
            else:
                cleaned.extend(split_space(s, *inter))

        self.spaces = cleaned + new_sps

        # 周期性合并
        if len(self.spaces) > 200:
            self.spaces = merge_spaces(self.spaces)

        self.placements.append(Placement(
            wp_name, px, py, pz, dx, dy, dz, profit, profit_density))
        return (px, py, pz)

    def get_placements_list(self) -> List[Placement]:
        return self.placements.copy()

    def get_used_volume(self) -> int:
        return sum(p.dx * p.dy * p.dz for p in self.placements)

    def get_waste(self) -> int:
        return self.volume - self.get_used_volume()

    def get_utilization(self) -> float:
        return self.get_used_volume() / self.volume if self.volume > 0 else 0.0

    def collect_items(self) -> List[Tuple]:
        """收集所有已放置工件的信息."""
        return [(p.wp_name, p.dx, p.dy, p.dz, p.profit, p.profit_density)
                for p in self.placements]


# ==============================================================================
# 自适应单阶段求解器
# ==============================================================================

@dataclass
class PoolItem:
    """工件池中的候选实例."""
    wp_name: str
    dx: int; dy: int; dz: int
    profit: int
    profit_density: float
    mandatory: bool = False  # 是否属于必须品的 10 件
    uid: int = 0             # 唯一标识


class AdaptiveSolver:
    """
    自适应单阶段构造 + 迭代局部搜索.

    核心思想:
      - 所有工件在同一池中, 通过动态评分选择下一步放置哪个
      - 评分 = 约束压力 × 利润密度 (带几何修正)
      - 约束压力: 低于 10 件的类型获得指数增长的优先级
      - 每次放置后更新约束状态, 动态调整优先级
    """

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.blocks_info = [
            (f"{m.name}_{i+1}", m.length, m.width, m.height)
            for m in MATERIALS for i in range(m.quantity)
        ]
        # 按体积降序排列块 (大块优先)
        self.blocks_info.sort(key=lambda b: b[1]*b[2]*b[3], reverse=True)

    # ---- 工件池生成 ----
    def generate_pool(self, extra_factor: float = 0.7) -> List[PoolItem]:
        """
        生成工件池: 10 件必须品 + 估计的额外候选.

        extra_factor: 剩余体积中每种工件可用的比例估计
        """
        mandatory_vol = sum(wp.volume * MIN_COUNT for wp in WORKPIECES)
        remaining_vol = TOTAL_RAW_VOL - mandatory_vol

        pool = []
        uid = 0

        for wp in WORKPIECES:
            oris = wp.get_orientations()
            # 必须品: 10 件, 轮换姿态
            for i in range(MIN_COUNT):
                ori = oris[i % len(oris)]
                pool.append(PoolItem(
                    wp.name, ori[0], ori[1], ori[2],
                    wp.profit, wp.profit_density,
                    mandatory=True, uid=uid))
                uid += 1

            # 额外候选: 根据体积估计
            est_extra = int(remaining_vol / wp.volume * extra_factor / len(WORKPIECES))
            est_extra = max(est_extra, 20)  # 至少 20 件候选
            est_extra = min(est_extra, 500)  # 上限 500

            for k in range(est_extra):
                ori = oris[k % len(oris)]
                pool.append(PoolItem(
                    wp.name, ori[0], ori[1], ori[2],
                    wp.profit, wp.profit_density,
                    mandatory=False, uid=uid))
                uid += 1

        return pool

    # ---- 约束压力计算 ----
    def compute_pressures(self, placed_counts: Dict[str, int],
                          remaining_by_type: Dict[str, int]) -> Dict[str, float]:
        """
        计算每种工件类型的约束压力.

        压力范围 [1.0, 1.0 + ALPHA]:
          - 超出最低产量: 1.0 (无压力)
          - 低于最低产量: 1.0 + ALPHA × (缺口 / 剩余候选)

        ALPHA = 5.0: 最高 6 倍压力, 确保必须品优先但不过度
        """
        ALPHA = 5.0
        pressures = {}
        for wp in WORKPIECES:
            name = wp.name
            count = placed_counts.get(name, 0)
            remaining = remaining_by_type.get(name, 0)
            shortage = max(0, MIN_COUNT - count)
            if shortage > 0 and remaining > 0:
                urgency = shortage / max(1, remaining)
                pressures[name] = 1.0 + ALPHA * urgency
            elif shortage > 0 and remaining == 0:
                pressures[name] = float('inf')  # 不可能满足
            else:
                pressures[name] = 1.0
        return pressures

    # ---- 单阶段构造 ----
    def construct(self, pool: List[PoolItem],
                  orientation_strategy: str = 'random',
                  sort_strategy: str = 'adaptive') -> Tuple[
                      Dict[str, BlockPacker], Dict[str, int], int]:
        """
        单阶段构造: 所有工件在同一框架下竞争.

        Args:
            pool: 工件池
            orientation_strategy: 'random' | 'rotate' | 'best_fit'
            sort_strategy: 'adaptive' | 'profit_density' | 'volume' | 'random'

        Returns:
            (packers, counts, total_profit)
        """
        # 初始化块
        packers = {}
        for bname, bx, by, bz in self.blocks_info:
            packers[bname] = BlockPacker(bx, by, bz, bname)

        placed_counts = {wp.name: 0 for wp in WORKPIECES}
        total_profit = 0

        # 建立索引: 按工件类型分组的未放置工件
        available = list(pool)  # shallow copy
        available_by_type = {wp.name: [] for wp in WORKPIECES}
        for item in available:
            available_by_type[item.wp_name].append(item)

        # --- 主循环: 每次选择最佳 (工件类型, 块, 姿态) 放置 ---
        # 预计算一次排序: 按工件类型的利润密度排序
        wp_order = sorted(WORKPIECES, key=lambda w: w.profit_density, reverse=True)
        wp_name_order = [w.name for w in wp_order]

        iteration = 0
        placement_count = 0
        merge_interval = 25  # 每 25 次放置进行一次空间合并

        while True:
            iteration += 1

            # 更新约束压力
            remaining_by_type = {
                name: len(lst) for name, lst in available_by_type.items()
            }
            pressures = self.compute_pressures(placed_counts, remaining_by_type)

            # 计算每种工件类型的当前得分
            type_scores = {}
            for wp in WORKPIECES:
                name = wp.name
                if not available_by_type[name]:
                    type_scores[name] = -1.0
                    continue
                # 得分 = 压力 × 利润密度
                type_scores[name] = pressures[name] * wp.profit_density

            # 选择得分最高的工件类型 (如果全部不可用则终止)
            max_score = max(type_scores.values())
            if max_score <= 0:
                break

            # 得分最高的类型中随机选一个 (引入随机性)
            best_types = [name for name, sc in type_scores.items()
                         if sc == max_score]
            chosen_type = self.rng.choice(best_types)

            # 从该类型的可用工件中采样
            candidates = available_by_type[chosen_type]
            sample_size = min(10, len(candidates))
            sampled = self.rng.sample(candidates, sample_size)

            # 在所有块中找最佳摆放
            best_item = None
            best_block = None
            best_score = -1.0
            best_xyz = None

            for item in sampled:
                pd = item.profit_density
                for bname, pk in packers.items():
                    if pk.get_waste() <= 0:
                        continue
                    result = pk.evaluate_placement(
                        item.dx, item.dy, item.dz, item.profit, pd, item.wp_name)
                    if result is None:
                        continue
                    score, si, px, py, pz = result
                    if score > best_score:
                        best_score = score
                        best_item = item
                        best_block = pk
                        best_xyz = (px, py, pz)

            if best_item is None:
                # chosen_type 在当前块中放不下, 尝试其他类型
                # 按得分降序尝试
                sorted_types = sorted(type_scores.items(), key=lambda x: x[1], reverse=True)
                placed_any = False
                for try_type, _ in sorted_types:
                    if try_type == chosen_type or type_scores[try_type] <= 0:
                        continue
                    candidates2 = available_by_type[try_type]
                    sample2 = self.rng.sample(
                        candidates2, min(10, len(candidates2)))
                    for item in sample2:
                        pd = item.profit_density
                        for bname, pk in packers.items():
                            if pk.get_waste() <= 0:
                                continue
                            result = pk.evaluate_placement(
                                item.dx, item.dy, item.dz,
                                item.profit, pd, item.wp_name)
                            if result is None:
                                continue
                            score, si, px, py, pz = result
                            best_item = item
                            best_block = pk
                            best_xyz = (px, py, pz)
                            placed_any = True
                            break
                        if placed_any:
                            break
                    if placed_any:
                        break

                if not placed_any:
                    # 合并空间后重试
                    for pk in packers.values():
                        pk.spaces = merge_spaces(pk.spaces)

                    # 再试一次
                    for try_type, _ in sorted_types:
                        if type_scores[try_type] <= 0:
                            continue
                        candidates3 = available_by_type[try_type]
                        sample3 = self.rng.sample(
                            candidates3, min(10, len(candidates3)))
                        for item in sample3:
                            pd = item.profit_density
                            for bname, pk in packers.items():
                                if pk.get_waste() <= 0:
                                    continue
                                result = pk.evaluate_placement(
                                    item.dx, item.dy, item.dz,
                                    item.profit, pd, item.wp_name)
                                if result is None:
                                    continue
                                best_item = item
                                best_block = pk
                                best_xyz = (px, py, pz)
                                placed_any = True
                                break
                            if placed_any:
                                break
                        if placed_any:
                            break

                    if not placed_any:
                        break  # 真的放不下了

            # 执行放置
            px, py, pz = best_xyz
            best_block.try_place(
                best_item.wp_name, best_item.dx, best_item.dy, best_item.dz,
                best_item.profit, best_item.profit_density)

            # 从可用池中移除
            available_by_type[best_item.wp_name].remove(best_item)
            placed_counts[best_item.wp_name] += 1
            total_profit += best_item.profit
            placement_count += 1

            # 周期性合并
            if placement_count % merge_interval == 0:
                for pk in packers.values():
                    if len(pk.spaces) > 50:
                        pk.spaces = merge_spaces(pk.spaces)

        # --- 后处理: 全局合并 + 缝隙填充 ---
        for pk in packers.values():
            pk.spaces = merge_spaces(pk.spaces)

        # 收集所有未放置的工件, 尝试缝隙填充
        unplaced = []
        for lst in available_by_type.values():
            unplaced.extend(lst)
        unplaced.sort(key=lambda x: x.profit_density, reverse=True)

        # 多轮填充 (逐轮减少工件尺寸门槛)
        for min_dim_threshold in [20, 10, 1]:
            remaining = [item for item in unplaced
                        if min(item.dx, item.dy, item.dz) <= 60
                        or min_dim_threshold <= 20]
            if not remaining:
                break
            unplaced = []
            for item in remaining:
                placed = False
                for bname, pk in packers.items():
                    if pk.get_waste() <= 0:
                        continue
                    result = pk.evaluate_placement(
                        item.dx, item.dy, item.dz,
                        item.profit, item.profit_density, item.wp_name)
                    if result is None:
                        continue
                    _, si, px, py, pz = result
                    pk.try_place(item.wp_name, item.dx, item.dy, item.dz,
                                item.profit, item.profit_density)
                    placed_counts[item.wp_name] += 1
                    total_profit += item.profit
                    placed = True
                    break
                if not placed:
                    unplaced.append(item)

        return packers, placed_counts, total_profit

    # ---- Destroy-and-Repair 局部搜索 ----
    def destroy_and_repair(self, packers: Dict[str, BlockPacker],
                           placed_counts: Dict[str, int],
                           total_profit: int,
                           destroy_ratio: float = 0.15,
                           iterations: int = 200) -> Tuple[
                               Dict[str, BlockPacker], Dict[str, int], int]:
        """
        迭代局部搜索: 破坏-重建.

        每轮:
          1. 选择 destroy_ratio 比例的非必须工件移出
          2. 将剩余工件重新打包
          3. 填充剩余空间
          4. 若改善则接受
        """
        # 收集所有已放置工件
        all_placed = []
        for pk in packers.values():
            all_placed.extend(pk.collect_items())

        # 分离必须品 (10 件的) 和非必须品
        mandatory_items = []
        optional_items = []
        counts_temp = {wp.name: 0 for wp in WORKPIECES}
        for item in all_placed:
            name = item[0]
            if counts_temp[name] < MIN_COUNT:
                mandatory_items.append(item)
            else:
                optional_items.append(item)
            counts_temp[name] += 1

        best_packers = packers
        best_counts = placed_counts
        best_profit = total_profit

        for it in range(iterations):
            # --- Destroy: 移出部分非必须工件 ---
            n_destroy = max(1, int(len(optional_items) * destroy_ratio))
            if n_destroy == 0:
                break

            # 偏向移出低利润密度的工件
            optional_with_idx = [(i, item) for i, item in enumerate(optional_items)]
            optional_with_idx.sort(key=lambda x: x[1][5])  # profit_density

            # 取最低的 n_destroy 个, 但加一些随机抖动
            destroy_indices = set()
            if self.rng.random() < 0.3:
                # 30% 概率完全随机破坏
                destroy_indices = set(self.rng.sample(
                    range(len(optional_items)),
                    min(n_destroy, len(optional_items))))
            else:
                # 70% 概率从低利润密度中选择
                candidates = optional_with_idx[:n_destroy*3]
                chosen = self.rng.sample(candidates, min(n_destroy, len(candidates)))
                destroy_indices = set(idx for idx, _ in chosen)

            remaining_optional = [item for i, item in enumerate(optional_items)
                                 if i not in destroy_indices]

            # --- Repair: 重新打包 ---
            # 将保留的工件重新放入空块
            for pk in best_packers.values():
                pk.reset()

            new_counts = {wp.name: 0 for wp in WORKPIECES}
            new_profit = 0

            # 先放必须品
            items_to_repack = list(mandatory_items) + remaining_optional
            # 按利润密度排序
            items_to_repack.sort(key=lambda x: x[5], reverse=True)

            for wp_name, dx, dy, dz, profit, pd in items_to_repack:
                placed = False
                for bname, pk in best_packers.items():
                    result = pk.try_place(wp_name, dx, dy, dz, profit, pd)
                    if result is not None:
                        new_counts[wp_name] += 1
                        new_profit += profit
                        placed = True
                        break
                if not placed:
                    pass  # 应该都能放入 (原来就在里面)

            # 填充: 生成新候选, 尝试放入
            filling_pool = self.generate_pool(extra_factor=0.3)
            # 移除已在 repack 中的类型
            filling = []
            for item in filling_pool:
                if new_counts.get(item.wp_name, 0) >= MIN_COUNT + 200:
                    continue
                filling.append(item)

            filling.sort(key=lambda x: x.profit_density, reverse=True)
            for item in filling:
                placed = False
                for bname, pk in best_packers.items():
                    if pk.get_waste() <= 0:
                        continue
                    result = pk.try_place(
                        item.wp_name, item.dx, item.dy, item.dz,
                        item.profit, item.profit_density)
                    if result is not None:
                        new_counts[item.wp_name] = new_counts.get(item.wp_name, 0) + 1
                        new_profit += item.profit
                        placed = True
                        break

            # 检查约束
            if any(new_counts.get(wp.name, 0) < MIN_COUNT for wp in WORKPIECES):
                continue  # 不可行, 跳过

            # --- Accept? ---
            if new_profit > best_profit:
                best_profit = new_profit
                best_counts = new_counts
                # 更新 optional_items 列表用于下一轮
                all_placed_new = []
                for pk in best_packers.values():
                    all_placed_new.extend(pk.collect_items())
                mandatory_items = []
                optional_items = []
                counts_temp = {wp.name: 0 for wp in WORKPIECES}
                for item in all_placed_new:
                    name = item[0]
                    if counts_temp[name] < MIN_COUNT:
                        mandatory_items.append(item)
                    else:
                        optional_items.append(item)
                    counts_temp[name] += 1

        return best_packers, best_counts, best_profit

    # ---- 多样本求解 ----
    def solve(self, num_trials: int = 20, ils_iterations: int = 300) -> Dict:
        """
        多样本求解 + ILS 改进.

        num_trials: 独立构造试验次数
        ils_iterations: 最优解上的 ILS 迭代数
        """
        pool = self.generate_pool(extra_factor=0.7)

        best_packers = None
        best_counts = None
        best_profit = 0

        t0 = time.time()

        for trial in range(num_trials):
            # 变化随机种子
            trial_seed = self.rng.randint(0, 100000)
            trial_rng = random.Random(trial_seed)

            # 变化工件池的顺序 (带来不同的贪心选择)
            shuffled_pool = list(pool)
            trial_rng.shuffle(shuffled_pool)

            # 构造
            packers, counts, profit = self.construct(shuffled_pool)

            # 验证约束
            if any(counts.get(wp.name, 0) < MIN_COUNT for wp in WORKPIECES):
                continue

            if profit > best_profit:
                best_profit = profit
                best_counts = counts
                best_packers = packers
                print(f"  Trial {trial+1:>3}: profit={profit:>10,}  "
                      f"items={sum(counts.values()):>4}  *** BEST ***")
            elif (trial + 1) % 5 == 0:
                print(f"  Trial {trial+1:>3}: best so far = {best_profit:,}")

        construct_time = time.time() - t0

        if best_packers is None:
            print("ERROR: No feasible solution found!")
            return None

        print(f"\n构造阶段完成: {num_trials} 次试验, "
              f"最优利润 {best_profit:,}, 耗时 {construct_time:.1f}s")

        # --- ILS 改进 ---
        if ils_iterations > 0:
            print(f"\n开始 ILS 改进 ({ils_iterations} 次迭代)...")
            t1 = time.time()
            best_packers, best_counts, best_profit = self.destroy_and_repair(
                best_packers, best_counts, best_profit,
                destroy_ratio=0.15, iterations=ils_iterations)
            ils_time = time.time() - t1
            print(f"ILS 完成: 最终利润 {best_profit:,}, 耗时 {ils_time:.1f}s")
        else:
            ils_time = 0

        elapsed = time.time() - t0

        # 组装输出
        results = {}
        total_used = 0
        for bname, pk in best_packers.items():
            total_used += pk.get_used_volume()
            results[bname] = {
                'dims': pk.dims,
                'placements': [(p.wp_name, p.x, p.y, p.z, p.dx, p.dy, p.dz)
                              for p in pk.placements],
                'utilization': pk.get_utilization(),
                'used_volume': pk.get_used_volume(),
                'waste_volume': pk.get_waste(),
            }

        # 上界
        ub = self._compute_upper_bound()

        return {
            'results': results,
            'counts': best_counts,
            'total_profit': best_profit,
            'total_used': total_used,
            'total_waste': TOTAL_RAW_VOL - total_used,
            'utilization': total_used / TOTAL_RAW_VOL,
            'total_items': sum(best_counts.values()),
            'elapsed': elapsed,
            'construct_time': construct_time,
            'ils_time': ils_time,
            'trials': num_trials,
            'ils_iterations': ils_iterations,
            'upper_bound': ub,
            'ub_gap': best_profit / ub if ub > 0 else 0,
        }

    def _compute_upper_bound(self) -> int:
        """体积背包松弛上界 (忽略几何约束)."""
        mand_vol = sum(wp.volume * MIN_COUNT for wp in WORKPIECES)
        mand_profit = sum(wp.profit * MIN_COUNT for wp in WORKPIECES)
        remaining_vol = TOTAL_RAW_VOL - mand_vol
        sorted_wp = sorted(WORKPIECES, key=lambda w: w.profit_density, reverse=True)
        extra_profit = 0
        for wp in sorted_wp:
            cnt = remaining_vol // wp.volume
            extra_profit += cnt * wp.profit
            remaining_vol -= cnt * wp.volume
        return mand_profit + extra_profit


# ==============================================================================
# 输出
# ==============================================================================

def print_solution(sol):
    print("\n" + "=" * 70)
    print("子问题 2: 每工件 ≥10 件 + 最大化利润  (自适应单阶段 + ILS)")
    print("=" * 70)

    print(f"\n--- 总体概览 ---")
    print(f"  构造试验 / ILS 迭代:    {sol['trials']} / {sol['ils_iterations']}")
    print(f"  总耗时:                  {sol['elapsed']:.1f}s "
          f"(构造 {sol['construct_time']:.1f}s + ILS {sol['ils_time']:.1f}s)")
    print(f"  总利润:                 {sol['total_profit']:>13,}")
    print(f"  理论利润上界:           {sol['upper_bound']:>13,}")
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
    print("子问题 2 求解: 自适应单阶段构造 + 迭代局部搜索")
    print("=" * 70)

    solver = AdaptiveSolver(seed=42)
    sol = solver.solve(num_trials=20, ils_iterations=300)
    print_solution(sol)
