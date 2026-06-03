"""greedy.py
초기해 생성.
  - serial_greedy : bay당 한 번에 한 block만 두는 직렬 스케줄 -> 항상 feasible (안전망).
  - packed_greedy : 후보 placement로 같은 bay에 시간겹쳐 공존 시도 -> bay 활용률/지연 개선.
                    공존은 geometry.coexist_ok 의 보수적 충분조건으로만 허용 -> 안전.
"""
from __future__ import annotations
import time
from geometry import (base_polygons, place, poly_aabb,
                      contained_in_bay, coexist_ok)
from candidates import fits, generate


# ------------------------------------------------------- 우선순위 (기획안 7.3)
def priority_order(prob_info, a=1.0, b=1.0, g=0.3, d=0.3, eta=2.0):
    """priority_i = a*D_i + b*slack_i - g*area_i - d*L_i - eta*feasibleBayCount_i.
       점수 오름차순 배치(= 납기 빠르고 slack 작고, 크고 무겁고, 갈 수 있는 bay
       적은 block을 먼저 배치)."""
    bays, blocks = prob_info["bays"], prob_info["blocks"]
    m = len(bays)
    scored = []
    for i, blk in enumerate(blocks):
        polys0 = next(iter(base_polygons(blk).values()))
        from geometry import union_area
        area = union_area(polys0)
        slack = blk["due_date"] - blk["release_time"] - blk["processing_time"]
        fbc = sum(1 for j in range(m)
                  if fits(blk, bays[j]["width"], bays[j]["height"]))
        s = (a * blk["due_date"] + b * slack
             - g * area - d * blk["workload"] - eta * fbc)
        scored.append((s, i))
    scored.sort()
    return [i for _, i in scored]


def _build_solution(ops):
    """ops: {day: [op,...]} -> 같은 날 EXIT 먼저 정렬한 solution dict."""
    operations = {}
    for day in sorted(ops):
        exits = [o for o in ops[day] if o["type"] == "EXIT"]
        entries = [o for o in ops[day] if o["type"] == "ENTRY"]
        operations[str(day)] = exits + entries
    return {"operations": operations}


def _pref_order(blk, m):
    return sorted(range(m), key=lambda j: -blk["bay_preferences"][j])


# ----------------------------------------------------------- 직렬 (항상 feasible)
def serial_greedy(prob_info):
    bays, blocks = prob_info["bays"], prob_info["blocks"]
    m = len(bays)
    order = priority_order(prob_info)
    bay_free = [0] * m
    ops = {}

    for i in order:
        blk = blocks[i]
        chosen = None
        for j in _pref_order(blk, m):
            f = fits(blk, bays[j]["width"], bays[j]["height"])
            if f:
                chosen = (j,) + f
                break
        if chosen is None:                       # 어느 bay에도 안 들어가는 병리 케이스
            j = max(range(m), key=lambda k: bays[k]["width"] * bays[k]["height"])
            o = blocks[i]["shape"][0]["orientation"]
            chosen = (j, o, 0, 0)
        j, o, x, y = chosen
        e = max(blk["release_time"], bay_free[j])
        xexit = e + blk["processing_time"]
        bay_free[j] = xexit
        ops.setdefault(e, []).append({"type": "ENTRY", "block_id": i, "bay_id": j,
                                      "x": int(x), "y": int(y), "orient_idx": o})
        ops.setdefault(xexit, []).append({"type": "EXIT", "block_id": i, "bay_id": j})
    return _build_solution(ops)


# --------------------------------------------------- 패킹(공존) 시도 + 직렬 fallback
def packed_greedy(prob_info, deadline=None):
    bays, blocks = prob_info["bays"], prob_info["blocks"]
    m = len(bays)
    order = priority_order(prob_info)
    base = [base_polygons(b) for b in blocks]
    placed = {j: [] for j in range(m)}           # bay -> [{e,xexit,polys,bid,...}]
    ops = {}

    def overlapping(j, e, xexit):
        return [p for p in placed[j] if p["e"] < xexit and e < p["xexit"]]

    def commit(i, j, o, x, y, e, P):
        polys = place(base[i][o], x, y)
        rec = {"e": e, "xexit": e + P, "polys": polys, "bid": i}
        placed[j].append(rec)
        ops.setdefault(e, []).append({"type": "ENTRY", "block_id": i, "bay_id": j,
                                      "x": int(x), "y": int(y), "orient_idx": o})
        ops.setdefault(e + P, []).append({"type": "EXIT", "block_id": i, "bay_id": j})

    for i in order:
        blk = blocks[i]
        P, R = blk["processing_time"], blk["release_time"]
        done = False

        if not (deadline and time.time() > deadline):
            for j in _pref_order(blk, m):
                W, H = bays[j]["width"], bays[j]["height"]
                # 후보 ENTRY 일: release date + 이 bay의 exit 이벤트들
                event_days = sorted({R} | {p["xexit"] for p in placed[j]
                                            if p["xexit"] >= R})
                for e in event_days:
                    occ = overlapping(j, e, e + P)
                    occ_aabbs = [poly_aabb(p["polys"]) for p in occ]
                    for (o, x, y) in generate(blk, W, H, occ_aabbs):
                        polys = place(base[i][o], x, y)
                        if not contained_in_bay(polys, W, H):
                            continue
                        if all(coexist_ok(polys, p["polys"]) for p in occ):
                            commit(i, j, o, x, y, e, P)
                            done = True
                            break
                    if done:
                        break
                if done:
                    break

        if not done:                              # fallback: bay 비운 뒤 배치
            for j in _pref_order(blk, m):
                f = fits(blk, bays[j]["width"], bays[j]["height"])
                if f:
                    o, x, y = f
                    e = max(R, max((p["xexit"] for p in placed[j]), default=0))
                    commit(i, j, o, x, y, e, P)
                    done = True
                    break

        if not done:                              # 최후의 강제 배치
            j = max(range(m), key=lambda k: bays[k]["width"] * bays[k]["height"])
            o = blk["shape"][0]["orientation"]
            e = max(R, max((p["xexit"] for p in placed[j]), default=0))
            commit(i, j, o, 0, 0, e, P)

    return _build_solution(ops)
