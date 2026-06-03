"""evaluator.py
목적함수와 평가지표 계산. 문제정의서 1.7절 수식을 그대로 구현.

    minimize  w1*Z1 + w2*Z2 + w3*Z3

  Z1 = sum_i  T_i,           T_i = max(0, EXIT_i - D_i)            (총 납기지연)
  Z2 = (workload imbalance)                                        (작업량 불균형)
  Z3 = sum_i (Smax_i - S_{i, j(i)}),  Smax_i = max_j S_ij          (선호도 손실)

  u_j = ( (sum_k W_k*H_k) / m ) / (W_j*H_j)        # 큰 bay일수록 가중치 작음
  V_j = u_j * sum_{i in N(j)} L_i                  # bay별 보정 workload
  Z2  = max_{j1!=j2} |V_j1 - V_j2|   (= max V - min V)

[Z2 sqrt 여부 — 확정] 문제정의서 Figure 9의 테스터 출력
   (objective=1627711.075, T=56, L=625.9075, P=427, weights w1=26667/w2=10/w3=300)을
   역산하면 56*26667 + 10*625.9075 + 300*427 = 1627711.075 로 정확히 일치한다.
   즉 Z2 = max|V_j1 - V_j2| 이며 sqrt가 없다(원문의 큰 기호는 절댓값 괄호).
   따라서 기본값 z2_sqrt=False. 그래도 제출 전 utils.py 로 한 번 더 대조 권장.
"""
from __future__ import annotations
import math


def derive_from_solution(solution):
    """solution operations -> block별 entry/exit/bay/orient."""
    entry, exit_, bay, orient = {}, {}, {}, {}
    for d_str, ops in solution.get("operations", {}).items():
        d = int(d_str)
        for op in ops:
            b = op["block_id"]
            if op["type"] == "ENTRY":
                entry[b] = d
                bay[b] = op["bay_id"]
                orient[b] = op["orient_idx"]
            else:  # EXIT
                exit_[b] = d
    return entry, exit_, bay, orient


def bay_weights(prob_info):
    """u_j = (평균 bay 면적) / (bay j 면적)."""
    areas = [bj["width"] * bj["height"] for bj in prob_info["bays"]]
    m = len(areas)
    avg = sum(areas) / m
    return [avg / a for a in areas]


def compute(prob_info, solution, z2_sqrt=False):
    blocks = prob_info["blocks"]
    bays = prob_info["bays"]
    m = len(bays)
    w = prob_info["weights"]
    entry, exit_, bay, orient = derive_from_solution(solution)

    # --- Z1: total tardiness
    Z1 = 0
    for i, blk in enumerate(blocks):
        if i in exit_:
            Z1 += max(0, exit_[i] - blk["due_date"])

    # --- Z2: workload imbalance
    u = bay_weights(prob_info)
    load = [0.0] * m
    for i, blk in enumerate(blocks):
        if i in bay:
            load[bay[i]] += blk["workload"]
    V = [u[j] * load[j] for j in range(m)]
    inner = (max(V) - min(V)) if m > 1 else 0.0
    Z2 = math.sqrt(inner) if z2_sqrt else inner

    # --- Z3: preference penalty
    Z3 = 0
    for i, blk in enumerate(blocks):
        if i in bay:
            smax = max(blk["bay_preferences"])
            Z3 += smax - blk["bay_preferences"][bay[i]]

    obj = w["w1"] * Z1 + w["w2"] * Z2 + w["w3"] * Z3
    tardy = sum(1 for i, b in enumerate(blocks)
                if i in exit_ and exit_[i] > b["due_date"])
    return {"objective": obj, "Z1": Z1, "Z2": Z2, "Z3": Z3,
            "weighted": {"w1Z1": w["w1"] * Z1, "w2Z2": w["w2"] * Z2,
                         "w3Z3": w["w3"] * Z3},
            "tardy_blocks": tardy, "bay_load": V}
