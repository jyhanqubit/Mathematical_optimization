# -*- coding: utf-8 -*-
"""run_benchmark.py
ogc2026 conda 환경(= shapely 포함)에서, baseline 폴더(utils.py, baseline_greedy.py가 있는 곳)에
내 모듈들과 함께 두고 실행한다. 주어진 인스턴스에 대해 baseline 과 myalgorithm 을
'진짜' utils.check_feasibility 로 채점·비교한다.

사용 예:
  conda activate ogc2026
  cd baseline                       # utils.py, baseline_greedy.py 위치
  python run_benchmark.py ../alg_tester/example/example_B2_b10.json --time 60
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, json, time, argparse
import utils
import baseline_greedy
import myalgorithm


def report(prob, sol, label):
    r = utils.check_feasibility(prob, sol)
    if r["feasible"]:
        print(f"  {label:12s}: FEASIBLE  obj={r['objective']:.1f}  "
              f"(Z1={r['obj1']:.1f}  Z2={r['obj2']:.2f}  Z3={r['obj3']:.0f})")
    else:
        v = r["violations"][0] if r["violations"] else ""
        print(f"  {label:12s}: INFEASIBLE (stage {r['stage']})  {v}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance", help="problem instance JSON path")
    ap.add_argument("--time", type=float, default=60.0, help="time limit (s)")
    args = ap.parse_args()

    prob = json.load(open(args.instance))
    print(f"instance={prob.get('name')}  blocks={len(prob['blocks'])}  "
          f"bays={len(prob['bays'])}  timelimit={args.time}s")

    t = time.time(); sb = baseline_greedy.greedyalgorithm(prob, args.time)
    rb = report(prob, sb, "baseline"); print(f"     (elapsed {time.time()-t:.1f}s)")

    t = time.time(); sm = myalgorithm.algorithm(prob, args.time)
    rm = report(prob, sm, "myalgorithm"); print(f"     (elapsed {time.time()-t:.1f}s)")

    if rb["feasible"] and rm["feasible"] and rb["objective"] > 0:
        imp = 100.0 * (rb["objective"] - rm["objective"]) / rb["objective"]
        print(f"\n  improvement vs baseline: {imp:+.1f}%  "
              f"(baseline {rb['objective']:.0f} -> myalgorithm {rm['objective']:.0f})")


if __name__ == "__main__":
    main()
