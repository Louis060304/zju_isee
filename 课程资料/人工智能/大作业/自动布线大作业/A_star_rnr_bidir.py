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
#
# 布线逻辑：RNR 幽灵模式 + 双向 A* — 队列调度 + 复活机制
#
#   与 A_star_rnr.py 相同调度逻辑，但寻路函数改为双向 A*：
#     - 起点和终点同时出发、相向搜索，在中间汇合
#     - 每次迭代正向反向各扩展一步，搜索空间更小
#
#   整体流程：
#     1. 线网按曼哈顿距离排序，短线优先入队
#     2. 逐条出队 → 双向标准 A*（干净路径）
#     3. 标准双向 A* 失败 → 双向幽灵 A*（允许穿越已有线网）
#     4. 幽灵 A* 失败 → 消耗复活次数（共 2 次），排到队尾重试
#     5. 幽灵 A* 成功 → 拆除被踩线网，更新历史地价，被拆线网排回队尾
#
#   三条保护线：
#     - 复活机制：失败线网有 2 次重试机会，穿墙罚金递减 600→300→0
#     - 历史地价：格子被撕次数越多，5^n 指数增长，引导后来者绕行
#     - 拆线上限：同一对 (被拆者, 拆除者) 最多互拆 5 次，不同拆除者独立计数
#
#   寻路函数：
#     - find_single_path: 双向 A*，起点正向 + 终点反向同时搜索，在中间汇合
#     - find_ghost_path:  双向带代价 A*，区分硬/软障碍，step_cost = 1 + penalty + 5^conflict
#
# ═══════════════════════════════════════════════════════════════════════════════

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


def find_single_path(
    start: tuple[int, int],
    end: tuple[int, int],
    occupied_set: set[tuple[int, int]],
    rows: int,
    cols: int
) -> list[tuple[int, int]]:
    """双向 A* 寻路：起点和终点同时出发，在中间汇合。"""
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [start]

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    # 启发式函数
    def h_f(r: int, c: int) -> int:
        return abs(r - er) + abs(c - ec)

    def h_b(r: int, c: int) -> int:
        return abs(r - sr) + abs(c - sc)

    # ── 正向（start → end）──
    g_f: dict[tuple[int, int], int] = {start: 0}
    came_from_f: dict[tuple[int, int], tuple[int, int]] = {}

    # ── 反向（end → start）──
    g_b: dict[tuple[int, int], int] = {end: 0}
    came_from_b: dict[tuple[int, int], tuple[int, int]] = {}

    counter = 0
    heap_f = [(h_f(sr, sc), counter, sr, sc)]
    counter += 1
    heap_b = [(h_b(er, ec), counter, er, ec)]
    counter += 1

    meeting: tuple[int, int] | None = None

    while heap_f and heap_b:
        # ── 正向扩展一步 ──
        if heap_f:
            _, _, cr, cc = heapq.heappop(heap_f)
            if (cr, cc) in g_f and g_f[(cr, cc)] < g_f.get((cr, cc), float("inf")):
                # 跳过过时的堆条目：当前 g 值已不是入堆时的值
                # 这里的逻辑：如果堆弹出的节点的 g 值与记录的 g 值不同，跳过
                pass
            # 用 closed 标记替代方案：比较弹出时的 f 与 g+h
            # 简化处理：直接检查是否已在对方搜索空间中
            if (cr, cc) in g_b:
                meeting = (cr, cc)
                break

            for dr, dc in dirs:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                neighbor = (nr, nc)
                if neighbor in occupied_set:
                    continue
                # 跳过已由正向处理过的节点（g_f 中已有更小或相等的值）
                new_g = g_f[(cr, cc)] + 1
                if new_g < g_f.get(neighbor, float("inf")):
                    g_f[neighbor] = new_g
                    came_from_f[neighbor] = (cr, cc)
                    counter += 1
                    heapq.heappush(heap_f, (new_g + h_f(nr, nc), counter, nr, nc))

        # ── 反向扩展一步 ──
        if heap_b:
            _, _, cr, cc = heapq.heappop(heap_b)
            if (cr, cc) in g_b and g_b[(cr, cc)] < g_b.get((cr, cc), float("inf")):
                pass
            if (cr, cc) in g_f:
                meeting = (cr, cc)
                break

            for dr, dc in dirs:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                neighbor = (nr, nc)
                if neighbor in occupied_set:
                    continue
                new_g = g_b[(cr, cc)] + 1
                if new_g < g_b.get(neighbor, float("inf")):
                    g_b[neighbor] = new_g
                    came_from_b[neighbor] = (cr, cc)
                    counter += 1
                    heapq.heappush(heap_b, (new_g + h_b(nr, nc), counter, nr, nc))

    if meeting is None:
        return []

    # ── 还原路径：start → meeting → end ──
    path: list[tuple[int, int]] = []

    cur: tuple[int, int] | None = meeting
    while cur is not None:
        path.append(cur)
        cur = came_from_f.get(cur)
    path.reverse()

    cur = came_from_b.get(meeting)
    while cur is not None:
        path.append(cur)
        cur = came_from_b.get(cur)

    return path


