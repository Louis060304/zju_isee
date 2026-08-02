import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import heapq

# ── 网格尺寸 ──────────────────────────────────────────────────────────────────
ROWS, COLS = 20, 20

# ── 初始网格（0=空闲, 1=障碍）────────────────────────────────────────────────
grid_base = np.zeros((ROWS, COLS), dtype=int)

# 障碍物：每条网络所在行设置两段障碍，强制 A* 绕行
obstacles = [
    # Net 1 所在行 (row 1)
    (1, 6), (1, 7), (1, 8), (1, 9),
    (1, 14), (1, 15),
    # Net 2 所在行 (row 4)
    (4, 5), (4, 6),
    (4, 11), (4, 12), (4, 13), (4, 14),
    # Net 3 所在行 (row 8)
    (8, 4), (8, 5), (8, 6), (8, 7),
    (8, 14), (8, 15),
    # Net 4 所在行 (row 12)
    (12, 3), (12, 4),
    (12, 8), (12, 9), (12, 10), (12, 11),
    # Net 5 所在行 (row 16)
    (16, 5), (16, 6), (16, 7), (16, 8),
    (16, 13), (16, 14),
    # Net 6 所在行 (row 19)
    (19, 6), (19, 7),
    (19, 13), (19, 14), (19, 15), (19, 16),
]
for r, c in obstacles:
    grid_base[r, c] = 1

# ── 6 对引脚（均为同行左右端点，保证可达性）──────────────────────────────────
# 每对引脚 (start, end)：start=(row, col=0), end=(row, col=19)
pin_pairs = [
    ((1,  0), (2,  6)),  # Net 1
    ((4,  0), (1,  19)),  # Net 2
    ((10, 0), (16,  17)),  # Net 3
    ((12, 6), (12, 13)),  # Net 4
    ((16, 0), (13, 16)),  # Net 5
    ((19, 0), (5, 18)),  # Net 6
]

# 各网络对应可视化颜色
PATH_COLORS = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4']

print(f"网格大小: {ROWS} × {COLS}")
print(f"障碍物数量: {len(obstacles)}")
print(f"引脚对数量: {len(pin_pairs)}")

