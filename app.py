import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 2호선 강남역 데이터 추출 (가장 최신 레코드 사용 가정)
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 데이터셋 정의 (역 정보 및 출구 상세) ---
STATION_DB = {
    "info": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "엘리베이터, 에스컬레이터, 수유실, 화장실(개찰구 밖), 무인민원발급기"
    },
    "exits": {
        "1번 출구": {"장소": "역삼동 방면, 특허청", "door": "교대행 1-1, 역삼행 10-4", "coord": [37.4981, 127.0286]},
        "2번 출구": {"장소": "테헤란로, 역삼1동 주민센터", "door": "교대행 2-3, 역삼행 9-2", "coord": [37.4983, 127.0282]},
        "3번 출구": {"장소": "강남대로, 역삼동 방면", "door": "교대행 3-2, 역삼행 8-3", "coord": [37.4972, 127.0284]},
        "4번 출구": {"장소": "역삼동, 대치동 방면", "door": "교대행 4-1, 역삼행 7-4", "coord": [37.4965, 127.0281]},
        "5번 출구": {"장소": "서초동 방면, 우성아파트", "door": "교대행 5-2, 역삼행 6-3", "coord": [37.4961, 127.0275]},
        "6번 출구": {"장소": "서초동, 강남대로 방면", "door": "교대행 6-3, 역삼행 5-2", "coord": [37.4965, 127.0268]},
        "7번 출구": {"장소": "서초동, 서초초등학교", "door": "교대행 7-4, 역삼행 4-1", "coord": [37.4973, 127.0264]},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대행 8-3, 역삼행 3-2", "coord": [37.4979, 127.0262]},
        "9번 출구": {"장소": "서초동 방면, 메가박스", "door": "교대행 9-2, 역삼행 2-3", "coord": [37.4988, 127.0263]},
        "10번 출구": {"장소": "강남대로, 서초동 방면", "door": "교대행 10-4, 역삼행 1-1", "coord": [37.4986, 127.0272]},
        "11번 출구": {"장소": "강남역 사거리, 글라스타워", "door": "교대행 10-4, 역삼행 1-1", "coord": [37.4989, 127.0275]},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대행 7-3, 역삼행 4-2", "coord": [37.4991, 127.0281]}
    }
}

try:
    data = load_data()
    
    st.title("🚉 강남역 스마트 내비게이션 (v1.5)")
    
    # --- 사이드바: 메인 컨트롤 ---
    st.sidebar.header("📍 승객 위치 설정")
    current_hour = st.sidebar.slider("시뮬레이션 시간", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("나갈 출구 선택", list(STATION_DB["exits"].keys()))
    
    # 데이터 파싱 및 혼잡도 계산
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_off = int(data[col_off])
    congestion_score = min(val_off / 160000, 1.0) # 임계값 16만명 기준
    
    tabs = st.tabs(["🚀 실시간 길찾기", "ℹ️ 역 정보/시간표"])

    # --- TAB 1: 실시간 길찾기 ---
    with tabs[0]:
        # 1. 혼잡도 신호등
        st.subheader("🚦 게이트 및 출구 혼잡도")
        c1, c2, c3, c4 = st.columns(4)
        exit_groups = [["1,2,12번"], ["3,4,5,6번"], ["7,8,9번"], ["10,11번"]]
        for i, (col, group) in enumerate(zip([c1, c2, c3, c4], exit_groups)):
            # 10, 11번 출구는 특정 시간대 혼잡 가중치 부여
            weight = 1.3 if (8 <= current_hour <= 9 or 18 <= current_hour <= 19) and i == 3 else 1.0
            score = congestion_score * weight
            status = "🔴 매우혼잡" if score > 0.7 else ("🟡 보통" if score > 0.4 else "🟢 원활")
            col.metric(f"구역: {group[0]}", status)

        st.divider()

        # 2 & 3. 지도 기반 내비게이션 및 예상 시간
        m_col, g_col = st.columns([2, 1])
        
        with m_col:
            st.subheader("🗺️ 실시간 최적 동선 (구조 기반)")
            center = [37.4979, 127.0276]
            m = folium.Map(location=center, zoom_start=18, tiles="cartodbpositron")
            
            target_coord = STATION_DB["exits"][selected_exit]["coord"]
            
            # 다이내믹 우회 로직: 10, 11번 혼잡 시 9번 우회 제안
            if (selected_exit in ["10번 출구", "11번 출구"]) and congestion_score > 0.6:
                st.error(f"⚠️ {selected_exit} 방면 통로가 마비되었습니다! 9번 출구 우회를 권장합니다.")
                folium.PolyLine([center, STATION_DB["exits"]["9번 출구"]["coord"]], color="green", weight=5, dash_array='10').add_to(m)
                folium.Marker(STATION_DB["exits"]["9번 출구"]["coord"], icon=folium.Icon(color="green")).add_to(m)
            else:
                folium.PolyLine([center, target_coord], color="blue", weight=5).add_to(m)
                folium.Marker(target_coord, icon=folium.Icon(color="blue")).add_to(m)
            
            st_folium(m, width="100%", height=450)

        with g_col:
            st.subheader("⏱️ Door-to-Gate")
            base_time = 4.0
            wait_penalty = congestion_score * 12
            total_time = base_time + wait_penalty
            
            st.metric("지상까지 예상 시간", f"{total_time:.1f} 분")
            st.progress(congestion_score, text=f"역사 밀집도: {congestion_score*100:.1f}%")
            
            # 5. 출구 상세 정보
            st.info(f"📍 **{selected_exit} 상세**\n\n**주요 장소:** {STATION_DB['exits'][selected_exit]['장소']}\n\n**가까운 하차문:** {STATION_DB['exits'][selected_exit]['door']}")

        # 4. 가변 운영 알림
        if 17 <= current_hour <= 19:
            st.toast("퇴근 시간대 가변 게이트(승차 전용) 운영 중", icon="⚠️")

    # --- TAB 2: 역 정보 / 시간표 ---
    with tabs[1]:
        i_col, t_col = st.columns(2)
        with i_col:
            st.subheader("🏢 역 정보")
            for k, v in STATION_DB["info"].items():
                st.write(f"**{k}:** {v}")
            
            st.subheader("🏁 첫차/막차")
            st.table(pd.DataFrame({
                "방면": ["평일(내선)", "평일(외선)", "토/일(내선)", "토/일(외선)"],
                "첫차": ["05:30", "05:30", "05:30", "05:30"],
                "막차": ["00:51", "00:48", "23:55", "23:50"]
            }))
        
        with t_col:
            st.subheader("🕒 열차 시간표 (대표 시간대)")
            time_df = pd.DataFrame({
                "시간": [f"{i}시" for i in range(7, 10)],
                "평균 간격": ["2.5분", "3분", "4분"],
                "비고": ["출근 피크", "출근 피크", "정규 배차"]
            })
            st.dataframe(time_df, use_container_width=True)

except Exception as e:
    st.error(f"데이터 파일 에러: {e}")
