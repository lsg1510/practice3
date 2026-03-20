import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 2호선 강남역 데이터 추출
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

try:
    data = load_data()
    
    # --- UI 헤더 ---
    st.title("📱 강남역 스마트 내비게이션 (Map Intelligence)")
    st.caption("실시간 역사 주변 혼잡도 분석 및 지도 기반 최적 경로 가이드")

    # --- 사이드바: 승객 설정 ---
    st.sidebar.header("📍 실시간 위치 설정")
    current_hour = st.sidebar.slider("시뮬레이션 시간 설정", 4, 23, 8)
    target_exit = st.sidebar.selectbox("목적지 출구", ["2번 출구", "7번 출구", "10번 출구", "11번 출구"])

    # 데이터 추출 및 혼잡도 엔진
    col_on = f"{current_hour:02d}시-{current_hour+1:02d}시 승차인원"
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_on, val_off = int(data[col_on]), int(data[col_off])
    
    is_morning_peak = 7 <= current_hour <= 9
    is_evening_peak = 17 <= current_hour <= 19
    flow_intensity = val_off if is_morning_peak else val_on
    congestion_score = min(flow_intensity / 150000, 1.0) 

    # --- 1. 출구별 신호등 ---
    st.subheader("🚦 출구별 실시간 혼잡도")
    cols = st.columns(4)
    exit_list = ["2번(테헤란로)", "7번(역삼방향)", "10번(강남대로)", "11번(강남대로)"]
    
    for i, ex in enumerate(exit_list):
        if congestion_score > 0.7 and "10번" in ex or "11번" in ex:
            status, color = "🔴 매우혼잡", "inverse"
        elif congestion_score > 0.4:
            status, color = "🟡 보통", "normal"
        else:
            status, color = "🟢 원활", "normal"
        cols[i].metric(ex, status, delta_color=color)

    st.divider()

    # --- 2 & 3. 지도 기반 최적 경로 가이드 ---
    col_map, col_guide = st.columns([2, 1])

    # 강남역 및 주요 출구 좌표 (WGS84)
    coords = {
        "center": [37.4979, 127.0276],
        "2번 출구": [37.4983, 127.0282],
        "7번 출구": [37.4975, 127.0280],
        "10번 출구": [37.4986, 127.0272],
        "11번 출구": [37.4989, 127.0275]
    }

    with col_map:
        st.subheader("🗺️ 실시간 최적 경로 (Geospatial Guide)")
        
        # 지도 생성 (네이버/구글 스타일의 기본 타일 사용)
        m = folium.Map(location=coords["center"], zoom_start=17, tiles="cartodbpositron")

        # 경로 및 마커 로직
        if is_morning_peak and congestion_score > 0.6:
            # 10, 11번 출구 혼잡 구역 표시
            folium.Circle(location=coords["10번 출구"], radius=30, color="red", fill=True, popup="병목지점").add_to(m)
            folium.Circle(location=coords["11번 출구"], radius=30, color="red", fill=True, popup="병목지점").add_to(m)
            
            # 우회 경로 (초록색 점선)
            path = [coords["center"], coords["2번 출구"]]
            folium.PolyLine(path, color="green", weight=5, opacity=0.8, dash_array='10').add_to(m)
            folium.Marker(coords["2번 출구"], icon=folium.Icon(color="green", icon="info-sign"), popup="최적 우회로").add_to(m)
            route_msg = "⚠️ 10번 출구 방면 마비! **2번 출구 우회** 시 5분 단축 예상"
        else:
            # 정상 경로
            dest = coords.get(target_exit, coords["center"])
            folium.PolyLine([coords["center"], dest], color="blue", weight=5).add_to(m)
            folium.Marker(dest, icon=folium.Icon(color="blue")).add_to(m)
            route_msg = "✅ 선택하신 출구로의 경로가 원활합니다."

        # 지도를 Streamlit에 렌더링
        st_folium(m, width="100%", height=500)

    with col_guide:
        st.subheader("⏱️ 소요 시간 분석")
        base_walk = 4.0
        wait_penalty = congestion_score * 12
        total_time = base_walk + wait_penalty
        
        st.metric("예상 소요 시간", f"{total_time:.1f} 분")
        st.write(f"역사 내 혼잡도: **{congestion_score*100:.1f}%**")
        st.progress(congestion_score)
        
        if congestion_score > 0.6:
            st.error(route_msg)
        else:
            st.success(route_msg)

    # --- 4. 가변 운영 알림 ---
    if is_evening_peak:
        st.toast("퇴근 시간 가변 게이트 운영 중", icon="⚠️")
        st.sidebar.info("📢 **안내**: 현재 승차 인원 급증으로 인해 일부 게이트가 '승차 전용'으로 전환되었습니다.")

except Exception as e:
    st.error(f"애플리케이션 실행 중 오류가 발생했습니다: {e}")
