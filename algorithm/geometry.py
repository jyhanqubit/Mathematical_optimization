"""geometry.py
OGC2026 조선소 블록 배치 — 기하/실현가능성(feasibility) 엔진.

[인덱스/좌표 규약]  문제정의서의 "알고리즘 솔루션" 규약을 따른다 (모두 0-based).
- bay j        : 사각형 [0, W_j] x [0, H_j]
- block i      : orientation id -> layers(낮은->높은 순), 각 layer는 polygon 정점 리스트
- reference pt : layer0의 첫 정점 [0,0]. 배치 (x,y)는 '모든 정점에 (x,y)를 더하는' 평행이동.
- 충돌 기준    : '내부(interior)' 교차만 충돌로 본다. 모서리/꼭짓점 접촉은 collision-free.

[주의] 최종 제출 전 실현가능성은 반드시 대회 제공 utils.check_feasibility() 로 확인할 것.
       이 모듈은 동일한 의미를 재현하지만, 평가 서버는 utils.py 를 사용한다.
"""
from __future__ import annotations
from shapely.geometry import Polygon, box
from shapely.affinity import translate
from shapely.ops import unary_union

AREA_TOL = 1e-7   # 내부 교차 판정 허용오차 (모서리 공유는 0 area)
OUT_TOL  = 1e-7   # bay 밖으로 삐져나간 면적 허용오차


# ---------------------------------------------------------------- 폴리곤 생성
def base_polygons(block):
    """block -> {orient_id: [Polygon(layer0), Polygon(layer1), ...]} (원점 기준)."""
    out = {}
    for o in block["shape"]:
        polys = [Polygon([(float(px), float(py)) for px, py in layer])
                 for layer in o["layers"]]
        out[o["orientation"]] = polys
    return out


def place(base_polys, x, y):
    """layer base polygon들을 정수 (x,y) 만큼 평행이동."""
    return [translate(p, xoff=float(x), yoff=float(y)) for p in base_polys]


def poly_aabb(polys):
    """layer 집합 union 의 (minx, miny, maxx, maxy)."""
    minx = miny = float("inf"); maxx = maxy = float("-inf")
    for p in polys:
        x0, y0, x1, y1 = p.bounds
        minx, miny = min(minx, x0), min(miny, y0)
        maxx, maxy = max(maxx, x1), max(maxy, y1)
    return minx, miny, maxx, maxy


def union_area(polys):
    return unary_union(polys).area


# ---------------------------------------------------------------- 원자 검사
def interior_intersect(a, b):
    """두 polygon의 '내부'가 겹치면 True. (모서리만 닿으면 False)"""
    if not a.intersects(b):
        return False
    return a.intersection(b).area > AREA_TOL


def contained_in_bay(polys, W, H):
    """모든 layer가 bay [0,W]x[0,H] 안에 완전히 포함되는가 (모서리 접촉 허용)."""
    bay = box(0, 0, W, H)
    for p in polys:
        if p.difference(bay).area > OUT_TOL:
            return False
    return True


def blocks_collide(polys1, polys2):
    """같은 bay·같은 시각의 두 block: '같은 layer level'끼리만 충돌 검사.
       l = 0..min(K1,K2)-1 중 하나라도 내부 교차하면 True."""
    for l in range(min(len(polys1), len(polys2))):
        if interior_intersect(polys1[l], polys2[l]):
            return True
    return False


def crane_blocked(crane_polys, other_polys):
    """crane으로 넣/빼는 block(crane_polys)이 other_polys에 의해 막히는가.
       crane block의 layer l1 이, 상대 block의 같거나 더 높은 layer l2(>=l1)와
       내부 교차하면 수직 이동이 막힌다 -> True."""
    K1, K2 = len(crane_polys), len(other_polys)
    for l1 in range(K1):
        for l2 in range(l1, K2):   # 같거나 더 높은 layer
            if interior_intersect(crane_polys[l1], other_polys[l2]):
                return True
    return False


