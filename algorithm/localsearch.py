# -*- coding: utf-8 -*-
"""localsearch.py
baseline(또는 임의의 feasible) 해를 받아, 진짜 utils.check_feasibility로 매 이동을
검증하며 objective를 낮추는 안전한 hill-climb. 개선 실패 시 입력 해를 그대로 보존한다.

이동(move):
  - EXIT-pull : 블록의 반출일을 (entry+proc)까지 당겨 tardiness 감소.
  - ENTRY/EXIT-pull : 투입일을 release까지 당기고 반출도 같이 당김.
  - bay/orient reassign : 더 선호하는 bay 또는 다른 방향으로 재배치(좌하단/접점 후보 탐색).
모든 이동은 utils로 전수 검증 → feasible & objective 감소일 때만 채택.
"""
from __future__ import annotations
import time


def parse(prob, sol):
    rec = {}
    for t_str, ops in sol["operations"].items():
        t = int(t_str)
        for op in ops:
            b = op["block_id"]
            if op["type"] == "ENTRY":
                rec.setdefault(b, {})
                rec[b].update(bay=op["bay_id"], x=op["x"], y=op["y"],
                              orient=op["orient_idx"], entry=t)
            else:
                rec.setdefault(b, {})["exit"] = t
    return rec


def build(rec):
    ops = {}
    for b, r in rec.items():
        ops.setdefault(r["entry"], []).append(
            {"type": "ENTRY", "block_id": b, "bay_id": r["bay"],
             "x": int(r["x"]), "y": int(r["y"]), "orient_idx": r["orient"]})
        ops.setdefault(r["exit"], []).append(
            {"type": "EXIT", "block_id": b, "bay_id": r["bay"]})
    out = {}
    for d in sorted(ops):
        ex = [o for o in ops[d] if o["type"] == "EXIT"]
        en = [o for o in ops[d] if o["type"] == "ENTRY"]
        out[str(d)] = ex + en
    return {"operations": out}


def improve(prob, sol, deadline, check_feasibility,
            candidate_fn=None, place_fn=None, do_reassign=True):
    """check_feasibility = utils.check_feasibility (진짜 채점기).
       candidate_fn/place_fn: 재배치 후보 생성용(선택). 없으면 timing 이동만."""
    rec = parse(prob, sol)
    r0 = check_feasibility(prob, build(rec))
    if not r0["feasible"]:
        return sol                              # 입력이 이미 infeasible이면 손대지 않음
    cur = r0["objective"]
    blocks = prob["blocks"]

    def try_set(b, **kw):
        nonlocal cur
        old = {k: rec[b][k] for k in kw}
        rec[b].update(kw)
        r = check_feasibility(prob, build(rec))
        if r["feasible"] and r["objective"] < cur - 1e-9:
            cur = r["objective"]
            return True
        rec[b].update(old)
        return False

    improved = True
    while improved and time.time() < deadline:
        improved = False
        for b in list(rec):
            if time.time() >= deadline:
                break
            P = blocks[b]["processing_time"]
            R = blocks[b]["release_time"]
            en, ex = rec[b]["entry"], rec[b]["exit"]
            # 1) EXIT-pull: 가장 이른 feasible 반출일
            for ne in range(en + P, ex):
                if try_set(b, exit=ne):
                    improved = True
                    break
            # 2) ENTRY-pull (+exit 동반): 더 이른 투입
            en, ex = rec[b]["entry"], rec[b]["exit"]
            for nen in range(R, en):
                if try_set(b, entry=nen, exit=nen + P):
                    improved = True
                    break
            # 3) bay/orient 재배치 (선호/균형 개선)
            if do_reassign and candidate_fn and place_fn and time.time() < deadline:
                bd = blocks[b]
                # 선호 높은 bay 우선
                for j in sorted(range(len(prob["bays"])),
                                key=lambda j: -bd["bay_preferences"][j]):
                    if j == rec[b]["bay"]:
                        continue
                    Wj, Hj = prob["bays"][j]["width"], prob["bays"][j]["height"]
                    found = False
                    for (o, x, y) in candidate_fn(bd, Wj, Hj):
                        if try_set(b, bay=j, orient=o, x=x, y=y):
                            improved = True; found = True; break
                    if found:
                        break
    return build(rec)
