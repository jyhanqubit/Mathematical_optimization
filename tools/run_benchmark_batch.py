# -*- coding: utf-8 -*-
"""run_benchmark_batch.py
training 폴더 전체에 대해 baseline vs myalgorithm 을 '진짜' utils.check_feasibility 로 채점·집계.
실행 환경: ogc2026 conda(=shapely). utils.py / baseline_greedy.py / 내 모듈(myalgorithm 등)과
같은 폴더에 두고 실행.
사용: python run_benchmark_batch.py "train/prob_*.json" --time 60
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, glob, json, time, argparse
import utils, baseline_greedy, myalgorithm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glob", nargs="?", default="train/prob_*.json")
    ap.add_argument("--time", type=float, default=60.0)
    a = ap.parse_args()
    files = sorted(glob.glob(a.glob), key=lambda f: int(''.join(c for c in f.split('_')[-1] if c.isdigit()) or 0))
    print(f"{'file':>14} {'blk':>4} | {'baseline':>12} {'myalgorithm':>12} {'gain%':>7} | feas")
    print("-" * 64)
    tb = tm = 0.0; feasB = feasM = 0; wins = 0
    for f in files:
        prob = json.load(open(f)); n = len(prob["blocks"])
        sb = baseline_greedy.greedyalgorithm(prob, a.time); rb = utils.check_feasibility(prob, sb)
        sm = myalgorithm.algorithm(prob, a.time); rm = utils.check_feasibility(prob, sm)
        ob = rb["objective"] if rb["feasible"] else float("inf")
        om = rm["objective"] if rm["feasible"] else float("inf")
        feasB += rb["feasible"]; feasM += rm["feasible"]
        g = 100 * (ob - om) / ob if (rb["feasible"] and rm["feasible"] and ob > 0) else 0.0
        if rb["feasible"]: tb += ob
        if rm["feasible"]: tm += om
        if rm["feasible"] and om <= ob + 1e-9: wins += 1
        bs = f"{ob:.0f}" if rb["feasible"] else "INFEAS"
        ms = f"{om:.0f}" if rm["feasible"] else "INFEAS"
        print(f"{f.split('/')[-1]:>14} {n:>4} | {bs:>12} {ms:>12} {g:>6.1f}% | {rm['feasible']}")
    print("-" * 64)
    print(f"feasible: baseline {feasB}/{len(files)}, myalgorithm {feasM}/{len(files)}")
    if tb > 0:
        print(f"합계 objective: baseline {tb:.0f} -> myalgorithm {tm:.0f}  (총 {100*(tb-tm)/tb:+.1f}%)")
    print(f"myalgorithm이 baseline 이상: {wins}/{len(files)} (악화 없음 확인)")


if __name__ == "__main__":
    main()
