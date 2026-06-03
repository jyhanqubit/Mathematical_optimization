# -*- coding: utf-8 -*-
"""app_streamlit.py — 브라우저 인터랙티브 시각화 (Codespaces 친화)
실행:  streamlit run viz/app_streamlit.py
  - 인스턴스 선택 → 해(solution) 로드/생성 → 날짜 슬라이더로 배치 변화 + Gantt + 목적값 확인.
  - 해 파일이 있으면 로드, 없고 알고리즘 실행 가능(shapely+competition)하면 버튼으로 생성,
    둘 다 없으면 인스턴스 미리보기.
"""
import os, sys, glob, json
import streamlit as st
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ("algorithm", "competition", "viz"):
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
import visualize as V

st.set_page_config(page_title="조선소 블록 배치 시각화", layout="wide")
st.title("조선소 선박 블록 배치 — 결과 시각화")

# --- 인스턴스 선택 ---
insts = sorted(glob.glob(os.path.join(ROOT, "data", "**", "*.json"), recursive=True))
insts = [f for f in insts if "_solution" not in f]
if not insts:
    st.warning("data/ 아래에 인스턴스 JSON이 없습니다."); st.stop()
labels = [os.path.relpath(f, ROOT) for f in insts]
sel = st.sidebar.selectbox("인스턴스", labels)
inst_path = os.path.join(ROOT, sel)
prob = json.load(open(inst_path))

# --- 해 확보: 같은 이름 _solution.json → 알고리즘 생성 → 없음 ---
sol_path = inst_path.replace(".json", "_solution.json")
info = {}
src = "없음"
if os.path.exists(sol_path):
    info = V.parse_solution(json.load(open(sol_path))); src = os.path.basename(sol_path)

with st.sidebar:
    st.caption(f"현재 해: **{src}**")
    if st.button("알고리즘으로 해 생성 (shapely+competition 필요)"):
        try:
            import myalgorithm
            with st.spinner("푸는 중..."):
                sol = myalgorithm.algorithm(prob, 30)
            json.dump(sol, open(sol_path, "w"))
            info = V.parse_solution(sol); src = "생성됨"
            st.success("해 생성 완료")
        except Exception as e:
            st.error(f"생성 실패: {type(e).__name__}: {e}")

# --- 본문 ---
if info:
    o = V.objective(prob, info)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("objective", f"{o['obj']:.0f}")
    c2.metric("Z1 납기지연", f"{o['Z1']}")
    c3.metric("Z2 불균형", f"{o['Z2']:.1f}")
    c4.metric("Z3 선호손실", f"{o['Z3']}")
    days = sorted({d.get("entry", 0) for d in info.values()} | {d.get("exit", 0) for d in info.values()})
    lo, hi = min(days), max(days)
    day = st.slider("날짜 (day)", int(lo), int(hi), int((lo + hi) // 2))
    left, right = st.columns(2)
    with left:
        fig1, ax1 = plt.subplots(figsize=(6, 5)); V.draw_layout(prob, info, day, ax1)
        st.pyplot(fig1)
    with right:
        fig2, ax2 = plt.subplots(figsize=(6, 5)); V.draw_gantt(prob, info, ax2, day=day)
        st.pyplot(fig2)
else:
    st.info("해가 없어 인스턴스 미리보기를 표시합니다. 사이드바에서 해를 생성하거나 *_solution.json 을 두세요.")
    fig, ax = plt.subplots(figsize=(7, 5))
    M = prob["bays"]
    from matplotlib.patches import Rectangle
    for j, bay in enumerate(M):
        ax.add_patch(Rectangle((0, j * 1.2), bay["width"], 1.0, fill=False))
        ax.text(0.3, j * 1.2 + 0.5, f"Bay {j} ({bay['width']}x{bay['height']})", fontsize=8, va="center")
    ax.set_xlim(-1, max(b["width"] for b in M) + 1); ax.set_ylim(-0.5, len(M) * 1.2); ax.set_yticks([])
    st.pyplot(fig)
