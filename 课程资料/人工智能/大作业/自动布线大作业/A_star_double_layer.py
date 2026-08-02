"""
PCB 双层布线 — 基于单层算法的双层扩展
=======================================

双层布线策略（三阶段）：
  Phase 1 — 正面单层布线：调用选定的单层求解器在正面布线
  Phase 2 — 反面单层布线：对剩余线网在反面调用单层求解器
  Phase 3 — 过孔穿越布线：对仍未布通的线网，使用 3D A* 允许过孔穿越到另一面

单层求解器通过 importlib 动态加载，默认使用 A_star_rnr.py。
可通过修改 SINGLE_LAYER_SOLVER 切换为其他七种算法之一。

本地测试：
    python A_star_double_layer.py                    # 内置 20×20 示例
    python A_star_double_layer.py case.json          # 加载指定题目
    python A_star_double_layer.py --generate 40 20   # 随机生成
"""

import json
import random
import sys
import os
import importlib.util
from dataclasses import dataclass
from collections import deque

# ── Windows UTF-8 编码修复 ──
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
#  配置：选择底层单层求解器（七选一）
# ═══════════════════════════════════════════════════════════════════════════════
#  可选值：
#    "A_star_rnr.py"
#    "A_star_rnr_bidir.py"
#    "A_star_rnr_immediate_reroute.py"
#    "A_star_rnr_immediate_reroute_bidir.py"
#    "A_star_global.py"
#    "A_star_global_x.py"
#    "A_star_global_x_bidir.py"
SINGLE_LAYER_SOLVER = "A_star_rnr.py" #输入使用的单层求解器文件
# 获取并拼接当前脚本所在目录的绝对路径
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_solver_path = os.path.join(_THIS_DIR, SINGLE_LAYER_SOLVER)
if not os.path.exists(_solver_path):
    raise FileNotFoundError(f"单层求解器不存在: {_solver_path}")
#动态加载
_spec = importlib.util.spec_from_file_location("single_layer_solver", _solver_path)
_sl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sl)
# 从单层模块中提取核心函数和数据类
Net = _sl.Net
Case = _sl.Case
sl_find_single_path = _sl.find_single_path
sl_solve = _sl.solve

# 尝试加载 find_ghost_path
sl_find_ghost_path = getattr(_sl, "find_ghost_path", None)

#
# # [日志] 模块加载时不打印，避免干扰 benchmark 输出
# print(f"[双层布线] 已加载单层求解器: {SINGLE_LAYER_SOLVER}")

# ── 图层元数据（供 app.py 可视化读取）──
_layer_data = None

# ═══════════════════════════════════════════════════════════════════════════════
#  过孔布线参数
# ═══════════════════════════════════════════════════════════════════════════════
VIA_PENALTY = 10          # 过孔基础代价（等价于走10步普通路径）
VIA_PENALTY_MAX = 40      # 过孔代价上限（用于迭代优化过孔数）
GHOST_VIA_PENALTY = 6     # 幽灵模式下穿越已有路径的额外代价
MAX_VIA_ITERATIONS = 3    # 过孔惩罚迭代次数上限


# ═══════════════════════════════════════════════════════════════════════════════
#  3D 过孔感知 A* 寻路（核心新增函数）
# ═══════════════════════════════════════════════════════════════════════════════

