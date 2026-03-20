import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime
# 실시간 갱신을 위한 라이브러리 추가
from streamlit_autorefresh import st_autorefresh

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="강남역 스마트 내비게이션",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 실시간 자동 갱신 설정 (5분 = 300,000ms) ──────────────────────────────────
# 5분마다 앱을 자동으로 재실행하여 실시간 시간과 데이터를 동기화합니다.
count = st_autorefresh(interval=300000, key="statrefresh")

# [기존 CSS 섹션 유지]
st.markdown("""
<style>
/* ... (기존 CSS 코드와 동일) ... */
</style>
""", unsafe_allow_html=True)

# ── 데이터 로드 (실시간 반영을 위해 캐시 만료 시간 설정) ────────────────────────
@st.cache_data(ttl=300) # 5분마다 캐시 만료
def load_data():
    import glob, os
    candidates = glob.glob(os.path.join(os.path.dirname(__file__), "*.csv"))
    if not candidates: return None
    fp = candidates[0]
    try:
        df = pd.read_csv(fp, encoding="utf-8")
    except Exception:
        df = pd.read_csv(fp, encoding="cp949")
    rows = df[(df["지하철역"] == "강남") & (df["호선명"] == "2호선")]
    return rows.iloc[0] if not rows.empty else None

# [STATION_DB, WEEKDAY_WEIGHTS 등 상수 섹션 유지]
# ...

# ── 메인 로직 시작 ───────────────────────────────────────────────────────────
now = datetime.now()
real_time_hour = now.hour
real_time_day = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()]

# ── 사이드바 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon">🚉</div>
        <div>
            <div class="sidebar-logo-text">강남역 내비게이션</div>
            <div class="sidebar-logo-sub">2호선 실시간 정보 시스템</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 실시간 모드 스위치
    auto_mode = st.toggle("실시간 시간 동기화", value=True)
    
    if auto_mode:
        current_day = real_time_day
        current_hour = real_time_hour
        st.success(f"● 실시간 연동 중 ({current_hour}시)")
    else:
        current_day = st.selectbox("요일 선택", ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"], 
                                  index=now.weekday())
        current_hour = st.slider("시간대 선택", 4, 23, real_time_hour, format="%d시")

    selected_exit = st.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.radio("날씨", ["☀️ 맑음", "🌧️ 비 / 눈"])
    
    st.markdown("---")
    st.caption(f"최근 동기화: {now.strftime('%H:%M:%S')}")
    st.caption("다음 갱신: 5분 후 자동 실행")

# ── 메인 UI 렌더링 ───────────────────────────────────────────────────────────
# (이하 기존의 KPI 카드, 지도, 탭 렌더링 코드를 그대로 배치합니다.)
# 데이터 분석 및 변수 계산 (congestion_ratio, exit_time 등) 로직 포함
data = load_data()
if data is not None:
    # ... (기존 분석 로직 및 시각화 코드) ...
    # [사용자님의 기존 UI 코드 블록이 이곳에 들어갑니다]
    st.info(f"현재 {current_day} {current_hour}시 기준 데이터를 분석 중입니다.")
else:
    st.error("데이터를 불러올 수 없습니다.")
