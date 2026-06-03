# -*- coding: utf-8 -*-
"""alns_improve.py
baseline 해를 출발점으로, '여러 블록 제거 -> 더 이른 시점/덜 붐비는 bay로 재패킹'을
반복하는 ALNS. 재삽입은 내 geometry(coexist_ok: 충돌+크레인 양방향 안전조건)로 후보를
거르고, 최종 채택은 진짜 utils.check_feasibility 로 검증. 개선 시에만 채택(절대 악화 없음).
"""
from __future__ import annotations
import time, random
from geometry import base_polygons, place, contained_in_bay, coexist_ok, poly_aabb
from candidates import generate as gen_candidates
from localsearch import parse, build


def _reinsert(prob, base, fixed, bid, horizon, deadline):
    """fixed(고정 블록 records dict)에 대해 bid를 가장 이른 feasible 시점/자리에 재삽입.
       성공 시 (bay,orient,x,y,entry,exit) 반환, 실패 시 None."""
    blocks = prob["blocks"]; bays = prob["bays"]
    P, R = blocks[bid]["processing_time"], blocks[bid]["release_time"]
    pref = sorted(range(len(bays)), key=lambda j: -blocks[bid]["bay_preferences"][j])
    best = None
    for j in pref:
        W, H = bays[j]["width"], bays[j]["height"]
        # fixed 중 bay j 의 것들
        fb = [(r, place(base[ob][r["orient"]], r["x"], r["y"]))
              for ob, r in fixed.items() if r["bay"] == j]
        for e in range(R, horizon + 1):
            if time.time() > deadline:
                return best
            ex = e + P
            occ = [(r, polys) for (r, polys) in fb if r["entry"] < ex and e < r["exit"]]
            occ_aabbs = [poly_aabb(polys) for (_r, polys) in occ]
            for (o, x, y) in gen_candidates(blocks[bid], W, H, occ_aabbs):
                polys = place(base[bid][o], x, y)
                if not contained_in_bay(polys, W, H):
                    continue
                if all(coexist_ok(polys, op) for (_r, op) in occ):
                    cand = {"bay": j, "orient": o, "x": x, "y": y, "entry": e, "exit": ex}
                    # 가장 이른 entry 우선 -> 첫 성공이 그 bay의 최선
                    return cand   # 선호 bay에서 가장 이른 e 채택
    return best


def improve(prob, init_sol, deadline, check_feasibility, k=3, seed=0):
    rng = random.Random(seed)
    rec = parse(prob, init_sol)
    base = [base_polygons(b) for b in prob["blocks"]]
    horizon = max(r["exit"] for r in rec.values()) + max(
        b["processing_time"] for b in prob["blocks"])
    r0 = check_feasibility(prob, build(rec))
    if not r0["feasible"]:
        return init_sol
    cur = r0["objective"]
    n = len(prob["blocks"])

    while time.time() < deadline:
        # destroy: tardy 우선 + 무작위 약간
        tardy = [b for b, r in rec.items()
                 if r["exit"] > prob["blocks"][b]["due_date"]]
        rng.shuffle(tardy)
        removed = set(tardy[:k]) | set(rng.sample(range(n), min(k, n)))
        fixed = {b: dict(r) for b, r in rec.items() if b not in removed}
        # repair: tardy/납기 빠른 순으로 재삽입
        order = sorted(removed, key=lambda b: prob["blocks"][b]["due_date"])
        ok = True
        for b in order:
            cand = _reinsert(prob, base, fixed, b, horizon, deadline)
            if cand is None:
                cand = dict(rec[b])      # 원위치 유지(안전)
            fixed[b] = cand
        r = check_feasibility(prob, build(fixed))
        if r["feasible"] and r["objective"] < cur - 1e-9:
            rec, cur = fixed, r["objective"]
    return build(rec)
