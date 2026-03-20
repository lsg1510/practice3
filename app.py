import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v2.5", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 상수 및 데이터셋 정의 ---
STATION_DB = {
    "exits": {
        "1번 출구": {"장소": "역삼동, 특허청", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True},
        "2번 출구": {"장소": "테헤란로", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False},
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

# 1. 요일별 가중치 테이블
WEEKDAY_WEIGHTS = {
    "월요일": 1.05, "화요일": 1.0, "수요일": 1.0, 
    "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9
}

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v2.5")
    
    # --- 사이드바: 정밀 파라미터 ---
    st.sidebar.header("⚙️ 분석 파라미터")
    
    # 요일 설정
    current_day = st.sidebar.selectbox("현재 요일", list(WEEKDAY_WEIGHTS.keys()), 
                                    index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    day_weight = WEEKDAY_WEIGHTS[current_day]
    
    # 시간 및 출구 설정
    current_hour = st.sidebar.slider("시뮬레이션 시간", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("나갈 출구 선택", list(STATION_DB["exits"].keys()))
    
    # 2. 날씨 설정 (API 대용 시뮬레이션)
    weather = st.sidebar.radio("현재 날씨", ["☀️ 맑음", "🌧️ 비/눈"])
    weather_multiplier = 1.2 if weather == "🌧️ 비/눈" else 1.0

    # --- 데이터 연산 ---
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_congestion = min(int(data[col_off]) / 160000, 1.0)
    
    # 요일 가중치가 적용된 최종 혼잡도
    final_congestion = min(base_congestion * day_weight, 1.0)
    
    # --- UI 렌더링 ---
    st.info(f"📊 **{current_day} 분석:** 평소 대비 혼잡도가 **{int((day_weight-1)*100)}%** {'증가' if day_weight >=1 else '감소'}하는 날입니다.")

    tabs = st.tabs(["🚀 실시간 분석 가이드", "🗓️ 통계 데이터"])

    with tabs[0]:
        # 3. Smart Rerouting 로직
        target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
        is_crowded = final_congestion > 0.6
        
        # 우회 출구 계산
        other_exits = []
        for name, info in STATION_DB["exits"].items():
            if name != selected_exit:
                dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                # 날씨가 안 좋을 땐 에스컬레이터(esc)가 있는 곳에 가중치 부여
                score = dist if not (weather == "🌧️ 비/눈" and info["esc"]) else dist * 0.5
                other_exits.append((name, score))
        
        best_detour = sorted(other_exits, key=lambda x: x[1])[0][0]
        
        # 메트릭 섹션
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("실시간 혼잡도", f"{final_congestion*100:.1f}%", 
                    delta=f"{current_day} 특수", delta_color="inverse")
        with m2:
            st.metric("기상 영향", weather, delta=f"속도 {int((weather_multiplier-1)*100)}% 저하" if weather_multiplier > 1 else "정상")
        with m3:
            total_time = (4.0 + (final_congestion * 12)) * weather_multiplier
            st.metric("예상 소요 시간", f"{total_time:.1f} 분")

        st.divider()

        # 안내 및 지도
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            if is_crowded:
                st.error(f"⚠️ **{selected_exit} 정체!** 인파가 몰려 위험할 수 있습니다.")
                st.success(f"💡 대안: **{best_detour}**를 이용하세요. {'(에스컬레이터 보유)' if STATION_DB['exits'][best_detour]['esc'] else ''}")
            
            # 지도 렌더링
            center = [37.4979, 127.0276]
            m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
            
            # 경로 시각화
            if is_crowded:
                # 우회로 (녹색)
                folium.PolyLine([center, STATION_DB["exits"][best_detour]["coord"]], color="green", weight=7).add_to(m)
                folium.Marker(STATION_DB["exits"][best_detour]["coord"], tooltip="추천 우회로", icon=folium.Icon(color='green')).add_to(m)
                # 정체로 (빨간색 투명)
                folium.PolyLine([center, target_coords], color="red", weight=5, opacity=0.3).add_to(m)
            else:
                folium.PolyLine([center, target_coords], color="#4285F4", weight=6).add_to(m)
                folium.Marker(target_coords, icon=folium.Icon(color='blue')).add_to(m)
                
            st_folium(m, width="100%", height=400)

        with col_right:
            st.write("### 🏃 이동 가이드")
            if weather == "🌧️ 비/눈":
                st.caption("※ 악천후로 인해 보행 속도가 보정되었습니다.")
                if not STATION_DB["exits"][selected_exit]["esc"]:
                    st.warning("⚠️ 선택하신 출구는 에스컬레이터가 없어 계단이 미끄러울 수 있습니다.")
            
            st.info(f"**현재 목표:** {selected_exit}\n\n**주요 장소:** {STATION_DB['exits'][selected_exit]['장소']}\n\n**최적 하차문:** {STATION_DB['exits'][selected_exit]['door']}")
            
            if is_crowded:
                detour_time = (4.0 + (final_congestion * 0.5 * 12)) * weather_multiplier + 1.0 # 우회 보정 시간
                st.write(f"⏱️ **우회 시 예상:** {detour_time:.1f} 분")

except Exception as e:
    st.error(f"시스템 오류: {e}")
