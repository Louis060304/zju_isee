"""
三算法布线成功率基准测试（global 系列）
======================================
测试 A_star_global / _global_x / _global_x_bidir 在不同场景下的表现。
使用与 RNR 系列相同的随机种子生成题目，保证公平对比。
"""
import sys
import os
import time
import importlib.util

# 工作目录
BASE = r"D:\Lqyiii\大学\专业类\人工智能\大作业\自动布线大作业要求"

def load_solver(module_name, file_name):
    """动态加载模块并返回 solve 函数"""
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(BASE, file_name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.solve, mod

# 加载三个 global 系列求解器
solve_global,     mod_global     = load_solver("global",     "A_star_global.py")
solve_global_x,   mod_global_x   = load_solver("global_x",   "A_star_global_x.py")
solve_global_x_b, mod_global_x_b = load_solver("global_x_b", "A_star_global_x_bidir.py")

SOLVERS = [
    ("global",      solve_global),
    ("global_x",    solve_global_x),
    ("global_x_b",  solve_global_x_b),
]

# ═══════════════════════════════════════════════════════════════════
#  加载 RNR 系列模块 —— 仅用于 generate_case（确保与 RNR 测试同一张图）
# ═══════════════════════════════════════════════════════════════════
_, mod_rnr = load_solver("rnr_ref", "A_star_rnr.py")

# ── 测试场景定义 ─────────────────────────────────────────────────
# (grid_size, nets_count, vias_count, label)
# 与 benchmark_rnr.py 使用完全相同的场景和种子

SCENARIOS = [
    # ── 20×20 ──
    (20, 5,  0,  "20×20 少线 无via"),
    (20, 5,  30, "20×20 少线 中via"),
    (20, 10, 0,  "20×20 中线 无via"),
    (20, 10, 30, "20×20 中线 中via"),
    (20, 10, 60, "20×20 中线 密via"),
    (20, 15, 0,  "20×20 多线 无via"),
    (20, 15, 20, "20×20 多线 中via"),

    # ── 40×40 ──
    (40, 10, 0,   "40×40 少线 无via"),
    (40, 10, 80,  "40×40 少线 中via"),
    (40, 10, 200, "40×40 少线 密via"),
    (40, 20, 0,   "40×40 中线 无via"),
    (40, 20, 80,  "40×40 中线 中via"),
    (40, 20, 200, "40×40 中线 密via"),
    (40, 30, 0,   "40×40 多线 无via"),
    (40, 30, 50,  "40×40 多线 中via"),

    # ── 60×60 ──
    (60, 15, 0,   "60×60 少线 无via"),
    (60, 15, 200, "60×60 少线 中via"),
    (60, 15, 500, "60×60 少线 密via"),
    (60, 30, 0,   "60×60 中线 无via"),
    (60, 30, 200, "60×60 中线 中via"),
    (60, 30, 500, "60×60 中线 密via"),
    (60, 45, 0,   "60×60 多线 无via"),
    (60, 45, 120, "60×60 多线 中via"),

    # ── 80×80 ──
    (80, 20, 0,   "80×80 少线 无via"),
    (80, 20, 400, "80×80 少线 中via"),
    (80, 20, 900, "80×80 少线 密via"),
    (80, 40, 0,   "80×80 中线 无via"),
    (80, 40, 400, "80×80 中线 中via"),
    (80, 40, 900, "80×80 中线 密via"),
    (80, 60, 0,   "80×80 多线 无via"),
    (80, 60, 200, "80×80 多线 中via"),

    # ── 100×100 ──
    (100, 30, 0,    "100×100 少线 无via"),
    (100, 30, 600,  "100×100 少线 中via"),
    (100, 30, 1500, "100×100 少线 密via"),
    (100, 50, 0,    "100×100 中线 无via"),
    (100, 50, 600,  "100×100 中线 中via"),
    (100, 50, 1500, "100×100 中线 密via"),
    (100, 70, 0,    "100×100 多线 无via"),
    (100, 70, 300,  "100×100 多线 中via"),
]

SEEDS = [42, 123, 456]  # 每个场景跑 3 个随机种子取平均（与 RNR 系列相同）


def run_benchmark():
    results = []

    for size, nets_n, vias_n, label in SCENARIOS:
        row = {"label": label, "size": size, "nets": nets_n, "vias": vias_n}

        # 初始化各求解器得分和耗时
        for name, _ in SOLVERS:
            row[name] = []            # 成功率列表
            row[name + "_time"] = []  # 耗时列表

        for seed in SEEDS:
            # ── 使用 mod_rnr.generate_case 生成题目，保证与 RNR 系列同一张图 ──
            case = mod_rnr.generate_case(
                rows=size, cols=size, num_nets=nets_n, num_vias=vias_n, seed=seed)

            for name, solve_fn in SOLVERS:
                t0 = time.time()
                paths = solve_fn(case)
                elapsed = time.time() - t0
                rate = len(paths) / len(case.nets) * 100 if case.nets else 0
                row[name].append(rate)
                row[name + "_time"].append(elapsed)

        # 计算平均成功率 & 平均耗时
        for name, _ in SOLVERS:
            scores = row[name]
            times = row[name + "_time"]
            row[name + "_avg"] = sum(scores) / len(scores)
            row[name + "_min"] = min(scores)
            row[name + "_max"] = max(scores)
            row[name + "_time_avg"] = sum(times) / len(times)
            row[name + "_time_min"] = min(times)
            row[name + "_time_max"] = max(times)

        results.append(row)
        print(f"[OK] {label}")

    return results


def print_table(results):
    """打印 Markdown 表格（成功率 + 耗时）"""
    # ── 表 1：成功率 ──
    header_rate = (
        "| 场景 | 网格 | 线网 | via | "
        "global 平均 | global 区间 | "
        "global_x 平均 | global_x 区间 | "
        "global_x_b 平均 | global_x_b 区间 |"
    )
    sep_rate = "|---|------|------|-----|" + "---|" * 9

    print("\n" + "=" * 130)
    print("                    global 系列三算法布线成功率对比 (%)")
    print("=" * 130)
    print(header_rate)
    print(sep_rate)

    for r in results:
        def fmt_rate(avg, lo, hi):
            return f"{avg:5.1f}%  [{lo:5.1f}%-{hi:5.1f}%]"

        print(
            f"| {r['label']:28s} | {r['size']:3d}×{r['size']:<3d} | {r['nets']:3d}  | {r['vias']:4d} | "
            f"{fmt_rate(r['global_avg'], r['global_min'], r['global_max'])} | "
            f"{fmt_rate(r['global_x_avg'], r['global_x_min'], r['global_x_max'])} | "
            f"{fmt_rate(r['global_x_b_avg'], r['global_x_b_min'], r['global_x_b_max'])} |"
        )

    # ── 表 2：耗时 ──
    header_time = (
        "| 场景 | 网格 | 线网 | via | "
        "global 平均 | global 区间 | "
        "global_x 平均 | global_x 区间 | "
        "global_x_b 平均 | global_x_b 区间 |"
    )
    sep_time = "|---|------|------|-----|" + "---|" * 9

    print("\n" + "=" * 130)
    print("                    global 系列三算法布线耗时对比 (秒)")
    print("=" * 130)
    print(header_time)
    print(sep_time)

    for r in results:
        def fmt_time(avg, lo, hi):
            return f"{avg:6.2f}s [{lo:6.2f}s-{hi:6.2f}s]"

        print(
            f"| {r['label']:28s} | {r['size']:3d}×{r['size']:<3d} | {r['nets']:3d}  | {r['vias']:4d} | "
            f"{fmt_time(r['global_time_avg'], r['global_time_min'], r['global_time_max'])} | "
            f"{fmt_time(r['global_x_time_avg'], r['global_x_time_min'], r['global_x_time_max'])} | "
            f"{fmt_time(r['global_x_b_time_avg'], r['global_x_b_time_min'], r['global_x_b_time_max'])} |"
        )

    # ── 汇总统计 ──
    print(sep_time)

    def summary(solver_name):
        key_rate = solver_name + "_avg"
        key_time = solver_name + "_time_avg"
        all_scores = [r[key_rate] for r in results]
        all_times = [r[key_time] for r in results]
        overall_rate = sum(all_scores) / len(all_scores)
        overall_time = sum(all_times) / len(all_times)
        total_time = sum(all_times)
        perfect = sum(1 for s in all_scores if s >= 99.99)
        high = sum(1 for s in all_scores if s >= 90)
        fastest = sum(1 for r in results
                      if r[key_time] == min(r[s[0] + "_time_avg"] for s in SOLVERS))
        return overall_rate, overall_time, total_time, perfect, high, fastest

    print("\n【成功率汇总】")
    for name, _ in SOLVERS:
        avg_rate, _, _, perfect, high, _ = summary(name)
        print(f"  {name:12s}: 总平均 {avg_rate:5.1f}%  |  完美({perfect}/{len(results)})  |  ≥90%({high}/{len(results)})")

    print("\n【耗时汇总】")
    for name, _ in SOLVERS:
        _, avg_time, total_time, _, _, fastest = summary(name)
        print(f"  {name:12s}: 场景平均 {avg_time:6.2f}s  |  总耗时 {total_time:7.2f}s  |  最快({fastest}/{len(results)})")

    # 胜出统计
    print("\n【各场景最佳（按成功率）】")
    for r in results:
        best = max(SOLVERS, key=lambda s: r[s[0] + "_avg"])
        best_score = r[best[0] + "_avg"]
        tied = [s[0] for s in SOLVERS if abs(r[s[0] + "_avg"] - best_score) < 0.01]
        if len(tied) > 1:
            print(f"  {r['label']:28s}: {' = '.join(tied)}  ({best_score:.1f}%)")
        else:
            print(f"  {r['label']:28s}: {best[0]:12s}  ({best_score:.1f}%)")

    print("\n【各场景最快（按耗时）】")
    for r in results:
        fastest = min(SOLVERS, key=lambda s: r[s[0] + "_time_avg"])
        fastest_time = r[fastest[0] + "_time_avg"]
        tied = [s[0] for s in SOLVERS if abs(r[s[0] + "_time_avg"] - fastest_time) < 0.001]
        if len(tied) > 1:
            print(f"  {r['label']:28s}: {' = '.join(tied)}  ({fastest_time:.2f}s)")
        else:
            print(f"  {r['label']:28s}: {fastest[0]:12s}  ({fastest_time:.2f}s)")


if __name__ == "__main__":
    print("开始 global 系列三算法基准测试...")
    print(f"场景数: {len(SCENARIOS)}, 种子数: {len(SEEDS)}, 总测试: {len(SCENARIOS) * len(SEEDS) * len(SOLVERS)}")
    results = run_benchmark()
    print_table(results)
    print("\n测试完成。")