def find_via_path_3d(
    start: tuple[int, int],
    end: tuple[int, int],
    front_occupied: set[tuple[int, int]],
    back_occupied: set[tuple[int, int]],
    rows: int,
    cols: int,
    via_penalty: int = VIA_PENALTY,
    ghost_front: dict[tuple[int, int], int] | None = None,
    ghost_back: dict[tuple[int, int], int] | None = None,
) -> list[tuple[int, int, int]]:
    """
    3D A* 寻路：允许在两层之间通过过孔（via）切换。

    状态空间: (row, col, layer)，layer=0 表示正面，layer=1 表示反面。

    邻居扩展（每个状态最多 5 个邻居）：
      - 4 个同层移动（上下左右）: 代价 = 1
      - 1 个过孔切换（同坐标换层）: 代价 = via_penalty

    启发函数: 3D 曼哈顿距离 = |r-er| + |c-ec|（可容许，因为过孔不减少平面距离）

    :param start:          起点坐标 (row, col)
    :param end:            终点坐标 (row, col)
    :param front_occupied: 正面不可通行的格子集合
    :param back_occupied:  反面不可通行的格子集合
    :param rows:           网格行数
    :param cols:           网格列数
    :param via_penalty:    单次过孔的代价（越高则过孔越少）
    :param ghost_front:    正面软障碍字典 {cell: extra_cost}（幽灵模式，可选）
    :param ghost_back:     反面软障碍字典 {cell: extra_cost}（幽灵模式，可选）
    :return:               成功返回 [(r,c,layer), ...]（含起终点），失败返回 []
    """
    import heapq

    sr, sc = start
    er, ec = end

    if start == end:
        return [(sr, sc, 0)]

    if ghost_front is None:
        ghost_front = {}
    if ghost_back is None:
        ghost_back = {}

    # 将每层的占用集合和软障碍打包
    occupied_by_layer = [front_occupied, back_occupied]
    ghost_by_layer = [ghost_front, ghost_back]

    def h(r: int, c: int, layer: int) -> int:
        """3D 启发：平面曼哈顿距离（过孔不减少平面距离，故可容许）"""
        return abs(r - er) + abs(c - ec)

    dirs_2d = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    # g_score: (r, c, layer) → cost
    g_score: dict[tuple[int, int, int], int] = {(sr, sc, 0): 0}
    came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    closed: set[tuple[int, int, int]] = set()

    counter = 0
    heap = [(h(sr, sc, 0), counter, sr, sc, 0)]

    found = False
    goal_state: tuple[int, int, int] | None = None

    while heap:
        _, _, cr, cc, cl = heapq.heappop(heap)

        if (cr, cc, cl) in closed:
            continue

        # 到达终点（任意层均可）
        if cr == er and cc == ec:
            found = True
            goal_state = (cr, cc, cl)
            break

        closed.add((cr, cc, cl))

        # ── 同层移动（4 个方向）──
        for dr, dc in dirs_2d:
            nr, nc = cr + dr, cc + dc

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            neighbor = (nr, nc, cl)
            if (nr, nc, cl) in closed:
                continue

            # 检查目标层该格是否硬障碍
            if (nr, nc) in occupied_by_layer[cl]:
                continue

            # 步进代价 = 1 + 幽灵软障碍代价（若存在）
            step_cost = 1
            if (nr, nc) in ghost_by_layer[cl]:
                step_cost += ghost_by_layer[cl][(nr, nc)]

            new_g = g_score[(cr, cc, cl)] + step_cost
            if new_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = new_g
                came_from[neighbor] = (cr, cc, cl)
                counter += 1
                heapq.heappush(heap, (new_g + h(nr, nc, cl), counter, nr, nc, cl))

        # ── 过孔切换（换层）──
        other_layer = 1 - cl
        via_neighbor = (cr, cc, other_layer)

        if via_neighbor not in closed:
            # 过孔需要目标层该格不是硬障碍
            if (cr, cc) not in occupied_by_layer[other_layer]:
                step_cost = via_penalty
                # 幽灵模式下过孔点也可能有软障碍
                if (cr, cc) in ghost_by_layer[other_layer]:
                    step_cost += ghost_by_layer[other_layer][(cr, cc)]

                new_g = g_score[(cr, cc, cl)] + step_cost
                if new_g < g_score.get(via_neighbor, float("inf")):
                    g_score[via_neighbor] = new_g
                    came_from[via_neighbor] = (cr, cc, cl)
                    counter += 1
                    heapq.heappush(heap, (new_g + h(cr, cc, other_layer), counter,
                                          cr, cc, other_layer))

    if not found or goal_state is None:
        return []

    # ── 回溯重建 3D 路径 ──
    path_3d: list[tuple[int, int, int]] = []
    cur: tuple[int, int, int] | None = goal_state
    while cur is not None:
        path_3d.append(cur)
        cur = came_from.get(cur)
    path_3d.reverse()
    return path_3d


def count_vias_in_path(path_3d: list[tuple[int, int, int]]) -> int:
    """统计 3D 路径中的过孔数量（相邻两点同坐标不同层即为一个过孔）"""
    vias = 0
    for i in range(1, len(path_3d)):
        prev_r, prev_c, prev_l = path_3d[i - 1]
        curr_r, curr_c, curr_l = path_3d[i]
        if prev_r == curr_r and prev_c == curr_c and prev_l != curr_l:
            vias += 1
    return vias


