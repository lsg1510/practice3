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
    
    st.title("📱 강남역 스마트 내비게이션 (Structural Guide)")
    st.caption("강남역 구조 기반 실시간 혼잡도 및 우회 경로 안내")

    # --- 사이드바: 승객 설정 ---
    st.sidebar.header("📍 실시간 위치 설정")
    current_hour = st.sidebar.slider("시뮬레이션 시간 설정", 4, 23, 8)
    target_exit = st.sidebar.selectbox("목적지 출구", ["2번 출구", "7번 출구", "10번 출구", "11번 출구"])

    # 데이터 추출 및 혼잡도 엔진
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_off = int(data[col_off])
    
    is_morning_peak = 7 <= current_hour <= 9
    congestion_score = min(val_off / 150000, 1.0) 

    # --- 1. 출구별 신호등 ---
    st.subheader("🚦 출구별 실시간 혼잡도")
    cols = st.columns(4)
    exit_info = [("2번(테헤란로)", 0), ("7번(역삼방향)", 1), ("10번(강남대로)", 2), ("11번(강남대로)", 3)]
    
    for i, (name, idx) in enumerate(exit_info):
        status = "🟢 원활"
        if congestion_score > 0.7 and idx >= 2: status = "🔴 매우혼잡"
        elif congestion_score > 0.4: status = "🟡 보통"
        cols[i].metric(name, status)

    st.divider()

    # --- 2 & 3. 지도 기반 평면도 가이드 ---
    col_map, col_guide = st.columns([2, 1])

    # 강남역 내부 주요 구조물 좌표 (평면도 시각화를 위한 Relative 좌표값)
    nodes = {
        "platform": [37.4979, 127.0276],
        "gate_center": [37.4981, 127.0276],
        "2번 출구": [37.4983, 127.0282],
        "7번 출구": [37.4975, 127.0280],
        "10번 출구": [37.4986, 127.0272],
        "11번 출구": [37.4989, 127.0275]
    }

    with col_map:
        st.subheader("🗺️ 역구조 기반 최적 동선")
        
        # 지도 배경을 가장 단순한 형태로 설정 (평면도 느낌)
        m = folium.Map(
            location=nodes["platform"], 
            zoom_start=18, 
            tiles="CartoDB positron", # 깨끗한 화이트톤 배경
            zoom_control=False,
            scrollWheelZoom=False,
            dragging=True
        )

        # 1. 역사 구조물 가이드라인 (평면도 선)
        folium.PolyLine(
            [nodes["10번 출구"], nodes["gate_center"], nodes["2번 출구"]],
            color="#E0E0E0", weight=15, opacity=0.5
        ).add_to(m)

        # 2. 동적 경로 로직
        if is_morning_peak and congestion_score > 0.6:
            # 병목 지점 (10, 11번 개찰구)
            folium.Circle(nodes["10번 출구"], radius=20, color="red", fill=True, fill_opacity=0.6).add_to(m)
            
            # 추천 우회 경로 (승강장 -> 2번 출구)
            path = [nodes["platform"], nodes["gate_center"], nodes["2번 출구"]]
            folium.PolyLine(path, color="green", weight=6, opacity=0.8, dash_array='10').add_to(m)
            
            folium.Marker(nodes["2번 출구"], tooltip="최적 우회", icon=folium.Icon(color="green")).add_to(m)
            msg = "⚠️ 10, 11번 출구 집중 혼잡! **2번 출구**로 이동하세요."
        else:
            # 정상 경로
            dest_coords = nodes.get(target_exit, nodes["2번 출구"])
            folium.PolyLine([nodes["platform"], dest_coords], color="blue", weight=5).add_to(m)
            folium.Marker(dest_coords, icon=folium.Icon(color="blue")).add_to(m)
            msg = "✅ 현재 선택하신 출구까지의 동선이 원활합니다."

        st_folium(m, width="100%", height=500)

    with col_guide:
        st.subheader("⏱️ Door-to-Gate 분석")
        base_time = 3.5
        penalty = congestion_score * 10
        total = base_time + penalty
        
        st.metric("예상 소요 시간", f"{total:.1f} 분")
        st.write(f"역사 내부 밀집도: **{congestion_score*100:.1f}%**")
        st.progress(congestion_score)
        
        if congestion_score > 0.6:
            st.error(msg)
        else:
            st.success(msg)

    # --- 4. 가변 운영 알림 (퇴근 시간) ---
    if 17 <= current_hour <= 19:
        st.sidebar.warning("📢 **알림**: 퇴근 피크 시간대 개찰구 가변 운영 중 (일부 승차 전용)")

except Exception as e:
    st.error(f"App 실행 오류: {e}")
