# -*- coding: utf-8 -*-
"""visualize.py
인스턴스 + 해(solution)를 그림으로: (1) 날짜별 bay 배치, (2) Gantt, (3) 목적값 분해.
shapely 불필요 — 도형은 좌표 평행이동만으로 그린다.
사용:
  python viz/visualize.py <instance.json> [solution.json] [--day 3] [--out out_dir]
해 파일이 없으면 인스턴스만(작업장 크기 + 일정 Gantt) 그린다.
"""
import os, sys, json, argparse
import matplotlib
matplotlib.use("Agg")                      # 파일 저장용(헤드리스)
import matplotlib.pyplot as plt
import matplotlib.font_manager as _fm
import glob as _glob
_cands = (_glob.glob("/usr/share/fonts/**/NotoSansCJK*.*", recursive=True)
          + _glob.glob("/usr/share/fonts/**/*Nanum*.*", recursive=True)
          + _glob.glob("/usr/share/fonts/**/malgun*.*", recursive=True)
          + _glob.glob("/Library/Fonts/AppleGothic.ttf"))
for _p in _cands:
    try:
        _fm.fontManager.addfont(_p)
        plt.rcParams["font.family"] = _fm.FontProperties(fname=_p).get_name()
        break
    except Exception:
        pass
plt.rcParams["axes.unicode_minus"] = False
from matplotlib.patches import Polygon as MplPoly, Rectangle


# ---------- 데이터 파싱 ----------
def footprint(block, orient):
    """해당 orientation의 layer 0 다각형 꼭짓점(상대좌표)."""
    for sh in block["shape"]:
        if sh["orientation"] == orient:
            return [(float(x), float(y)) for x, y in sh["layers"][0]]
    sh = block["shape"][0]
    return [(float(x), float(y)) for x, y in sh["layers"][0]]


def parse_solution(sol):
    """operations dict -> {block_id: {bay,x,y,orient,entry,exit}}"""
    info = {}
    ops = sol.get("operations", sol)
    for day_str, lst in ops.items():
        t = int(day_str)
        for op in lst:
            b = op["block_id"]
            if op["type"] == "ENTRY":
                info.setdefault(b, {})
                info[b].update(bay=op["bay_id"], x=op.get("x", 0), y=op.get("y", 0),
                               orient=op.get("orient_idx", 0), entry=t)
            elif op["type"] == "EXIT":
                info.setdefault(b, {})
                info[b]["exit"] = t
    return info


def objective(prob, info):
    B = prob["blocks"]; M = prob["bays"]; w = prob["weights"]
    areas = [bb["width"] * bb["height"] for bb in M]
    avg = sum(areas) / len(M); u = [avg / a for a in areas]
    # Z1
    Z1 = 0
    for b, d in info.items():
        if "exit" in d:
            Z1 += max(0, d["exit"] - B[b]["due_date"])
    # Z2
    V = [0.0] * len(M)
    for b, d in info.items():
        V[d["bay"]] += B[b]["workload"]
    V = [u[j] * V[j] for j in range(len(M))]
    Z2 = (max(V) - min(V)) if len(M) > 1 else 0.0
    # Z3
    Z3 = 0
    for b, d in info.items():
        S = B[b]["bay_preferences"]; Z3 += max(S) - S[d["bay"]]
    obj = w["w1"] * Z1 + w["w2"] * Z2 + w["w3"] * Z3
    return dict(Z1=Z1, Z2=Z2, Z3=Z3, obj=obj, w=w)


# ---------- 그리기 ----------
_PALETTE = ["#2A9D8F", "#E9A23B", "#E76F51", "#1B4965", "#6A4C93", "#2F7D9A",
            "#8AB17D", "#C44536", "#3D5A80", "#9C6644", "#588157", "#BC4749"]


def draw_layout(prob, info, day, ax):
    M = prob["bays"]; B = prob["blocks"]
    gap = max(2.0, 0.06 * max(b["height"] for b in M))
    y0 = 0.0
    yticks = []
    maxW = max(b["width"] for b in M)
    # 위에서 아래로 bay 0,1,2...
    offsets = []
    total_h = sum(b["height"] for b in M) + gap * (len(M) - 1)
    cur = total_h
    for j, bay in enumerate(M):
        cur -= bay["height"]
        offsets.append(cur)
        cur -= gap
    for j, bay in enumerate(M):
        oy = offsets[j]
        ax.add_patch(Rectangle((0, oy), bay["width"], bay["height"],
                               fill=False, edgecolor="#33414d", lw=1.5))
        ax.text(0.3, oy + bay["height"] - 0.4, f"Bay {j}  ({bay['width']}×{bay['height']})",
                fontsize=8, color="#33414d", va="top")
        yticks.append(oy + bay["height"] / 2)
    # 해당 날짜에 존재하는 블록
    present = [b for b, d in info.items()
               if d.get("entry", 0) <= day < d.get("exit", 10**9)]
    for b in present:
        d = info[b]; oy = offsets[d["bay"]]
        verts = [(vx + d["x"], vy + d["y"] + oy) for vx, vy in footprint(B[b], d["orient"])]
        col = _PALETTE[b % len(_PALETTE)]
        ax.add_patch(MplPoly(verts, closed=True, facecolor=col, edgecolor="white",
                             alpha=0.85, lw=1.0))
        cx = sum(p[0] for p in verts) / len(verts); cy = sum(p[1] for p in verts) / len(verts)
        tardy = "exit" in d and d["exit"] > B[b]["due_date"]
        ax.text(cx, cy, f"B{b}", fontsize=7, ha="center", va="center",
                color="white", weight="bold")
    ax.set_xlim(-1, maxW + 1); ax.set_ylim(-1, total_h + 1)
    ax.set_aspect("equal"); ax.set_yticks([]); ax.set_xticks([])
    ax.set_title(f"Day {day}  ·  blocks in bays: {len(present)}", fontsize=11)


