#!/usr/bin/env python3
"""
PCB Routability Analyzer — Interactive Local App
=================================================
Usage:
    pip install flask
    python app.py <solver.py> [puzzle.json]
    → Open http://localhost:5000 in your browser

    solver.py must define:
        solve(case) -> dict[int, list]
    puzzle.json defaults to routing_22nets.json if not specified.
"""

import json
import importlib.util
import sys
import os
from dataclasses import dataclass
from flask import Flask, request, jsonify

# ═══════════════════════════════════════════════
#  Load student solver
# ═══════════════════════════════════════════════

if len(sys.argv) < 2:
    print("Usage: python app.py <solver.py> [puzzle.json]")
    print("  solver.py must define: solve(case) -> dict[int, list]")
    sys.exit(1)

_solver_path = sys.argv.pop(1)  # remove before Flask sees it

_spec = importlib.util.spec_from_file_location("student_solver", _solver_path)
_mod = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_mod)
except Exception as e:
    print(f"Error loading {_solver_path}: {e}")
    sys.exit(1)

if not hasattr(_mod, "solve"):
    print(f"Error: {_solver_path} does not define a solve() function")
    sys.exit(1)

student_solve = _mod.solve
print(f"Loaded solver: {_solver_path}")

# ═══════════════════════════════════════════════
#  Data structures
# ═══════════════════════════════════════════════

@dataclass
class Net:
    id: int
    endpoints: list   # [[r1, c1], [r2, c2]]
    color: str = ""
    name: str = ""

@dataclass
class Case:
    rows: int
    cols: int
    vias: list        # [[r, c], ...]
    nets: list        # [Net, ...]

# ═══════════════════════════════════════════════
#  Load puzzle
# ═══════════════════════════════════════════════

_DEFAULT_PUZZLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routing_22nets.json")
if len(sys.argv) >= 2 and sys.argv[1].endswith(".json"):
    _PUZZLE_FILE = sys.argv.pop(1)
else:
    _PUZZLE_FILE = _DEFAULT_PUZZLE

with open(_PUZZLE_FILE, encoding="utf-8") as _f:
    _puzzle = json.load(_f)

PUZZLE_ROWS = _puzzle["grid"]["rows"]
PUZZLE_COLS = _puzzle["grid"]["cols"]
PUZZLE_VIAS = _puzzle["vias"]
PUZZLE_NETS = _puzzle["nets"]   # list of dicts: id/name/color/endpoints

print(f"Puzzle: {PUZZLE_ROWS}×{PUZZLE_COLS}, {len(PUZZLE_VIAS)} vias, {len(PUZZLE_NETS)} nets")

# ═══════════════════════════════════════════════
#  Helpers (channel density, congestion)
# ═══════════════════════════════════════════════

def congestion_map(vias, nets, rows, cols):
    vs = set((r, c) for r, c in vias)
    heat = [[0] * cols for _ in range(rows)]
    for net in nets:
        (sr, sc), (er, ec) = net["endpoints"]
        for r in range(min(sr, er), max(sr, er) + 1):
            for c in range(min(sc, ec), max(sc, ec) + 1):
                if (r, c) not in vs:
                    heat[r][c] += 1
    return heat

# ═══════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════

app = Flask(__name__)

@app.route("/")
def index():
    return HTML_PAGE

@app.route("/api/puzzle")
def api_puzzle():
    return jsonify({
        "rows": PUZZLE_ROWS,
        "cols": PUZZLE_COLS,
        "vias": PUZZLE_VIAS,
        "nets": PUZZLE_NETS,
    })

@app.route("/api/solve", methods=["POST"])
def api_solve():
    data = request.json
    rows, cols = data["rows"], data["cols"]
    nets_obj = [Net(id=n["id"], endpoints=n["endpoints"],
                    color=n.get("color", ""), name=n.get("name", ""))
                for n in data["nets"]]
    case = Case(rows=rows, cols=cols, vias=data["vias"], nets=nets_obj)

    try:
        paths = student_solve(case)
    except NotImplementedError as e:
        return jsonify({"error": f"NotImplementedError: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {e}"}), 500

    result_paths = {str(k): [list(p) for p in v] for k, v in paths.items()}
    heat = congestion_map(data["vias"], data["nets"], rows, cols)

    # ── 提取双层布线元数据（如果求解器导出了的话）──
    layer_data = None
    try:
        if hasattr(_mod, "_layer_data") and _mod._layer_data:
            raw = _mod._layer_data
            layer_data = {
                "front_nets": [int(k) for k in raw.get("front_nets", [])],
                "back_nets":  [int(k) for k in raw.get("back_nets", [])],
                "via_nets":   [int(k) for k in raw.get("via_nets", [])],
                "via_points": {str(k): [list(p) for p in v]
                               for k, v in raw.get("via_points", {}).items()},
            }
    except Exception:
        pass

    return jsonify({
        "routed_count": len(paths),
        "total": len(data["nets"]),
        "paths": result_paths,
        "congestion": heat,
        "layer_data": layer_data,
    })

