# -*- coding: utf-8 -*-
"""solve_to_json.py — myalgorithm 으로 해를 만들어 <instance>_solution.json 으로 저장.
실행 환경: shapely + competition(utils.py, baseline_greedy.py) 필요.
사용: python tools/solve_to_json.py data/train/prob_1.json --time 60
"""
import os, sys, json, argparse
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ("algorithm", "competition"):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time", type=float, default=60.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import myalgorithm
    prob = json.load(open(a.instance))
    sol = myalgorithm.algorithm(prob, a.time)
    out = a.out or a.instance.replace(".json", "_solution.json")
    json.dump(sol, open(out, "w"))
    print("saved", out)
    try:
        import utils
        r = utils.check_feasibility(prob, sol)
        print("feasible:", r["feasible"], "| objective:", round(r["objective"], 1) if r["feasible"] else None)
    except Exception as e:
        print("utils 채점 생략:", type(e).__name__)

if __name__ == "__main__":
    main()
