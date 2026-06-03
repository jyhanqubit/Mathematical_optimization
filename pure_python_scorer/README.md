shapely 없이 대회 utils.py 채점하기
====================================
이 두 파일(polygeom.py, pyshapely_shim.py)을 utils.py 와 같은 폴더에 두고,
utils 보다 먼저 pyshapely_shim 을 import 하면 shapely 설치 없이 채점이 됩니다.

    import pyshapely_shim     # 가짜(순수파이썬) shapely 등록
    import utils
    import json
    prob = json.load(open("instance.json"))
    solution = ...            # 알고리즘 결과
    r = utils.check_feasibility(prob, solution)
    print(r["feasible"], r["objective"])

정확성: 다각형 교차/차집합 면적을 삼각분할+볼록클리핑으로 정확히 계산.
  - 사각형: 해석해와 오차 ~1e-15
  - 오목 다각형(L자 등): Monte Carlo 추정치와 일치
주의: 실제 shapely 가 설치된 ogc2026 환경에서는 이 shim을 쓰지 마세요(원본이 더 빠름).
이 도구는 shapely 설치가 번거로운 곳에서 빠르게 채점/디버깅할 때 유용합니다.
