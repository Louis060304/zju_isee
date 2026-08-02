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
# 布线逻辑：全局幽灵布线 → 迭代替换（阶梯复活罚金） → 事务恢复
#          所有寻路均使用双向 A*（起点和终点同时出发、相向搜索、中间汇合）
#
#   三阶段算法：
#
#   Phase 1 — 全局幽灵同步布线（罚金衰减）：
#     所有线网同时进行双向幽灵 A* 寻路，罚金采用衰减机制：
#       penalty = max(50, 300 - overlap_count × 50)
#     被重叠次数越多的线网穿越代价越低，逐步释放保护。
#     允许路径重叠，不对重叠线网进行拆线（不使用 RNR）。
#     重叠格子记录在多层占用表 cell_occupancy 中（0=空, 1=独占, 2+=重叠）。
#
#   Phase 2 — 迭代替换最差线网：
#     1. 找出"最差线网"：重叠格子数最多 → 路径最长
#     2. 拆除该线网并立即重新双向幽灵寻路（罚金依复活次数阶梯递增）
#     3. 每条线网拥有 3 次复活机会，罚金依次为 300 → 600 → 1200
#     4. 三次机会耗尽后永久淘汰（无振荡检测、无迭代上限、无罚金衰减）
#
#   Phase 3 — 事务型恢复（被淘汰线网的最后救援）：
#     对每条被淘汰线网：
#       1. 双向幽灵寻路（罚金 600）建立候选路径
#       2. 拆除挡路的已布线网，立即用双向标准 A* 全部重布（必须无重叠）
#       3. 全部重布成功 → 提交；任一失败 → 回滚，该线网彻底淘汰
#
#   关键参数：
#     GHOST_PENALTY         = 300   # Phase 1 基础穿墙代价
#     OVERLAP_DECAY         = 50    # 每次重叠衰减量
#     MIN_PENALTY           = 50    # 衰减下限
#     RESURRECTION_PENALTIES = [300, 600, 1200]  # Phase 2 阶梯罚金
#     PHASE3_PENALTY        = 600   # Phase 3 固定罚金
#     MAX_RESURRECTIONS     = 3     # 每条线网复活次数上限
#
#   寻路函数（双向版本）：
#     - find_single_path: 双向 A*，起点正向 + 终点反向同时搜索，在中间汇合
#     - find_ghost_path:  双向带代价 A*，soft_penalty 字典逐格指定穿越罚金
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
    """双向 A* 寻路：起点和终点同时出发，在中间汇合。
    occupied_set 中格子绝对不可通行。成功返回路径（含起终点），失败返回 []。"""
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [start]

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    # 启发函数
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
            # 若当前节点已在反向搜索空间中出现，则找到汇合点
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
                new_g = g_f[(cr, cc)] + 1
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
    soft_penalty: dict[tuple[int, int], int],
    rows: int,
    cols: int,
) -> list[tuple[int, int]]:
    """双向幽灵寻路：起点和终点同时出发，带代价惩罚，在中间汇合。

    硬障碍（via + 受保护端点 + 重叠次数≥2 的格子）→ 绝对不可通行。
    软障碍由 soft_penalty 字典给出：cell → 穿越该格需额外付出的代价。
    本算法允许穿越已被其他线网占用的格子（付出罚金代价），但绝不通行走不通的格子。

    :param start:          起点
    :param end:            终点
    :param hard_obstacles: 不可通行的坐标集合
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

    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def h_f(r: int, c: int) -> int:
        return abs(r - er) + abs(c - ec)

    def h_b(r: int, c: int) -> int:
        return abs(r - sr) + abs(c - sc)

    def step_cost(cell: tuple[int, int]) -> int:
        """计算进入该格的代价：基础 1 + 软障碍罚金"""
        cost = 1
        if cell in soft_penalty:
            cost += soft_penalty[cell]
        return cost

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


# ═══════════════════════════════════════════════════════════════════════════════
#  核心布线算法：三阶段全局幽灵 + 阶梯复活 + 事务恢复（双向 A* 版）
# ═══════════════════════════════════════════════════════════════════════════════

def solve(case: Case) -> dict[int, list]:
    """全局幽灵布线 + 迭代替换 + 事务恢复（全部寻路采用双向 A*）。

    三阶段算法：
      Phase 1：所有线网同时双向幽灵布线，罚金衰减 max(50, 300-50*n)，允许重叠，不拆线。
      Phase 2：迭代替换最差线网，罚金阶梯递增 300→600→1200，3 次复活后永久淘汰。
      Phase 3：对被淘汰线网尝试事务型救援——双向幽灵通路线路通才能最终落地。
    """

    # ═══════════════════════════════════════════════════════════════════
    #  参数常量
    # ═══════════════════════════════════════════════════════════════════
    # ── Phase 1 罚金衰减参数（同原始 global.py）──
    GHOST_PENALTY = 300       # 基础穿墙代价
    OVERLAP_DECAY = 50        # 每次重叠衰减量
    MIN_PENALTY   = 50        # 衰减下限（不低于此值）

    RESURRECTION_PENALTIES = [300, 600, 1200]  # Phase 2 阶梯罚金（第1/2/3次复活）
    PHASE3_PENALTY = 600                     # Phase 3 事务恢复幽灵罚金
    MAX_RESURRECTIONS = 3                    # 每条线网最大复活次数

    # ═══════════════════════════════════════════════════════════════════
    #  环境初始化
    # ═══════════════════════════════════════════════════════════════════

    # 硬障碍：via 格子
    via_set: set[tuple[int, int]] = set()
    for via in case.vias:
        via_set.add((via[0], via[1]))

    # 所有线网端点（受保护，不可穿越）
    all_endpoints: set[tuple[int, int]] = set()
    for net in case.nets:
        for ep in net.endpoints:
            all_endpoints.add((ep[0], ep[1]))

    # 按曼哈顿距离排序：短线优先
    sorted_nets = sorted(
        case.nets,
        key=lambda net: abs(net.endpoints[0][0] - net.endpoints[1][0])
                      + abs(net.endpoints[0][1] - net.endpoints[1][1])
    )

    net_by_id = {n.id: n for n in case.nets}

    # ═══════════════════════════════════════════════════════════════════
    #  全局状态
    # ═══════════════════════════════════════════════════════════════════
    cell_occupancy: dict[tuple[int, int], int] = {}  # cell → 占用次数（0=空,1=独占,2+=重叠）
    cell_owner:    dict[tuple[int, int], int] = {}  # cell → 独占者的 net_id
    paths:         dict[int, list] = {}              # net_id → 路径
    net_overlap_count: dict[int, int] = {}           # net_id → 累计被重叠次数（Phase 1 衰减用）

    # ═══════════════════════════════════════════════════════════════════
    #  辅助函数
    # ═══════════════════════════════════════════════════════════════════

    def apply_path(net_id: int, path: list[tuple[int, int]]):
        """将一条路径写入 cell_occupancy / cell_owner。
        对于路径上的每个格子：占用计数 +1；若原为 0（空）则记录占有者，
        若原为 1（独占→重叠）则清除占有者；≥2 时无占有者。"""
        for cell in path:
            occ = cell_occupancy.get(cell, 0)
            cell_occupancy[cell] = occ + 1
            if occ == 0:
                cell_owner[cell] = net_id
            elif occ == 1:
                # 从独占变为重叠，清除占有者记录
                cell_owner.pop(cell, None)

    def remove_path(net_id: int, path: list[tuple[int, int]]):
        """从 cell_occupancy / cell_owner 中移除一条路径。
        对于路径上的每个格子：占用计数 -1；若降为 0 则清除该格记录，
        若降为 1 则在其他路径中找回该格的唯一占有者。"""
        for cell in path:
            cnt = cell_occupancy.get(cell, 0) - 1
            if cnt <= 0:
                cell_occupancy.pop(cell, None)
                cell_owner.pop(cell, None)
            else:
                cell_occupancy[cell] = cnt
                if cnt == 1:
                    # 重叠→独占，需要在剩余路径中找回占有者
                    cell_owner.pop(cell, None)
                    for nid, p in paths.items():
                        if nid != net_id and cell in p:
                            cell_owner[cell] = nid
                            break

    def build_hard_soft(
        net_start: tuple[int, int],
        net_end: tuple[int, int],
        penalty: int,
        use_decay: bool = False,
        overlap_decay: dict[int, int] | None = None,
    ) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
        """为一条线网构建 hard / soft_penalty 视图。

        硬障碍（不可通行）：via + 其他线网端点 + 占用次数 ≥2 的格子
        软障碍（额外代价）：占用次数 == 1 的格子

        :param penalty:       基础罚金（use_decay=False 时统一使用）
        :param use_decay:     是否启用罚金衰减机制（仅 Phase 1 使用）
        :param overlap_decay: {net_id: 累计被重叠次数}，用于计算衰减罚金
        :return:              (hard 集合, soft_penalty 字典)
        """
        hard: set[tuple[int, int]] = set(via_set)

        # 将其他线网的端点设为硬障碍（保护起点和终点可通行）
        for ep in all_endpoints:
            if ep != net_start and ep != net_end:
                hard.add(ep)

        # 占用 ≥2 的格子设为硬障碍
        for cell, cnt in cell_occupancy.items():
            if cnt >= 2:
                hard.add(cell)

        # 占用 == 1 的格子设为软障碍
        soft_penalty: dict[tuple[int, int], int] = {}
        for cell, cnt in cell_occupancy.items():
            if cnt == 1 and cell not in hard:
                if use_decay and overlap_decay is not None:
                    # ── 罚金衰减：max(MIN, GHOST - overlap_count * DECAY) ──
                    ow = cell_owner.get(cell)
                    if ow is not None:
                        decay = overlap_decay.get(ow, 0) * OVERLAP_DECAY
                        p = max(MIN_PENALTY, GHOST_PENALTY - decay)
                    else:
                        p = GHOST_PENALTY
                    soft_penalty[cell] = p
                else:
                    # ── 固定罚金：Phase 2 / Phase 3 使用 ──
                    soft_penalty[cell] = penalty

        return hard, soft_penalty

    def route_one_net(
        net: Net,
        penalty: int,
        use_decay: bool = False,
        overlap_decay: dict[int, int] | None = None,
    ) -> list[tuple[int, int]]:
        """为一条线网进行幽灵寻路（调用双向幽灵 A*）。

        :param net:           线网对象
        :param penalty:       穿越独占格子时的罚金
        :param use_decay:     是否启用罚金衰减（仅 Phase 1）
        :param overlap_decay: 衰减计数字典（仅 Phase 1）
        :return:              成功返回路径，失败返回 []
        """
        (sr, sc), (er, ec) = net.endpoints
        start, end = (sr, sc), (er, ec)
        hard, sp = build_hard_soft(start, end, penalty,
                                   use_decay=use_decay, overlap_decay=overlap_decay)
        return find_ghost_path(start, end, hard, sp, case.rows, case.cols)

    def compute_overlaps() -> dict[int, tuple[int, int]]:
        """计算所有已布线网的冲突情况。

        :return: {net_id: (重叠格子数, 路径长度)}，仅包含存在重叠的线网
        """
        info: dict[int, tuple[int, int]] = {}
        for nid, path in paths.items():
            ov = sum(1 for cell in path if cell_occupancy.get(cell, 0) >= 2)
            if ov > 0:
                info[nid] = (ov, len(path))
        return info

    def build_occupied_set(
        exclude_endpoints: tuple[tuple[int, int], ...] = ()
    ) -> set[tuple[int, int]]:
        """构建标准 A* 所需的 occupied_set（完全不可通行的格子集合）。

        包含：via + 所有端点（排除指定端点）+ 当前所有路径的格子。

        :param exclude_endpoints: 需要排除的端点（当前待布线网的起终点）
        """
        occ: set[tuple[int, int]] = set(via_set)
        for ep in all_endpoints:
            if ep not in exclude_endpoints:
                occ.add(ep)
        for p in paths.values():
            for cell in p:
                occ.add(cell)
        return occ

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 1：全局幽灵同步布线（罚金衰减 max(50, 300-50*n)，允许重叠，不拆线）
    #          使用双向幽灵 A* 寻路
    # ═══════════════════════════════════════════════════════════════════
    #
    #  罚金衰减机制：被重叠次数越多的线网，穿越它的代价越低
    #    penalty = max(MIN_PENALTY, GHOST_PENALTY - net_overlap_count[owner] * OVERLAP_DECAY)
    #    = max(50, 300 - n * 50)
    #  引导后来线网"欺软怕硬"，逐步释放对重复被踩线网的保护。
    #
    for net in sorted_nets:
        path = route_one_net(net, GHOST_PENALTY,
                             use_decay=True, overlap_decay=net_overlap_count)
        if path:
            paths[net.id] = path
            apply_path(net.id, path)
            # 统计本线网与其他线网的重叠格数，累加到衰减计数
            ov = sum(1 for cell in path if cell_occupancy.get(cell, 0) >= 2)
            if ov > 0:
                net_overlap_count[net.id] = net_overlap_count.get(net.id, 0) + ov
        # 注：Phase 1 寻路失败的线网直接放弃，不进入后续阶段

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 2：迭代替换最差线网（阶梯复活罚金，无振荡检测）
    #          使用双向幽灵 A* 寻路
    # ═══════════════════════════════════════════════════════════════════
    resurrection_count: dict[int, int] = {}   # net_id → 剩余复活次数（初始 3）
    eliminated: set[int] = set()              # 永久淘汰的线网 ID 集合

    while True:
        overlap_info = compute_overlaps()
        if not overlap_info:
            break  # 无重叠，Phase 2 完成

        # 找出最差线网：重叠格子数最多 → 平局时路径最长
        worst_id = max(
            overlap_info.keys(),
            key=lambda nid: (overlap_info[nid][0], overlap_info[nid][1])
        )

        # 检查复活次数
        remain = resurrection_count.get(worst_id, MAX_RESURRECTIONS)

        if remain <= 0:
            # 复活次数耗尽 → 永久淘汰
            old_path = paths.pop(worst_id, None)
            if old_path:
                remove_path(worst_id, old_path)
            eliminated.add(worst_id)
            continue

        # 确定本次罚金（按当前剩余次数索引）
        # remain=3 → penalties[0]=300, remain=2 → penalties[1]=600, remain=1 → penalties[2]=1200
        dyn_penalty = RESURRECTION_PENALTIES[MAX_RESURRECTIONS - remain]

        # 消耗一次复活机会
        resurrection_count[worst_id] = remain - 1

        # 拆除旧路径
        old_path = paths.pop(worst_id, None)
        if old_path:
            remove_path(worst_id, old_path)

        # 立即重新幽灵寻路（双向）
        worst_net = net_by_id.get(worst_id)
        if worst_net is None:
            eliminated.add(worst_id)
            continue

        new_path = route_one_net(worst_net, dyn_penalty)

        if new_path:
            # 重新布线成功
            paths[worst_id] = new_path
            apply_path(worst_id, new_path)
        else:
            # 寻路失败（无路可走）→ 永久淘汰
            eliminated.add(worst_id)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 3：事务型恢复 —— 对淘汰线网的最后救援
    #          使用双向幽灵 A* + 双向标准 A*
    # ═══════════════════════════════════════════════════════════════════
    #
    # 对每条被淘汰线网：
    #   1. 双向幽灵寻路（罚金 600）→ 候选路径
    #   2. 找出候选路径踩到的已布线网 → 临时拆除
    #   3. 候选路径入局 → 被拆线网全部用双向标准 A* 重布（必须无重叠）
    #   4. 全部成功 → 提交；任一失败 → 回滚到事务前状态，该线网彻底放弃

    for eliminated_id in sorted(eliminated):  # 按 ID 排序，确定性处理
        eliminated_net = net_by_id.get(eliminated_id)
        if eliminated_net is None:
            continue

        # ── 保存事务前快照（深拷贝，用于失败回滚）──
        backup_paths = {nid: list(p) for nid, p in paths.items()}
        backup_occupancy = dict(cell_occupancy)
        backup_owner = dict(cell_owner)

        # ── 步骤 1：双向幽灵寻路（罚金 600）──
        ghost_path = route_one_net(eliminated_net, PHASE3_PENALTY)
        if not ghost_path:
            continue  # 幽灵寻路失败，彻底放弃

        # ── 步骤 2：找出被踩的已布线网 ──
        ghost_set = set(ghost_path)
        conflict_ids: list[int] = []
        for nid, existing_path in paths.items():
            for cell in existing_path:
                if cell in ghost_set:
                    conflict_ids.append(nid)
                    break

        # ── 步骤 3：拆除被踩线网，布入候选路径 ──
        for nid in conflict_ids:
            remove_path(nid, paths[nid])
        # 注意：被拆线网暂存于 conflict_ids 列表中，paths 中已无它们

        apply_path(eliminated_id, ghost_path)
        paths[eliminated_id] = ghost_path

        # ── 步骤 4：被拆线网全部用双向标准 A* 重布（必须无重叠）──
        rollback_needed = False
        rerouted: dict[int, list] = {}  # 暂存重布结果

        for nid in conflict_ids:
            victim_net = net_by_id.get(nid)
            if victim_net is None:
                rollback_needed = True
                break

            (sr, sc), (er, ec) = victim_net.endpoints
            start, end = (sr, sc), (er, ec)

            # 构建当前 occupied_set（含幽灵路径和已重布成功的路径）
            occupied = build_occupied_set(exclude_endpoints=(start, end))
            clean_path = find_single_path(start, end, occupied, case.rows, case.cols)

            if clean_path:
                # 重布成功，暂存并立即更新 occupied 以供后续重布使用
                rerouted[nid] = clean_path
                apply_path(nid, clean_path)
                paths[nid] = clean_path
            else:
                rollback_needed = True
                break

        # ── 步骤 5：根据结果提交或回滚 ──
        if rollback_needed:
            # 回滚到事务前状态
            paths.clear()
            paths.update(backup_paths)
            cell_occupancy.clear()
            cell_occupancy.update(backup_occupancy)
            cell_owner.clear()
            cell_owner.update(backup_owner)
            # 该线网彻底淘汰，不出现在 paths 中
        # 若成功：paths 中已包含 eliminated_id + 所有重布成功的 conflict_ids

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
