# -*- coding: utf-8 -*-
"""run_qiskit.py
같은 배정 QUBO를 'Qiskit QAOA(게이트형 양자 알고리즘)'로 푼다.
로컬 시뮬레이터는 무료·무제한. 실제 IBM 양자칩도 무료 티어 사용 가능.

설치(무료):  pip install qiskit qiskit-optimization qiskit-aer
실행:        python run_qiskit.py [instance.json]
주의: QAOA 시뮬레이션은 변수 수가 커지면 급격히 느려진다(양자 시뮬레이터 한계).
      PoC는 작은 인스턴스(블록 ~12개, bay 2~3개)로 시연하는 것을 권장.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", nargs="?",
                    default=_SAMPLE)
    ap.add_argument("--reps", type=int, default=2, help="QAOA layer 수 p")
    a = ap.parse_args()
    prob = json.load(open(a.instance))
    Q, const, meta = q.build_qubo(prob)
    n, m = meta["n"], meta["m"]

    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.converters import QuadraticProgramToQubo
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit.primitives import Sampler
    from qiskit_optimization.algorithms import MinimumEigenOptimizer

    qp = QuadraticProgram("assignment")
    for k in range(n * m):
        qp.binary_var(name=f"x{k}")
    linear = {}
    quadratic = {}
    for (k, l), v in Q.items():
        if k == l:
            linear[f"x{k}"] = linear.get(f"x{k}", 0.0) + v
        else:
            quadratic[(f"x{k}", f"x{l}")] = v
    qp.minimize(constant=const, linear=linear, quadratic=quadratic)

    qaoa = QAOA(sampler=Sampler(), optimizer=COBYLA(maxiter=100), reps=a.reps)
    solver = MinimumEigenOptimizer(qaoa)
    res = solver.solve(qp)

    x = [int(round(res.x[k])) for k in range(n * m)]
    assign = q.decode(x, n, m)
    z2, z3, V = q.true_Z2_Z3(prob, assign)
    print("backend = Qiskit QAOA (Sampler 시뮬레이터)")
    print(f"배정 = {assign}")
    print(f"Z2={z2:.2f}  Z3={z3}  목적값(QUBO)={res.fval:.2f}")
    print("※ demo_local.py(고전 정확해)와 배정 일치율을 비교하면 'GT 대비 일치' 지표가 됩니다.")


if __name__ == "__main__":
    main()
