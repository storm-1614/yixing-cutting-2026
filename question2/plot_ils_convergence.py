#!/usr/bin/env python3
"""不修改 ems_solver_optimal.py，通过外部包装提取 ILS 迭代历史并生成折线图"""

import sys, pickle, time, random, types
sys.path.insert(0, '/data/project/yixing-cutting-2026/question2')

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

# ── 导入原始模块 ──────────────────────────────────────────
import ems_solver_optimal as eso

# ── 思源黑体 ────────────────────────────────────────────
SOURCE_HAN = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf")
SOURCE_HAN_BOLD = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Bold.otf")
SOURCE_HAN_MEDIUM = FontProperties(
    fname="/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Medium.otf")

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Source Han Sans CN"]
plt.rcParams["axes.unicode_minus"] = False

C_BLUE   = "#3262A8"
C_ORANGE = "#D4743E"
C_GREEN  = "#3E8A52"
C_RED    = "#E31A1C"
C_PURPLE = "#7B4FBF"
DPI = 250

# ═══════════════════════════════════════════════════════════════
# Step 1: 用原始 solve 跑出结果
# ═══════════════════════════════════════════════════════════════
print("=== 运行原始求解器（不改动源代码）===")
t0 = time.time()
sol = eso.solve(num_trials=48, ils_iterations=800)
print(f"\n求解完成: {time.time()-t0:.1f}s")
print(f"最终利润: {sol['total_profit']:,}")

# ═══════════════════════════════════════════════════════════════
# Step 2: 从结果中提取 best_packers，重跑 ILS 并记录历史
# ═══════════════════════════════════════════════════════════════
print("\n=== 重跑 ILS 以记录迭代历史 ===")

# 从 sol['results'] 重建 best_packers（与原始 ILS 相同的初始状态）
blocks = eso.create_blocks()
best_packers = {}
for bname, bx, by, bz in blocks:
    pk = eso.BlockPacker(bx, by, bz, bname)
    best_packers[bname] = pk

# 从 sol 结果中回填 placements
for bname, info in sol['results'].items():
    if bname in best_packers:
        best_packers[bname].placements = info['placements'].copy()
        best_packers[bname].spaces = [eso.Space(0, 0, 0, *info['dims'])]

# 验证回填正确
assert eso.total_profit(best_packers) == sol['total_profit'], "profit mismatch"

# Monkey-patch: 包装 destroy_and_repair 以记录历史
original_destroy = eso.destroy_and_repair

history_data = []

def patched_destroy(packers, rng, iterations=500, destroy_ratio=0.15):
    # 复用原始逻辑，但在每次迭代后记录 best_profit
    blocks_local = eso.create_blocks()
    sorted_blocks_local = sorted(blocks_local, key=lambda b: b[1]*b[2]*b[3], reverse=True)

    def extract_items(pkrs):
        items = []
        for pk in pkrs.values():
            for name, _, _, _, dx, dy, dz in pk.placements:
                items.append((name, dx, dy, dz, eso.WP_MAP[name].profit_density))
        return items

    filling_pool = []
    remaining_vol_est = eso.TOTAL_RAW_VOL - eso.total_used_vol(packers)
    for wp in eso.WORKPIECES:
        oris = wp.get_orientations()
        est_max = max(50, int(remaining_vol_est / wp.volume * 0.5))
        est_max = min(est_max, 300)
        for k in range(est_max):
            ori = rng.choice(oris)
            filling_pool.append(
                (wp.name, ori[0], ori[1], ori[2], wp.profit_density))
    filling_pool.sort(key=lambda x: x[4], reverse=True)

    best_items_local = extract_items(packers)
    best_profit_local = eso.total_profit(packers)

    history_data.append((0, best_profit_local))

    for it in range(iterations):
        current_items = list(best_items_local)

        mandatory = []
        optional = []
        counts = {}
        for item in current_items:
            name = item[0]
            c = counts.get(name, 0)
            if c < eso.MIN_COUNT:
                mandatory.append(item)
            else:
                optional.append(item)
            counts[name] = c + 1

        n_destroy = max(1, int(len(optional) * destroy_ratio))
        if n_destroy == 0 or len(optional) == 0:
            history_data.append((it + 1, best_profit_local))
            continue

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

        new_packers = {}
        for bname_l, bx, by, bz in blocks_local:
            new_packers[bname_l] = eso.BlockPacker(bx, by, bz, bname_l)

        kept_items.sort(key=lambda x: x[4], reverse=True)
        remaining = [(n, dx, dy, dz, pd) for n, dx, dy, dz, pd in kept_items]

        for bname_l, bx, by, bz in sorted_blocks_local:
            pk = new_packers[bname_l]
            changed = True
            while changed and remaining:
                changed = False
                res = pk.find_best_to_place(remaining)
                if res is not None:
                    idx, name, dx, dy, dz = res
                    pk.try_place(name, dx, dy, dz)
                    remaining.pop(idx)
                    changed = True
            pk.spaces = eso.merge_spaces(pk.spaces)

        fill_remaining = list(filling_pool)
        for bname_l in sorted(new_packers.keys(),
                            key=lambda n: new_packers[n].get_waste(),
                            reverse=True):
            pk = new_packers[bname_l]
            if pk.get_waste() <= 0:
                continue
            pk.spaces = eso.merge_spaces(pk.spaces)
            while fill_remaining:
                res = pk.find_best_to_place(fill_remaining)
                if res is None:
                    break
                idx, name, dx, dy, dz = res
                pk.try_place(name, dx, dy, dz)
                fill_remaining.pop(idx)

        counts_new = eso.count_items(new_packers)
        if any(counts_new.get(wp.name, 0) < eso.MIN_COUNT for wp in eso.WORKPIECES):
            history_data.append((it + 1, best_profit_local))
            continue

        profit_new = eso.total_profit(new_packers)
        if profit_new > best_profit_local:
            best_profit_local = profit_new
            best_packers_local = new_packers
            best_items_local = extract_items(new_packers)

        history_data.append((it + 1, best_profit_local))

    return packers  # 返回原始的（已由 solve 正确处理）

