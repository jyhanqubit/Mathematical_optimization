# -*- coding: utf-8 -*-
"""analyze_all.py
폴더 안 모든 인스턴스를 한 번에 EDA. shapely 불필요.
사용: python analyze_all.py "train/prob_*.json"
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _d in ('algorithm', 'competition', 'pure_python_scorer', 'quantum_poc'):
    _p = os.path.join(_ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
_SAMPLE = os.path.join(_ROOT, 'data', 'sample', 'synthetic_demo.json')

import sys, glob, json, statistics


def main():
    pat = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_ROOT, "data", "sample", "*.json")
    files = sorted(glob.glob(pat), key=lambda f: int(''.join(c for c in f.split('_')[-1] if c.isdigit()) or 0))
    if not files:
        print("no files:", pat); return
    print(f"{'file':>14} {'blk':>4} {'bay':>3} {'w1':>6} {'w2':>4} {'w3':>4} "
          f"{'slack m/μ/M':>12} {'neg':>3} {'LBtard':>6} {'hz':>4}")
    print("-" * 78)
    blks, bays, w1s = [], [], []
    for f in files:
        d = json.load(open(f)); B = d["blocks"]; M = d["bays"]; w = d["weights"]
        sl = [b["due_date"] - b["release_time"] - b["processing_time"] for b in B]
        neg = sum(1 for s in sl if s < 0)
        lb = sum(max(0, b["release_time"] + b["processing_time"] - b["due_date"]) for b in B)
        hz = max(max(b["due_date"] for b in B), max(b["release_time"] + b["processing_time"] for b in B))
        blks.append(len(B)); bays.append(len(M)); w1s.append(w["w1"])
        print(f"{f.split('/')[-1]:>14} {len(B):>4} {len(M):>3} {w['w1']:>6} {w['w2']:>4} {w['w3']:>4} "
              f"{min(sl):>3}/{statistics.mean(sl):>3.1f}/{max(sl):>2} {neg:>3} {lb:>6} {hz:>4}")
    print("-" * 78)
    print(f"인스턴스 {len(files)}개 | blocks {min(blks)}~{max(blks)} | bays {min(bays)}~{max(bays)} "
          f"| w1 {min(w1s)}~{max(w1s)}")
    print("관찰: w1(납기)이 압도적, slack 작음, LBtard=0(지연은 순수 혼잡에서 발생) → 동시 패킹이 핵심.")


if __name__ == "__main__":
    main()
