import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

try:
    data = load_data()
    
    st.title("📱 강남역 스마트 내비게이션 (Naver Map API 연동)")
    
    # 사이드바 설정
    st.sidebar.header("📍 관제 설정")
    current_hour = st.sidebar.slider("시간 설정", 4, 23, 8)
    
    # 데이터 파싱 및 혼잡도 계산
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_off = int(data[col_off])
    congestion_score = min(val_off / 150000, 1.0)
    is_morning_peak = 7 <= current_hour <= 9

    # --- 메인 레이아웃 ---
    col_map, col_guide = st.columns([2, 1])

    with col_map:
        st.subheader("🗺️ 실시간 최적 경로 가이드 (Naver Map)")
        
        # 강남역 중심 좌표
        gangnam_coords = [37.4979, 127.0276]
        
        # Folium을 이용한 네이버 지도 타일 설정
        # Note: 네이버 타일 서버 주소는 정책에 따라 변경될 수 있으나, 보통 아래 형식을 사용합니다.
        m = folium.Map(
            location=gangnam_coords,
            zoom_start=17,
            tiles='https://map.pstatic.net/nrb/styles/basic/1612411478/{z}/{x}/{y}.png?debug=true',
            attr='Naver Map'
        )

        # 출구 좌표 데이터 (샘플)
        exits = {
            "2번 출구": [37.4983, 127.0282],
            "10번 출구": [37.4986, 127.0272],
            "11번 출구": [37.4989, 127.0275],
            "7번 출구": [37.4975, 127.0280]
        }

        # 동선 시뮬레이션 시각화
        if is_morning_peak and congestion_score > 0.6:
            # 1. 병목 구간 표시 (빨간색)
            folium.PolyLine(
                locations=[exits["10번 출구"], exits["11번 출구"]],
                color='red', weight=10, opacity=0.8, tooltip="병목 현상 심화"
            ).add_to(m)
            
            # 2. 최적 우회 경로 표시 (초록색)
            # 승강장에서 2번 출구로 나가는 가상의 경로
            folium.PolyLine(
                locations=[gangnam_coords, exits["2번 출구"]],
                color='green', weight=7, dash_array='10', tooltip="최적 우회 경로"
            ).add_to(m)
            
            folium.Marker(exits["2번 출구"], popup="최적 우회", icon=folium.Icon(color='green', icon='star')).add_to(m)
        else:
            folium.Marker(exits["10번 출구"], popup="정상 경로").add_to(m)

        # Streamlit에 지도 렌더링
        st_folium(m, width=800, height=500)

    with col_guide:
        st.subheader("⏱️ 예상 소요 시간")
        base_walk = 4.0
        delay = congestion_score * 12
        st.metric("현재 위치 ➔ 지상 출구", f"{base_walk + delay:.1f} 분")
        
        st.write(f"역사 내 밀집 지수: **{congestion_score*100:.1f}%**")
        st.progress(congestion_score)
        
        if is_morning_peak and congestion_score > 0.6:
            st.error("⚠️ 10, 11번 출구 인근 마비! 2번 출구를 이용하세요.")
        else:
            st.success("✅ 선택하신 경로가 원활합니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")
