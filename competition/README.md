# competition/

대회가 제공한 파일을 여기에 두세요 (저장소에는 포함하지 않음 / `.gitignore` 처리):
- `utils.py` — 공식 채점기(check_feasibility). shapely 필요.
- `baseline_greedy.py` — 공식 baseline.

`tools/`·`quantum_poc/`의 스크립트는 이 폴더를 자동으로 import 경로에 추가하므로,
파일만 넣으면 `import utils`, `import baseline_greedy` 가 동작합니다.

shapely 설치가 어려우면 `pure_python_scorer/`의 `pyshapely_shim`으로 대체 가능합니다.