# 应用 patch 并重跑
eso.destroy_and_repair = patched_destroy

sol2 = eso.solve(num_trials=48, ils_iterations=800)

# 恢复原函数
eso.destroy_and_repair = original_destroy

# ═══════════════════════════════════════════════════════════════
# Step 3: 生成折线图
# ═══════════════════════════════════════════════════════════════
iterations_arr = np.array([h[0] for h in history_data])
profits_arr = np.array([h[1] for h in history_data])

initial_profit = profits_arr[0]
final_profit = profits_arr[-1]
improvement = final_profit - initial_profit
upper_bound = sol['upper_bound']

# 找到改进点
improvement_points = []
prev = profits_arr[0]
for it, p in zip(iterations_arr, profits_arr):
    if p != prev:
        improvement_points.append((it, p, p - prev))
        prev = p

print(f"\nILS 迭代历史: {len(history_data)} 条")
print(f"初始: {initial_profit:,} → 最终: {final_profit:,}")
print(f"提升: +{improvement:,} ({improvement/initial_profit*100:.2f}%)")
print(f"改进次数: {len(improvement_points)}")

# --- 图1: 主折线图 ---
fig1, ax1 = plt.subplots(figsize=(14, 7))
fig1.patch.set_facecolor("#FAFAFA")

ax1.step(iterations_arr, profits_arr / 10000, where='post',
         color=C_BLUE, linewidth=2.0, alpha=0.9, zorder=3)
ax1.fill_between(iterations_arr, profits_arr / 10000, initial_profit / 10000,
                 alpha=0.12, color=C_BLUE, step='post')

# 初始值标注
ax1.annotate(f'初始: {initial_profit/10000:.2f}万',
             xy=(0, initial_profit / 10000),
             xytext=(35, initial_profit / 10000 + 0.4),
             ha='left', fontproperties=SOURCE_HAN_MEDIUM, fontsize=12,
             color='#555',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF',
                       edgecolor=C_BLUE, alpha=0.8),
             arrowprops=dict(arrowstyle='->', color='#999', lw=1.2))

# 终值标注
ax1.annotate(f'最优: {final_profit/10000:.2f}万\n提升: +{improvement/10000:.2f}万 (+{improvement/initial_profit*100:.1f}%)',
             xy=(iterations_arr[-1], final_profit / 10000),
             xytext=(iterations_arr[-1] - 180, final_profit / 10000 - 1.3),
             ha='right', fontproperties=SOURCE_HAN_MEDIUM, fontsize=12,
             color='#555',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF',
                       edgecolor=C_GREEN, alpha=0.8),
             arrowprops=dict(arrowstyle='->', color='#999', lw=1.2))

# 理论上界线
ax1.axhline(y=upper_bound / 10000, color=C_RED, linestyle='--',
            linewidth=1.5, alpha=0.5)
ax1.text(iterations_arr[-1] + 8, upper_bound / 10000,
         f'理论上界 {upper_bound/10000:.2f}万',
         fontproperties=SOURCE_HAN, fontsize=11, color=C_RED, ha='left', va='bottom')

