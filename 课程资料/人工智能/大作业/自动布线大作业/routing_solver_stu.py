"""
PCB 布线作业 — 学生模板
========================
请在下方实现 solve 函数，其余代码（数据结构、可视化、命令行）已提供，无需修改。

本地测试：
    python routing_solver_stu.py                    # 内置 20×20 示例
    python routing_solver_stu.py case.json          # 加载指定题目
    python routing_solver_stu.py --generate 40 20   # 随机生成 40×40、20 条线网
    python routing_solver_stu.py case.json --export result.json
"""

import json
import random
import sys
import os
from dataclasses import dataclass

# ─── 数据结构 ─────────────────────────────────────────────────────────────────
#
# Net  表示一条需要连通的线网，包含起止两个端点。
# Case 表示完整的布线题目：网格尺寸 + via 障碍列表 + 所有线网。
#
# 坐标约定：(row, col)，从左上角 (0, 0) 开始，向右 col 增大，向下 row 增大。

@dataclass
class Net:
    id: int           # 线网编号，0 起始
    endpoints: list   # [[r1, c1], [r2, c2]]，需要连通的两个端点
    color: str = ""   # 显示颜色（可忽略）
    name: str = ""    # 线网名称，如 "CIF_CLKO"（可忽略）

@dataclass
class Case:
    rows: int         # 网格行数
    cols: int         # 网格列数
    vias: list        # 障碍格子列表，每项为 [r, c]，不可进入
    nets: list        # 线网列表，每项为 Net 对象

    def to_dict(self):
        return {
            "grid": {"rows": self.rows, "cols": self.cols},
            "vias": self.vias,
            "nets": [{"id": n.id, "name": n.name, "color": n.color, "endpoints": n.endpoints} for n in self.nets],
            "notes": {
                "coordinate_format": "[row, col], 0-indexed from top-left",
                "via": "blocked cell, cannot be traversed or used as endpoint",
                "routing_rules": [
                    "paths move horizontally or vertically (4-connectivity)",
                    "no two nets may share a cell",
                    "vias may not be used",
                    "goal: maximize number of successfully routed nets"
                ]
            }
        }

    def export_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"Exported to {path}")

    @staticmethod
    def from_json(path: str) -> "Case":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        g = data["grid"]
        nets = [Net(id=n["id"], endpoints=n["endpoints"], color=n.get("color", ""), name=n.get("name", ""))
                for n in data["nets"]]
        return Case(rows=g["rows"], cols=g["cols"], vias=data["vias"], nets=nets)


# ═══════════════════════════════════════════════════════════════════════════════
#  TODO：在此实现你的布线算法
# ═══════════════════════════════════════════════════════════════════════════════

def solve(case: Case) -> dict[int, list]:
    """对给定网格，尽可能多地完成线网布线。

    【输入】
    case.rows, case.cols
        网格尺寸，行 × 列。

    case.vias
        障碍格子列表，形如 [[r, c], ...]。
        这些格子不可进入，也不能用作端点。

    case.nets
        线网列表，每条线网包含：
            net.id        线网编号（int，0 起始）
            net.name      线网名称（str，可用于调试打印）
            net.endpoints [[r1, c1], [r2, c2]]，需要连通的起止坐标

    【布线规则】
    - 坐标 (row, col)，从左上角 (0, 0) 开始。
    - 只能上下左右移动（4 连通），不允许斜向。
    - 不同线网的路径不能共用任何格子（包括端点）。
    - Via 格子不可进入。
    - 目标：最大化成功布线的线网数量。

    【输出】
    返回一个 dict，键为 net.id，值为路径。
    路径是从起点到终点的格子序列（含两端），每个格子为 (r, c) 或 [r, c]。
    未能布线的线网不出现在返回值中。

    【示例】
    线网 id=2，端点 [[0,0],[0,3]]，一条合法路径：
        {2: [(0,0), (0,1), (0,2), (0,3)]}
    """
    # TODO: 在此实现你的算法
    raise NotImplementedError("solve() 尚未实现")


# ─── 以下代码已提供，无需修改 ─────────────────────────────────────────────────

COLORS = [
    "#ef4444", "#3b82f6", "#14b8a6", "#f59e0b", "#a855f7",
    "#ec4899", "#f97316", "#22c55e", "#1e3a5f", "#92400e",
    "#06b6d4", "#84cc16", "#e11d48", "#7c3aed", "#0ea5e9",
    "#d946ef", "#65a30d", "#dc2626", "#2563eb", "#059669",
    "#ca8a04", "#9333ea", "#db2777", "#0891b2", "#c2410c",
]

