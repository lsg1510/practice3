import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime
import time  # 시간 지연을 위해 추가

# ── 페이지 설정 (기존과 동일) ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="강남역 스마트 내비게이션",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# [CSS 섹션은 기존과 동일하므로 생략합니다 - 코드의 일관성을 유지합니다]
# ... (기존 CSS 코드 유지) ...

# ── 데이터 & 상수 (기존과 동일) ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    import glob, os
    # 현재 파일의 디렉토리에서 csv 검색
    candidates = glob.glob(os.path.join(os.path.dirname(__file__), "*.csv"))
    if not candidates: return None
    fp = candidates[0]
    try:
        df = pd.read_csv(fp, encoding="utf-8")
    except Exception:
        df = pd.read_csv(fp, encoding="cp949")
    rows = df[(df["지하철역"] == "강남") & (df["호선명"] == "2호선")]
    return rows.iloc[0] if not rows.empty else None

# [STATION_DB, WEEKDAY_WEIGHTS 및 유틸 함수 기존과 동일]
# ... (기존 STATION_DB, safe_int, next_train_minutes 등 유지) ...

# ── 실시간 업데이트 컨테이너 ──────────────────────────────────────────────────────
# 페이지가 새로고침되어도 루프가 돌아가도록 설정합니다.
if "run_loop" not in st.session_state:
    st.session_state.run_loop = True

# 전체 화면을 감싸는 빈 컨테이너 생성
main_container = st.empty()

# 1분(60초)마다 루프를 돌며 실시간 시간을 반영합니다.
# 사용자가 사이드바를 조작하면 Streamlit 특성상 즉시 재실행됩니다.
while st.session_state.run_loop:
    with main_container.container():
        # 현재 실제 시간 가져오기
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
            
            # 실시간 반영 체크박스 (사용자가 수동 조절하고 싶을 때를 위해)
            auto_mode = st.checkbox("실시간 시간 동기화", value=True)
            
            if auto_mode:
                current_day = real_time_day
                current_hour = real_time_hour
                st.info(f"📍 현재 시간 반영 중\n({current_day} {current_hour}시)")
            else:
                current_day = st.selectbox("요일 선택", ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"], 
                                          index=now.weekday())
                current_hour = st.slider("시간대 선택", 4, 23, real_time_hour, format="%d시")

            selected_exit = st.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
            weather = st.radio("날씨", ["☀️ 맑음", "🌧️ 비 / 눈"])
            
            st.markdown("---")
            st.markdown(f"<div style='font-size:.7rem;color:#475569;'>업데이트: {now.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

        # ── 메인 계산 및 UI 렌더링 (이후 로직은 기존과 동일) ─────────────────────────
        data = load_data()
        if data is None:
            st.error("CSV 파일을 찾을 수 없습니다.")
            st.stop()

        # [기존의 KPI 카드, 탭, 지도 렌더링 로직이 이 안에 위치합니다]
        # ... (기존 렌더링 코드 그대로 유지) ...
        
        # ── 하단 실시간 시계 표시 ──
        st.markdown(f"""
            <div style="text-align:right; color:#94a3b8; font-size:0.8rem; margin-top:20px;">
                자동 갱신까지 대기 중... 마지막 동기화: {now.strftime('%H:%M:%S')}
            </div>
        """, unsafe_allow_html=True)

    # 1분간 대기 후 루프 재실행 (실시간성 유지)
    time.sleep(60)
    st.rerun()
