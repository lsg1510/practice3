import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 2호선 강남역 최신 데이터(첫 행 기준 샘플링)
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 정적 데이터 정의 ---
STATION_INFO = {
    "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
    "전화번호": "02-6110-2221",
    "분실물센터": "02-6110-1122",
    "시설정보": "엘리베이터(4개), 에스컬레이터(16개), 수유실, 무인민원발급기, 환전키오스크"
}

EXIT_DETAILS = {
    "10번 출구": {"장소": "강남대로, 서초동 방면", "하차문": "내선(역삼행) 4-2 / 외선(교대행) 7-3"},
    "11번 출구": {"장소": "강남역 사거리, 글라스타워", "하차문": "내선(역삼행) 5-1 / 외선(교대행) 6-4"},
    "12번 출구": {"장소": "국립어린이청소년도서관", "하차문": "내선(역삼행) 4-2 / 외선(교대행) 7-3"},
}

try:
    data = load_data()
    
    # --- 상단 헤더 ---
    st.title("🚉 강남역 스마트 내비게이션 (App Developer Edition)")
    
    tabs = st.tabs(["🔴 실시간 혼잡도/내비", "🕒 시간표/역 정보"])

    with tabs[0]:
        # --- 사이드바 설정 ---
        st.sidebar.header("📍 실시간 관제 설정")
        current_hour = st.sidebar.slider("현재 시간 설정", 4, 23, datetime.now().hour)
        target_exit = st.sidebar.selectbox("나갈 출구 선택", list(EXIT_DETAILS.keys()) + ["기타 출구"])

        # 데이터 파싱
        col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
        val_off = int(data[col_off])
        congestion_score = min(val_off / 150000, 1.0) # 15만명 기준 정규화
        
        # 1. 실시간 혼잡도 신호등
        st.subheader("🚦 출구별 실시간 혼잡도 (신호등)")
        cols = st.columns(4)
        for i, ex in enumerate(["2번", "8번", "10번", "11번"]):
            status = "🔴 매우혼잡" if congestion_score > 0.7 and i > 1 else ("🟡 보통" if congestion_score > 0.4 else "🟢 원활")
            cols[i].metric(f"{ex} 출구", status)

        st.divider()

        # 2 & 3. 지도 기반 우회 경로 및 Door-to-Gate
        col_map, col_guide = st.columns([1.5, 1])
        
        with col_map:
            st.subheader("🗺️ 다이내믹 우회 경로 안내")
            m = folium.Map(location=[37.4979, 127.0276], zoom_start=17, tiles="cartodbpositron")
            
            # 출구 좌표 샘플
            exit_coords = {"10번": [37.4986, 127.0272], "11번": [37.4989, 127.0275], "9번": [37.4992, 127.0263]}
            
            if congestion_score > 0.6: # 혼잡 시 우회 경로 활성화
                folium.Circle(exit_coords["10번"], radius=30, color="red", fill=True).add_to(m)
                folium.PolyLine([[37.4979, 127.0276], exit_coords["9번"]], color="green", dash_array='10', tooltip="우회 권장").add_to(m)
                st.warning("⚠️ 현재 10, 11번 출구 마비! 9번 출구 우회로를 이용하세요.")
            
            st_folium(m, width="100%", height=400)

        with col_guide:
            st.subheader("⏱️ Door-to-Gate 예상")
            base_walk = 3.5
            wait_time = congestion_score * 15
            st.metric("현재 위치 ➔ 지상 출구", f"{base_walk + wait_time:.1f} 분")
            st.info(f"📍 **{target_exit} 정보**\n\n**장소:** {EXIT_DETAILS.get(target_exit, {}).get('장소', '정보 준비 중')}\n\n**추천 하차문:** {EXIT_DETAILS.get(target_exit, {}).get('하차문', '정보 준비 중')}")

        # 4. 가변 운영 알림
        if 17 <= current_hour <= 19:
            st.sidebar.error("📢 [가변 운영] 현재 퇴근 피크로 인해 중앙 개찰구가 '승차 전용'으로 운영됩니다.")

    with tabs[1]:
        col_info, col_time = st.columns(2)
        
        with col_info:
            st.subheader("🏢 강남역 시설 정보")
            for k, v in STATION_INFO.items():
                st.write(f"**{k}**: {v}")
            
            st.subheader("📜 첫차/막차 시간표")
            st.table(pd.DataFrame({
                "방면": ["평일(내선)", "평일(외선)", "휴일(내선)", "휴일(외선)"],
                "첫차": ["05:30", "05:30", "05:30", "05:30"],
                "막차": ["00:51", "00:48", "23:55", "23:50"]
            }))

        with col_time:
            st.subheader("🕒 열차 도착 시간표 (평일 기준)")
            # 샘플 시간표 생성 (실제 API 연동 가능 영역)
            time_data = pd.DataFrame({
                "시": [f"{i}시" for i in range(5, 25)],
                "내선(역삼행)": ["05, 12, 20, 30..." for _ in range(20)],
                "외선(교대행)": ["02, 08, 15, 22..." for _ in range(20)]
            })
            st.dataframe(time_data, use_container_width=True, height=500)

    with tabs[2]:
        st.subheader("📈 강남역 승하차 통계 데이터")
        # 데이터 전처리 후 그래프화
        hours = [f"{i:02d}시" for i in range(4, 24)]
        on_vals = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
        off_vals = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hours, y=on_vals, name="승차", line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=hours, y=off_vals, name="하차", line=dict(color='orange')))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"데이터 파일 확인 필요: {e}")
