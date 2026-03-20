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
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 데이터셋 정의 ---
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
    st.title("🚉 강남역 스마트 내비게이션 (v1.9)")
    
    # --- 사이드바 ---
    st.sidebar.header("📍 승객 위치 설정")
    current_hour = st.sidebar.slider("시뮬레이션 시간", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("나갈 출구 선택", list(STATION_DB["exits"].keys()))
    
    # 기초 혼잡도 계산
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_off = int(data[col_off])
    base_congestion = min(val_off / 160000, 1.0)
    
    # 선택된 출구의 개별 혼잡도 (특정 출구 가중치 적용)
    def get_exit_congestion(exit_name, hour, base_score):
        weight = 1.3 if (8 <= hour <= 9 or 18 <= hour <= 19) and (exit_name in ["10번 출구", "11번 출구"]) else 1.0
        return min(base_score * weight, 1.0)

    current_exit_congestion = get_exit_congestion(selected_exit, current_hour, base_congestion)
    
    tabs = st.tabs(["🚀 실시간 길찾기", "ℹ️ 역 정보/전체 시간표"])

    with tabs[0]:
        # --- 1. 우회 추천 알고리즘 섹션 ---
        st.subheader("💡 지능형 경로 가이드")
        
        target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
        is_crowded = current_exit_congestion > 0.6
        
        if is_crowded:
            # 우회 출구 찾기: (선택 출구 제외) 거리순 정렬
            detour_candidates = []
            for name, info in STATION_DB["exits"].items():
                if name == selected_exit: continue
                dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                c_score = get_exit_congestion(name, current_hour, base_congestion)
                # 혼잡도가 현재보다 낮거나 보통(0.5) 이하인 것 중 가장 가까운 것
                if c_score < current_exit_congestion:
                    detour_candidates.append({"name": name, "dist": dist, "score": c_score})
            
            best_detour = sorted(detour_candidates, key=lambda x: x["dist"])[0]
            
            c1, c2 = st.columns(2)
            with c1:
                st.warning(f"⚠️ 현재 {selected_exit}은 매우 혼잡합니다!")
                st.metric("현재 출구 혼잡도", f"{current_exit_congestion*100:.0f}%", delta="CROWDED", delta_color="inverse")
            with c2:
                st.success(f"✅ 최적 우회로: {best_detour['name']}")
                st.metric("우회 출구 혼잡도", f"{best_detour['score']*100:.0f}%", delta="CLEAR")
            
            st.info(f"👉 **추천 이유:** {best_detour['name']}는 현재 혼잡도가 낮아 더 쾌적하게 이동할 수 있습니다. ({STATION_DB['exits'][best_detour['name']]['장소']})")
        else:
            st.success(f"✨ 현재 {selected_exit} 방면은 원활합니다. 기존 경로를 이용하세요.")

        st.divider()

        # --- 2. 지도 및 상세 정보 ---
        m_col, g_col = st.columns([2, 1])
        with m_col:
            center = [37.4979, 127.0276]
            google_map_tile = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
            m = folium.Map(location=center, zoom_start=18, tiles=google_map_tile, attr='Google')
            
            if is_crowded:
                detour_coord = STATION_DB["exits"][best_detour['name']]["coord"]
                # 기존 경로 (빨간색)
                folium.PolyLine([center, target_coords], color="#FF0000", weight=8, opacity=0.3).add_to(m)
                # 우회 경로 (초록색)
                folium.PolyLine([center, detour_coord], color="#0F9D58", weight=6, dash_array='10').add_to(m)
                folium.Marker(detour_coord, icon=folium.Icon(color="green", icon="share")).add_to(m)
                folium.Marker(target_coords, icon=folium.Icon(color="red", icon="remove")).add_to(m)
            else:
                folium.PolyLine([center, target_coords], color="#4285F4", weight=6).add_to(m)
                folium.Marker(target_coords, icon=folium.Icon(color="blue", icon="star")).add_to(m)
            
            st_folium(m, width="100%", height=450)

        with g_col:
            st.subheader("⏱️ 예상 소요 시간")
            
            base_walk = 4.0
            congestion_penalty = current_exit_congestion * 15
            current_total = base_walk + congestion_penalty
            
            if is_crowded:
                # 우회 시: 기본 보행 + (우회 출구 혼잡도 페널티) + (이동 거리 차이 가중치)
                detour_penalty = best_detour['score'] * 15
                dist_penalty = best_detour['dist'] * 5000 # 좌표 차이에 따른 가중치
                detour_total = base_walk + detour_penalty + dist_penalty
                
                st.metric("기존 출구 이용 시", f"{current_total:.1f} 분", delta=f"{current_total - detour_total:.1f} 분 느림", delta_color="inverse")
                st.metric("우회 출구 이용 시", f"{detour_total:.1f} 분", delta="최적")
                st.caption("※ 우회 거리에 따른 추가 보행 시간이 반영되었습니다.")
            else:
                st.metric("지상까지 예상 시간", f"{current_total:.1f} 분")
            
            st.divider()
            target_info = best_detour['name'] if is_crowded else selected_exit
            st.write(f"📍 **이동 목적지 정보 ({target_info})**")
            st.write(f"- 주요 장소: {STATION_DB['exits'][target_info]['장소']}")
            st.write(f"- 추천 하차문: {STATION_DB['exits'][target_info]['door']}")

    # --- TAB 2: 역 정보 / 전체 시간표 (기존 유지) ---
    with tabs[1]:
        i_col, t_col = st.columns([1, 1.5])
        with i_col:
            st.subheader("🏢 역 시설 정보")
            for k, v in STATION_DB["info"].items():
                st.write(f"**{k}:** {v}")
            st.subheader("🏁 첫차/막차 정보")
            st.table(pd.DataFrame({
                "방면": ["평일(내선)", "평일(외선)", "휴일(내선)", "휴일(외선)"],
                "첫차": ["05:30", "05:30", "05:30", "05:30"],
                "막차": ["00:51", "00:48", "23:55", "23:50"]
            }))
        with t_col:
            st.subheader("📅 전체 시간대별 배차 정보")
            hours = [f"{i:02d}시" for i in range(5, 25)]
            intervals = ["2.5분 ~ 3분 (피크)" if (8 <= h <= 9 or 18 <= h <= 19) else "4분 ~ 6분 (정규)" for h in range(5, 25)]
            st.dataframe(pd.DataFrame({"시간대": hours, "내선/외선 순환": intervals}), use_container_width=True, height=500)

except Exception as e:
    st.error(f"알고리즘 연산 오류: {e}")
