import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v6.0", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- [기능 통합] 고도화된 데이터베이스 ---
STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396",
        "연락처": "📞 02-6110-2221 (분실물: 1122)",
        "시설": "수유실(B1), 무인민원발급기(2, 7번), 엘리베이터(1, 4, 5, 8, 9, 11, 12번)",
        "full_timetable": {
            "구분": ["05시", "06-07시", "08-09시(피크)", "10-17시", "18-19시(피크)", "20-23시", "24시 이후"],
            "배차간격": ["8~12분", "4~6분", "2.5~3분", "5~7분", "2.5~3분", "5~8분", "10~15분"],
            "상태": ["원활", "보통", "매우혼잡", "보통", "매우혼잡", "보통", "원활"]
        }
    },
    "exits": {
        "9번 출구": {"장소": "메가박스, 서초동", "door": "교대 9-2", "coord": [37.4988, 127.0263], "esc": True, "type": "일반"},
        "10번 출구": {"장소": "교보타워, 강남대로", "door": "교대 10-4", "coord": [37.4986, 127.0272], "esc": False, "type": "가변운영(피크시 하차전용)"},
        "11번 출구": {"장소": "강남역 사거리", "door": "역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "type": "일반"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "type": "일반"},
        "신분당선": {"장소": "강남대로 남단", "door": "환승통로 이용", "coord": [37.4965, 127.0281], "esc": True, "type": "환승구역"}
    }
}

def get_congestion_color(val):
    if val < 0.4: return "🟢 원활", "#00E676"
    elif val < 0.7: return "🟡 보통", "#FFD600"
    else: return "🔴 매우 혼잡", "#FF1744"

try:
    data = load_data()
    st.title("🚉 강남역 실시간 경로 최적화 v6.0")
    
    # --- [기능 4] 가변 운영 및 긴급 알림 ---
    is_peak = 8 <= datetime.now().hour <= 9 or 18 <= datetime.now().hour <= 19
    if is_peak:
        st.error("📢 [가변 운영] 현재 출퇴근 피크 시간대로 인해 10번 게이트가 **'하차 전용'**으로 운행 중입니다.")
    else:
        st.warning("🚨 [실시간] 2호선 외선순환 차량 점검으로 약 3분 지연 중")

    # 사이드바 설정
    st.sidebar.header("📍 실시간 환경 설정")
    current_hour = st.sidebar.slider("시간대 설정", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # 로직 연산
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = int(str(data[col_off]).replace(',', ''))
    congestion_score = min(base_count / 140000 * (1.2 if weather == "🌧️ 비/눈" else 1.0), 1.0)
    status_text, status_color = get_congestion_color(congestion_score)

    # --- [기능 2] 도어-투-게이트 예상 소요 시간 ---
    base_time = 3.0 # 기본 도보 시간 (분)
    traffic_delay = congestion_score * 15 # 혼잡도에 따른 지연 (최대 15분)
    weather_delay = 2.0 if weather == "🌧️ 비/눈" else 0
    total_exit_time = base_time + traffic_delay + weather_delay

    tabs = st.tabs(["🚦 실시간 혼잡도", "🗺️ 다이내믹 우회 경로", "📅 전체 시간표 & 정보"])

    # --- [기능 1] 실시간 게이트 신호등 ---
    with tabs[0]:
        st.subheader("🚥 현재 게이트/개찰구 상태")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("현재 게이트 혼잡도", status_text)
            st.markdown(f"<div style='height:20px; background-color:{status_color}; border-radius:10px;'></div>", unsafe_allow_html=True)
        with c2:
            st.metric("출구 도달 예상 시간", f"{total_exit_time:.1f} 분")
        with c3:
            st.metric("가장 빠른 하차문", STATION_DB["exits"][selected_exit]["door"])
        
        st.info(f"💡 **분석 결과:** {selected_exit}로 나가는 데 평소보다 {traffic_delay:.1f}분 더 소요됩니다.")

    # --- [기능 3] 다이내믹 우회 경로 안내 ---
    with tabs[1]:
        st.subheader("🗺️ 최적 동선 가이드")
        col_map, col_guide = st.columns([2, 1])
        
        with col_map:
            center = [37.4979, 127.0276]
            m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
            
            # 우회 로직: 10/11번 출구가 빨간불이면 9번으로 우회
            if congestion_score > 0.7 and (selected_exit == "10번 출구" or selected_exit == "11번 출구"):
                detour_exit = "9번 출구"
                folium.PolyLine([center, STATION_DB["exits"][detour_exit]["coord"]], color="green", weight=7, tooltip="추천 우회로").add_to(m)
                folium.Marker(STATION_DB["exits"][detour_exit]["coord"], popup="우회 추천", icon=folium.Icon(color='green')).add_to(m)
                st.success(f"⚠️ **다이내믹 우회 발령:** {selected_exit}가 매우 혼잡합니다. 지하상가를 통과해 **{detour_exit}**로 나가는 경로를 추천합니다!")
            else:
                folium.PolyLine([center, STATION_DB["exits"][selected_exit]["coord"]], color="blue", weight=5).add_to(m)
                folium.Marker(STATION_DB["exits"][selected_exit]["coord"], icon=folium.Icon(color='blue')).add_to(m)
            
            st_folium(m, width="100%", height=400)

        with col_guide:
            st.markdown(f"**📍 주변 추천:** {STATION_DB['exits'][selected_exit]['장소']}")
            st.write(f"**⚠️ 특이사항:** {STATION_DB['exits'][selected_exit]['type']}")
            if weather == "🌧️ 비/눈":
                st.warning("☔ 비 오는 날에는 8번 또는 12번 엘리베이터 출구를 권장합니다.")

    # --- [기능 5] 전체 시간표 및 정보 ---
    with tabs[2]:
        st.subheader("📅 강남역 통합 가이드")
        st.write(f"🏢 {STATION_DB['general']['주소']} | {STATION_DB['general']['연락처']}")
        st.write(f"🚻 {STATION_DB['general']['시설']}")
        
        st.divider()
        st.subheader("⏰ 열차 운행 시간표 (전체)")
        time_df = pd.DataFrame(STATION_DB["general"]["full_timetable"])
        st.table(time_df)

except Exception as e:
    st.error(f"데이터 렌더링 오류: {e}")
