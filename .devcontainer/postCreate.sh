#!/usr/bin/env bash
set -e
# 한글 폰트(시각화) + 시스템 라이브러리
sudo apt-get update -y && sudo apt-get install -y fonts-noto-cjk libgl1 || true
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-viz.txt
echo ""
echo "환경 준비 완료."
echo "  - 대회 채점/벤치마크가 필요하면: competition/ 에 utils.py, baseline_greedy.py 를 넣으세요."
echo "  - 대회 training 데이터: data/train/ 에 prob_*.json 을 넣으세요."
echo "  - 시각화 실행:  streamlit run viz/app_streamlit.py"
