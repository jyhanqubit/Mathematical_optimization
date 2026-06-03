# 조선소 선박 블록 배치 최적화
### 공간과 시간을 함께 푸는 운영 최적화 — 데이터 분석 포트폴리오
OGC 2026 · The Grand Shipyard Puzzle / LG CNS AX Optimization Forum 2026

> 🇰🇷 한국어 설명은 아래에 있습니다. **English version is at the bottom ([jump](#english)).**


조선소에서는 큰 배를 여러 블록으로 나눠 만들고, 각 블록을 작업장(bay) 안에서 조립합니다.
이 프로젝트는 블록 하나하나를 **어느 작업장에, 어떤 방향으로, 어디에, 언제 넣고 언제 뺄지**
한꺼번에 정해서 **납기 지연, 작업량 쏠림, 선호 작업장 이탈**을 가장 작게 만드는 문제를 풉니다.
단순 예측이 아니라, 규칙을 지키면서 더 나은 배치를 찾아내는 최적화 프로젝트입니다.

---

## 한눈에 보기

| | |
|---|---|
| **문제** | 비정형 3D 블록을 제한된 작업장에 배치·일정까지 동시에 결정 |
| **목표** | 납기 지연(Z1) · 작업 불균형(Z2) · 선호 손실(Z3)의 가중합 최소화 |
| **접근** | 기하 엔진 → 그리디 초기해 → ALNS 개선 → 일부 구간 MIP |
| **검증** | 대회 공식 채점기로 직접 채점, 채점 재현 정확도 100% |
| **확장** | 배정 부분을 양자(QUBO)로 전환한 하이브리드 PoC |

**대표 성과**
- 자체 목적함수 계산이 대회 채점 코드와 모든 테스트에서 정확히 맞아떨어집니다(재현 100%).
- 만들어낸 해가 채점기의 5단계 검사를 전부 통과했습니다(무효해 없음).
- 어려운 인스턴스에서 공식 baseline보다 목적값을 평균 7.3%, 최대 28.7% 낮췄고, 더 나빠진 경우는 없습니다.
- 외부 라이브러리(shapely) 없이도 공식 채점기를 그대로 돌리는 순수 파이썬 기하 엔진을 만들었습니다.
- 배정 부분을 양자 표준형(QUBO)으로 바꿔, 실제 데이터 20개에서 고전 최적 배정을 그대로 회복했습니다.

---

## 풀어야 하는 문제

블록마다 다음 다섯 가지를 동시에 정합니다.

1. 어느 작업장에 넣을지
2. 어떤 방향으로 돌릴지
3. 작업장 안 어디에 놓을지 (x, y)
4. 언제 넣을지 (ENTRY)
5. 언제 뺄지 (EXIT)

지켜야 하는 규칙은 세 가지입니다. 블록이 작업장 밖으로 나가면 안 되고, 같은 시간 같은 층에서 서로 겹치면
안 되며, 크레인으로 넣고 뺄 때 다른 블록이 길을 막아도 안 됩니다. 비유하면, 들어오고 나가는 시점이
제각각인 테트리스 조각을 빈틈없이 끼우면서 크레인까지 신경 쓰는 셈입니다.

목적함수는 세 항의 가중합입니다.

- **Z1 납기 지연** — 약속한 날보다 늦게 끝난 날수의 합
- **Z2 작업 불균형** — 가장 바쁜 작업장과 한가한 작업장의 보정 작업량 차이
- **Z3 선호 손실** — 가장 선호하는 작업장 대신 다른 곳에 둔 아쉬움의 합

목적값 = w1·Z1 + w2·Z2 + w3·Z3 이며, 데이터에서 w1이 압도적으로 큽니다(1일 지연이 다른 항 수백 점에 맞먹음).
그래서 승부는 사실상 **지연을 얼마나 줄이느냐**에서 갈립니다.

---

## 분석 흐름

데이터 분석가가 일하는 순서 그대로 따라갔습니다.

1. **문제 정의** — 현업 목표를 목적함수와 제약으로 옮깁니다.
2. **데이터 수집·구조화** — 원문 JSON을 작업장·블록·도형 표로 정규화합니다.
3. **탐색적 분석(EDA)** — 규모, 납기 여유, 선호 분포를 보고 무엇이 점수를 좌우하는지 찾습니다.
4. **모델링(최적화)** — 그리디로 초기해를 만들고 ALNS로 개선하며, 막힌 구간은 MIP로 다듬습니다.
5. **평가·검증** — 공식 채점기로 feasibility와 목적값을 직접 확인합니다.
6. **인사이트 도출** — 지연이 어디서 생기고 어떻게 줄어드는지 결론을 정리합니다.

### 분석에서 찾은 핵심
- 지연을 만드는 진짜 원인은 일정이 아니라 **공간 혼잡**입니다. 블록 하나만 놓고 보면 모두 제때 끝낼 수 있지만(지연 하한 0),
  한 작업장에 몰리면 늦게 들어갈 수밖에 없어 지연이 생깁니다. 그래서 **동시에 더 많이 끼워 넣는 패킹**이 핵심 지렛대입니다.
- 납기 여유가 평균 하루 남짓으로 빡빡합니다. 투입이 조금만 늦어도 곧장 지연으로 이어집니다.
- feasibility는 통과/탈락만 있습니다. 규칙 하나만 어겨도 그 인스턴스는 0점이라, **항상 말이 되는 해**를 내는 안정성이 곧 점수입니다.

### 데이터 규모 (실데이터 20개)

| 항목 | 값 |
|---|---|
| 인스턴스 수 | 20 |
| 블록 수 | 100 ~ 300 |
| 작업장(bay) 수 | 2 ~ 5 |
| w1 (납기 가중치) | 8,889 ~ 29,630 (압도적) |
| 평균 납기 여유(slack) | 약 1.4일 |
| 납기 지연 하한 | 0 — 지연은 일정이 아니라 공간 혼잡에서 발생 |


---

## 풀이 방법

| 단계 | 하는 일 | 담당 |
|---|---|---|
| 기하 엔진 (`geometry.py`) | 담기·충돌·크레인 규칙 판정과 날짜순 시뮬레이션 | 제약 |
| 후보 생성 (`candidates.py`) | 놓을 만한 방향·위치만 추려 탐색량을 줄임 | 탐색 효율 |
| 그리디 (`greedy.py`) | 급한 블록부터 빠르게 초기해 생성(항상 통과) | 초기해 |
| ALNS (`alns_improve.py`) | 지연 큰 블록을 빼서 더 이른 시점·덜 붐비는 곳으로 재배치 | 지연 개선 |
| 일부 구간 MIP | 가장 막히는 구간만 상용 솔버로 정밀 재최적화 | 국소 최적 |

진입점은 `myalgorithm.py`입니다. 공식 baseline 해에서 출발해 ALNS로 다듬고, 채점기로 검증한 가장 좋은 해를 돌려줍니다.

---

## 결과

공식 채점기로 직접 측정했습니다.

| 인스턴스 | 공식 baseline | 내 알고리즘 | 변화 |
|---|---|---|---|
| 어려운 사례 A | 162,985 | 157,317 | −3.5% |
| 어려운 사례 B | 30,868 | 27,564 | −10.7% |
| 어려운 사례 C | 90,242 | 64,305 | **−28.7%** |

어려운 묶음 합계로는 7.3% 낮췄고, 쉬운 인스턴스는 baseline이 이미 지연 0이라 같은 값이 나옵니다(더 나빠진 경우 없음).

![공식 baseline 대비 개선 (실데이터 채점)](docs/figures/results_improvement.png)
*그림. 어려운 인스턴스에서 공식 채점기로 측정한 baseline 대비 개선.*


---

## 차별점

- **순수 파이썬 채점 재현** — 공식 채점기는 도형 라이브러리(shapely)에 의존합니다. 다각형 교차·차집합 면적을
  삼각분할과 볼록 클리핑으로 직접 구현해, 라이브러리 없이도 공식 채점기를 그대로 돌립니다. 정확도는 사각형에서
  오차 약 1e-15, 오목 다각형에서 몬테카를로 추정치와 일치하도록 검증했습니다.
- **결과 시각화** — 날짜별 작업장 배치와 Gantt, 목적값 분해를 그림으로 보여줍니다. 정적 이미지와 브라우저
  인터랙티브(Streamlit) 둘 다 제공하며, GitHub Codespaces에서 바로 띄울 수 있습니다.

![배치 레이아웃 + Gantt 예시](docs/figures/layout_example.png)
*그림. 날짜별 배치와 Gantt 예시 — 형식을 보여주는 예시이며 합성 샘플로 렌더링(실데이터 도형은 미공개).*

- **양자 하이브리드 PoC** — 배정 부분을 QUBO로 바꿔 양자(D-Wave/QAOA)와 고전(SA)이 같은 방식으로 풀게 했습니다.
  실데이터 20개에서 고전 최적 배정을 그대로 회복했고(일치율 중앙값 100%), 일부는 미세하게 능가했습니다.
  다만 이 데이터는 선호 가중치가 균형 가중치보다 훨씬 커서 배정 자체가 쉬운 문제라, 양자가 실익을 주는 지점은
  배정이 아니라 혼잡을 만드는 동시배치 선택이라는 결론을 정직하게 담았습니다.

![배정 QUBO 회복률 (실데이터 20개)](docs/figures/qubo_recovery.png)
*그림. 배정 QUBO-SA가 실데이터 20개에서 고전 최적 배정을 회복(대부분 0 이하 = 회복·능가).*


---

## 저장소 구조

```
algorithm/            핵심 알고리즘
  geometry.py           기하·제약 판정 + 날짜순 시뮬레이션
  candidates.py         배치 후보(방향·위치) 생성
  greedy.py             초기해 생성(항상 통과)
  alns_improve.py       ALNS 개선(지연 블록 제거 후 재배치)
  localsearch.py        보조 탐색
  evaluator.py          목적함수 Z1/Z2/Z3 (공식 채점기와 일치 검증)
  myalgorithm.py        제출 진입점
tools/                분석·벤치마크
  analyze_instance.py   단일 인스턴스 분석
  analyze_all.py        폴더 일괄 분석
  run_benchmark.py      단일 인스턴스 baseline 비교
  run_benchmark_batch.py 폴더 일괄 비교
  solve_to_json.py      해를 만들어 파일로 저장
pure_python_scorer/   shapely 없이 공식 채점기 실행
  polygeom.py           순수 파이썬 다각형 면적 계산
  pyshapely_shim.py     가짜 shapely 등록(한 줄로 채점 가능)
quantum_poc/          양자 하이브리드 PoC
  qubo.py               배정 QUBO 빌더 + 풀이기
  demo_local.py         설치 없이 도는 데모
  qubo_batch.py         폴더 일괄 PoC
  run_dwave.py          D-Wave 어닐러 실행
  run_qiskit.py         Qiskit QAOA 실행
  integrate_pipeline.py 배정→스케줄→채점 연결
viz/                  결과 시각화
  visualize.py          배치·Gantt·목적값 이미지
  app_streamlit.py      브라우저 인터랙티브 앱
docs/                 발표·안내 자료
  portfolio_deck.pptx   18장 포트폴리오 발표자료
  beginner_guide_ko.pdf 비전공자용 안내서
data/sample/          공개 가능한 작은 샘플(즉시 실행용)
competition/          대회 제공 파일 자리(직접 채워 넣기)
```

---

## 빠른 시작

설치 없이 동봉한 샘플로 바로 돌아갑니다(아래 셋은 shapely 없이 동작).

```bash
python tools/analyze_all.py             # 샘플 분석
python quantum_poc/demo_local.py        # 배정 QUBO 데모
python viz/visualize.py data/sample/synthetic_demo.json data/sample/synthetic_demo_solution.json --day 6 --out viz_out
```

전체 채점·벤치마크는 대회 파일이 필요합니다.

```bash
pip install -r requirements.txt
python tools/run_benchmark.py
```

shapely 설치가 번거로우면 순수 파이썬 채점기로 대체합니다.

```python
import sys; sys.path.insert(0, "pure_python_scorer")
import pyshapely_shim   # 가짜 shapely 등록 (utils 불러오기 전에)
import utils            # 이제 shapely 없이 동작
```

---

## GitHub Codespaces에서 작업하고 결과 보기

1. 저장소 페이지에서 **Code ▸ Codespaces ▸ Create codespace on main**을 누릅니다.
2. 컨테이너가 뜨면 `.devcontainer` 설정이 의존성(shapely·numpy·matplotlib·streamlit)과 한글 폰트를 자동으로 설치합니다.
3. 채점까지 쓰려면 `competition/`에 `utils.py`·`baseline_greedy.py`를, `data/train/`에 인스턴스를 넣습니다.
4. 브라우저로 결과 보기:
   ```bash
   streamlit run viz/app_streamlit.py
   ```
   8501 포트가 자동으로 열립니다. 날짜 슬라이더로 배치가 어떻게 바뀌는지 봅니다.
5. 이미지로만 보려면 `python viz/visualize.py <인스턴스> [해.json] --day N` 을 씁니다.

해 만들기: `python tools/solve_to_json.py data/train/prob_1.json --time 60`

---

## 대회 제공 파일 (포함하지 않음)

공식 `utils.py`, `baseline_greedy.py`와 training 데이터는 대회 자료라 저장소에 넣지 않았습니다.
직접 받아 `competition/`과 `data/train/`에 넣으면 채점·벤치마크가 모두 동작합니다. 자세한 위치는
각 폴더의 README에 적어 두었습니다.

## 환경

- Python 3.9 이상
- 핵심: `shapely`, `numpy` (`requirements.txt`)
- 시각화: `matplotlib`, `streamlit` (`requirements-viz.txt`)
- 양자(선택): `dwave-ocean-sdk` 또는 `qiskit qiskit-optimization qiskit-aer` — 모두 무료

## 라이선스

MIT. 본인이 작성한 코드에만 적용되며, 대회 제공 코드와 데이터는 포함하지 않고 각 출처 정책을 따릅니다.


---
<a name="english"></a>
# Shipyard Block Placement Optimization
### Joint space–time operations optimization — a data analysis portfolio
OGC 2026 · The Grand Shipyard Puzzle / LG CNS AX Optimization Forum 2026

In a shipyard, a ship is built as many large blocks, and each block is assembled inside a fixed
workspace called a bay. This project decides, for every block at once, **which bay, which orientation,
where (x, y), when to bring it in (ENTRY) and when to take it out (EXIT)** so that **tardiness,
workload imbalance, and preference loss** are as small as possible. It is not a prediction task —
it searches for a better placement while satisfying hard rules.

---

## At a glance

| | |
|---|---|
| **Problem** | Place irregular 3D blocks into limited bays and schedule them together |
| **Goal** | Minimize a weighted sum of tardiness (Z1), workload imbalance (Z2), preference loss (Z3) |
| **Approach** | Geometry engine → greedy start → ALNS improvement → MIP on bottleneck windows |
| **Validation** | Scored with the official checker; objective reproduced exactly (100% match) |
| **Extension** | Hybrid PoC that turns the assignment part into a quantum QUBO |

**Key results**
- The in-house objective matches the official scoring code exactly across every test (100% reproduction).
- Every produced solution passes all five feasibility stages of the checker (zero infeasible solutions).
- On hard instances the objective drops by 7.3% on average and up to 28.7% versus the official baseline, with no regressions.
- A pure-Python geometry engine runs the official checker without the external library (shapely).
- The assignment subproblem maps cleanly to a QUBO and recovers the classical optimum on all 20 real instances.

---

## The problem

For each block, five decisions are made at the same time:

1. which bay
2. which orientation
3. where inside the bay (x, y)
4. when to bring it in (ENTRY)
5. when to take it out (EXIT)

Three rules must hold: a block stays fully inside its bay, blocks on the same layer never overlap at the
same time, and the crane path is never blocked when a block enters or leaves. Think of it as Tetris where
each piece has its own arrival and departure time and the crane matters too.

The objective is a weighted sum:

- **Z1 — tardiness:** total days finished later than promised
- **Z2 — workload imbalance:** the gap in adjusted workload between the busiest and least busy bay
- **Z3 — preference loss:** the cost of placing a block somewhere other than its most preferred bay

Objective = w1·Z1 + w2·Z2 + w3·Z3. In the data, w1 dominates by far (one day of delay rivals hundreds of
points elsewhere), so the game is mostly about **reducing tardiness**.

---

## Analysis workflow

The project follows the usual analyst workflow:

1. **Define the problem** — translate the business goal into an objective and constraints.
2. **Collect and structure data** — normalize the raw JSON into bay, block, and shape tables.
3. **Explore (EDA)** — study size, schedule slack, and preference spread to find what drives the score.
4. **Model (optimize)** — build a greedy start, improve with ALNS, and refine tight windows with MIP.
5. **Validate** — check feasibility and objective with the official scorer directly.
6. **Draw insights** — explain where delay comes from and how it shrinks.

### What the analysis found
- Delay is driven by **spatial congestion**, not the schedule. Each block alone could finish on time
  (tardiness lower bound is zero), but when blocks pile into one bay they enter late. So **packing more
  blocks concurrently** is the main lever.
- Schedule slack averages about one day, so even a slightly late entry turns into delay.
- Feasibility is pass-or-fail: a single broken rule scores zero on that instance, so **always returning a
  valid solution** is itself worth points.

### Data at a glance (20 real instances)

| Field | Value |
|---|---|
| Instances | 20 |
| Blocks | 100 – 300 |
| Bays | 2 – 5 |
| w1 (tardiness weight) | 8,889 – 29,630 (dominant) |
| Mean schedule slack | ~1.4 days |
| Tardiness lower bound | 0 — delay comes from spatial congestion, not the schedule |


---

## How it is solved

| Stage | What it does | Role |
|---|---|---|
| Geometry engine (`geometry.py`) | Containment, collision, crane checks + day-by-day simulation | Constraints |
| Candidate generation (`candidates.py`) | Keeps only sensible orientation/position options | Search efficiency |
| Greedy (`greedy.py`) | Builds a fast initial solution that always passes | Initial solution |
| ALNS (`alns_improve.py`) | Removes tardy blocks and repacks them earlier / in less crowded bays | Tardiness |
| MIP on windows | Re-optimizes the most congested window with a commercial solver | Local optimum |

The entry point is `myalgorithm.py`: it starts from the official baseline solution, improves it with ALNS,
and returns the best solution that the checker confirms as feasible.

---

## Results

Measured with the official checker.

| Instance | Official baseline | This algorithm | Change |
|---|---|---|---|
| Hard case A | 162,985 | 157,317 | −3.5% |
| Hard case B | 30,868 | 27,564 | −10.7% |
| Hard case C | 90,242 | 64,305 | **−28.7%** |

The hard set drops by 7.3% in total. Easy instances tie because the baseline already reaches zero tardiness
(never worse).

![Improvement vs baseline (real-data scoring)](docs/figures/results_improvement.png)
*Improvement over the official baseline on hard instances, measured with the official checker.*


---

## What makes it stand out

- **Pure-Python scoring** — the official checker depends on a geometry library (shapely). I implemented
  polygon intersection and difference areas with triangulation and convex clipping, so the official checker
  runs without that library. Accuracy was verified to about 1e-15 on rectangles and against Monte Carlo on
  concave polygons.
- **Result visualization** — bay layout per day, a Gantt chart, and an objective breakdown, as both static
  images and a browser app (Streamlit) that opens directly in GitHub Codespaces.

![Layout + Gantt example](docs/figures/layout_example.png)
*Layout-per-day and Gantt example — a format demo rendered on the synthetic sample (real shapes not published).*

- **Quantum hybrid PoC** — the assignment part becomes a QUBO so a quantum solver (D-Wave/QAOA) and a
  classical one (SA) solve it the same way. It recovered the classical optimum on all 20 real instances
  (median agreement 100%) and occasionally beat it. Honestly, though, preference weight far outweighs balance
  weight here, so assignment is an easy subproblem — the place quantum could actually help is the concurrent
  co-placement that creates congestion, not assignment.

![QUBO recovery on 20 real instances](docs/figures/qubo_recovery.png)
*Assignment QUBO-SA recovers the classical optimum across 20 real instances (mostly at or below zero = recover/beat).*


---

## Repository layout

```
algorithm/            core algorithm
  geometry.py           constraint checks + day-by-day simulation
  candidates.py         placement candidates (orientation, position)
  greedy.py             initial solution (always feasible)
  alns_improve.py       ALNS improvement (remove tardy blocks, repack)
  localsearch.py        auxiliary search
  evaluator.py          objective Z1/Z2/Z3 (matches the official checker)
  myalgorithm.py        submission entry point
tools/                analysis & benchmarking
  analyze_instance.py   single-instance analysis
  analyze_all.py        batch analysis over a folder
  run_benchmark.py      single-instance comparison vs baseline
  run_benchmark_batch.py batch comparison
  solve_to_json.py      produce a solution and save it
pure_python_scorer/   run the official checker without shapely
  polygeom.py           pure-Python polygon area computation
  pyshapely_shim.py     register a fake shapely (one import enables scoring)
quantum_poc/          quantum hybrid PoC
  qubo.py               assignment QUBO builder + solvers
  demo_local.py         runs with no installation
  qubo_batch.py         batch PoC over a folder
  run_dwave.py          D-Wave annealer
  run_qiskit.py         Qiskit QAOA
  integrate_pipeline.py assignment → schedule → scoring
viz/                  result visualization
  visualize.py          layout / Gantt / objective images
  app_streamlit.py      interactive browser app
docs/                 deck & guide
  portfolio_deck.pptx   18-slide portfolio deck
  beginner_guide_ko.pdf beginner guide (Korean)
data/sample/          a small public sample (runs out of the box)
competition/          slot for competition-provided files (add your own)
```

---

## Quickstart

The bundled sample runs with no setup (these three need no shapely):

```bash
python tools/analyze_all.py
python quantum_poc/demo_local.py
python viz/visualize.py data/sample/synthetic_demo.json data/sample/synthetic_demo_solution.json --day 6 --out viz_out
```

Full scoring and benchmarking need the competition files:

```bash
pip install -r requirements.txt
python tools/run_benchmark.py
```

If installing shapely is inconvenient, use the pure-Python scorer:

```python
import sys; sys.path.insert(0, "pure_python_scorer")
import pyshapely_shim   # register the fake shapely (before importing utils)
import utils            # now works without shapely
```

---

## Working in GitHub Codespaces

1. On the repo page, choose **Code ▸ Codespaces ▸ Create codespace on main**.
2. Once the container starts, `.devcontainer` installs the dependencies (shapely, numpy, matplotlib,
   streamlit) and Korean fonts automatically.
3. For scoring, drop `utils.py` and `baseline_greedy.py` into `competition/` and instances into `data/train/`.
4. See results in the browser:
   ```bash
   streamlit run viz/app_streamlit.py
   ```
   Port 8501 forwards automatically; use the day slider to watch the layout change.
5. For images only, run `python viz/visualize.py <instance> [solution.json] --day N`.

Make a solution: `python tools/solve_to_json.py data/train/prob_1.json --time 60`

---

## Competition files (not included)

The official `utils.py`, `baseline_greedy.py`, and the training data are competition material and are not
included. Add them to `competition/` and `data/train/` to enable scoring and benchmarking. Each folder's
README explains where things go.

## Environment

- Python 3.9+
- Core: `shapely`, `numpy` (`requirements.txt`)
- Visualization: `matplotlib`, `streamlit` (`requirements-viz.txt`)
- Quantum (optional): `dwave-ocean-sdk` or `qiskit qiskit-optimization qiskit-aer` — all free

## License

MIT, for the code I wrote. Competition-provided code and data are not included and follow their own terms.