def heuristic(a, b):
    """曼哈顿距离启发函数：估算从 a 到 b 的最小步数。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(node, grid):
    """
    返回 node 的 4-连通可通行邻居（仅 grid 值为 0 的格子）。

    Parameters
    ----------
    node : tuple(int, int)  当前坐标 (row, col)
    grid : np.ndarray       当前网格状态

    Returns
    -------
    list of tuple(int, int)
    """
    r, c = node
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < grid.shape[0] and 0 <= nc < grid.shape[1]:
            if grid[nr, nc] == 0:
                neighbors.append((nr, nc))
    return neighbors


def reconstruct_path(came_from, current):
    """
    从 came_from 字典回溯，还原从起点到 current 的完整路径。

    Parameters
    ----------
    came_from : dict  {node: parent_node}
    current   : tuple 终点坐标

    Returns
    -------
    list of tuple(int, int)  路径节点列表（含起止点，顺序从起到终）
    """
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    CORE BLOCK 1：A* 搜索算法                                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def astar(grid, start, end):
    """
    A* 路径搜索。

    Parameters
    ----------
    grid  : np.ndarray        当前网格（0=可通行，非0=不可通行）
    start : tuple(int, int)   起始引脚坐标 (row, col)
    end   : tuple(int, int)   目标引脚坐标 (row, col)

    Returns
    -------
    list of (row, col) 或 None
        找到路径则返回节点列表（含起止点），否则返回 None
    """
    # TODO: 请在此处补全 A* 算法实现
    # 提示：
    # 1. 初始化 open_set（最小堆），放入起点
    open_set = []
    heapq.heappush(open_set, (heuristic(start, end), 0, start)) #采用堆模块达到最小堆功能，放入起点，（f_score,g_score,节点数）
    
    # 2. 初始化 came_from 字典和 g_score 字典
    came_from = {}
    g_score = {(r, c): float('inf') for r in range(ROWS) for c in range(COLS)} #遍历网格中的行和列
    g_score[start] = 0
    
    # 3. 循环从 open_set 中取出 f 值最小的节点
    while open_set:
        current_f, current_g, current = heapq.heappop(open_set)
        
        # 4. 若到达终点，调用 reconstruct_path 返回路径
        if current == end:
            return reconstruct_path(came_from, current)
            
        # 5. 否则展开邻居，更新 g_score 和 open_set
        for neighbor in get_neighbors(current, grid):
            next_g_score = current_g + 1 #下一步的g_score
            if next_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = next_g_score
                f_score = next_g_score + heuristic(neighbor, end)
                heapq.heappush(open_set, (f_score, next_g_score, neighbor)) #若新的路径更优，则进行替代

    # 6. 若 open_set 为空，返回 None
    return None

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    CORE BLOCK 1 END                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    CORE BLOCK 2：顺序布线主流程                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def route_all_pairs(grid_init, pin_pairs):
    """
    依次对每对引脚执行 A* 布线。
    每条线布通后将路径标记到网格，确保后续线不重叠。

    Parameters
    ----------
    grid_init : np.ndarray        初始网格（不会被修改）
    pin_pairs : list of (s, e)    引脚对列表

    Returns
    -------
    grid_routed : np.ndarray  最终网格（已标记所有路径）
    paths       : list        每对引脚对应的路径节点列表
    """
    # TODO: 请在此处补全布线主流程
    # 提示：
    # 1. 复制初始网格
    grid_routed = grid_init.copy()
    paths = []
    
    # 2. 对每对引脚循环：
    for idx, (start, end) in enumerate(pin_pairs):
    #    a. 将起止引脚格临时置为 0
        grid_routed[start] = 0
        grid_routed[end] = 0
    #    b. 调用 astar 求路径
        path = astar(grid_routed, start, end)
    #    c. 若路径为 None，抛出异常
        if path is None:
            raise RuntimeError(f"Net {idx+1} ({start} -> {end})异常！")
    #    d. 将路径上的格子标记为 idx+2
         path_val = idx + 2
        for (r, c) in path:
            grid_routed[(r, c)] = path_val
    #    e. 打印布线信息
        paths.append(path)
        print(f"Net {idx+1} 布线完成，路径长: {len(path)}")

    # 3. 返回最终网格和所有路径
    return grid_routed, paths
    
# 执行布线
grid_routed, all_paths = route_all_pairs(grid_base, pin_pairs)
print(f"\n全部 {len(pin_pairs)} 对引脚布线完成！")

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    CORE BLOCK 2 END                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def visualize_routing(grid_base, pin_pairs, all_paths, path_colors):
    """绘制初始环境与 A* 布线结果的对比图。"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('single A* auto routing result', fontsize=15, fontweight='bold')

    # ── 左图：初始环境 ────────────────────────────────────────────────────────
    ax = axes[0]
    ax.set_facecolor('#f5f5f5')

    # 绘制障碍物
    for r in range(ROWS):
        for c in range(COLS):
            if grid_base[r, c] == 1:
                ax.add_patch(plt.Rectangle(
                    (c - 0.5, r - 0.5), 1, 1,
                    color='#444444', zorder=2
                ))

    # 绘制引脚
    for idx, (s, e) in enumerate(pin_pairs):
        color = path_colors[idx]
        ax.plot(s[1], s[0], 's', color=color, markersize=11,
                markeredgecolor='black', markeredgewidth=0.7, zorder=5)
        ax.plot(e[1], e[0], 'D', color=color, markersize=11,
                markeredgecolor='black', markeredgewidth=0.7, zorder=5)
        ax.text(s[1], s[0], f'{idx+1}S', ha='center', va='center',
                fontsize=5.5, color='white', fontweight='bold', zorder=6)
        ax.text(e[1], e[0], f'{idx+1}E', ha='center', va='center',
                fontsize=5.5, color='white', fontweight='bold', zorder=6)

    ax.set_xlim(-0.5, COLS - 0.5)
    ax.set_ylim(ROWS - 0.5, -0.5)
    ax.set_xticks(range(COLS))
    ax.set_yticks(range(ROWS))
    ax.tick_params(labelsize=6)
    ax.grid(True, linewidth=0.4, color='#cccccc', zorder=0)
    ax.set_title('Original (obstacle + pin)', fontsize=12)
    ax.set_xlabel('Col', fontsize=9)
    ax.set_ylabel('Row', fontsize=9)

    # ── 右图：布线结果 ────────────────────────────────────────────────────────
    ax2 = axes[1]
    ax2.set_facecolor('#f5f5f5')

    # 绘制障碍物
    for r in range(ROWS):
        for c in range(COLS):
            if grid_base[r, c] == 1:
                ax2.add_patch(plt.Rectangle(
                    (c - 0.5, r - 0.5), 1, 1,
                    color='#444444', zorder=2
                ))

    # 绘制路径
    for idx, path in enumerate(all_paths):
        color = path_colors[idx]
        rs = [p[0] for p in path]
        cs = [p[1] for p in path]
        ax2.plot(cs, rs, '-', color=color, linewidth=3.5,
                 alpha=0.85, zorder=3, solid_capstyle='round')

    # 绘制引脚（覆盖在路径上方）
    for idx, (s, e) in enumerate(pin_pairs):
        color = path_colors[idx]
        ax2.plot(s[1], s[0], 's', color=color, markersize=11,
                 markeredgecolor='black', markeredgewidth=0.7, zorder=7)
        ax2.plot(e[1], e[0], 'D', color=color, markersize=11,
                 markeredgecolor='black', markeredgewidth=0.7, zorder=7)

    # 图例
    legend_handles = [
        mpatches.Patch(color=path_colors[i], label=f'Net {i+1}')
        for i in range(len(pin_pairs))
    ]
    legend_handles.append(mpatches.Patch(color='#444444', label='Obstacle'))
    ax2.legend(handles=legend_handles, loc='upper right',
               fontsize=8, framealpha=0.9)

    ax2.set_xlim(-0.5, COLS - 0.5)
    ax2.set_ylim(ROWS - 0.5, -0.5)
    ax2.set_xticks(range(COLS))
    ax2.set_yticks(range(ROWS))
    ax2.tick_params(labelsize=6)
    ax2.grid(True, linewidth=0.4, color='#cccccc', zorder=0)
    ax2.set_title('A* routing result', fontsize=12)
    ax2.set_xlabel('Col', fontsize=9)
    ax2.set_ylabel('Row', fontsize=9)

    plt.tight_layout()
    plt.savefig('routing_result.png', dpi=150, bbox_inches='tight')
    plt.show()
    print('图像已保存为 routing_result.png')


visualize_routing(grid_base, pin_pairs, all_paths, PATH_COLORS)

print('=' * 55)
print(f'{"布线统计":^55}')
print('=' * 55)
total = 0
for i, (path, (s, e)) in enumerate(zip(all_paths, pin_pairs)):
    total += len(path)
    print(f"Net {i+1}  {str(s):>10} → {str(e):<10}  长度 = {len(path):3d}")
print('-' * 55)
print(f'总布线格数: {total}')
print(f'布通率: {len(all_paths)}/{len(pin_pairs)} = 100%')
print('=' * 55)