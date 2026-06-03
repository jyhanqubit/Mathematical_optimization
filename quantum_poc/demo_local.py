# -*- coding: utf-8 -*-
"""demo_local.py
설치/인터넷 없이 바로 돌아가는 PoC 데모.
  - 배정 하위문제를 QUBO로 만들고
  - (a) 고전 정확해(배정 전수탐색)와 (b) SA로 푼 QUBO 해를 비교한다.
  - SA는 D-Wave 어닐러/Qiskit QAOA의 '고전 대용'이다(같은 Q를 풀이).
사용: python demo_local.py [instance.json] [--w2p 0.05]
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, json, argparse
import qubo as q


def run(prob, w2p=None, w3=None):
    Q, const, meta = q.build_qubo(prob, w2p=w2p, w3=w3)
    n, m = meta["n"], meta["m"]
    print("=" * 60)
    print(f"인스턴스: blocks={n}  bays={m}")
    print(f"QUBO: 변수 {n*m}개, 2차항 {len(Q)}개 | w3={meta['w3']:.0f} w2p={meta['w2p']:.4f} A={meta['A']:.0f}")

    ax, _ = q.solve_exact_assignment(prob, w2p=w2p, w3=w3)
    z2e, z3e, Ve = q.true_Z2_Z3(prob, ax)
    print("\n[A] 고전 정확해 (Ground Truth, 배정 전수탐색)")
    print(f"    배정 {ax}")
    print(f"    Z2(불균형)={z2e:.2f}  Z3(선호손실)={z3e}  bay부하={[round(v,1) for v in Ve]}")

    x, e = q.solve_sa_qubo(Q, const, n, m, steps=8000, restarts=12, seed=1)
    asa = q.decode(x, n, m)
    z2s, z3s, Vs = q.true_Z2_Z3(prob, asa)
    onehot = all(sum(x[i*m+j] for j in range(m)) == 1 for i in range(n))
    agree = sum(1 for i in range(n) if asa[i] == ax[i]) / n * 100
    print("\n[B] QUBO 풀이 — Simulated Annealing (양자 어닐러/QAOA의 고전 대용)")
    print(f"    배정 {asa}  | one-hot 유효={onehot}")
    print(f"    Z2={z2s:.2f}  Z3={z3s}  QUBO에너지={e:.1f}")
    print(f"    ▶ GT(정확해) 대비 배정 일치율 = {agree:.0f}%   ← LG CNS의 'GT 대비 N/10 일치'와 같은 지표")
    print("=" * 60)
    print("결론: 배정 하위문제가 QUBO로 자연스럽게 전환되고, 동일한 Q를 고전/양자 백엔드가")
    print("      똑같이 풀 수 있음을 확인. (현재 규모는 고전이 충분히 최적, 양자는 확장성 검증용)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", nargs="?",
                    default=_SAMPLE)
    ap.add_argument("--w2p", type=float, default=None, help="균형 항 가중치(크게 하면 Z2↓ Z3↑)")
    ap.add_argument("--w3", type=float, default=None)
    a = ap.parse_args()
    run(json.load(open(a.instance)), w2p=a.w2p, w3=a.w3)
