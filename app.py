import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v6.2", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 강남역 2호선 데이터만 필터링
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터베이스 ---
STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "수유실(B1), 무인민원발급기(2, 7번 출구), 엘리베이터(1, 4, 5, 8, 9, 11, 12번)",
        "first_last": {
            "평일(내선)": ["05:30", "00:51"], "평일(외선)": ["05:30", "00:48"],
            "휴일(내선)": ["05:30", "23:55"], "휴일(외선)": ["05:30", "23:50"]
        }
    },
    "exits": {
        "1번 출구": {"장소": "특허청, 역삼세무서", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True, "transit": "택시 승강장", "bus": "광역(9404, 9503)"},
        "2번 출구": {"장소": "테헤란로, 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)"},
        "5번 출구": {"장소": "서초동 우성아파트", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True, "transit": "광역버스 정류장", "bus": "M버스(6427)"},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True, "transit": "지하 연결통로", "bus": "순환(41)"},
        "9번 출구": {"장소": "메가박스, 서초동", "door": "교대 9-2, 역삼 2-3", "coord": [37.4988, 127.0263], "esc": True, "transit": "서초동 방면", "bus": "간선(740)"},
        "10번 출구": {"장소": "교보타워, 강남대로", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "transit": "중앙버스차로", "bus": "심야(N13)"},
        "11번 출구": {"장소": "강남역 사거리", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "transit": "택시 승강장", "bus": "직행(1100, 2000)"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "transit": "국기원 방면", "bus": "간선(421)"}
    },
    "train_env": {
        "여름(약냉방)": "4, 7호차",
        "겨울(강한히터)": "1, 10호차",
        "공지": "🚨 [실시간] 2호선 외선순환 차량 고장으로 약 5분 지연 중"
    }
}

WEEKDAY_WEIGHTS = {"월요일": 1.05, "화요일": 1.0, "수요일": 1.0, "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9}

def get_safe_int(val):
    try: return int(str(val).replace(',', ''))
    except: return 0

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v6.2")
    st.warning(STATION_DB["train_env"]["공지"])

    # --- 사이드바 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("작동 모드", ["일반 모드", "AI 챗봇 인터페이스"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # --- 연산 로직 ---
    day_weight = WEEKDAY_WEIGHTS[current_day]
    weather_multiplier = 1.2 if weather == "🌧️ 비/눈" else 1.0
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = get_safe_int(data[col_off])
    
    # 기본 예상 소요 시간 계산
    final_congestion = min((base_count / 150000) * day_weight * weather_multiplier, 1.0)
    selected_exit_time = (4.0 + (final_congestion * 12)) * weather_multiplier
    is_crowded = final_congestion > 0.65

    if mode == "일반 모드":
        st.info(f"📊 **{current_day} {current_hour}시 분석:** 실시간 하차 인원 {base_count:,}명 기반 분석 결과입니다.")
        tabs = st.tabs(["🚀 실시간 동선 최적화", "🏢 역 정보 & 시간표"])

        with tabs[0]:
            # --- 우회로 및 시간 정밀 연산 ---
            target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
            best_detour = selected_exit
            detour_time = selected_exit_time
            
            if is_crowded:
                other_exits = []
                for name, info in STATION_DB["exits"].items():
                    if name != selected_exit:
                        dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                        score = dist if not (weather == "🌧️ 비/눈" and info["esc"]) else dist * 0.5
                        other_exits.append((name, score))
                
                best_detour = sorted(other_exits, key=lambda x: x[1])[0][0]
                # 우회 시 혼잡도 감소(50%) 및 이동 거리 페널티(1분) 적용
                detour_time = (4.0 + (final_congestion * 0.5 * 12)) * weather_multiplier + 1.0

            # 시간 차이 계산
            time_difference = selected_exit_time - detour_time

            # 지표 표시
            m1, m2, m3 = st.columns(3)
            m1.metric("선택 출구 예상 시간", f"{selected_exit_time:.1f} 분")
            
            if is_crowded and best_detour != selected_exit:
                m2.metric("우회 경로 예상 시간", f"{detour_time:.1f} 분")
                m3.metric("단축 가능 시간", f"{time_difference:.1f} 분", delta=f"-{time_difference:.1f}m", delta_color="normal")
                
                # 요청하신 안내 문구 출력
                st.success(f"💡 **최적 우회 경로:** {selected_exit} 정체가 심합니다. **{best_detour}** 이용 시 약 **{time_difference:.1f}분** 더 빨리 지상 도달이 가능합니다.")
            else:
                m2.metric("우회 경로 예상 시간", "-")
                m3.metric("상태", "최적 경로 이용 중")

            st.divider()

            col_map, col_info = st.columns([2, 1])
            with col_map:
                center = [37.4979, 127.0276]
                m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                
                # 지도에 선택/우회 경로 표시
                final_target = best_detour if is_crowded else selected_exit
                folium.PolyLine([center, STATION_DB["exits"][final_target]["coord"]], color="green" if is_crowded else "blue", weight=7).add_to(m)
                folium.Marker(STATION_DB["exits"][final_target]["coord"], icon=folium.Icon(color='green' if is_crowded else 'blue', icon='star')).add_to(m)
                st_folium(m, width="100%", height=450)

            with col_info:
                st.markdown(f"### 📍 {selected_exit} 안내")
                st.write(f"**최적 하차문:** {STATION_DB['exits'][selected_exit]['door']}")
                st.write(f"**연계 교통:** {STATION_DB['exits'][selected_exit]['bus']}")
                if weather == "🌧️ 비/눈" and not STATION_DB["exits"][selected_exit]["esc"]:
                    st.error("⚠️ 계단 미끄러움 주의")

        with tabs[1]:
            st.table(pd.DataFrame(STATION_DB["general"]["first_last"], index=["첫차", "막차"]))

    # --- AI 챗봇 인터페이스 ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        user_query = st.text_input("질문을 입력하세요")
        if user_query:
            if is_crowded:
                st.write(f"🤖 **분석:** {selected_exit}은 현재 매우 혼잡하여 {selected_exit_time:.1f}분이 소요됩니다. {best_detour}로 우회하면 약 {time_difference:.1f}분 더 빨리 가실 수 있습니다.")
            else:
                st.write(f"🤖 **분석:** {selected_exit} 이용 시 약 {selected_exit_time:.1f}분 소요되며, 현재 동선이 가장 효율적입니다.")

except Exception as e:
    st.error(f"시스템 오류: {e}")