def generate_case(rows=40, cols=40, num_nets=20, num_vias=0, seed=None,
                  min_manhattan=None) -> Case:
    """随机生成一个布线测试用例。"""
    if seed is not None:
        random.seed(seed)
    if min_manhattan is None:
        min_manhattan = (rows + cols) // 3  # 要求端点之间至少有一定距离

    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(all_cells)
    vias_set = set()
    for r, c in all_cells:
        if len(vias_set) >= num_vias:
            break
        vias_set.add((r, c))

    vias = [list(v) for v in sorted(vias_set)]
    used = set(vias_set)  # 已被占用的格子（via 和端点均不能重叠）
    nets = []
    for i in range(num_nets):
        for _ in range(1000):  # 最多尝试 1000 次放置端点
            r1, c1 = random.randint(0, rows - 1), random.randint(0, cols - 1)
            r2, c2 = random.randint(0, rows - 1), random.randint(0, cols - 1)
            if (r1, c1) in used or (r2, c2) in used:
                continue
            if (r1, c1) == (r2, c2):
                continue
            if abs(r1 - r2) + abs(c1 - c2) < min_manhattan:
                continue
            used.add((r1, c1))
            used.add((r2, c2))
            nets.append(Net(id=i, endpoints=[[r1, c1], [r2, c2]], color=COLORS[i % len(COLORS)]))
            break
        else:
            print(f"警告：只能放置 {len(nets)} 条线网（请求 {num_nets} 条）")
            break

    return Case(rows=rows, cols=cols, vias=vias, nets=nets)


