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
# 布线逻辑：全局幽灵布线 → 迭代替换（阶梯复活罚金） → 最终严格布线
#
#   三阶段算法：
#
#   Phase 1 — 全局幽灵同步布线（罚金衰减）：
#     所有线网通过 global_sync_round 同时进行幽灵 A* 寻路，罚金采用衰减机制：
#       penalty = max(MIN_PENALTY, GHOST_PENALTY - net_overlap_count[owner] × OVERLAP_DECAY)
#       = max(50, 300 - n × 50)
#     被重叠次数越多的线网穿越代价越低，逐步释放对重复被踩线网的保护。
#     允许路径重叠，不对重叠线网进行拆线（不使用 RNR）。
#     重叠格子记录在多层占用表 cell_occupancy 中（0=空, 1=独占, 2+=重叠）。
#
#   Phase 2 — 迭代替换最差线网：
#     1. 找出"最差线网"：重叠格子数最多 → 平局时路径最长
#     2. 拆除该线网并立即重新幽灵寻路（罚金依复活次数阶梯递增）
#     3. 每条线网拥有 MAX_RESURRECTIONS=3 次复活机会，罚金依次为 300 → 600 → 1200
#     4. 三次机会耗尽后永久淘汰（无振荡检测、无迭代上限——复活次数有限自然终止）
#     5. Phase 2 使用 penalty_override 覆盖衰减机制，固定罚金
#
#   Phase 3 — 最终严格布线：
#     Phase 2 结束后，对未被淘汰的线网用标准 A* 做一次无重叠的单次布线。
#     失败即放弃，不再回溯或重试。
#
#   关键参数：
#     GHOST_PENALTY         = 300               # Phase 1 基础穿墙代价
#     OVERLAP_DECAY         = 50                # 每次重叠衰减量
#     MIN_PENALTY           = 50                # 衰减下限
#     RESURRECTION_PENALTIES = [300, 600, 1200] # Phase 2 阶梯罚金
#     MAX_RESURRECTIONS     = 3                 # 每条线网复活次数上限
#
#   寻路函数：
#     - find_single_path: 标准 A*，曼哈顿启发，四连通，occupied_set 中格子不可通行
#     - find_ghost_path:  带代价 A*，hard_obstacles → 不可通行，soft_penalty 字典 → 逐格罚金
#
#   solve 内部使用以下辅助闭包：
#     - apply_path / remove_path：多层占用表读写
#     - build_hard_soft：为线网构建当前 hard/soft_penalty 视图
#     - route_one_net：封装 build_hard_soft + find_ghost_path
#     - compute_overlaps：计算各线网重叠格子数
#     - global_sync_round：对一组线网执行全局同步幽灵布线
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
    """标准 A* 寻路。曼哈顿启发，四连通，occupied_set 中格子绝对不可通行。
    成功返回路径（含起终点），失败返回 []。"""
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [start]

    def h(r: int, c: int) -> int:
        return abs(r - er) + abs(c - ec)

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    g_score: dict[tuple[int, int], int] = {start: 0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    closed: set[tuple[int, int]] = set()

    counter = 0
    heap = [(h(sr, sc), counter, sr, sc)]

    found = False
    while heap:
        _, _, cr, cc = heapq.heappop(heap)

        if (cr, cc) in closed:
            continue

        if cr == er and cc == ec:
            found = True
            break

        closed.add((cr, cc))

        for dr, dc in dirs:
            nr, nc = cr + dr, cc + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            neighbor = (nr, nc)
            if neighbor in closed or neighbor in occupied_set:
                continue

            new_g = g_score[(cr, cc)] + 1
            if new_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = new_g
                came_from[neighbor] = (cr, cc)
                counter += 1
                heapq.heappush(heap, (new_g + h(nr, nc), counter, nr, nc))

    if not found:
        return []

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = end
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    path.reverse()
    return path


def find_ghost_path(
    start: tuple[int, int],
    end: tuple[int, int],
    hard_obstacles: set[tuple[int, int]],
    soft_penalty: dict[tuple[int, int], int],
    rows: int,
    cols: int,
) -> list[tuple[int, int]]:
    """
    幽灵寻路函数（带逐格可变罚金的 A* 算法）

    硬障碍（via + 受保护端点）→ 绝对不可通行。
    软障碍由 soft_penalty 字典给出：cell → 穿越该格需额外付出的代价。

    :param start:          起点
    :param end:            终点
    :param hard_obstacles: 不可通行的坐标集合（via + 受保护端点）
    :param soft_penalty:   可变软障碍字典 cell → 穿越惩罚值
    :param rows:           地图行数
    :param cols:           地图列数
    :return:               成功返回路径，失败返回空列表
    """
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [start]

    def h(r: int, c: int) -> int:
        return abs(r - er) + abs(c - ec)

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    g_score: dict[tuple[int, int], int] = {start: 0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    closed: set[tuple[int, int]] = set()

    counter = 0
    heap = [(h(sr, sc), counter, sr, sc)]

    found = False
    while heap:
        _, _, cr, cc = heapq.heappop(heap)

        if (cr, cc) in closed:
            continue

        if cr == er and cc == ec:
            found = True
            break

        closed.add((cr, cc))

        for dr, dc in dirs:
            nr, nc = cr + dr, cc + dc

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            neighbor = (nr, nc)

            if neighbor in closed or neighbor in hard_obstacles:
                continue

            step_cost = 1
            if neighbor in soft_penalty:
                step_cost += soft_penalty[neighbor]

            new_g = g_score[(cr, cc)] + step_cost
            if new_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = new_g
                came_from[neighbor] = (cr, cc)
                counter += 1
                heapq.heappush(heap, (new_g + h(nr, nc), counter, nr, nc))

    if not found:
        return []

    path: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = end
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    path.reverse()
    return path


def solve(case: Case) -> dict[int, list]:
    """全局幽灵布线 + 迭代替换（阶梯复活罚金） + 最终严格布线。

    三阶段算法：
      Phase 1：全局同步幽灵布线，罚金衰减 max(50, 300-50*n)，允许重叠，不拆线。
      Phase 2：迭代替换最差线网，罚金阶梯递增 300→600→1200，3 次复活后永久淘汰。
      Phase 3：对未淘汰线网用标准 A* 做一次干净布线（无重叠，失败即放弃）。

    【输入】 case.rows/cols/vias/nets
    【输出】 {net_id: [(r,c), ...], ...}  仅包含成功布线的线网
    """
    from collections import deque

    # ── 硬障碍：via ──
    via_set: set[tuple[int, int]] = set()
    for via in case.vias:
        via_set.add((via[0], via[1]))

    # ── 端点保护：全图所有线网端点提升为 via 级硬障碍 ──
    all_endpoints: set[tuple[int, int]] = set()
    for net in case.nets:
        for ep in net.endpoints:
            all_endpoints.add((ep[0], ep[1]))

    # 按曼哈顿距离从小到大排序：短线优先
    sorted_nets = sorted(
        case.nets,
        key=lambda net: abs(net.endpoints[0][0] - net.endpoints[1][0])
                      + abs(net.endpoints[0][1] - net.endpoints[1][1])
    )

    GHOST_PENALTY = 300       # 基础穿墙代价
    OVERLAP_DECAY = 50        # 重叠衰减量
    MIN_PENALTY   = 50        # 衰减下限
    RESURRECTION_PENALTIES = [300, 600, 1200]  # Phase 2 阶梯罚金（第1/2/3次复活）
    MAX_RESURRECTIONS = 3                      # 每条线网最大复活次数

    # ── 辅助函数 ─────────────────────────────────────────────────────

    def build_hard_soft(net_start, net_end, occupancy, owner, hard_override=None):
        """为一条线网构建当前 hard / soft_penalty 视图"""
        hard = set(via_set) if hard_override is None else set(hard_override)
        if hard_override is None:
            for ep in all_endpoints:
                if ep != net_start and ep != net_end:
                    hard.add(ep)
        for cell, cnt in occupancy.items():
            if cnt >= 2:
                hard.add(cell)

        soft_penalty: dict[tuple[int, int], int] = {}
        for cell, cnt in occupancy.items():
            if cnt == 1 and cell not in hard:
                ow = owner.get(cell)
                if ow is not None:
                    # 被重叠次数（net_overlap_count）越多，罚金衰减越厉害
                    decay = net_overlap_count.get(ow, 0) * OVERLAP_DECAY
                    p = max(MIN_PENALTY, GHOST_PENALTY - decay) # 下限 50，上限 300
                else:
                    p = GHOST_PENALTY
                soft_penalty[cell] = p
        return hard, soft_penalty

    def route_one_net(net, occupancy, owner, penalty_override=None):
        """为一条线网寻路，返回路径或 []。penalty_override 不为 None 时覆盖软障碍罚金"""
        (sr, sc), (er, ec) = net.endpoints
        start, end = (sr, sc), (er, ec)
        hard, sp = build_hard_soft(start, end, occupancy, owner)
        if penalty_override is not None:
            sp = {c: penalty_override for c in sp}
        return find_ghost_path(start, end, hard, sp, case.rows, case.cols)

    def apply_path(net_id, path, occupancy, owner):
        """将路径写入 occupancy / owner"""
        for cell in path:
            occ = occupancy.get(cell, 0)
            occupancy[cell] = occ + 1
            if occ == 0:
                owner[cell] = net_id
            elif occ == 1:
                owner.pop(cell, None)

    def remove_path(net_id, path, occupancy, owner, all_paths):
        """从 occupancy / owner 中移除一条路径"""
        for cell in path:
            cnt = occupancy.get(cell, 0) - 1
            if cnt <= 0:
                occupancy.pop(cell, None)
                owner.pop(cell, None)
            else:
                occupancy[cell] = cnt
                if cnt == 1:
                    owner.pop(cell, None)
                    for nid, p in all_paths.items():
                        if nid != net_id and cell in p:
                            owner[cell] = nid
                            break

    def compute_overlaps(occupancy, all_paths):
        """返回 {net_id: (重叠数, 路径长)} 仅含存在重叠的线网"""
        info: dict[int, tuple[int, int]] = {}
        for nid, path in all_paths.items():
            ov = sum(1 for cell in path if occupancy.get(cell, 0) >= 2)
            if ov > 0:
                info[nid] = (ov, len(path))
        return info

    def global_sync_round(nets, occupancy, owner, all_paths):
        """对 nets 执行一次全局同步布线，写入 occupancy/owner/all_paths"""
        for net in nets:
            path = route_one_net(net, occupancy, owner)
            if path:
                all_paths[net.id] = path
                apply_path(net.id, path, occupancy, owner)

    # ── 全局状态 ─────────────────────────────────────────────────────
    net_overlap_count: dict[int, int] = {}   # Phase 1 罚金衰减计数
    resurrection_count: dict[int, int] = {}   # Phase 2 复活次数 net_id → 剩余
    eliminated: set[int] = set()              # Phase 2 永久淘汰的线网 ID

    cell_occupancy: dict[tuple[int, int], int] = {}
    cell_owner: dict[tuple[int, int], int] = {}
    paths: dict[int, list] = {}

    net_by_id = {n.id: n for n in case.nets}

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 1：初次全局同步布线（罚金衰减 max(50, 300-50*n)，允许重叠，不拆线）
    # ═══════════════════════════════════════════════════════════════════
    global_sync_round(sorted_nets, cell_occupancy, cell_owner, paths)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 2：迭代替换最差线网（阶梯复活罚金，无振荡检测）
    # ═══════════════════════════════════════════════════════════════════
    #
    #  每条线网拥有 MAX_RESURRECTIONS 次被拆除后重布的机会。
    #  罚金依复活次数阶梯递增：300 → 600 → 1200，引导线网逐步避让。
    #  复活次数耗尽后永久淘汰。无振荡检测、无迭代上限（次数有限自然终止）。
    #
    while True:
        overlap_info = compute_overlaps(cell_occupancy, paths)
        if not overlap_info:
            break  # 零重叠，Phase 2 完成

        # 找出最差线网：重叠格子数最多 → 平局时路径最长
        worst_id = max(
            # 首要：重叠格子数（overlap_info[nid][0]）越多，越差
            overlap_info.keys(), 
            # 次要：若重叠数相同，路径长度（overlap_info[nid][1]）越长，越差
            key=lambda nid: (overlap_info[nid][0], overlap_info[nid][1])
        )

        # 检查复活次数
        remain = resurrection_count.get(worst_id, MAX_RESURRECTIONS)

        if remain <= 0:
            # 复活次数耗尽 → 永久淘汰
            old_path = paths.pop(worst_id, None)
            if old_path:
                remove_path(worst_id, old_path, cell_occupancy, cell_owner, paths)
            eliminated.add(worst_id)
            continue

        # 确定本次罚金（按当前剩余次数索引）
        # remain=3 → penalties[0]=300, remain=2 → penalties[1]=600, remain=1 → penalties[2]=1200
        dyn_penalty = RESURRECTION_PENALTIES[MAX_RESURRECTIONS - remain]

        # 消耗一次复活机会
        resurrection_count[worst_id] = remain - 1

        # 拆除旧路径
        worst_net = net_by_id.get(worst_id)
        if worst_net is None:
            eliminated.add(worst_id)
            continue

        old_path = paths.pop(worst_id, None)
        if old_path:
            remove_path(worst_id, old_path, cell_occupancy, cell_owner, paths)

        # 立即重新幽灵寻路（固定罚金覆盖衰减机制，惩罚由 remainder 阶段决定）
        new_path = route_one_net(worst_net, cell_occupancy, cell_owner,
                                 penalty_override=dyn_penalty)

        if new_path:
            paths[worst_id] = new_path
            apply_path(worst_id, new_path, cell_occupancy, cell_owner)
        else:
            # 无路可走 → 永久淘汰
            eliminated.add(worst_id)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 3：最终轮 —— 对未淘汰线网严格布线（不允许重叠）
    # ═══════════════════════════════════════════════════════════════════
    #
    #  Phase 2 结束后，从 sorted_nets 中筛出未被淘汰的线网，
    #  用标准 A* 做一次干净的单次布线（不允许重叠，失败即放弃）。
    #
    active_nets = [n for n in sorted_nets if n.id not in eliminated]
    occupied_set: set[tuple[int, int]] = via_set | all_endpoints
    final_paths: dict[int, list] = {}

    for net in active_nets:
        (sr, sc), (er, ec) = net.endpoints
        start, end = (sr, sc), (er, ec)
        occupied_set.discard(start)
        occupied_set.discard(end)
        path = find_single_path(start, end, occupied_set, case.rows, case.cols)
        if path:
            for cell in path:
                occupied_set.add(cell)
            final_paths[net.id] = path
        else:
            occupied_set.add(start)
            occupied_set.add(end)

    return final_paths


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
