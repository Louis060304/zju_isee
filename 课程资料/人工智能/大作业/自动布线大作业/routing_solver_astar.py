"""
PCB Routability Analyzer — Single-pass A* baseline
====================================================
Solves the routing problem with one greedy A* pass:
route each net in order, treating already-routed cells as hard obstacles.

Usage:
    python routing_solver_astar.py                    # run with built-in example
    python routing_solver_astar.py case.json          # load a case file
    python routing_solver_astar.py --generate 40 20   # generate 40×40 grid, 20 nets
    python routing_solver_astar.py case.json --export result.json
"""

import json
import heapq
import random
import sys
import os
from dataclasses import dataclass

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Net:
    id: int
    endpoints: list  # [[r1, c1], [r2, c2]]
    color: str = ""

@dataclass
class Case:
    rows: int
    cols: int
    vias: list   # [[r, c], ...]
    nets: list   # [Net, ...]

    def to_dict(self):
        return {
            "grid": {"rows": self.rows, "cols": self.cols},
            "vias": self.vias,
            "nets": [{"id": n.id, "color": n.color, "endpoints": n.endpoints} for n in self.nets],
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
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"Exported to {path}")

    @staticmethod
    def from_json(path: str) -> "Case":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        g = data["grid"]
        nets = [Net(id=n["id"], endpoints=n["endpoints"], color=n.get("color", ""))
                for n in data["nets"]]
        return Case(rows=g["rows"], cols=g["cols"], vias=data["vias"], nets=nets)


# ─── Routing algorithm ────────────────────────────────────────────────────────

DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]

def solve(case: Case) -> dict[int, list]:
    """Route nets one by one using A*. Already-routed cells are hard obstacles."""
    blocked = set(map(tuple, case.vias))  # vias + cells claimed by routed nets

    paths = {}
    for net in case.nets:
        (sr, sc), (er, ec) = net.endpoints

        # A* from (sr, sc) to (er, ec)
        if (sr, sc) == (er, ec):
            paths[net.id] = [(sr, sc)]
            continue

        h = lambda r, c: abs(r - er) + abs(c - ec)
        g_score = {(sr, sc): 0}
        came_from = {}
        counter = 0
        heap = [(h(sr, sc), counter, sr, sc)]
        closed = set()

        found = False
        while heap:
            _, _, cr, cc = heapq.heappop(heap)
            if (cr, cc) in closed:
                continue
            if cr == er and cc == ec:
                found = True
                break
            closed.add((cr, cc))
            for dr, dc in DIRS:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < case.rows and 0 <= nc < case.cols):
                    continue
                if (nr, nc) in closed or (nr, nc) in blocked:
                    continue
                ng = g_score[(cr, cc)] + 1
                if ng < g_score.get((nr, nc), float("inf")):
                    g_score[(nr, nc)] = ng
                    came_from[(nr, nc)] = (cr, cc)
                    counter += 1
                    heapq.heappush(heap, (ng + h(nr, nc), counter, nr, nc))

        if not found:
            continue  # net cannot be routed, skip it

        # Reconstruct path
        path = []
        cur = (er, ec)
        while cur is not None:
            path.append(cur)
            cur = came_from.get(cur)
        path.reverse()

        # Commit: mark all path cells as blocked for subsequent nets
        for cell in path:
            blocked.add(cell)
        paths[net.id] = path

    return paths


# ─── Provided: case generator, visualization, CLI ────────────────────────────

COLORS = [
    "#ef4444", "#3b82f6", "#14b8a6", "#f59e0b", "#a855f7",
    "#ec4899", "#f97316", "#22c55e", "#1e3a5f", "#92400e",
    "#06b6d4", "#84cc16", "#e11d48", "#7c3aed", "#0ea5e9",
    "#d946ef", "#65a30d", "#dc2626", "#2563eb", "#059669",
    "#ca8a04", "#9333ea", "#db2777", "#0891b2", "#c2410c",
]

def generate_case(rows=40, cols=40, num_nets=20, num_vias=0, seed=None,
                  min_manhattan=None) -> Case:
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
            nets.append(Net(id=i, endpoints=[[r1, c1], [r2, c2]], color=COLORS[i % len(COLORS)]))
            break
        else:
            print(f"Warning: could only place {len(nets)} nets (requested {num_nets})")
            break

    return Case(rows=rows, cols=cols, vias=vias, nets=nets)


def visualize(case: Case, paths: dict[int, list], save_path=None):
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("matplotlib not installed — pip install matplotlib")
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
        f"Routability: {routed_count}/{total}  |  {case.rows}×{case.cols}  |  {len(case.vias)} vias",
        color=title_color, fontsize=14, fontweight="bold", pad=12)
    ax.tick_params(colors="#333", labelsize=6)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"Saved visualization to {save_path}")
    else:
        plt.show()


def builtin_example() -> Case:
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
    total = len(case.nets)
    routed = len(paths)
    print(f"\n{'='*50}")
    print(f"  Result: {routed}/{total} nets routed")
    print(f"{'='*50}")
    for net in case.nets:
        path = paths.get(net.id)
        manhattan = (abs(net.endpoints[0][0] - net.endpoints[1][0])
                   + abs(net.endpoints[0][1] - net.endpoints[1][1]))
        if path:
            print(f"  Net {net.id:2d}  OK  len={len(path):3d}  (manhattan={manhattan})")
        else:
            print(f"  Net {net.id:2d}  --  FAILED  (manhattan={manhattan})")
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
        print(f"Generated {size}×{size}, {num_nets} nets, {num_vias} vias"
              + (f", seed={seed}" if seed else ""))
    elif len(args) >= 1 and os.path.isfile(args[0]):
        case = Case.from_json(args[0])
        print(f"Loaded from {args[0]}")
    else:
        case = builtin_example()
        print("Using built-in 20×20 example")

    paths = solve(case)
    print_results(case, paths)

    if export_path:
        result_data = case.to_dict()
        result_data["solver_result"] = {
            "routed_count": len(paths),
            "total": len(case.nets),
            "paths": {str(k): v for k, v in paths.items()},
        }
        with open(export_path, "w") as f:
            json.dump(result_data, f, indent=2)
        print(f"Exported result to {export_path}")

    if not no_viz:
        if case.rows * case.cols > 50 * 50:
            print(f"网格较大（{case.rows}×{case.cols}），跳过本地可视化。")
            print("请使用 app.py 查看结果：python app.py routing_solver_astar.py")
        else:
            visualize(case, paths, save_path=viz_path)


if __name__ == "__main__":
    main()