def find_ghost_path(
    start: tuple[int, int],
    end: tuple[int, int],
    hard_obstacles: set[tuple[int, int]],
    soft_obstacles: set[tuple[int, int]],
    conflict_count: dict[tuple[int, int], int],
    rows: int,
    cols: int,
    penalty: int = 600,
) -> list[tuple[int, int]]:
    """双向幽灵寻路：起点和终点同时出发，带代价惩罚，在中间汇合。"""
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [start]

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def h_f(r: int, c: int) -> int:
        return abs(r - er) + abs(c - ec)

    def h_b(r: int, c: int) -> int:
        return abs(r - sr) + abs(c - sc)

    def step_cost(cell: tuple[int, int]) -> int:
        cost = 1
        if cell in soft_obstacles:
            cost += penalty
        cost += 5 ** conflict_count.get(cell, 0)
        return cost

    # ── 正向 ──
    g_f: dict[tuple[int, int], int] = {start: 0}
    came_from_f: dict[tuple[int, int], tuple[int, int]] = {}

    # ── 反向 ──
    g_b: dict[tuple[int, int], int] = {end: 0}
    came_from_b: dict[tuple[int, int], tuple[int, int]] = {}

    counter = 0
    heap_f = [(h_f(sr, sc), counter, sr, sc)]
    counter += 1
    heap_b = [(h_b(er, ec), counter, er, ec)]
    counter += 1

    meeting: tuple[int, int] | None = None

    while heap_f and heap_b:
        # ── 正向扩展一步 ──
        if heap_f:
            _, _, cr, cc = heapq.heappop(heap_f)
            if (cr, cc) in g_b:
                meeting = (cr, cc)
                break

            for dr, dc in dirs:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                neighbor = (nr, nc)
                if neighbor in hard_obstacles:
                    continue
                new_g = g_f[(cr, cc)] + step_cost(neighbor)
                if new_g < g_f.get(neighbor, float("inf")):
                    g_f[neighbor] = new_g
                    came_from_f[neighbor] = (cr, cc)
                    counter += 1
                    heapq.heappush(heap_f, (new_g + h_f(nr, nc), counter, nr, nc))

        # ── 反向扩展一步 ──
        if heap_b:
            _, _, cr, cc = heapq.heappop(heap_b)
            if (cr, cc) in g_f:
                meeting = (cr, cc)
                break

            for dr, dc in dirs:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                neighbor = (nr, nc)
                if neighbor in hard_obstacles:
                    continue
                new_g = g_b[(cr, cc)] + step_cost(neighbor)
                if new_g < g_b.get(neighbor, float("inf")):
                    g_b[neighbor] = new_g
                    came_from_b[neighbor] = (cr, cc)
                    counter += 1
                    heapq.heappush(heap_b, (new_g + h_b(nr, nc), counter, nr, nc))

    if meeting is None:
        return []

    # ── 还原路径：start → meeting → end ──
    path: list[tuple[int, int]] = []

    cur: tuple[int, int] | None = meeting
    while cur is not None:
        path.append(cur)
        cur = came_from_f.get(cur)
    path.reverse()

    cur = came_from_b.get(meeting)
    while cur is not None:
        path.append(cur)
        cur = came_from_b.get(cur)

    return path


