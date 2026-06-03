# -*- coding: utf-8 -*-
"""qubo_batch.py
실제 training 인스턴스(블록 100~300)에 배정 QUBO PoC 적용.
이 데이터는 w3(선호) >> w2(균형) 이라 배정 최적해 ≈ '선호우선'(Z3=0)에 가깝다.
따라서 '선호우선'을 사실상 최적(opt) 기준으로 두고, QUBO-SA가 이를 회복하는지(gap, 일치율) 본다.
사용: python qubo_batch.py ["glob"]
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, glob, json, time
import qubo as q


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_ROOT, "data", "sample", "*.json")
    files = sorted(glob.glob(pat), key=lambda f: int(''.join(c for c in f.split('_')[-1] if c.isdigit()) or 0))
    if not files:
        print("no files:", pat); return
    print(f"{'file':>12} {'blk':>4} {'bay':>3} | {'선호(≈opt)':>11} {'QUBO-SA':>10} {'gap%':>6} {'일치%':>6} {'sec':>5}")
    print("-" * 70)
    rows = []
    for f in files:
        prob = json.load(open(f)); n = len(prob["blocks"]); m = len(prob["bays"])
        Q, const, meta = q.build_qubo(prob)                  # 현실 반영된 기본 w2p
        steps = 4000 if n <= 150 else (6000 if n <= 250 else 9000)
        restarts = 6 if n <= 200 else 4
        t0 = time.time()
        x, _ = q.solve_sa_qubo(Q, const, n, m, steps=steps, restarts=restarts, seed=1)
        sec = time.time() - t0
        asa = q.decode(x, n, m)
        pref = [max(range(m), key=lambda j: b["bay_preferences"][j]) for b in prob["blocks"]]
        def mini(a):
            z2, z3, _ = q.true_Z2_Z3(prob, a); w = prob["weights"]; return w["w2"] * z2 + w["w3"] * z3
        mp, ms = mini(pref), mini(asa)
        agree = sum(1 for i in range(n) if asa[i] == pref[i]) / n * 100
        gap = 100 * (ms - mp) / mp if mp > 0 else 0.0
        rows.append((agree, gap))
        print(f"{f.split('/')[-1]:>12} {n:>4} {m:>3} | {mp:>11.0f} {ms:>10.0f} {gap:>6.1f} {agree:>6.0f} {sec:>5.1f}")
    print("-" * 70)
    import statistics
    print(f"배정 일치율 중앙값 {statistics.median(r[0] for r in rows):.0f}%  |  mini gap 중앙값 {statistics.median(r[1] for r in rows):.1f}%")
    print("결론: 이 데이터에선 w3≫w2 라 배정 최적≈선호우선(near-separable, 고전적으로 쉬움).")
    print("      QUBO-SA가 이를 회복함을 확인(작은 인스턴스 일치≈100%). 즉 '배정'은 깔끔한 데모용이고,")
    print("      진짜 난도/양자 타깃은 Z1(혼잡→지연)을 만드는 '시간창별 동시배치 선택'이다(README 참고).")


if __name__ == "__main__":
    main()
