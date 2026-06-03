# -*- coding: utf-8 -*-
"""integrate_pipeline.py
하이브리드 오케스트레이션의 '연결' 코드.
  [양자/고전이 푼 배정]  ->  [고전 엔진이 그 배정 위에서 기하·일정 확정]  ->  [진짜 utils 채점]

배정 주입 방법(비침습): 각 블록의 bay 선호도를 '배정된 bay=100, 나머지=0'으로 임시 치환하면,
선호도 순으로 배치하는 기존 greedy가 자연스럽게 그 bay로 배치한다. 채점은 '원본' 선호도로 한다.

실행 환경: ogc2026 conda(=shapely) 에서, utils.py / baseline_greedy.py / 내 모듈(greedy.py 등)과
같은 폴더에 두고 실행. (이 파일은 그 환경에서 동작; 배정 자체는 오프라인 SA로도 산출 가능)
사용: python integrate_pipeline.py [instance.json] --backend sa|dwave|qiskit
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, os, json, copy, argparse
sys.path.insert(0, os.path.dirname(__file__))
# 내 알고리즘/채점 모듈 경로(필요 시 수정)
for pth in ("../ogc2026_work", "../baseline_pkg/ogc2026/baseline", "."):
    p = os.path.join(os.path.dirname(__file__), pth)
    if os.path.isdir(p):
        sys.path.insert(0, p)

import qubo as q


def get_assignment(prob, backend):
    if backend == "sa":
        Q, const, meta = q.build_qubo(prob)
        x, _ = q.solve_sa_qubo(Q, const, meta["n"], meta["m"], steps=8000, restarts=12)
        return q.decode(x, meta["n"], meta["m"])
    if backend == "dwave":
        import run_dwave
        Q, const, meta = q.build_qubo(prob)
        sample, _, _ = run_dwave.solve(Q, const)
        x = [int(sample[k]) for k in range(meta["n"] * meta["m"])]
        return q.decode(x, meta["n"], meta["m"])
    if backend == "qiskit":
        raise SystemExit("qiskit 백엔드는 run_qiskit.py 로 배정을 산출해 --assign 으로 넘겨주세요.")
    raise SystemExit("unknown backend")


def force_assignment(prob, assign):
    """배정을 강제하도록 선호도를 임시 치환한 prob 사본 반환."""
    p2 = copy.deepcopy(prob)
    m = len(prob["bays"])
    for i, blk in enumerate(p2["blocks"]):
        blk["bay_preferences"] = [100 if j == assign[i] else 0 for j in range(m)]
    return p2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", nargs="?",
                    default=_SAMPLE)
    ap.add_argument("--backend", default="sa", choices=["sa", "dwave", "qiskit"])
    ap.add_argument("--time", type=float, default=20.0)
    a = ap.parse_args()
    prob = json.load(open(a.instance))

    import utils, greedy   # shapely 환경 필요

    # 1) 양자/고전이 배정 산출
    assign = get_assignment(prob, a.backend)
    z2, z3, V = q.true_Z2_Z3(prob, assign)
    print(f"[{a.backend}] 배정 = {assign}  (Z2={z2:.2f}, Z3={z3})")

    # 2) 그 배정을 강제해 고전 엔진으로 기하·일정 확정
    forced = force_assignment(prob, assign)
    sol_q = greedy.packed_greedy(forced)
    r_q = utils.check_feasibility(prob, sol_q)        # 채점은 '원본' prob

    # 3) 비교군: 배정도 고전이 알아서(선호 기반) 한 일반 해
    sol_c = greedy.packed_greedy(prob)
    r_c = utils.check_feasibility(prob, sol_c)

    def line(tag, r):
        if r["feasible"]:
            print(f"  {tag:22s} feasible  obj={r['objective']:.1f}  (Z1={r['obj1']:.1f} Z2={r['obj2']:.2f} Z3={r['obj3']:.0f})")
        else:
            print(f"  {tag:22s} INFEASIBLE(stage {r['stage']})")
    print("\n[진짜 utils 채점]")
    line(f"hybrid({a.backend} 배정)", r_q)
    line("classical(자동 배정)", r_c)
    print("\n※ PoC 메시지: 양자가 정한 배정을 고전 엔진이 그대로 받아 전체 해를 완성하고,")
    print("  대회 채점기로 동일하게 평가되는 '하이브리드 오케스트레이션'을 실증.")


if __name__ == "__main__":
    main()