def draw_gantt(prob, info, ax, day=None):
    B = prob["blocks"]
    items = sorted(info.items(), key=lambda kv: kv[1].get("entry", 0))
    for row, (b, d) in enumerate(items):
        e = d.get("entry", 0); x = d.get("exit", e)
        col = _PALETTE[b % len(_PALETTE)]
        tardy = x > B[b]["due_date"]
        ax.barh(row, max(0.3, x - e), left=e, height=0.6,
                color=("#E63946" if tardy else col), alpha=0.9)
        ax.plot([B[b]["due_date"]], [row], marker="v", color="#222", markersize=5)  # 납기 표시
        ax.text(e - 0.2, row, f"B{b}", fontsize=6, ha="right", va="center", color="#444")
    if day is not None:
        ax.axvline(day, color="#1B4965", lw=1.2, ls="--")
    ax.set_ylim(-1, len(items)); ax.invert_yaxis()
    ax.set_xlabel("day"); ax.set_yticks([])
    ax.set_title("Gantt (막대=점유기간, ▼=납기, 빨강=지연)", fontsize=11)


def figure_for(prob, info, day, out_path):
    fig = plt.figure(figsize=(13, 6))
    if info:
        ax1 = fig.add_subplot(1, 2, 1); draw_layout(prob, info, day, ax1)
        ax2 = fig.add_subplot(1, 2, 2); draw_gantt(prob, info, ax2, day=day)
        o = objective(prob, info)
        fig.suptitle(f"{prob.get('name','instance')}  |  obj={o['obj']:.0f}  "
                     f"(Z1={o['Z1']} Z2={o['Z2']:.1f} Z3={o['Z3']})", fontsize=12, weight="bold")
    else:
        # 해가 없으면: bay 크기 + 일정(release~due) Gantt
        ax1 = fig.add_subplot(1, 2, 1)
        M = prob["bays"]
        for j, bay in enumerate(M):
            ax1.add_patch(Rectangle((0, j * 1.2), bay["width"], 1.0, fill=False, edgecolor="#33414d"))
            ax1.text(0.3, j * 1.2 + 0.5, f"Bay {j} ({bay['width']}×{bay['height']})", fontsize=8, va="center")
        ax1.set_xlim(-1, max(b["width"] for b in M) + 1); ax1.set_ylim(-0.5, len(M) * 1.2)
        ax1.set_yticks([]); ax1.set_title("Bays", fontsize=11)
        ax2 = fig.add_subplot(1, 2, 2); B = prob["blocks"]
        for row, b in enumerate(B):
            ax2.barh(row, b["due_date"] - b["release_time"], left=b["release_time"],
                     height=0.6, color="#9FB3C4", alpha=0.8)
            ax2.barh(row, b["processing_time"], left=b["release_time"], height=0.6, color="#2A9D8F")
        ax2.invert_yaxis(); ax2.set_xlabel("day"); ax2.set_yticks([])
        ax2.set_title("일정: 회색=release~due, 청록=processing", fontsize=11)
        fig.suptitle(f"{prob.get('name','instance')} (해 없음 — 인스턴스 미리보기)", fontsize=12, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("solution", nargs="?", default=None)
    ap.add_argument("--day", type=int, default=None)
    ap.add_argument("--out", default="viz_out")
    a = ap.parse_args()
    prob = json.load(open(a.instance))
    info = {}
    if a.solution and os.path.exists(a.solution):
        info = parse_solution(json.load(open(a.solution)))
    os.makedirs(a.out, exist_ok=True)
    if info:
        days = sorted({d.get("entry", 0) for d in info.values()} |
                      {d.get("exit", 0) for d in info.values()})
        day = a.day if a.day is not None else (days[len(days) // 2] if days else 0)
        p = figure_for(prob, info, day, os.path.join(a.out, f"layout_day{day}.png"))
        o = objective(prob, info)
        print(f"saved {p}")
        print(f"objective={o['obj']:.0f}  Z1(지연)={o['Z1']}  Z2(불균형)={o['Z2']:.1f}  Z3(선호손실)={o['Z3']}")
    else:
        p = figure_for(prob, {}, 0, os.path.join(a.out, "instance_preview.png"))
        print(f"saved {p} (해 파일이 없어 인스턴스만 그렸습니다)")


if __name__ == "__main__":
    main()