def visualize(case: Case, paths: dict[int, list], save_path=None):
    """用 matplotlib 绘制布线结果。实心圆 = 起点，虚线圆 = 终点。"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("未安装 matplotlib，跳过可视化 — pip install matplotlib")
        return

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(-0.5, case.cols - 0.5)
    ax.set_ylim(case.rows - 0.5, -0.5)
    ax.set_aspect("equal")
    ax.set_facecolor("#0a0a0f")
    fig.patch.set_facecolor("#0a0a0f")

    # 网格线
    for r in range(case.rows + 1):
        ax.axhline(r - 0.5, color="#1a1a25", linewidth=0.3)
    for c in range(case.cols + 1):
        ax.axvline(c - 0.5, color="#1a1a25", linewidth=0.3)

    # Via 障碍（画叉）
    for r, c in case.vias:
        rect = patches.FancyBboxPatch((c - 0.4, r - 0.4), 0.8, 0.8,
            boxstyle="round,pad=0.05", facecolor="#1e1e2a", edgecolor="#333", linewidth=0.5)
        ax.add_patch(rect)
        ax.plot([c - 0.25, c + 0.25], [r - 0.25, r + 0.25], color="#444", linewidth=0.8)
        ax.plot([c + 0.25, c - 0.25], [r - 0.25, r + 0.25], color="#444", linewidth=0.8)

    # 布线路径与端点
    routed_count = 0
    for net in case.nets:
        path = paths.get(net.id)
        color = net.color if net.color else COLORS[net.id % len(COLORS)]
        if path:
            routed_count += 1
            cs = [p[1] for p in path]
            rs = [p[0] for p in path]
            ax.plot(cs, rs, color=color, linewidth=2, alpha=0.85,
                    solid_capstyle="round", solid_joinstyle="round")
        for ei, (pr, pc) in enumerate(net.endpoints):
            if ei == 0:  # 起点：实心圆
                circle = plt.Circle((pc, pr), 0.35, facecolor=color, edgecolor="white",
                                     linewidth=0.8, alpha=0.9, zorder=5)
            else:         # 终点：虚线圆
                circle = plt.Circle((pc, pr), 0.35, facecolor="none", edgecolor=color,
                                     linewidth=1.5, linestyle="--", alpha=0.9, zorder=5)
            ax.add_patch(circle)
            ax.text(pc, pr, str(net.id), ha="center", va="center",
                    color="white" if ei == 0 else color,
                    fontsize=max(5, min(9, 200 // case.rows)),
                    fontweight="bold", zorder=6)

    total = len(case.nets)
    title_color = ("#22c55e" if routed_count == total
                   else "#f59e0b" if routed_count >= total * 0.7
                   else "#ef4444")
    ax.set_title(
        f"Routability: {routed_count}/{total}  |  {case.rows}×{case.cols}  |  {len(case.vias)} vias",
        color=title_color, fontsize=14, fontweight="bold", pad=12)
    ax.tick_params(colors="#333", labelsize=6)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"已保存图片到 {save_path}")
    else:
        plt.show()


def builtin_example() -> Case:
    """内置的 20×20 示例，用于快速本地测试。"""
    vias = [[1,4],[3,10],[7,15],[14,1],[19,8],[0,13],[5,7],[8,18],[12,3],[16,11],
            [2,16],[6,2],[9,9],[13,14],[17,5],[4,19],[10,6],[15,17],[18,0],[11,12],
            [3,3],[7,7],[11,4],[14,14],[17,17],[1,17],[6,13],[9,1],[13,8],[16,3],
            [2,10],[5,18],[8,5],[12,16],[18,13],[0,6],[4,12],[10,19],[15,2],[19,15],
            [3,8],[7,11],[11,18],[14,6],[17,1]]
    nets = [
        Net(0, [[0,1],[19,18]], "#ef4444"), Net(1, [[1,5],[18,14]], "#3b82f6"),
        Net(2, [[0,10],[15,3]], "#14b8a6"), Net(3, [[2,16],[17,5]], "#f59e0b"),
        Net(4, [[5,0],[12,19]], "#a855f7"), Net(5, [[3,7],[16,12]], "#ec4899"),
        Net(6, [[13,1],[4,14]], "#f97316"), Net(7, [[2,8],[17,10]], "#22c55e"),
        Net(8, [[9,4],[8,13]], "#1e3a5f"), Net(9, [[15,6],[6,19]], "#92400e"),
    ]
    return Case(rows=20, cols=20, vias=vias, nets=nets)


def print_results(case, paths):
    """打印布线结果汇总。"""
    total = len(case.nets)
    routed = len(paths)
    print(f"\n{'='*50}")
    print(f"  结果：{routed}/{total} 条线网成功布线")
    print(f"{'='*50}")
    for net in case.nets:
        path = paths.get(net.id)
        manhattan = (abs(net.endpoints[0][0] - net.endpoints[1][0])
                   + abs(net.endpoints[0][1] - net.endpoints[1][1]))
        label = f"({net.name})" if net.name else ""
        if path:
            print(f"  Net {net.id:2d} {label:15s}  OK  路径长={len(path):3d}  (曼哈顿距离={manhattan})")
        else:
            print(f"  Net {net.id:2d} {label:15s}  --  FAILED  (曼哈顿距离={manhattan})")
    print()


def main():
    args = sys.argv[1:]

    export_path = None
    if "--export" in args:
        idx = args.index("--export")
        export_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    viz_path = None
    if "--save-fig" in args:
        idx = args.index("--save-fig")
        viz_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    no_viz = "--no-viz" in args
    if no_viz:
        args.remove("--no-viz")

    if len(args) >= 1 and args[0] == "--generate":
        size     = int(args[1]) if len(args) > 1 else 40
        num_nets = int(args[2]) if len(args) > 2 else 20
        num_vias = int(args[3]) if len(args) > 3 else 0
        seed     = int(args[4]) if len(args) > 4 else None
        case = generate_case(size, size, num_nets, num_vias, seed)
        print(f"已生成 {size}×{size}，{num_nets} 条线网，{num_vias} 个 via"
              + (f"，seed={seed}" if seed else ""))
    elif len(args) >= 1 and os.path.isfile(args[0]):
        case = Case.from_json(args[0])
        print(f"已加载 {args[0]}")
    else:
        case = builtin_example()
        print("使用内置 20×20 示例")

    paths = solve(case)
    print_results(case, paths)

    if export_path:
        result_data = case.to_dict()
        result_data["solver_result"] = {
            "routed_count": len(paths),
            "total": len(case.nets),
            "paths": {str(k): v for k, v in paths.items()},
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2)
        print(f"已导出结果到 {export_path}")

    if not no_viz:
        if case.rows * case.cols > 50 * 50:
            print(f"网格较大（{case.rows}×{case.cols}），跳过本地可视化。")
            print("请使用 app.py 查看结果：python app.py routing_solver_stu.py")
        else:
            visualize(case, paths, save_path=viz_path)


if __name__ == "__main__":
    main()
