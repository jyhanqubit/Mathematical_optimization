# -*- coding: utf-8 -*-
"""qubo.py
'블록 -> bay 배정' 하위문제를 QUBO(이진 2차 최적화)로 수식화한다.
QUBO는 D-Wave 어닐러/Qiskit QAOA가 푸는 표준 형태이므로, 동일한 Q를
양자 백엔드(d-wave/qiskit)와 고전 백엔드(SA/exact)에 똑같이 넣어 비교할 수 있다.

변수: x_ij = 1  (블록 i 를 bay j 에 배정)      index = i*m + j
목적(최소화):
  A   * Σ_i (Σ_j x_ij - 1)^2            # 각 블록은 정확히 한 bay (제약 페널티)
  w3  * Σ_ij (Smax_i - S_ij) x_ij       # Z3: 선호 손실
  w2p * Σ_j ( u_j Σ_i L_i x_ij )^2      # Z2 대용: bay별 보정부하 제곱합 -> 균형 유도
(u_j = 평균 bay면적 / bay j 면적,  L_i = workload,  S_ij = preference)
"""
from __future__ import annotations
import itertools, math, random


def instance_arrays(prob):
    bays = prob["bays"]; blocks = prob["blocks"]
    m = len(bays); n = len(blocks)
    areas = [b["width"] * b["height"] for b in bays]
    avg = sum(areas) / m
    u = [avg / a for a in areas]
    L = [b["workload"] for b in blocks]
    S = [b["bay_preferences"] for b in blocks]            # n x m, 합 100
    Smax = [max(s) for s in S]
    return n, m, u, L, S, Smax


def build_qubo(prob, w2p=None, w3=None, A=None):
    """returns (Q dict {(k,l):coeff, k<=l}, const, meta)."""
    n, m, u, L, S, Smax = instance_arrays(prob)
    w = prob.get("weights", {"w2": 1, "w3": 1})
    w3 = w["w3"] if w3 is None else w3
    # 균형 항 가중치 기본값: 원 목적의 w2 규모를 부하제곱합 스케일에 맞춰 축소
    if w2p is None:
        w2p = w.get("w2", 1) / max(1.0, sum(L) ** 2)   # 균형항을 실제 w2 규모로 보정
    # 제약 페널티 A: 목적 변동폭보다 충분히 크게
    if A is None:
        A = w3 * (max(Smax) + 1) + w2p * (max(u) ** 2) * (sum(L) ** 2) + 10.0

    def idx(i, j): return i * m + j
    Q = {}
    def add(k, l, v):
        if k > l: k, l = l, k
        Q[(k, l)] = Q.get((k, l), 0.0) + v

    const = 0.0
    # 1) one-hot 제약: A * (Σ_j x_ij - 1)^2
    for i in range(n):
        const += A * 1.0
        for j in range(m):
            add(idx(i, j), idx(i, j), A * (1 - 2))      # x^2 - 2x = -x  -> -A on diag
        for j in range(m):
            for j2 in range(j + 1, m):
                add(idx(i, j), idx(i, j2), 2 * A)       # 2A cross (same block)
    # 2) Z3 선호 손실 (선형 -> diagonal)
    for i in range(n):
        for j in range(m):
            add(idx(i, j), idx(i, j), w3 * (Smax[i] - S[i][j]))
    # 3) Z2 대용: w2p * Σ_j u_j^2 (Σ_i L_i x_ij)^2
    for j in range(m):
        uj2 = u[j] ** 2
        for i in range(n):
            add(idx(i, j), idx(i, j), w2p * uj2 * (L[i] ** 2))
            for i2 in range(i + 1, n):
                add(idx(i, j), idx(i2, j), w2p * uj2 * 2 * L[i] * L[i2])
    meta = dict(n=n, m=m, u=u, L=L, S=S, Smax=Smax, w2p=w2p, w3=w3, A=A)
    return Q, const, meta


# ----------------------------------------------------------------- 평가
def qubo_energy(Q, const, x):
    e = const
    for (k, l), v in Q.items():
        if k == l:
            e += v * x[k]
        else:
            e += v * x[k] * x[l]
    return e