# 标注关键改进
for it, p, delta in improvement_points[:5]:
    ax1.annotate(f'+{delta:,}',
                 xy=(it, p / 10000),
                 xytext=(0, 14), textcoords='offset points',
                 ha='center', fontproperties=SOURCE_HAN, fontsize=9,
                 color=C_GREEN, alpha=0.8)

ax1.set_xlabel('ILS 迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax1.set_ylabel('最优利润 (万元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax1.set_title('子问题2 ILS 迭代收敛过程', fontproperties=SOURCE_HAN_BOLD, fontsize=22, pad=15)
ax1.set_xlim(-10, iterations_arr[-1] + 15)
ax1.grid(True, alpha=0.25, zorder=1)
ax1.set_axisbelow(True)
ax1.tick_params(axis='both', labelsize=12)

fig1.tight_layout()
for ext in ["png", "pdf"]:
    fig1.savefig(f"/data/project/yixing-cutting-2026/question2/fig_ils_convergence.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig1.get_facecolor())
plt.close(fig1)
print("✅ fig_ils_convergence.png/pdf")

# --- 图2: 改进增量柱状图 ---
fig2, ax2 = plt.subplots(figsize=(14, 7))
fig2.patch.set_facecolor("#FAFAFA")

imp_iters = np.array([p[0] for p in improvement_points])
imp_deltas = np.array([p[2] for p in improvement_points])
colors_bar = [C_GREEN if d > 0 else C_RED for d in imp_deltas]
bar_width = max(1, 800 / len(imp_iters) * 0.6)
ax2.bar(imp_iters, imp_deltas, color=colors_bar, alpha=0.75,
        edgecolor='white', linewidth=0.3, zorder=2, width=bar_width)
ax2.axhline(y=0, color='#555', linewidth=0.8, zorder=1)

for i in range(min(6, len(imp_iters))):
    ax2.annotate(f'+{imp_deltas[i]:,}',
                 xy=(imp_iters[i], imp_deltas[i]),
                 xytext=(0, 10), textcoords='offset points',
                 ha='center', fontproperties=SOURCE_HAN, fontsize=9, color=C_GREEN)

ax2.set_xlabel('ILS 迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax2.set_ylabel('利润改进量 (元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax2.set_title('ILS 每次改进的利润增量', fontproperties=SOURCE_HAN_BOLD, fontsize=22, pad=15)
ax2.set_xlim(-10, iterations_arr[-1] + 15)
ax2.grid(True, alpha=0.2, axis='y', zorder=1)
ax2.set_axisbelow(True)
ax2.tick_params(axis='both', labelsize=12)

fig2.tight_layout()
for ext in ["png", "pdf"]:
    fig2.savefig(f"/data/project/yixing-cutting-2026/question2/fig_ils_improvements.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig2.get_facecolor())
plt.close(fig2)
print("✅ fig_ils_improvements.png/pdf")

# --- 图3: 双Y轴 ---
fig3, ax3a = plt.subplots(figsize=(14, 7))
fig3.patch.set_facecolor("#FAFAFA")

ax3a.step(iterations_arr, profits_arr / 10000, where='post',
          color=C_BLUE, linewidth=2.5, zorder=3)
ax3a.fill_between(iterations_arr, profits_arr / 10000, initial_profit / 10000,
                  alpha=0.1, color=C_BLUE, step='post')
ax3a.set_xlabel('ILS 迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16)
ax3a.set_ylabel('最优利润 (万元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16, color=C_BLUE)
ax3a.tick_params(axis='y', labelcolor=C_BLUE, labelsize=12)
ax3a.set_xlim(-10, iterations_arr[-1] + 15)

ax3b = ax3a.twinx()
gap_pct = profits_arr / upper_bound * 100
ax3b.step(iterations_arr, gap_pct, where='post',
          color=C_ORANGE, linewidth=2.5, zorder=3)
ax3b.set_ylabel('占理论上界比例 (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=16, color=C_ORANGE)
ax3b.tick_params(axis='y', labelcolor=C_ORANGE, labelsize=12)

ax3a.set_title('ILS 迭代收敛 — 利润与占上界比例', fontproperties=SOURCE_HAN_BOLD, fontsize=22, pad=15)
ax3a.grid(True, alpha=0.2, zorder=1)
ax3a.set_axisbelow(True)
ax3a.tick_params(axis='x', labelsize=12)

fig3.tight_layout()
for ext in ["png", "pdf"]:
    fig3.savefig(f"/data/project/yixing-cutting-2026/question2/fig_ils_convergence_dual.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig3.get_facecolor())
plt.close(fig3)
print("✅ fig_ils_convergence_dual.png/pdf")

# --- 图4: 仪表盘 ---
fig4 = plt.figure(figsize=(18, 12))
fig4.patch.set_facecolor("#F5F5F5")
gs = fig4.add_gridspec(2, 2, hspace=0.3, wspace=0.25)

ax_a = fig4.add_subplot(gs[0, 0])
ax_a.step(iterations_arr, profits_arr / 10000, where='post', color=C_BLUE, linewidth=2, alpha=0.9, zorder=3)
ax_a.fill_between(iterations_arr, profits_arr / 10000, initial_profit / 10000, alpha=0.12, color=C_BLUE, step='post')
ax_a.axhline(y=upper_bound / 10000, color=C_RED, linestyle='--', linewidth=1.2, alpha=0.6)
ax_a.set_title('(a) 利润收敛曲线', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_a.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_a.set_ylabel('利润 (万元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_a.set_xlim(-10, iterations_arr[-1] + 15)
ax_a.grid(True, alpha=0.2); ax_a.set_axisbelow(True)
ax_a.tick_params(axis='both', labelsize=11)

ax_b = fig4.add_subplot(gs[0, 1])
ax_b.step(iterations_arr, gap_pct, where='post', color=C_GREEN, linewidth=2, alpha=0.9, zorder=3)
ax_b.fill_between(iterations_arr, gap_pct, gap_pct[0], alpha=0.12, color=C_GREEN, step='post')
ax_b.axhline(y=100, color=C_RED, linestyle='--', linewidth=1.2, alpha=0.6)
ax_b.set_title('(b) 占理论上界比例', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_b.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_b.set_ylabel('占上界 (%)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_b.set_xlim(-10, iterations_arr[-1] + 15)
ax_b.grid(True, alpha=0.2); ax_b.set_axisbelow(True)
ax_b.tick_params(axis='both', labelsize=11)

cumulative_gain = profits_arr - initial_profit
ax_c = fig4.add_subplot(gs[1, 0])
ax_c.step(iterations_arr, cumulative_gain / 10000, where='post', color=C_ORANGE, linewidth=2, alpha=0.9, zorder=3)
ax_c.fill_between(iterations_arr, cumulative_gain / 10000, 0, alpha=0.15, color=C_ORANGE, step='post')
ax_c.set_title('(c) ILS 累计利润提升', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_c.set_xlabel('迭代次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_c.set_ylabel('累计提升 (万元)', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_c.set_xlim(-10, iterations_arr[-1] + 15)
ax_c.grid(True, alpha=0.2); ax_c.set_axisbelow(True)
ax_c.tick_params(axis='both', labelsize=11)

bin_edges = np.arange(0, iterations_arr[-1] + 101, 100)
bin_counts, _ = np.histogram(imp_iters, bins=bin_edges)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
ax_d = fig4.add_subplot(gs[1, 1])
ax_d.bar(bin_centers, bin_counts, width=80, color=C_PURPLE, alpha=0.7,
         edgecolor='white', linewidth=0.5, zorder=2)
for x, cnt in zip(bin_centers, bin_counts):
    if cnt > 0:
        ax_d.text(x, cnt + 0.3, str(cnt), ha='center', fontproperties=SOURCE_HAN, fontsize=10, color=C_PURPLE)
ax_d.set_title('(d) 每100轮改进次数分布', fontproperties=SOURCE_HAN_BOLD, fontsize=18)
ax_d.set_xlabel('迭代区间', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_d.set_ylabel('改进次数', fontproperties=SOURCE_HAN_MEDIUM, fontsize=13)
ax_d.set_xlim(-20, iterations_arr[-1] + 20)
ax_d.grid(True, alpha=0.2, axis='y'); ax_d.set_axisbelow(True)
ax_d.tick_params(axis='both', labelsize=11)

fig4.suptitle("子问题2 ILS 迭代收敛综合分析", fontproperties=SOURCE_HAN_BOLD, fontsize=25, y=1.01, color="#111")
for ext in ["png", "pdf"]:
    fig4.savefig(f"/data/project/yixing-cutting-2026/question2/fig_ils_dashboard.{ext}",
                 dpi=DPI, bbox_inches="tight", facecolor=fig4.get_facecolor())
plt.close(fig4)
print("✅ fig_ils_dashboard.png/pdf")

print(f"\n🎉 全部完成! (ems_solver_optimal.py 未被修改)")
print(f"  fig_ils_convergence.png/pdf       — ILS 迭代收敛曲线")
print(f"  fig_ils_improvements.png/pdf      — 每次改进增量")
print(f"  fig_ils_convergence_dual.png/pdf  — 双Y轴综合图")
print(f"  fig_ils_dashboard.png/pdf         — 四合一仪表盘")
