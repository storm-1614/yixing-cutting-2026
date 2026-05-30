"""子问题 1: 最大化原材料体积利用率 (无产量约束)"""

from collections import Counter
from data import RAW_MATERIALS, WORKPIECES
from ems import EMSBin, create_candidates, SORT_STRATEGIES


def solve_subproblem1():
    # 构建原材料块列表
    blocks = []
    for name, L, W, H, qty in RAW_MATERIALS:
        for i in range(qty):
            blocks.append((f"{name}_{i+1}", L, W, H))

    total_volume = sum(L * W * H for _, L, W, H in blocks)

    results = []
    all_placed = []

    for block_name, L, W, H in blocks:
        # 每个块有独立的候选池 (无产量约束, 不限量)
        candidates = create_candidates(
            [(name, l, w, h, _) for name, l, w, h, _ in WORKPIECES],
            with_orientations=True
        )
        # 每类工件/姿态复制 80 份 → 约 80*42=3360 个候选
        pool = []
        for c in candidates:
            pool.extend([c] * 80)

        # 尝试多种排序策略，选该块利用率最高的
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

        results.append({
            "block": block_name,
            "L": L, "W": W, "H": H,
            "placed": best_placed,
            "count": len(best_placed),
            "used_vol": best_vol,
            "total_vol": L * W * H,
        })
        all_placed.extend(best_placed)

        print(f"  {block_name}: {len(best_placed)} 件, "
              f"利用率 {best_vol / (L * W * H) * 100:.2f}%")

    # 汇总
    total_used = sum(r["used_vol"] for r in results)
    utilization = total_used / total_volume

    print(f"\n========== 子问题1 结果汇总 ==========")
    print(f"原材料总体积:     {total_volume:,}")
    print(f"已使用体积:       {total_used:,}")
    print(f"废料体积:         {total_volume - total_used:,}")
    print(f"总体积利用率:     {utilization * 100:.2f}%")
    print(f"总工件数:         {len(all_placed)}")

    # 各块详情
    print(f"\n各块详情:")
    for r in results:
        u = r["used_vol"] / r["total_vol"] * 100
        print(f"  {r['block']}: {r['count']:>4} 件, "
              f"利用率 {u:.2f}%")

    # 按工件类型统计
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