def decode(x, n, m):
    """x(이진벡터) -> 블록별 bay (one-hot 깨지면 argmax/첫번째로 보정)."""
    assign = []
    for i in range(n):
        chosen = [j for j in range(m) if x[i * m + j] == 1]
        assign.append(chosen[0] if len(chosen) == 1 else (chosen[0] if chosen else 0))
    return assign


def true_Z2_Z3(prob, assign):
    """배정만으로 정해지는 진짜 Z2(max-pair 불균형)와 Z3(선호손실)."""
    n, m, u, L, S, Smax = instance_arrays(prob)
    V = [0.0] * m
    Z3 = 0
    for i, j in enumerate(assign):
        V[j] += L[i]
        Z3 += Smax[i] - S[i][j]
    V = [u[j] * V[j] for j in range(m)]
    Z2 = (max(V) - min(V)) if m > 1 else 0.0
    return Z2, Z3, V


# ----------------------------------------------------------------- 풀이기
def solve_exact_assignment(prob, w2p=None, w3=None):
    """배정 공간(m^n) 전수 탐색으로 QUBO 목적의 최적 배정(작은 n 전용)."""
    n, m, u, L, S, Smax = instance_arrays(prob)
    Q, const, meta = build_qubo(prob, w2p=w2p, w3=w3)
    w3 = meta["w3"]; w2p = meta["w2p"]
    best = None; best_obj = math.inf
    for assign in itertools.product(range(m), repeat=n):
        V = [0.0] * m; z3 = 0
        for i, j in enumerate(assign):
            V[j] += L[i]; z3 += Smax[i] - S[i][j]
        disp = sum((u[j] ** 2) * (V[j] ** 2) for j in range(m))
        obj = w3 * z3 + w2p * disp                      # 제약은 항상 만족(one-hot)
        if obj < best_obj:
            best_obj = obj; best = assign
    return list(best), best_obj


def solve_sa_qubo(Q, const, n, m, steps=20000, restarts=8, seed=0):
    """순수 파이썬 simulated annealing 으로 QUBO 풀이(양자 어닐러의 고전 대용)."""
    rng = random.Random(seed)
    N = n * m
    # 변수별 인접(같은 항에 등장) 미리 모으기
    lin = [0.0] * N
    quad = {}
    for (k, l), v in Q.items():
        if k == l: lin[k] += v
        else:
            quad.setdefault(k, []).append((l, v)); quad.setdefault(l, []).append((k, v))
    best_x = None; best_e = math.inf
    for r in range(restarts):
        # one-hot 초기해
        x = [0] * N
        for i in range(n):
            x[i * m + rng.randrange(m)] = 1
        e = qubo_energy(Q, const, x)

        def contrib(idx_on):
            c = lin[idx_on]
            for (o, v) in quad.get(idx_on, []):
                c += v * x[o]
            return c

        def move_delta(i):
            curj = next(j for j in range(m) if x[i * m + j] == 1)
            newj = rng.randrange(m)
            if newj == curj:
                return None
            x[i * m + curj] = 0
            de = -contrib(i * m + curj)
            x[i * m + newj] = 1
            de += contrib(i * m + newj)
            x[i * m + newj] = 0; x[i * m + curj] = 1     # 원복(평가만)
            return curj, newj, de

        # 온도 초기값: 실제 이동 폭(|de|) 기준으로 설정
        samples = []
        for _ in range(min(80, 5 * n)):
            md = move_delta(rng.randrange(n))
            if md:
                samples.append(abs(md[2]))
        T = (sorted(samples)[len(samples)//2] if samples else 1.0) or 1.0
        cooling = (1e-3) ** (1.0 / max(1, steps))     # 끝에는 거의 0으로 식힘

        for t in range(steps):
            i = rng.randrange(n)
            curj = next(j for j in range(m) if x[i * m + j] == 1)
            newj = rng.randrange(m)
            if newj == curj:
                continue
            x[i * m + curj] = 0
            de = -contrib(i * m + curj)
            x[i * m + newj] = 1
            de += contrib(i * m + newj)
            if de <= 0 or rng.random() < math.exp(-de / max(T, 1e-9)):
                e += de                                 # 채택
            else:
                x[i * m + newj] = 0; x[i * m + curj] = 1  # 기각
            T *= cooling
        if e < best_e:
            best_e = e; best_x = x[:]
    return best_x, best_e


def cur_idx(x, i, m):   # helper (사용 안 함, 가독성용 placeholder)
    return 0
