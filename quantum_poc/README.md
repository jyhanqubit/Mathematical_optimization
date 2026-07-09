# 물류 블록배치 × 양자 PoC: "Hybrid Orchestration"

LG CNS의 Quantum-Augmented PoC와 같은 프레이밍으로, 우리 조선소 블록배치 문제에
양자(quantum) 하위문제를 붙인 개념검증(PoC)이다.

## 0. 가장 먼저: 정직한 메시지
이 PoC는 "양자가 더 빠르다/우월하다"를 주장하지 않는다. 무료로 쓸 수 있는 현재 양자 자원으로는
우리 문제 전체(블록 100개·실수좌표·비정형 다각형)를 풀 수 없고, 고전(classical)이 거의 항상
더 좋은 답을 더 빨리 낸다. 핵심 메시지는 LG CNS와 같다.

  "고전 자원이 큰 문제를 축소·분해하고, 그 작은 하위문제만 양자에 넘긴다 (Hybrid Orchestration)."

## 1. 무엇을 양자로 푸는가: '블록 → bay 배정' 하위문제
- 배정은 본질적으로 이산 선택이라 QUBO(양자 표준형)로 깔끔히 전환됨.
- 우리 목적함수의 Z2(작업 불균형)·Z3(선호 손실)가 '배정만'으로 정의됨 → 양자가 푸는 부분과
  평가지표가 직접 연결.
- 기하/크레인/일정(Z1)은 고전 엔진(greedy/ALNS)이 담당. 역할 분담이 명확.

## 2. 수식 (QUBO)
변수 x_ij = 1 (블록 i 를 bay j 에 배정).
minimize
  A   · Σ_i (Σ_j x_ij − 1)²            # 각 블록 정확히 한 bay (제약 페널티)
  + w3 · Σ_ij (Smax_i − S_ij) x_ij      # Z3 선호 손실
  + w2'· Σ_j ( u_j Σ_i L_i x_ij )²      # Z2 대용: bay 보정부하 제곱합 → 균형 유도
A 는 제약이 깨지지 않도록 충분히 큰 페널티. w2' 를 키우면 균형(Z2↓)·선호손실(Z3↑) 트레이드오프.

## 3. 비용 0원 환경 구성
- 오프라인·무설치 데모: `demo_local.py` (순수 파이썬. 고전 정확해 vs SA로 QUBO 풀이/비교).
- D-Wave 양자 어닐러: 무료 `pip install dwave-ocean-sdk` + Leap 신규 크레딧. `run_dwave.py`
  (접속 실패 시 자동으로 neal 고전 SA 폴백 → 항상 데모 가능).
- Qiskit QAOA: 무료 `pip install qiskit qiskit-optimization qiskit-aer`. `run_qiskit.py`
  (로컬 시뮬레이터 무제한. 변수 많으면 느리므로 작은 인스턴스 권장).
- 채점/기하/스케줄: 이미 보유한 utils.py + 내 모듈 재사용(추가 비용 0).

## 4. 파일
- `qubo.py`              배정 QUBO 빌더 + 평가(decode/Z2/Z3) + 풀이기(exact, SA)
- `demo_local.py`        설치 없이 바로 돌아가는 PoC 데모(고전 정확해 vs QUBO-SA)
- `run_dwave.py`         같은 QUBO를 D-Wave 어닐러로 (무료 크레딧/neal 폴백)
- `run_qiskit.py`        같은 QUBO를 Qiskit QAOA(시뮬레이터)로
- `integrate_pipeline.py` 양자 배정 → 고전 엔진 스케줄 → 진짜 utils 채점(전체 objective)

## 5. 실행 (예)
```
# (1) 무설치 오프라인 데모 — 지금 바로
python demo_local.py
python demo_local.py --w2p 0.5          # 균형 가중치 키워 Z2↓/Z3↑ 트레이드오프 시연

# (2) 무료 양자 백엔드
pip install dwave-ocean-sdk             # 또는: pip install qiskit qiskit-optimization qiskit-aer
python run_dwave.py                     # Leap 토큰 있으면 실제 QPU, 없으면 자동 고전 폴백
python run_qiskit.py

# (3) 하이브리드 전체 파이프라인 채점 (shapely 있는 ogc2026 환경)
python integrate_pipeline.py --backend sa
```

## 6. 검증된 결과 (실제 training 20개 인스턴스, 블록 100~300)
`qubo_batch.py` 로 train/prob_1~20 전체 실행:
- 이 데이터는 **w3(선호 125~200) ≫ w2(균형 4~10)** → 배정 최적해 ≈ '선호우선'(Z3=0)에 가깝고
  near-separable(블록마다 독립적으로 최선호 bay 선택). 즉 배정은 고전적으로 쉬운 하위문제.
- QUBO-SA(양자 어닐러/QAOA의 고전 대용)가 이 최적을 **회복**: 배정 일치율 중앙값 100%,
  mini목적 gap 중앙값 0.0%. 일부 인스턴스(prob_15 −19%, prob_10 −3%)는 미세하게 능가.
- one-hot 제약은 항상 만족(유효).

## 7. PoC의 정직한 결론과 '진짜 양자 타깃'
배정 하위문제는 **수식·인터페이스 검증용 깔끔한 데모**다(QUBO↔양자/고전 백엔드 동일 처리 확인).
다만 이 데이터에선 배정이 고전적으로 trivial 하므로, 양자가 실익을 줄 곳은 아니다.
진짜 난도는 **w1(압도적)을 좌우하는 '시간·공간 혼잡 → 납기지연(Z1)'** 에 있다.
→ 권장 양자 타깃: **시간창별 '동시 배치 블록 선택' QUBO**.
   한 bay·한 혼잡 구간에서 서로 기하적으로 충돌하지 않는 블록 부분집합을 최대로 고르는
   문제(가중 독립집합/패킹 구조)는 충돌로 촘촘히 결합돼 진짜 조합 난도가 있고, QUBO로
   자연스럽게 표현된다. 변수 x_b=1(블록 b를 이 창에 투입), 제약: 충돌쌍 (b,b') 동시선택 금지
   (페널티 A·x_b x_b'), 목적: 납기 임박 블록을 많이/일찍 투입(−Σ value_b x_b). 충돌행렬은
   기존 geometry 엔진으로 사전계산.

## 8. 새 training 데이터와의 연동(버무린 내역)
- `analyze_all.py`(상위 training_tools): 20개 인스턴스 일괄 EDA(규모·가중치·slack·하한).
- `qubo_batch.py`: 20개 전부에 배정 QUBO PoC 적용·집계(위 결과).
- `run_benchmark_batch.py`(training_tools, shapely 환경): baseline vs myalgorithm 일괄 채점.
- 기존 단일-인스턴스 도구(demo_local/run_dwave/run_qiskit/integrate_pipeline)는 train/*.json 도
  그대로 인자로 받는다.
