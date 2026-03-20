import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v3.0", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터셋 정의 ---
STATION_DB = {
    "info": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "엘리베이터, 에스컬레이터, 수유실, 화장실(개찰구 밖), 무인민원발급기"
    },
    "exits": {
        "1번 출구": {"장소": "역삼동, 특허청", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True},
        "2번 출구": {"장소": "테헤란로, 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False},
        "3번 출구": {"장소": "강남대로, 역삼동", "door": "교대 3-2, 역삼 8-3", "coord": [37.4972, 127.0284], "esc": False},
        "4번 출구": {"장소": "역삼동, 대치동", "door": "교대 4-1, 역삼 7-4", "coord": [37.4965, 127.0281], "esc": True},
        "5번 출구": {"장소": "서초동, 우성아파트", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True},
        "6번 출구": {"장소": "서초동, 강남대로", "door": "교대 6-3, 역삼 5-2", "coord": [37.4965, 127.0268], "esc": False},
        "7번 출구": {"장소": "서초동, 서초초교", "door": "교대 7-4, 역삼 4-1", "coord": [37.4973, 127.0264], "esc": False},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True},
        "9번 출구": {"장소": "서초동, 메가박스", "door": "교대 9-2, 역삼 2-3", "coord": [37.4988, 127.0263], "esc": True},
        "10번 출구": {"장소": "강남대로, 서초동", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False},
        "11번 출구": {"장소": "강남역 사거리", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True},
        "12번 출구": {"장소": "국립어린이도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True}
    }
}

WEEKDAY_WEIGHTS = {
    "월요일": 1.05, "화요일": 1.0, "수요일": 1.0, 
    "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9
}

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 (v3.0)")
    
    # --- 사이드바: 사용자 설정 ---
    st.sidebar.header("📍 실시간 환경 설정")
    current_day = st.sidebar.selectbox("현재 요일", list(WEEKDAY_WEIGHTS.keys()), 
                                    index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시뮬레이션 시간", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("나갈 출구 선택", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("현재 날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # --- 연산 로직 ---
    day_weight = WEEKDAY_WEIGHTS[current_day]
    weather_multiplier = 1.2 if weather == "🌧️ 비/눈" else 1.0
    
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_congestion = min(int(data[col_off]) / 160000, 1.0)
    final_congestion = min(base_congestion * day_weight, 1.0)
    
    # --- 메인 UI 상단 인사이트 ---
    st.info(f"📊 **{current_day} 분석:** 평소 대비 유동인구가 **{int((day_weight-1)*100)}%** 변동되는 날입니다. (현재 시각 기준 하차: {int(data[col_off]):,}명)")

    tabs = st.tabs(["🚀 실시간 분석 가이드", "ℹ️ 역 정보 & 통계"])

    # --- TAB 1: 실시간 분석 가이드 (v2.5 기반) ---
    with tabs[0]:
        # 지능형 우회로 계산 (Smart Rerouting)
        target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
        is_crowded = final_congestion > 0.6
        
        other_exits = []
        for name, info in STATION_DB["exits"].items():
            if name != selected_exit:
                dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                # 비 올 땐 에스컬레이터 우선순위 가중치
                score = dist if not (weather == "🌧️ 비/눈" and info["esc"]) else dist * 0.5
                other_exits.append((name, score))
        
        best_detour = sorted(other_exits, key=lambda x: x[1])[0][0]

        # 지표 표시
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("최종 혼잡도", f"{final_congestion*100:.1f}%", delta=f"{current_day} 보정됨", delta_color="inverse")
        with m2:
            st.metric("기상 보정", weather, delta=f"보행 {int((weather_multiplier-1)*100)}% 지연" if weather_multiplier > 1 else "정상")
        with m3:
            total_time = (4.0 + (final_congestion * 12)) * weather_multiplier
            st.metric("예상 소요 시간", f"{total_time:.1f} 분")

        st.divider()

        # 안내 및 지도
        col_m, col_g = st.columns([2, 1])
        with col_m:
            st.subheader("🗺️ 실시간 최적 동선")
            if is_crowded:
                st.error(f"⚠️ **{selected_exit} 혼잡!** 현재 인파가 매우 많습니다.")
                st.success(f"💡 **{best_detour}**로 우회하세요. {'(에스컬레이터 있음)' if STATION_DB['exits'][best_detour]['esc'] else ''}")
            
            center = [37.4979, 127.0276]
            m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps')
            
            if is_crowded:
                folium.PolyLine([center, STATION_DB["exits"][best_detour]["coord"]], color="#0F9D58", weight=7, tooltip="추천 우회로").add_to(m)
                folium.Marker(STATION_DB["exits"][best_detour]["coord"], icon=folium.Icon(color='green')).add_to(m)
                folium.PolyLine([center, target_coords], color="#EA4335", weight=5, opacity=0.3).add_to(m)
            else:
                folium.PolyLine([center, target_coords], color="#4285F4", weight=6).add_to(m)
                folium.Marker(target_coords, icon=folium.Icon(color='blue')).add_to(m)
            
            st_folium(m, width="100%", height=450)

        with col_g:
            st.subheader("🏃 이동 가이드")
            if weather == "🌧️ 비/눈":
                if not STATION_DB["exits"][selected_exit]["esc"]:
                    st.warning("⚠️ 선택 출구 계단 주의 (에스컬레이터 없음)")
            
            st.info(f"📍 **{selected_exit} 상세**\n\n**주요지:** {STATION_DB['exits'][selected_exit]['장소']}\n\n**하차문:** {STATION_DB['exits'][selected_exit]['door']}")
            
            if is_crowded:
                detour_time = (4.0 + (final_congestion * 0.5 * 12)) * weather_multiplier + 1.0
                st.write(f"⏱️ **우회 시 예상 시간:** {detour_time:.1f} 분")

    # --- TAB 2: 역 정보 & 통계 (v1.8 기반) ---
    with tabs[1]:
        col_info, col_time = st.columns([1, 1.5])
        with col_info:
            st.subheader("🏢 역 시설 정보")
            for k, v in STATION_DB["info"].items():
                st.write(f"**{k}:** {v}")
            
            st.divider()
            st.subheader("🏁 첫차/막차 시간")
            st.table(pd.DataFrame({
                "방면": ["평일(내선)", "평일(외선)", "휴일(내선)", "휴일(외선)"],
                "첫차": ["05:30", "05:30", "05:30", "05:30"],
                "막차": ["00:51", "00:48", "23:55", "23:50"]
            }))
        
        with col_time:
            st.subheader("📅 시간대별 배차 및 통계")
            hours = [f"{i:02d}시" for i in range(5, 25)]
            intervals = ["2.5~3분(피크)" if (8 <= h <= 9 or 18 <= h <= 19) else "4~6분(정규)" if 7 <= h <= 22 else "8~12분" for h in range(5, 25)]
            
            full_timetable = pd.DataFrame({
                "시간대": hours,
                "내/외선 배차": intervals,
                "요일 가중치 적용": [f"{base_congestion * day_weight * 100:.1f}%" for h in range(5, 25)] # 참고용 수치
            })
            st.dataframe(full_timetable, use_container_width=True, height=550)

except Exception as e:
    st.error(f"⚠️ 통합 데이터 렌더링 중 오류 발생: {e}")
