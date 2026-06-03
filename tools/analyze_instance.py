# -*- coding: utf-8 -*-
"""analyze_instance.py
문제 인스턴스 EDA + 유효 하한(lower bound) 계산. shapely 불필요(면적은 shoelace).
사용: python analyze_instance.py <instance.json>
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import json, sys, statistics, math


def shoelace(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def union_bbox(layers):
    xs = [v[0] for l in layers for v in l]
    ys = [v[1] for l in layers for v in l]
    return min(xs), min(ys), max(xs), max(ys)


def orient_wh(layers):
    x0, y0, x1, y1 = union_bbox(layers)
    return x1 - x0, y1 - y0


def analyze(prob):
    bays = prob["bays"]; blocks = prob["blocks"]; m = len(bays); n = len(blocks)
    w = prob.get("weights", {"w1": 1, "w2": 1, "w3": 1})
    bay_area = [b["width"] * b["height"] for b in bays]
    avg_area = sum(bay_area) / m
    u = [avg_area / a for a in bay_area]

    print("=" * 64)
    print(f"INSTANCE: {prob.get('name')}   blocks={n}  bays={m}")
    print(f"weights: w1={w['w1']}  w2={w['w2']}  w3={w['w3']}")
    print("bays (W x H, area, u_j):")
    for j, b in enumerate(bays):
        print(f"  bay{j}: {b['width']}x{b['height']}  area={bay_area[j]}  u={u[j]:.3f}")

    slacks, footprints, fbcounts, proc, work = [], [], [], [], []
    horizon = 0
    lb_tardiness = 0
    best_bay_loads = [0.0] * m          # 모두 최선호 bay 배정 시 부하
    for i, blk in enumerate(blocks):
        R, D, P, L = blk["release_time"], blk["due_date"], blk["processing_time"], blk["workload"]
        slack = D - R - P
        slacks.append(slack); proc.append(P); work.append(L)
        horizon = max(horizon, D, R + P)
        # 면적(footprint = layer0), orientation0 기준
        fp = shoelace([list(v) for v in blk["shape"][0]["layers"][0]])
        footprints.append(fp)
        # feasible bay count (AABB, 어떤 orientation으로든 들어가면 가능)
        fb = 0
        for j, bj in enumerate(bays):
            ok = any(orient_wh(o["layers"])[0] <= bj["width"] and
                     orient_wh(o["layers"])[1] <= bj["height"] for o in blk["shape"])
            fb += 1 if ok else 0
        fbcounts.append(fb)
        # 납기지연 하한: 공간/공유 무시 -> 가장 빨라도 R+P 에 끝남
        lb_tardiness += max(0, R + P - D)
        # 최선호 bay
        bestj = max(range(m), key=lambda j: blk["bay_preferences"][j])
        best_bay_loads[bestj] += L

    def stat(name, arr, fmt="{:.1f}"):
        print(f"  {name:22s} min={fmt.format(min(arr))}  mean={fmt.format(statistics.mean(arr))}"
              f"  max={fmt.format(max(arr))}")

    print("\n-- block statistics --")
    stat("slack (D-R-P)", slacks)
    stat("processing_time", proc)
    stat("workload", work)
    stat("footprint area", footprints)
    stat("feasible bay count", fbcounts, "{:d}".format if False else "{:.0f}")
    print(f"  blocks with slack<0   : {sum(1 for s in slacks if s < 0)}")
    print(f"  blocks fitting 1 bay  : {sum(1 for c in fbcounts if c == 1)}")
    print(f"  planning horizon (days): {horizon}")
    print(f"  total workload        : {sum(work)}   ideal per-bay (area-weighted balance目표)")

    print("\n-- LOWER BOUNDS (valid floors; any feasible solution is >= these) --")
    print(f"  Z1 (tardiness) LB = sum max(0, R+P - D) = {lb_tardiness}")
    print(f"     -> 공간/공유를 완전히 무시해도 이만큼의 지연은 불가피.")
    print(f"  Z2 (imbalance) LB = 0   (완벽 균형은 완화문제에서 가능)")
    print(f"  Z3 (preference) LB = 0  (모두 최선호 bay 배정 시)")
    obj_lb = w["w1"] * lb_tardiness
    print(f"  => objective LB = w1*{lb_tardiness} = {obj_lb}")

    print("\n-- TRADE-OFF 진단 (배정만 본 두 극단) --")
    # 극단 A: 모두 최선호 bay -> Z3=0, Z2는?
    VA = [u[j] * best_bay_loads[j] for j in range(m)]
    z2_all_pref = (max(VA) - min(VA)) if m > 1 else 0.0
    print(f"  [모두 최선호 bay]  Z3=0,  Z2={z2_all_pref:.1f}   bay부하 V={[round(v,1) for v in VA]}")
    # 극단 B: workload 균형 우선(그리디로 부하 작은 bay에) -> Z2 작아지나 Z3 증가 가능
    loads = [0.0] * m; pen = 0
    for i in sorted(range(n), key=lambda i: -work[i]):
        j = min(range(m), key=lambda j: u[j] * (loads[j] + work[i]))
        loads[j] += work[i]
        smax = max(blocks[i]["bay_preferences"])
        pen += smax - blocks[i]["bay_preferences"][j]
    VB = [u[j] * loads[j] for j in range(m)]
    z2_bal = (max(VB) - min(VB)) if m > 1 else 0.0
    print(f"  [부하 균형 우선]   Z3={pen},  Z2={z2_bal:.1f}   bay부하 V={[round(v,1) for v in VB]}")
    print(f"  => w2*Z2 vs w3*Z3 의 균형점을 찾는 것이 배정의 핵심 (w2={w['w2']}, w3={w['w3']}).")
    print("=" * 64)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else _SAMPLE
    analyze(json.load(open(path)))
