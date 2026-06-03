# data/

- `sample/synthetic_demo.json` — 공개 가능한 작은 합성 인스턴스(12 블록·3 bay). 코드 즉시 실행용.
- `train/` — **대회 training 데이터를 직접 넣으세요** (prob_1.json ... prob_20.json).
  대회 자료이므로 저장소에는 포함하지 않으며 `.gitignore` 처리되어 있습니다.

배치 도구 실행 예:
```
python tools/analyze_all.py "data/train/prob_*.json"
python quantum_poc/qubo_batch.py "data/train/prob_*.json"
```
