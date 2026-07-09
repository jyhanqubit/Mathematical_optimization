# 시각화 (Visualization)

결과(배치 레이아웃 + Gantt + 목적값)를 그림으로 본다. shapely 없이도 동작한다.

## 1) 정적 PNG (matplotlib)
```bash
pip install -r requirements-viz.txt
# 해가 있으면 배치+Gantt, 없으면 인스턴스 미리보기
python viz/visualize.py data/sample/synthetic_demo.json data/sample/synthetic_demo_solution.json --day 6 --out viz_out
```
- 왼쪽: 선택한 day 에 각 bay 안에 있는 블록 배치(색=블록).
- 오른쪽: Gantt(막대=점유기간, ▼=납기, 빨강=지연), 점선=현재 day.
- 콘솔에 objective(Z1/Z2/Z3) 출력.

## 2) 브라우저 인터랙티브 (Streamlit), Codespaces 추천
```bash
streamlit run viz/app_streamlit.py
```
- 사이드바에서 인스턴스 선택, 날짜 슬라이더로 배치 변화 확인, 상단에 Z1/Z2/Z3·objective 지표.
- 해가 없으면 "알고리즘으로 해 생성" 버튼(= shapely + competition 파일 필요).
- Codespaces 는 8501 포트를 자동 포워딩해 브라우저 미리보기 URL을 띄운다(devcontainer 설정 포함).

## 3) 해(solution) 만들기
```bash
# shapely + competition(utils.py, baseline_greedy.py) 이 있을 때
python tools/solve_to_json.py data/train/prob_1.json --time 60
# -> data/train/prob_1_solution.json 생성, 위 시각화로 바로 확인
```

## 참고
- 한글이 깨지면 폰트(fonts-noto-cjk)를 설치하면 된다. devcontainer 는 자동 설치한다.
- 대회 공식 GUI(PyQt6 alg_tester)는 데스크톱 X 환경이 필요해 브라우저 Codespaces 에서는
  바로 뜨지 않는다. 브라우저에서는 위 Streamlit 방식을 쓰면 된다.