def solve(case: Case) -> dict[int, list]:
    from collections import deque

    via_set: set[tuple[int, int]] = set()
    for via in case.vias:
        via_set.add((via[0], via[1]))

    all_endpoints: set[tuple[int, int]] = set()
    for net in case.nets:
        for ep in net.endpoints:
            all_endpoints.add((ep[0], ep[1]))

    conflict_count: dict[tuple[int, int], int] = {}

    sorted_nets = sorted(
        case.nets,
        key=lambda net: abs(net.endpoints[0][0] - net.endpoints[1][0])
                      + abs(net.endpoints[0][1] - net.endpoints[1][1])
    )

    occupied_set: set[tuple[int, int]] = via_set | all_endpoints
    paths: dict[int, list] = {}

    queue = deque(sorted_nets)
    # (被拆线网, 拆除线网) → 被拆次数，同一对最多 5 次，不同拆除者独立计数
    ripup_count: dict[tuple[int, int], int] = {}
    MAX_RIPUPS = 5

    GHOST_PENALTY = 600

    # ── 复活机制：每条线网初始拥有 2 次复活机会 ──
    MAX_RESURRECTIONS = 2
    resurrection_count: dict[int, int] = {}  # net.id → 剩余复活次数

    while queue:
        net = queue.popleft()

        (sr, sc), (er, ec) = net.endpoints
        start = (sr, sc)
        end = (er, ec)

        # ── 正常双向寻路 ──
        occupied_set.discard(start)
        occupied_set.discard(end)

        path = find_single_path(start, end, occupied_set, case.rows, case.cols)

        if path:
            for cell in path:
                occupied_set.add(cell)
            paths[net.id] = path
            continue

        occupied_set.add(start)
        occupied_set.add(end)

        # ── 幽灵双向寻路 ──
        hard = set(via_set)
        for ep in all_endpoints:
            if ep != start and ep != end:
                hard.add(ep)

        soft: set[tuple[int, int]] = set()
        for p in paths.values():
            for cell in p:
                soft.add(cell)

        # ── 动态罚金：复活次数越少，穿墙代价越低 ──
        # remain=2 → 首次尝试，全额罚金 600
        # remain=1 → 第一次复活后，罚金减半 300
        # remain=0 → 最后一次复活，罚金归零（放手一搏）
        remain = resurrection_count.get(net.id, MAX_RESURRECTIONS)
        if remain == 2:
            dyn_penalty = GHOST_PENALTY       # 600
        elif remain == 1:
            dyn_penalty = GHOST_PENALTY // 2  # 300
        else:
            dyn_penalty = 0                   # 最后机会，无视软障碍

        ghost_path = find_ghost_path(
            start, end, hard, soft, conflict_count,
            case.rows, case.cols, penalty=dyn_penalty
        )

        if not ghost_path:
            # ── 幽灵模式失败，不直接淘汰，消耗一次复活机会 ──
            if remain > 0:
                resurrection_count[net.id] = remain - 1
                queue.append(net)  # 排到队尾，等待后续重试
            # 复活次数耗尽 → 彻底放弃该线网
            continue

        ghost_set = set(ghost_path)
        conflict_ids: list[int] = []
        for nid, existing_path in paths.items():
            for cell in existing_path:
                if cell in ghost_set:
                    conflict_ids.append(nid)
                    break

        for nid in conflict_ids:
            old_path = paths[nid]
            for cell in old_path:
                if cell in ghost_set:
                    conflict_count[cell] = conflict_count.get(cell, 0) + 1

        for nid in conflict_ids:
            old_path = paths.pop(nid)
            for cell in old_path:
                occupied_set.discard(cell)

        for cell in ghost_path:
            occupied_set.add(cell)
        paths[net.id] = ghost_path

        # 按 (被拆者, 拆除者) 配对计数，同一对最多拆 5 次
        for nid in conflict_ids:
            pair = (nid, net.id)
            ripup_count[pair] = ripup_count.get(pair, 0) + 1
            if ripup_count[pair] > MAX_RIPUPS:
                continue
            for n in case.nets:
                if n.id == nid:
                    queue.append(n)
                    break

    return paths


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
