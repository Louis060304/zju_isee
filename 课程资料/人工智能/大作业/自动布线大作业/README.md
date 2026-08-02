# 文件说明

## 1 算法

### 单层布线算法： 
        A_star_rnr.py
        A_star_rnr_bidir.py
        A_star_rnr_immediate_reroute.py
        A_star_rnr_immediate_reroute_bidir.py
        A_star_global.py
        A_star_global_x.py
        A_star_global_x_bidir.py
    注：每个算法的核心思路都在对应文件开头

### 双层布线算法：
        A_star_double_layer.py
    注：双层布线算法以单层布线算法为基础，可以通过修改变量引用上述7种不同单层布线算法作为求解器

## 2 测试集
        benchmark_double_layer.py
        benchmark_global.py
        benchmark_rnr.py
    注：直接运行上述三个文件即可进行测试，自动输出测试结果
    注：测试集涵盖20*20-100*100的网络规模，以及低、中、高密度障碍状况，测试场景由种子随机生成

## 3 测试结果
    两个测试结果文件夹分别存放单层、双层布线测试结果，包含给定样例测试结果以及benchmark测试集测试结果


-------- 以下是大作业题目描述 ---------


# PCB 布线作业

## 任务描述

给定一个 PCB 网格，其中包含若干条线网（net），每条线网有两个端点需要连通。网格上存在部分不可穿越的 via 障碍。

**你的目标**：实现 `routing_solver_stu.py` 中的 `solve` 函数，目标PCB为`routing_22nets.json`，使尽可能多的线网成功布线。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `routing_solver_stu.py` | **你需要修改的文件**，在其中实现 `solve` 函数 |
| `routing_solver_astar.py` | 参考实现（单次 A* 贪心），可参考但不能直接提交 |
| `app.py` | 可视化工具，用于在真实 PCB 数据上测试你的实现 |
| `case.json` | 本地测试用例（50×50 网格，60 个过孔，15 条线网） |
| `routing_22nets.json` | 真实 PCB 题目数据（163×836 网格，22 条线网），供 `app.py` 使用 |

---

## 布线规则

- 坐标格式为 `(row, col)`，从左上角 `(0, 0)` 开始
- 移动方式：上、下、左、右，**4 连通**，不支持斜向移动
- Via 格子**不可进入**，也不能作为端点
- **不同线网之间不能共用任何格子**（包括端点）
- 目标：最大化成功布线的线网数量

---

## 你需要实现的接口

编辑 `routing_solver_stu.py`，实现以下函数：

```python
def solve(case: Case) -> dict[int, list]:
```

**输入** `case`：

| 属性 | 类型 | 说明 |
|------|------|------|
| `case.rows` | `int` | 网格行数 |
| `case.cols` | `int` | 网格列数 |
| `case.vias` | `list` | 障碍格子列表，每项为 `[r, c]` |
| `case.nets` | `list[Net]` | 线网列表 |
| `net.id` | `int` | 线网编号（0 起始） |
| `net.name` | `str` | 线网名称（如 `"CIF_CLKO"`） |
| `net.endpoints` | `list` | `[[r1, c1], [r2, c2]]`，起止端点 |

**输出**：`dict`，键为 `net.id`，值为路径（`[(r, c), ...]`，从起点到终点，含两端点）。
未能布线的线网**不出现**在返回值中。

**示例**：

```python
# 线网 id=2，端点 [0,0] → [0,3]
{2: [(0,0), (0,1), (0,2), (0,3)]}
```

---

## 本地测试

`routing_solver_stu.py` 内置了一个 20×20 的小示例，可直接运行：

```bash
python routing_solver_stu.py
```

支持的参数：

```bash
python routing_solver_stu.py                        # 内置 20×20 示例
python routing_solver_stu.py case.json              # 加载指定题目文件
python routing_solver_stu.py --generate 40 20       # 随机生成 40×40、20 条线网
python routing_solver_stu.py --no-viz               # 不显示可视化图形
```

---

## 可视化工具 (Interactive UI)

使用 `app.py` 提供了一个强大的基于 Web 的交互式路由可视化与编辑器。特别针对十几万量级的真实大尺度 PCB 数据进行了深度性能优化。

### 1. 启动工具

首先确保安装了 Flask 依赖，然后指定你的求解器脚本启动：

```bash
pip install flask
python app.py routing_solver_stu.py                   # 默认加载 routing_22nets.json
python app.py routing_solver_stu.py case.json          # 指定题目文件
python app.py routing_solver_astar.py				  # 用示例算法加载 routing_22nets.json
```

终端启动后，在浏览器中打开 `http://127.0.0.1:5000` 即可进入交互界面。

### 2. 画布操作与导航

工具纯前端处理渲染，支持在极高分辨率（如 836×163 大板）下流畅交互：
- **缩放 (Zoom)**：按住 `Ctrl` + `鼠标滚轮`，以鼠标为中心进行平滑缩放。
- **平移 (Pan)**：按住 `鼠标左键` 或 `鼠标中键（滚轮按键）` 并在画布上拖动，即可像地图一样在整个网格中自由平移。或者按住 `Shift + 左键` 拖动。
- **高亮观测**：在右侧的 **Net List (线网列表)** 中将鼠标悬停在特定线网上，视图会瞬间高亮该线网的端点（起止点）、虚线飞线（未布线时）和高亮实线（已布线时）。

### 3. 图纸编辑与交互

除了查看加载的数据外，你还可以完全在网页上自定义测试用例：
- **修改端点 (Move Endpoints)**：支持两种操作模式：
  1. **拖拽模式（推荐）**：直接在画布按住线网的 `起点` 或 `终点` 圆圈，拖放至目标空白格子。
  2. **点击模式**：点击圆圈选中端点（顶部会提示正在移动中），再到目标位置点击一下将其放下。
- **编辑盲孔/过孔 (Add/Remove Vias)**：点击顶部栏的 `+ Via` 按钮进入编辑模式，用鼠标在网格上涂抹点击，即可动态增加或删减黑色的被阻挡区域。编辑完成后再次点击 `✓ Done` 退出。
- **新建线网 (Add Net)**：点击底部或右侧的增一线网按钮，随机在画布空白处生成一组新的待连接端点。
- **删除线网**：在右侧 Net List 对应的网格项上点击红色的 `✕` 即可删除任意线网。

### 4. 求解与数据管理

- **自动布线 (▶ Solve)**：点击顶部工具栏的绿色运行按钮，会自动调用后端你编写的 `solver_xxx.py` 算法进行运算，并将布线结果实时画在网页上。
- **视图切换**：
  - **Routes**：显示正常的实线布线路径。
  - **Congestion**：热力图模式。颜色越红代表该区域的通道密度或走线拥挤度越高，用于辅助观察不可布线区域（Cut）。
- **生成随机数据 (Generate)**：点击顶部菜单可输入行列数、线网数等参数，一键生成随机地形检验算法健壮性。
- **导出/导入 (Export/Load)**：可通过 `Load Case` 上传本地 JSON 测试集，调整完毕后也可以 `Export` 导出当前画布所有的障碍与线路线网状态。

---

## 提交

提交修改后的 `routing_solver_stu.py`，确保：

1. `solve` 函数已实现（不再抛出 `NotImplementedError`）
2. 返回值格式正确：`{net_id: [(r, c), ...], ...}`
3. 路径满足布线规则（无冲突、不经过 via、4 连通）