def coexist_ok(new_polys, other_polys):
    """두 block이 같은 bay에서 시간 겹치게 공존할 때, 어떤 EXIT 순서에서도
       안전함을 보장하는 '보수적 충분조건'.
         (1) 같은 layer 충돌 없음            (정적 공존)
         (2) new 를 내릴 때 other에 안 막힘   (crane ENTRY of new)
         (3) other 를 뺄 때 new 에 안 막힘    (crane EXIT of other, new 존재 상태)
       세 조건을 모두 만족해야 True. (보수적이라 일부 실현가능 해를 놓칠 수 있음)"""
    if blocks_collide(new_polys, other_polys):
        return False
    if crane_blocked(new_polys, other_polys):
        return False
    if crane_blocked(other_polys, new_polys):
        return False
    return True


# ---------------------------------------------- 전체 솔루션 day-by-day 시뮬 검증
def feasibility_report(prob_info, solution):
    """날짜별 operation을 순서대로 시뮬레이션하며 모든 제약을 검사한다.
       returns (violations, entry_day, exit_day, placement)
       violations 가 빈 리스트면 (이 엔진 기준) feasible.
    """
    bays = prob_info["bays"]
    blocks = prob_info["blocks"]
    base = [base_polygons(b) for b in blocks]

    ops_by_day = solution.get("operations", {})
    days = sorted(int(d) for d in ops_by_day)

    entry_day, exit_day, placement = {}, {}, {}
    n_entry, n_exit = {}, {}
    present = {j: {} for j in range(len(bays))}   # bay -> {block_id: polys}
    viol = []

    for d in days:
        ops = ops_by_day[str(d)]
        # (a) 같은 날엔 EXIT 가 ENTRY 보다 먼저
        seen_entry = False
        for op in ops:
            if op["type"] == "ENTRY":
                seen_entry = True
            elif op["type"] == "EXIT" and seen_entry:
                viol.append(("ORDER_EXIT_AFTER_ENTRY", d))
        # (b) EXIT 먼저 처리
        for op in ops:
            if op["type"] != "EXIT":
                continue
            b, j = op["block_id"], op["bay_id"]
            n_exit[b] = n_exit.get(b, 0) + 1
            exit_day[b] = d
            if b not in present[j]:
                viol.append(("EXIT_NOT_PRESENT", d, b)); continue
            cp = present[j][b]
            for ob, opolys in present[j].items():
                if ob == b:
                    continue
                if crane_blocked(cp, opolys):
                    viol.append(("CRANE_EXIT_BLOCKED", d, b, ob))
            del present[j][b]
        # (c) ENTRY 처리
        for op in ops:
            if op["type"] != "ENTRY":
                continue
            b, j = op["block_id"], op["bay_id"]
            x, y, o = op["x"], op["y"], op["orient_idx"]
            n_entry[b] = n_entry.get(b, 0) + 1
            entry_day[b] = d
            placement[b] = (j, o, x, y)
            polys = place(base[b][o], x, y)
            if not contained_in_bay(polys, bays[j]["width"], bays[j]["height"]):
                viol.append(("BAY_CONTAINMENT", d, b))
            for ob, opolys in present[j].items():
                if blocks_collide(polys, opolys):
                    viol.append(("LAYER_COLLISION", d, b, ob))
                if crane_blocked(polys, opolys):
                    viol.append(("CRANE_ENTRY_BLOCKED", d, b, ob))
            present[j][b] = polys

    # (d) block별 operation 수 / 시간 제약
    for i, blk in enumerate(blocks):
        if n_entry.get(i, 0) != 1 or n_exit.get(i, 0) != 1:
            viol.append(("OP_COUNT", i)); continue
        if entry_day[i] < blk["release_time"]:
            viol.append(("RELEASE_DATE", i))
        if exit_day[i] - entry_day[i] < blk["processing_time"]:
            viol.append(("PROCESSING_TIME", i))

    return viol, entry_day, exit_day, placement
