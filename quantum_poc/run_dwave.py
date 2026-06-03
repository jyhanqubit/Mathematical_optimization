# -*- coding: utf-8 -*-
"""run_dwave.py
같은 배정 QUBO를 'D-Wave 양자 어닐러'로 푼다. (무료: D-Wave Leap 신규 크레딧)
인터넷/계정이 없으면 자동으로 dwave-neal(고전 SA)로 폴백한다.

설치(무료):  pip install dwave-ocean-sdk
인증:        dwave config create     (Leap 토큰 입력)  또는 환경변수 DWAVE_API_TOKEN
실행:        python run_dwave.py [instance.json]
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


def to_bqm(Q, const):
    import dimod
    lin, quad = {}, {}
    for (k, l), v in Q.items():
        if k == l:
            lin[k] = lin.get(k, 0.0) + v
        else:
            quad[(k, l)] = quad.get((k, l), 0.0) + v
    return dimod.BinaryQuadraticModel(lin, quad, const, dimod.BINARY)


def solve(Q, const, num_reads=200):
    bqm = to_bqm(Q, const)
    # 1) 진짜 양자 어닐러 시도
    try:
        from dwave.system import DWaveSampler, EmbeddingComposite
        sampler = EmbeddingComposite(DWaveSampler())     # Leap 토큰 필요
        res = sampler.sample(bqm, num_reads=num_reads, label="OGC2026-assignment-PoC")
        backend = "D-Wave QPU (양자 어닐러)"
    except Exception as ex:
        # 2) 폴백: 고전 SA (neal)
        try:
            import neal
            sampler = neal.SimulatedAnnealingSampler()
            res = sampler.sample(bqm, num_reads=num_reads)
            backend = f"neal SA 폴백 (양자 접속 실패: {type(ex).__name__})"
        except Exception:
            # 3) 최후 폴백: dimod 정확/SA
            import dimod
            sampler = dimod.SimulatedAnnealingSampler() if hasattr(dimod, "SimulatedAnnealingSampler") \
                else dimod.ExactSolver()
            res = sampler.sample(bqm)
            backend = "dimod 폴백"
    best = res.first
    return best.sample, best.energy, backend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", nargs="?",
                    default=_SAMPLE)
    a = ap.parse_args()
    prob = json.load(open(a.instance))
    Q, const, meta = q.build_qubo(prob)
    n, m = meta["n"], meta["m"]
    sample, energy, backend = solve(Q, const)
    x = [int(sample[k]) for k in range(n * m)]
    assign = q.decode(x, n, m)
    z2, z3, V = q.true_Z2_Z3(prob, assign)
    print(f"backend = {backend}")
    print(f"배정 = {assign}")
    print(f"Z2={z2:.2f}  Z3={z3}  QUBO에너지={energy:.2f}")
    print("※ 같은 Q를 demo_local.py(고전)와 비교하면 동일 인터페이스 검증이 됩니다.")


if __name__ == "__main__":
    main()
