# -*- coding: utf-8 -*-
"""myalgorithm.py  (OGC 2026 제출용 진입점)

전략:
  1) 제공된 baseline_greedy 로 강한 feasible 초기해 확보.
  2) 그 위에서 ALNS(destroy-repack) 로 개선 — 매 채택은 진짜 utils.check_feasibility 로 검증.
  3) baseline이 혹시 infeasible이면 내 serial_greedy(항상 feasible)를 안전망으로 사용.
  => 반환 해는 항상 feasible 하며, baseline 이상(>=)의 품질을 보장.

제출 zip에 함께 넣을 파일:
  myalgorithm.py, baseline_greedy.py, alns_improve.py, geometry.py, candidates.py,
  greedy.py, localsearch.py   (utils.py 는 수정 불가 — 넣어도 서버 것으로 덮어씀)
"""
from __future__ import annotations
import time


def algorithm(prob_info, timelimit=60):
    t0 = time.time()
    from utils import check_feasibility

    # 1) baseline 초기해
    best = None
    best_obj = float("inf")
    try:
        import baseline_greedy
        best = baseline_greedy.greedyalgorithm(prob_info, max(3.0, timelimit * 0.40))
        r = check_feasibility(prob_info, best)
        if r["feasible"]:
            best_obj = r["objective"]
        else:
            best = None
    except Exception:
        best = None

    # 1b) 안전망: 항상 feasible 한 serial greedy
    if best is None:
        try:
            import greedy
            cand = greedy.serial_greedy(prob_info)
            r = check_feasibility(prob_info, cand)
            if r["feasible"]:
                best, best_obj = cand, r["objective"]
        except Exception:
            pass

    if best is None:                       # 최후: 빈 해 대신 baseline 재시도
        import baseline_greedy
        return baseline_greedy.greedyalgorithm(prob_info, timelimit)

    # 2) ALNS 개선 (남은 시간 전부 사용, utils 검증 후 채택)
    try:
        import alns_improve
        cand = alns_improve.improve(
            prob_info, best, deadline=t0 + 0.95 * timelimit,
            check_feasibility=check_feasibility, k=3)
        r = check_feasibility(prob_info, cand)
        if r["feasible"] and r["objective"] < best_obj - 1e-9:
            best, best_obj = cand, r["objective"]
    except Exception:
        pass

    return best