# ═══════════════════════════════════════════════
#  Embedded HTML/JS/CSS
# ═══════════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⬡ Routability Analyzer</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&display=swap');
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'JetBrains Mono',monospace; background:#0a0a0f; color:#e0e0e8; min-height:100vh; padding:16px; }
  button, select { font-family:inherit; cursor:pointer; }
  .btn {
    padding:5px 12px; font-size:11px; border-radius:4px;
    border:1px solid #2a2a35; background:#14141f; color:#888;
    transition: all 0.15s;
  }
  .btn:hover { border-color:#555; color:#ccc; }
  .btn.active { border-color:#8b5cf6; background:#8b5cf620; color:#c4b5fd; }
  .btn.primary { border-color:#06b6d4; background:#06b6d420; color:#67e8f9; }
  .btn.warn { border-color:#f59e0b; background:#f59e0b20; color:#fbbf24; }
  .btn.danger { border-color:#ef4444; color:#f87171; }
  .btn:disabled { opacity:0.4; cursor:wait; }
  .header { display:flex; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap; }
  .logo { font-size:17px; font-weight:700; letter-spacing:1px;
    background:linear-gradient(135deg,#06b6d4,#8b5cf6);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .info { font-size:11px; color:#666; margin-left:auto; }
  .controls { display:flex; gap:6px; margin-bottom:8px; flex-wrap:wrap; align-items:center; }
  .controls .spacer { flex:1; }
  .main { display:flex; gap:16px; flex-wrap:nowrap; height: calc(100vh - 120px); width: 100%; overflow: hidden; }
  .grid-wrap {
    background:#12121a; border:1px solid #1e1e2a; border-radius:6px; padding:12px;
    position:relative; overflow:auto;
    flex: 1 1 0;
    min-width: 0;
  }
  .side { width: 300px; flex-shrink: 0; display:flex; flex-direction:column; gap:10px; overflow-y: auto; padding-right: 4px; }
  .card { background:#12121a; border:1px solid #1e1e2a; border-radius:6px; padding:14px; }
  .card-title { font-size:11px; color:#666; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }
  .score { font-size:36px; font-weight:800; }
  .score.good { color:#22c55e; } .score.mid { color:#f59e0b; } .score.bad { color:#ef4444; }
  .bar-bg { height:6px; background:#1e1e2a; border-radius:3px; margin-top:8px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:3px; transition:width 0.5s ease; }
  .net-row {
    display:flex; align-items:center; gap:8px; padding:5px 6px; border-radius:4px;
    font-size:11px; transition:background 0.15s;
  }
  .net-row:hover { background:#1e1e2a; }
  .net-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
  .net-info { flex:1; }
  .net-status { font-size:9px; padding:2px 6px; border-radius:3px; font-weight:600; }
  .net-status.ok { background:#22c55e15; color:#4ade80; }
  .net-status.fail { background:#ef444415; color:#f87171; }
  .net-list { flex:1; overflow-y:auto; max-height:400px; }
  .legend { font-size:10px; color:#555; line-height:1.8; }
  .legend span { color:#888; }
  .banner {
    position:absolute; top:0; left:0; right:0; z-index:10;
    background:#f59e0b20; color:#fbbf24; font-size:11px;
    padding:4px 8px; text-align:center; border-radius:6px 6px 0 0;
  }
  .error-banner {
    background:#ef444420; color:#f87171; font-size:11px;
    padding:6px 10px; border-radius:4px; margin-bottom:8px;
    border:1px solid #ef444440; word-break:break-all;
  }
  .hidden { display:none; }
</style>
<style id="dynamic-style"></style>
</head>
<body>

<div class="header">
  <div class="logo">⬡ ROUTABILITY ANALYZER</div>
  <div class="info" id="infoLabel">Loading puzzle...</div>
</div>

<div id="errorBanner" class="error-banner hidden"></div>

<!-- View tabs + edit tools -->
<div class="controls">
  <button class="btn active" data-view="routes" onclick="setView('routes',this)">🔌 Routes</button>
  <button class="btn" data-view="congestion" onclick="setView('congestion',this)">🌡 Congestion</button>
  <button class="btn" id="btnLayers" onclick="cycleLayerMode()" disabled>👁 Layers: Off</button>
  <div class="spacer"></div>
  <button class="btn" id="btnVia" onclick="toggleViaMode()">+ Via</button>
  <button class="btn" onclick="addNet()">+ Net</button>
  <button class="btn" onclick="importCase()">📂 Import</button>
  <button class="btn" onclick="exportCase()">💾 Export</button>
  <button class="btn primary" id="btnSolve" onclick="runSolve()">▶ Solve</button>
</div>

<div class="main">
  <div class="grid-wrap">
    <div id="banner" class="banner hidden"></div>
    <svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg>
  </div>
  <div class="side">
    <div class="card">
      <div class="card-title">Routability Score</div>
      <div><span class="score" id="scoreNum">—</span><span style="font-size:16px;color:#555" id="scoreTotal"></span></div>
      <div class="bar-bg"><div class="bar-fill" id="scoreBar"></div></div>
      <div style="font-size:10px;color:#555;margin-top:6px" id="scoreSub"></div>
    </div>
    <div class="card">
    <div class="card net-list" id="netList"></div>
    <div class="card legend">
      <div><span>Click endpoint</span> → select, then click cell to move</div>
      <div><span>+ Via</span> → click cells to toggle obstacles</div>
      <div><span>▶ Solve</span> → run your solver</div>
      <div><span>Click × on net row</span> → delete net</div>
      <div><span>Ctrl+Wheel</span> → zoom</div>
    </div>
  </div>
</div>

<input type="file" id="fileInput" accept=".json" style="display:none" onchange="handleImport(event)">

<script>
// ═══════════════════════════════════════════════
//  State
// ═══════════════════════════════════════════════
let ROWS = 1, COLS = 1;
let vias = [];
let nets = [];
let view = "routes";
let viaMode = false;
let pendingEp = null;
let solveResult = null;
let highlightNet = null;
let zoomLevel = 1.0;
let layerMode = "off";       // "off" | "all" | "front" | "back"
let layerData = null;

const PALETTE = [
  "#ef4444","#3b82f6","#14b8a6","#f59e0b","#a855f7",
  "#ec4899","#f97316","#22c55e","#6366f1","#92400e",
  "#06b6d4","#84cc16","#e11d48","#7c3aed","#0ea5e9",
  "#d946ef","#65a30d","#dc2626","#2563eb","#059669",
];

// ═══════════════════════════════════════════════
//  Load puzzle on startup
// ═══════════════════════════════════════════════
fetch("/api/puzzle").then(r => r.json()).then(d => {
  ROWS = d.rows; COLS = d.cols;
  vias = d.vias;
  nets = d.nets;
  syncServerState(false);
  render();
}).catch(e => {
  showError("Failed to load puzzle: " + e.message);
});

// ═══════════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════════
function viaKey(r,c) { return r+","+c; }
function viaSet() { const s=new Set(); vias.forEach(([r,c])=>s.add(viaKey(r,c))); return s; }
function epSet() {
  const s=new Map();
  nets.forEach((n,ni)=>n.endpoints.forEach(([r,c],ei)=>s.set(viaKey(r,c),{ni,ei})));
  return s;
}
function cellSize() { return Math.max(6, Math.min(28, Math.floor(580/Math.max(ROWS,COLS)))); }

function showError(msg) {
  const el = document.getElementById("errorBanner");
  if (msg) { el.textContent = msg; el.classList.remove("hidden"); }
  else { el.classList.add("hidden"); }
}

function splitPathAtVias(path, viaPoints) {
  // 在过孔点处将路径切分为多个段（段0=正面，段1=反面，段2=正面...交替）
  const viaSet = new Set(viaPoints.map(([r, c]) => `${r},${c}`));
  const segments = [];
  let cur = [];
  for (const pt of path) {
    cur.push(pt);
    if (viaSet.has(`${pt[0]},${pt[1]}`)) {
      if (cur.length > 0) segments.push(cur);
      cur = [[pt[0], pt[1]]];  // 过孔点同时属于下一段起点
    }
  }
  if (cur.length > 1) segments.push(cur);
  return segments.length > 0 ? segments : [path];
}

function congestionMapJS(vias, nets, rows, cols) {
  const vs = new Set(vias.map(v => v[0] + "," + v[1]));
  const heat = Array.from({length: rows}, () => Array(cols).fill(0));
  for (const net of nets) {
    const sr = net.endpoints[0][0], sc = net.endpoints[0][1];
    const er = net.endpoints[1][0], ec = net.endpoints[1][1];
    for (let r = Math.min(sr, er); r <= Math.max(sr, er); r++)
      for (let c = Math.min(sc, ec); c <= Math.max(sc, ec); c++)
        if (!vs.has(r + "," + c)) heat[r][c] += 1;
  }
  return heat;
}

function syncServerState(keepPaths=true) {
  if (!solveResult || !keepPaths) {
    solveResult = { routed_count: 0, total: nets.length, paths: {} };
    layerData = null;
  }
  solveResult.total = nets.length;
  if (solveResult.paths) solveResult.routed_count = Object.keys(solveResult.paths).length;
  solveResult.congestion = congestionMapJS(vias, nets, ROWS, COLS);
}

// ═══════════════════════════════════════════════
//  Rendering
// ═══════════════════════════════════════════════
function render(skipNetList = false) {
  const CS = cellSize();
  const W = COLS*CS, H = ROWS*CS;
  const svg = document.getElementById("svg");
  svg.setAttribute("width", W * zoomLevel);
  svg.setAttribute("height", H * zoomLevel);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.style.cursor = (viaMode || pendingEp) ? "crosshair" : "default";

  let html = "";

  for (let r=0; r<=ROWS; r++)
    html += `<line x1="0" y1="${r*CS}" x2="${W}" y2="${r*CS}" stroke="#1a1a25" stroke-width="0.5"/>`;
  for (let c=0; c<=COLS; c++)
    html += `<line x1="${c*CS}" y1="0" x2="${c*CS}" y2="${H}" stroke="#1a1a25" stroke-width="0.5"/>`;

  if (view === "congestion" && solveResult && solveResult.congestion) {
    const cg = solveResult.congestion;
    let mx = 1;
    for (let r=0;r<ROWS;r++) for (let c=0;c<COLS;c++) mx=Math.max(mx,cg[r][c]);
    for (let r=0;r<ROWS;r++) for (let c=0;c<COLS;c++) {
      if (cg[r][c]>0) {
        const t = cg[r][c]/mx;
        const col = t<0.33 ? `rgba(34,197,94,${t*2})` : t<0.66 ? `rgba(250,204,21,${t*1.5})` : `rgba(239,68,68,${0.3+t*0.7})`;
        html += `<rect x="${c*CS+1}" y="${r*CS+1}" width="${CS-2}" height="${CS-2}" fill="${col}" rx="2"/>`;
      }
    }
  }

  if (view === "routes" && solveResult && solveResult.paths) {
    for (const net of nets) {
      const p = solveResult.paths[String(net.id)];
      if (!p) continue;
      const sw = Math.max(1.5, Math.min(3, CS/10));

      // ── 图层模式：按 front/back/all 过滤和渲染 ──
      let drawSegments = null;  // null = draw full path; array = draw only these segments
      let dash = null;
      let opacity = 0.85;
      if (layerMode !== "off" && layerData) {
        const nid = Number(net.id);
        const isFront = layerData.front_nets.includes(nid);
        const isBack  = layerData.back_nets.includes(nid);
        const isVia   = layerData.via_nets.includes(nid);

        // 单面模式：隐藏纯另一面的线网
        if (layerMode === "front" && isBack && !isVia) { continue; }
        if (layerMode === "back"  && isFront && !isVia) { continue; }

        // 过孔线网：在过孔点处切分路径，各段交替为正面/反面
        if (isVia && layerData.via_points) {
          const viaPts = layerData.via_points[String(net.id)];
          if (viaPts && viaPts.length > 0) {
            const segments = splitPathAtVias(p, viaPts);
            drawSegments = [];
            for (let si = 0; si < segments.length; si++) {
              const isBackSeg = (si % 2 === 1);  // 偶数段=正面, 奇数段=反面
              if (layerMode === "front" && isBackSeg) continue;   // 仅正面
              if (layerMode === "back"  && !isBackSeg) continue;  // 仅反面
              drawSegments.push({
                pts: segments[si],
                dash: (layerMode === "all" && isBackSeg)
                      ? `${Math.max(3,CS/5)},${Math.max(2,CS/8)}` : null,
                opacity: (layerMode === "all" && isBackSeg) ? 0.7 : 0.75,
              });
            }
          }
        } else {
          // 非过孔线网：双面模式下反面用虚线
          if (layerMode === "all" && isBack) {
            dash = `${Math.max(3,CS/5)},${Math.max(2,CS/8)}`;
            opacity = 0.7;
          }
        }
      }

      // ── 绘制路径 ──
      if (drawSegments) {
        // 分段绘制（过孔线网）
        for (const seg of drawSegments) {
          if (seg.pts.length < 2) continue;
          const pts = seg.pts.map(([r,c])=>`${c*CS+CS/2},${r*CS+CS/2}`).join(" ");
          if (seg.dash) {
            html += `<polyline class="net-el net-${net.id} routed-line" points="${pts}" fill="none" stroke="${net.color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="${seg.dash}" style="opacity:${seg.opacity}"/>`;
          } else {
            html += `<polyline class="net-el net-${net.id} routed-line" points="${pts}" fill="none" stroke="${net.color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" style="opacity:${seg.opacity}"/>`;
          }
        }
      } else {
        // 整条绘制（非过孔线网或 off 模式）
        const pts = p.map(([r,c])=>`${c*CS+CS/2},${r*CS+CS/2}`).join(" ");
        if (dash) {
          html += `<polyline class="net-el net-${net.id} routed-line" points="${pts}" fill="none" stroke="${net.color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="${dash}" style="opacity:${opacity}"/>`;
        } else {
          html += `<polyline class="net-el net-${net.id} routed-line" points="${pts}" fill="none" stroke="${net.color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" style="opacity:${opacity}"/>`;
        }
      }
    }

    // ── 过孔标记（所有图层模式下均显示）──
    if (layerMode !== "off" && layerData && layerData.via_points) {
      const viaR = Math.max(2.5, CS/2 - 1.5);
      for (const [nidStr, points] of Object.entries(layerData.via_points)) {
        const net = nets.find(n => String(n.id) === nidStr);
        const color = net ? net.color : "#fff";
        for (const [r, c] of points) {
          const cx = c*CS+CS/2, cy = r*CS+CS/2;
          // 菱形过孔标记
          const s = viaR;
          html += `<polygon class="net-el net-${nidStr} via-marker" points="${cx},${cy-s} ${cx+s},${cy} ${cx},${cy+s} ${cx-s},${cy}" fill="${color}80" stroke="#fff" stroke-width="0.8" style="opacity:0.9"/>`;
        }
      }
    }
  }

  for (const net of nets) {
    const p = solveResult?.paths?.[String(net.id)];
    if (!p) {
      const [r1, c1] = net.endpoints[0];
      const [r2, c2] = net.endpoints[1];
      const x1 = c1*CS+CS/2, y1 = r1*CS+CS/2;
      const x2 = c2*CS+CS/2, y2 = r2*CS+CS/2;
      html += `<line class="net-el net-${net.id} fly-line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${net.color}" stroke-width="1.5" stroke-dasharray="5,4" style="opacity:0.4" />`;
    }
  }

  const pd = Math.max(1, CS*0.08);
  const vm = Math.max(2, CS*0.2);
  for (const [r,c] of vias) {
    html += `<rect x="${c*CS+pd}" y="${r*CS+pd}" width="${CS-pd*2}" height="${CS-pd*2}" fill="#1e1e2a" stroke="#333" stroke-width="0.5" rx="${Math.max(1,CS*0.1)}"/>`;
    html += `<line x1="${c*CS+vm}" y1="${r*CS+vm}" x2="${(c+1)*CS-vm}" y2="${(r+1)*CS-vm}" stroke="#444" stroke-width="0.8"/>`;
    html += `<line x1="${(c+1)*CS-vm}" y1="${r*CS+vm}" x2="${c*CS+vm}" y2="${(r+1)*CS-vm}" stroke="#444" stroke-width="0.8"/>`;
  }

  const fs = Math.max(5, Math.min(10, CS-4));
  const epR = Math.max(3, CS/2-2);
  for (let ni=0; ni<nets.length; ni++) {
    const net = nets[ni];
    for (let ei=0; ei<2; ei++) {
      const [r,c] = net.endpoints[ei];
      const cx = c*CS+CS/2, cy = r*CS+CS/2;
      const selected = pendingEp && pendingEp.ni===ni && pendingEp.ei===ei;
      if (ei===0) {
        html += `<circle class="net-el net-${net.id} endpoint-el" cx="${cx}" cy="${cy}" r="${epR}" fill="${net.color}90" stroke="${selected?"#fff":net.color}" stroke-width="${selected?2.5:1.2}" data-ep="${ni},${ei}" style="cursor:pointer; opacity:1"/>`;
      } else {
        html += `<circle class="net-el net-${net.id} endpoint-el" cx="${cx}" cy="${cy}" r="${epR}" fill="transparent" stroke="${net.color}" stroke-width="${selected?2.5:1.5}" stroke-dasharray="${Math.max(2,CS/8)},${Math.max(1,CS/14)}" data-ep="${ni},${ei}" style="cursor:pointer; opacity:1"/>`;
      }
      html += `<text class="net-el net-${net.id} text-el" x="${cx}" y="${cy+1}" text-anchor="middle" dominant-baseline="middle" fill="${ei===0?'#fff':net.color}" font-size="${fs}" font-weight="800" style="pointer-events:none; opacity:1">${net.id}</text>`;
    }
  }

  html += `<rect width="${W}" height="${H}" fill="transparent" style="pointer-events:none"/>`;
  svg.innerHTML = html;

  let mdx = 0, mdy = 0;
  svg.onmousedown = function(e) {
    if (e.button !== 0) return; // Only allow left-clicks
    mdx = e.clientX;
    mdy = e.clientY;
  };

  svg.onmouseup = function(e) {
    if (e.button !== 0) return;
    const isDrag = Math.abs(e.clientX - mdx) + Math.abs(e.clientY - mdy) > 5;

    // If we are currently holding an endpoint and we drag-and-drop it
    if (pendingEp && isDrag) {
      const rect = svg.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const c = Math.floor(x / (CS * zoomLevel));
      const r = Math.floor(y / (CS * zoomLevel));
      if (r>=0 && r<ROWS && c>=0 && c<COLS) {
        handleCellClick(r, c);
      }
      return;
    }

    if (isDrag) return; // Ignore drag for normal clicks

    if (e.target.closest && e.target.closest("[data-ep]")) return;
    const rect = svg.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const c = Math.floor(x / (CS * zoomLevel));
    const r = Math.floor(y / (CS * zoomLevel));
    if (r<0||r>=ROWS||c<0||c>=COLS) return;
    handleCellClick(r, c);
  };

  svg.querySelectorAll("[data-ep]").forEach(el => {
    let epmdx = 0, epmdy = 0;
    el.addEventListener("mousedown", function(e) {
      if (e.button !== 0) return;
      e.stopPropagation();
      if (viaMode) return;
      // Mark it as pending immediately on mousedown to allow drag-and-drop
      const [ni,ei] = this.dataset.ep.split(",").map(Number);
      pendingEp = {ni, ei};
      document.getElementById("banner").textContent = `Click or Drag to move Net ${nets[ni].id} endpoint ${ei===0?"start":"end"}`;
      document.getElementById("banner").classList.remove("hidden");
    });
    el.addEventListener("mouseup", function(e) {
      if (e.button !== 0) return;
      // If it's a drag release over the ORIGINAL element, do nothing, let them click again
    });
  });

  document.getElementById("infoLabel").textContent = `${ROWS}×${COLS} · ${vias.length} vias · ${nets.length} nets`;
  if (!skipNetList) renderNetList();
  renderScore();
}

function handleCellClick(r, c) {
  const vs = viaSet();
  const es = epSet();
  const k = viaKey(r,c);
  if (viaMode) {
    if (es.has(k)) return;
    if (vs.has(k)) {
      vias = vias.filter(([vr,vc])=>!(vr===r&&vc===c));
    } else {
      vias.push([r,c]);
    }
    syncServerState(true);
    render();
  } else if (pendingEp) {
    if (vs.has(k)) return;
    if (solveResult && solveResult.paths) delete solveResult.paths[String(nets[pendingEp.ni].id)];
    nets[pendingEp.ni].endpoints[pendingEp.ei] = [r,c];
    pendingEp = null;
    document.getElementById("banner").classList.add("hidden");
    syncServerState(true);
    render();
  }
}

function setHighlight(id) {
  highlightNet = id;
  const styleEl = document.getElementById("dynamic-style");
  if (id === null) {
    styleEl.textContent = "";
  } else {
    styleEl.textContent = `
      .net-el { transition: opacity 0.1s; }
      .net-el.routed-line { opacity: 0.12 !important; }
      .net-el.fly-line { opacity: 0.08 !important; }
      .net-el.endpoint-el { opacity: 0.15 !important; }
      .net-el.text-el { opacity: 0.15 !important; }
      
      .net-${id}.routed-line { opacity: 0.85 !important; }
      .net-${id}.fly-line { opacity: 0.4 !important; }
      .net-${id}.endpoint-el { opacity: 1 !important; z-index: 10; }
      .net-${id}.text-el { opacity: 1 !important; z-index: 11; }
    `;
  }
}

function renderNetList() {
  const el = document.getElementById("netList");
  let html = '<div class="card-title">Net List</div>';
  for (let i=0; i<nets.length; i++) {
    const net = nets[i];
    const path = solveResult?.paths?.[String(net.id)];
    const routed = !!path;
    const pathLen = path ? path.length : 0;
    const manhattan = Math.abs(net.endpoints[0][0]-net.endpoints[1][0]) + Math.abs(net.endpoints[0][1]-net.endpoints[1][1]);
    const label = net.name ? `${net.name} (${net.id})` : `Net ${net.id}`;
    html += `<div class="net-row" data-netid="${net.id}" onmouseenter="if(highlightNet!==${net.id}) setHighlight(${net.id});" onmouseleave="if(highlightNet!==null) setHighlight(null);">
      <div class="net-dot" style="background:${net.color};${routed?`box-shadow:0 0 6px ${net.color}60`:''}"></div>
      <div class="net-info">
        <span style="color:${routed?'#ccc':'#666'}">${label}</span>
      </div>
      <span style="font-size:10px;color:#555">L=${manhattan}</span>
      <span class="net-status ${routed?'ok':'fail'}">${routed?'✓ '+pathLen:'✗'}</span>
      <button class="btn" data-netid="${net.id}" style="padding:2px 6px;font-size:9px;color:#ef4444;border-color:#ef4444" onmousedown="event.stopPropagation(); removeNet(${net.id})">✕</button>
    </div>`;
  }
  el.innerHTML = html;
}

function renderScore() {
  const num = document.getElementById("scoreNum");
  const tot = document.getElementById("scoreTotal");
  const bar = document.getElementById("scoreBar");
  const sub = document.getElementById("scoreSub");
  if (!solveResult) { num.textContent="—"; tot.textContent=""; bar.style.width="0%"; sub.textContent=""; return; }
  const cnt = solveResult.routed_count, total = solveResult.total;
  num.textContent = cnt;
  num.className = "score " + (cnt===total?"good":cnt>=total*0.7?"mid":"bad");
  tot.textContent = " / "+total;
  const pct = (cnt/total*100)+"%";
  bar.style.width = pct;
  bar.style.background = cnt===total?"#22c55e":cnt>=total*0.7?"#f59e0b":"#ef4444";
  sub.textContent = cnt > 0 ? `${(cnt/total*100).toFixed(0)}% routed` : "Not solved yet";
}

// ═══════════════════════════════════════════════
//  Actions
// ═══════════════════════════════════════════════
function setView(v, btn) {
  view = v;
  document.querySelectorAll("[data-view]").forEach(b=>b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  render();
}

function cycleLayerMode() {
  if (!layerData) return;
  const modes = ["off", "all", "front", "back"];
  const labels = {
    "off":   "👁 Layers: Off",
    "all":   "👁 Layers: All",
    "front": "👁 Front Only",
    "back":  "👁 Back Only"
  };
  const idx = modes.indexOf(layerMode);
  layerMode = modes[(idx + 1) % modes.length];
  const btn = document.getElementById("btnLayers");
  btn.textContent = labels[layerMode];
  btn.classList.toggle("active", layerMode !== "off");
  render();
}

function toggleViaMode() {
  viaMode = !viaMode;
  pendingEp = null;
  document.getElementById("btnVia").classList.toggle("warn", viaMode);
  document.getElementById("btnVia").textContent = viaMode ? "✓ Done" : "+ Via";
  document.getElementById("banner").classList.toggle("hidden", !viaMode);
  if (viaMode) document.getElementById("banner").textContent = "Click cells to add/remove vias";
  render();
}

function addNet() {
  const newId = nets.length > 0 ? Math.max(...nets.map(n=>n.id)) + 1 : 0;
  const color = PALETTE[newId % PALETTE.length];
  const vs = viaSet();
  let a, b;
  do { a=[Math.floor(Math.random()*ROWS),Math.floor(Math.random()*COLS)]; } while(vs.has(viaKey(...a)));
  do { b=[Math.floor(Math.random()*ROWS),Math.floor(Math.random()*COLS)]; } while(vs.has(viaKey(...b))||(a[0]===b[0]&&a[1]===b[1]));
  nets.push({id:newId, name:"", color, endpoints:[a,b]});
  syncServerState(true);
  render();
}

function removeNet(id) {
  nets = nets.filter(n=>n.id!==id);
  pendingEp = null;
  document.getElementById("banner").classList.add("hidden");
  if (solveResult && solveResult.paths) delete solveResult.paths[String(id)];
  syncServerState(true);
  render();
}

async function runSolve() {
  const btn = document.getElementById("btnSolve");
  btn.disabled = true;
  btn.textContent = "⏳ Solving…";
  showError(null);
  try {
    const resp = await fetch("/api/solve", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({rows: ROWS, cols: COLS, vias, nets}),
    });
    const result = await resp.json();
    if (!resp.ok) {
      showError("Solver error: " + (result.error || resp.statusText));
    } else {
      solveResult = result;
      layerData = result.layer_data || null;
      // 更新图层按钮状态
      const btnL = document.getElementById("btnLayers");
      const layerLabels = {
        "off":   "👁 Layers: Off",
        "all":   "👁 Layers: All",
        "front": "👁 Front Only",
        "back":  "👁 Back Only"
      };
      if (layerData) {
        btnL.disabled = false;
        btnL.textContent = layerLabels[layerMode] || "👁 Layers: Off";
        btnL.classList.toggle("active", layerMode !== "off");
      } else {
        btnL.disabled = true;
        btnL.textContent = "👁 Layers: N/A";
        btnL.classList.remove("active");
        layerMode = "off";
      }
      view = "routes";
      document.querySelectorAll("[data-view]").forEach(b=>b.classList.remove("active"));
      document.querySelector("[data-view='routes']").classList.add("active");
    }
  } catch(e) {
    showError("Request failed: " + e.message);
  }
  btn.disabled = false;
  btn.textContent = "▶ Solve";
  render();
}

function exportCase() {
  const data = {
    grid: {rows:ROWS, cols:COLS},
    vias,
    nets: nets.map(n=>({id:n.id, name:n.name||"", color:n.color, endpoints:n.endpoints})),
  };
  if (solveResult && solveResult.paths) {
    data.solver_paths = solveResult.paths;
  }
  const blob = new Blob([JSON.stringify(data,null,2)], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `routing_${ROWS}x${COLS}_${nets.length}nets.json`;
  a.click();
}

function importCase() {
  document.getElementById("fileInput").click();
}

function handleImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(ev) {
    try {
      const data = JSON.parse(ev.target.result);
      if (data.grid) { ROWS=data.grid.rows; COLS=data.grid.cols; }
      if (data.vias) vias=data.vias;
      if (data.nets) nets=data.nets.map(n=>({...n}));
      syncServerState(false);
      render();
    } catch(err) { showError("Import failed: "+err.message); }
  };
  reader.readAsText(file);
  e.target.value = "";
}

// Ctrl+Wheel zoom
const gridWrap = document.querySelector(".grid-wrap");
gridWrap.addEventListener("wheel", function(e) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault();
    const oldZoom = zoomLevel;
    zoomLevel *= e.deltaY < 0 ? 1.1 : 0.9;
    zoomLevel = Math.max(0.1, Math.min(zoomLevel, 20.0));
    const rect = this.getBoundingClientRect();
    const mouseX = e.clientX - rect.left + this.scrollLeft;
    const mouseY = e.clientY - rect.top + this.scrollTop;
    const svg = document.getElementById("svg");
    const CS = cellSize();
    svg.setAttribute("width", COLS * CS * zoomLevel);
    svg.setAttribute("height", ROWS * CS * zoomLevel);
    this.scrollLeft = mouseX * (zoomLevel / oldZoom) - (e.clientX - rect.left);
    this.scrollTop = mouseY * (zoomLevel / oldZoom) - (e.clientY - rect.top);
  }
}, {passive: false});

// Middle-click or shift-click & drag to pan the sub-window
let isPanning = false;
let startX, startY, scrollL, scrollT;
gridWrap.addEventListener("mousedown", (e) => {
  // If clicking on an endpoint with left click, do not pan
  if (e.button === 0 && e.target.closest && e.target.closest(".endpoint-el, .text-el")) return;

  if (e.button === 1 || e.shiftKey || e.button === 0) { 
    if (e.button === 1) e.preventDefault(); // Prevent browser's auto-scroll mode
    isPanning = true;
    startX = e.pageX - gridWrap.offsetLeft;
    startY = e.pageY - gridWrap.offsetTop;
    scrollL = gridWrap.scrollLeft;
    scrollT = gridWrap.scrollTop;
    gridWrap.style.cursor = 'grabbing';
  }
});
gridWrap.addEventListener("mouseleave", () => { isPanning = false; gridWrap.style.cursor = ''; });
gridWrap.addEventListener("mouseup", () => { isPanning = false; gridWrap.style.cursor = ''; });
gridWrap.addEventListener("mousemove", (e) => {
  if (!isPanning) return;
  e.preventDefault();
  const x = e.pageX - gridWrap.offsetLeft;
  const y = e.pageY - gridWrap.offsetTop;
  gridWrap.scrollLeft = scrollL - (x - startX);
  gridWrap.scrollTop = scrollT - (y - startY);
});
</script>
</body>
</html>"""

# ═══════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import webbrowser, threading
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  ⬡ Routability Analyzer")
    print(f"  → http://localhost:{port}\n")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False)