def project_3d_to_2d(path_3d: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    """将 3D 路径投影为 2D 路径（合并连续相同坐标的不同层）"""
    if not path_3d:
        return []
    result: list[tuple[int, int]] = []
    for r, c, layer in path_3d:
        p = (r, c)
        if not result or result[-1] != p:
            result.append(p)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  双层布线主函数
# ═══════════════════════════════════════════════════════════════════════════════

def solve_double_layer(case: Case) -> dict[int, list]:
    """
    双层布线：正面 → 反面 → 过孔穿越 三阶段算法。

    Phase 1: 正面单层布线
        调用单层求解器在正面独立布线。

    Phase 2: 反面单层布线
        对 Phase 1 未布通的线网，在反面独立布线。

    Phase 3: 过孔穿越布线
        对仍未布通的线网，使用 3D A* 寻路允许过孔穿越。
        先尝试严格模式（不冲突），失败则尝试幽灵模式（允许穿越已有路径），
        幽灵模式成功后拆除冲突线网并尝试重布。

    :param case: 布线题目
    :return:     {net_id: [(r,c), ...], ...}  仅包含成功布线的线网
    """
    rows, cols = case.rows, case.cols

    # ── 构建 via 障碍集合（双面共享）──
    via_set: set[tuple[int, int]] = set()
    for via in case.vias:
        via_set.add((via[0], via[1]))

    # ── 所有线网端点（双面共享，保护不被穿越）──
    all_endpoints: set[tuple[int, int]] = set()
    for net in case.nets:
        for ep in net.endpoints:
            all_endpoints.add((ep[0], ep[1]))

    net_by_id = {n.id: n for n in case.nets}
    total_nets = len(case.nets)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 1: 正面单层布线
    # ═══════════════════════════════════════════════════════════════════

    front_case = Case(rows=rows, cols=cols, vias=case.vias, nets=case.nets)
    front_paths = sl_solve(front_case)

    # ── 构建正面已占用集合 ──
    front_occupied: set[tuple[int, int]] = set(via_set)
    for ep in all_endpoints:
        front_occupied.add(ep)
    for path in front_paths.values():
        for cell in path:
            front_occupied.add(cell)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 2: 反面单层布线（剩余线网）
    # ═══════════════════════════════════════════════════════════════════
    routed_ids = set(front_paths.keys())
    remaining_nets = [n for n in case.nets if n.id not in routed_ids]

    back_paths: dict[int, list] = {}

    if remaining_nets:
        back_case = Case(rows=rows, cols=cols, vias=case.vias, nets=remaining_nets)
        back_paths = sl_solve(back_case)
        routed_ids.update(back_paths.keys())
    else:
        back_paths = {}

    # ── 构建反面已占用集合 ──
    back_occupied: set[tuple[int, int]] = set(via_set)
    for ep in all_endpoints:
        back_occupied.add(ep)
    for path in back_paths.values():
        for cell in path:
            back_occupied.add(cell)

    # ═══════════════════════════════════════════════════════════════════
    #  Phase 3: 过孔穿越布线（最终剩余线网）
    # ═══════════════════════════════════════════════════════════════════
    final_remaining = [n for n in case.nets if n.id not in routed_ids]

    via_paths_2d: dict[int, list] = {}       # 2D 投影路径（返回值）
    via_paths_3d: dict[int, list] = {}       # 3D 完整路径（含层信息）
    via_count_per_net: dict[int, int] = {}   # 每条线网的过孔数

    if final_remaining:
        # 按曼哈顿距离排序，短线优先
        final_remaining.sort(
            key=lambda net: abs(net.endpoints[0][0] - net.endpoints[1][0])
                          + abs(net.endpoints[0][1] - net.endpoints[1][1])
        )

        for idx, net in enumerate(final_remaining):
            (sr, sc), (er, ec) = net.endpoints
            start = (sr, sc)
            end = (er, ec)

            # 临时移除本线网端点（允许作为路径起终点）
            front_occupied.discard(start)
            front_occupied.discard(end)
            back_occupied.discard(start)
            back_occupied.discard(end)

            # ── 步骤 1: 严格 3D A*（不冲突任何已有路径）──
            best_path_3d = find_via_path_3d(
                start, end,
                front_occupied, back_occupied,
                rows, cols,
                via_penalty=VIA_PENALTY
            )

            # ── 步骤 2: 过孔惩罚迭代优化（尝试减少过孔数）──
            if best_path_3d:
                best_vias = count_vias_in_path(best_path_3d)
                current_penalty = VIA_PENALTY * 2
                for _ in range(MAX_VIA_ITERATIONS - 1):
                    if best_vias == 0:
                        break  # 已零过孔，无需继续
                    candidate = find_via_path_3d(
                        start, end,
                        front_occupied, back_occupied,
                        rows, cols,
                        via_penalty=current_penalty
                    )
                    if candidate:
                        c_vias = count_vias_in_path(candidate)
                        if c_vias < best_vias:
                            best_path_3d = candidate
                            best_vias = c_vias
                        elif c_vias == best_vias and len(candidate) < len(best_path_3d):
                            # 同样过孔数但路径更短，选择更短的
                            best_path_3d = candidate
                    current_penalty = min(current_penalty * 2, VIA_PENALTY_MAX)

            # ── 步骤 3: 严格模式失败 → 幽灵模式 ──
            if not best_path_3d:
                # 构建幽灵软障碍：已布线网占用的格子，穿越需付出额外代价
                ghost_f: dict[tuple[int, int], int] = {}
                ghost_b: dict[tuple[int, int], int] = {}

                for path in front_paths.values():
                    for cell in path:
                        if cell != start and cell != end:
                            ghost_f[cell] = GHOST_VIA_PENALTY
                for path in back_paths.values():
                    for cell in path:
                        if cell != start and cell != end:
                            ghost_b[cell] = GHOST_VIA_PENALTY
                # 也加入 Phase 3 中已布线网的路径
                for path in via_paths_2d.values():
                    for cell in path:
                        if cell != start and cell != end:
                            ghost_f[cell] = GHOST_VIA_PENALTY
                            ghost_b[cell] = GHOST_VIA_PENALTY

                best_path_3d = find_via_path_3d(
                    start, end,
                    front_occupied, back_occupied,
                    rows, cols,
                    via_penalty=VIA_PENALTY,
                    ghost_front=ghost_f,
                    ghost_back=ghost_b,
                )

                if best_path_3d:
                    # ── 幽灵路径踩到的冲突线网 ──
                    ghost_set_2d = set(project_3d_to_2d(best_path_3d))
                    conflict_ids: set[int] = set()

                    for nid, existing_path in front_paths.items():
                        for cell in existing_path:
                            if cell in ghost_set_2d:
                                conflict_ids.add(nid)
                                break
                    for nid, existing_path in back_paths.items():
                        for cell in existing_path:
                            if cell in ghost_set_2d:
                                conflict_ids.add(nid)
                                break

                    # ── 拆除冲突线网 ──
                    for nid in conflict_ids:
                        if nid in front_paths:
                            old_p = front_paths.pop(nid)
                            for cell in old_p:
                                front_occupied.discard(cell)
                        if nid in back_paths:
                            old_p = back_paths.pop(nid)
                            for cell in old_p:
                                back_occupied.discard(cell)
                        routed_ids.discard(nid)

                    # ── 尝试重布被拆线网（先正面 → 再反面 → 最后过孔穿越）──
                    still_failed: list[int] = []
                    for nid in sorted(conflict_ids):
                        victim = net_by_id.get(nid)
                        if victim is None:
                            still_failed.append(nid)
                            continue

                        (vsr, vsc), (ver, vec) = victim.endpoints
                        vs, ve = (vsr, vsc), (ver, vec)
                        rerouted = False

                        # 尝试 1: 正面标准 A*
                        front_occupied.discard(vs)
                        front_occupied.discard(ve)
                        reroute_p = sl_find_single_path(vs, ve, front_occupied, rows, cols)
                        if reroute_p:
                            for cell in reroute_p:
                                front_occupied.add(cell)
                            front_paths[nid] = reroute_p
                            routed_ids.add(nid)
                            front_occupied.add(vs)
                            front_occupied.add(ve)
                            continue

                        # 尝试 2: 反面标准 A*
                        back_occupied.discard(vs)
                        back_occupied.discard(ve)
                        reroute_p = sl_find_single_path(vs, ve, back_occupied, rows, cols)
                        if reroute_p:
                            for cell in reroute_p:
                                back_occupied.add(cell)
                            back_paths[nid] = reroute_p
                            routed_ids.add(nid)
                            back_occupied.add(vs)
                            back_occupied.add(ve)
                            front_occupied.add(vs)
                            front_occupied.add(ve)
                            continue

                        # 尝试 3: 过孔穿越 3D A*（允许被拆线网打过孔）
                        via_reroute_3d = find_via_path_3d(
                            vs, ve,
                            front_occupied, back_occupied,
                            rows, cols,
                            via_penalty=VIA_PENALTY
                        )
                        if via_reroute_3d:
                            # 过孔迭代优化
                            best_vias = count_vias_in_path(via_reroute_3d)
                            cur_pen = VIA_PENALTY * 2
                            for _ in range(MAX_VIA_ITERATIONS - 1):
                                if best_vias == 0:
                                    break
                                cand = find_via_path_3d(
                                    vs, ve,
                                    front_occupied, back_occupied,
                                    rows, cols, via_penalty=cur_pen
                                )
                                if cand:
                                    cv = count_vias_in_path(cand)
                                    if cv < best_vias:
                                        via_reroute_3d = cand
                                        best_vias = cv
                                    elif cv == best_vias and len(cand) < len(via_reroute_3d):
                                        via_reroute_3d = cand
                                cur_pen = min(cur_pen * 2, VIA_PENALTY_MAX)

                            for r, c, layer in via_reroute_3d:
                                if layer == 0:
                                    front_occupied.add((r, c))
                                else:
                                    back_occupied.add((r, c))
                            via_paths_2d[nid] = project_3d_to_2d(via_reroute_3d)
                            via_paths_3d[nid] = via_reroute_3d
                            via_count_per_net[nid] = best_vias
                            routed_ids.add(nid)
                            back_occupied.add(vs)
                            back_occupied.add(ve)
                            front_occupied.add(vs)
                            front_occupied.add(ve)
                            continue

                        # 三重尝试均失败
                        front_occupied.add(vs)
                        front_occupied.add(ve)
                        back_occupied.add(vs)
                        back_occupied.add(ve)
                        still_failed.append(nid)

                    # 如果有被拆线网重布失败，放弃当前幽灵路径
                    if still_failed:
                        # 回滚：放弃该线网的幽灵路径
                        best_path_3d = []
                        # 注意：已重布成功的被拆线网保留（它们找到了更好的路径）

            # ── 步骤 4: 提交路径 ──
            if best_path_3d:
                # 将路径的各段分别标记到对应层
                for r, c, layer in best_path_3d:
                    if layer == 0:
                        front_occupied.add((r, c))
                    else:
                        back_occupied.add((r, c))

                path_2d = project_3d_to_2d(best_path_3d)
                via_paths_2d[net.id] = path_2d
                via_paths_3d[net.id] = best_path_3d
                n_vias = count_vias_in_path(best_path_3d)
                via_count_per_net[net.id] = n_vias
                routed_ids.add(net.id)
            else:
                pass

            # 恢复端点保护
            front_occupied.add(start)
            front_occupied.add(end)
            back_occupied.add(start)
            back_occupied.add(end)

    # ═══════════════════════════════════════════════════════════════════
    #  汇总结果
    # ═══════════════════════════════════════════════════════════════════
    all_paths: dict[int, list] = {}
    all_paths.update(front_paths)
    all_paths.update(back_paths)
    all_paths.update(via_paths_2d)

    # ── 导出图层元数据（供 app.py 可视化使用）──
    _export_layer_data(front_paths, back_paths, via_paths_2d, via_paths_3d)

    return all_paths


def _export_layer_data(
    front_paths: dict[int, list],
    back_paths: dict[int, list],
    via_paths_2d: dict[int, list],
    via_paths_3d: dict[int, list],
) -> None:
    """将双层布线图层信息写入模块全局变量 _layer_data，供 app.py 读取。"""
    global _layer_data
    via_pts: dict[int, list] = {}
    for nid, path_3d in via_paths_3d.items():
        pts = []
        for i in range(1, len(path_3d)):
            pr, pc, pl = path_3d[i - 1]
            cr, cc, cl = path_3d[i]
            if pr == cr and pc == cc and pl != cl:
                pts.append([pr, pc])
        if pts:
            via_pts[nid] = pts

    _layer_data = {
        "front_nets": list(front_paths.keys()),
        "back_nets": list(back_paths.keys()),
        "via_nets": list(via_paths_2d.keys()),
        "via_points": via_pts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  主入口：solve(case) — app.py 调用的接口
# ═══════════════════════════════════════════════════════════════════════════════

def solve(case: Case) -> dict[int, list]:
    """
    双层布线求解器入口。

    【输入】 case.rows/cols/vias/nets
    【输出】 {net_id: [(r,c), ...], ...}  仅包含成功布线的线网

    可通过修改文件顶部 SINGLE_LAYER_SOLVER 切换底层单层算法。
    """
    return solve_double_layer(case)


# ═══════════════════════════════════════════════════════════════════════════════
#  以下为测试与可视化辅助代码（与单层文件保持兼容）
# ═══════════════════════════════════════════════════════════════════════════════

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
        min_manhattan = (rows + cols) // 3

    all_cells = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(all_cells)
    vias_set = set()
    for r, c in all_cells:
        if len(vias_set) >= num_vias:
            break
        vias_set.add((r, c))

    vias = [list(v) for v in sorted(vias_set)]
    used = set(vias_set)
    nets = []
    for i in range(num_nets):
        for _ in range(1000):
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
            nets.append(Net(id=i, endpoints=[[r1, c1], [r2, c2]],
                           color=COLORS[i % len(COLORS)]))
            break
        else:
            print(f"警告：只能放置 {len(nets)} 条线网（请求 {num_nets} 条）")
            break

    return Case(rows=rows, cols=cols, vias=vias, nets=nets)


def visualize(case: Case, paths: dict[int, list], save_path=None):
    """用 matplotlib 绘制布线结果。"""
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

    for r in range(case.rows + 1):
        ax.axhline(r - 0.5, color="#1a1a25", linewidth=0.3)
    for c in range(case.cols + 1):
        ax.axvline(c - 0.5, color="#1a1a25", linewidth=0.3)

    for r, c in case.vias:
        rect = patches.FancyBboxPatch((c - 0.4, r - 0.4), 0.8, 0.8,
            boxstyle="round,pad=0.05", facecolor="#1e1e2a", edgecolor="#333", linewidth=0.5)
        ax.add_patch(rect)
        ax.plot([c - 0.25, c + 0.25], [r - 0.25, r + 0.25], color="#444", linewidth=0.8)
        ax.plot([c + 0.25, c - 0.25], [r - 0.25, r + 0.25], color="#444", linewidth=0.8)

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
            if ei == 0:
                circle = plt.Circle((pc, pr), 0.35, facecolor=color, edgecolor="white",
                                     linewidth=0.8, alpha=0.9, zorder=5)
            else:
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
        f"Double-Layer Routability: {routed_count}/{total}  |  {case.rows}×{case.cols}  |  {len(case.vias)} vias",
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

    # 解析 --solver 参数（允许命令行覆盖单层求解器）
    global SINGLE_LAYER_SOLVER, _sl, sl_find_single_path, sl_solve, sl_find_ghost_path
    if "--solver" in args:
        idx = args.index("--solver")
        solver_name = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
        SINGLE_LAYER_SOLVER = solver_name
        _solver_path = os.path.join(_THIS_DIR, SINGLE_LAYER_SOLVER)
        _spec = importlib.util.spec_from_file_location("single_layer_solver", _solver_path)
        _sl = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_sl)
        sl_find_single_path = _sl.find_single_path
        sl_solve = _sl.solve
        sl_find_ghost_path = getattr(_sl, "find_ghost_path", None)
        print(f"[双层布线] 已切换单层求解器: {SINGLE_LAYER_SOLVER}")

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
            print("请使用 app.py 查看结果：python app.py A_star_double_layer.py")
        else:
            visualize(case, paths, save_path=viz_path)


if __name__ == "__main__":
    main()
