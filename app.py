import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v6.5", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터베이스 ---
STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "수유실(B1), 무인민원발급기(2, 7번 출구), 엘리베이터(1, 4, 5, 8, 9, 11, 12번)",
        "first_last": {
            "평일(내선-잠실)": ["05:30", "00:51"], "평일(외선-신도림)": ["05:30", "00:48"],
            "휴일(내선-잠실)": ["05:30", "23:55"], "휴일(외선-신도림)": ["05:30", "23:50"]
        },
        "headway": 4
    },
    "exits": {
        "1번 출구": {"장소": "특허청, 역삼세무서", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True, "transit": "택시 승강장", "bus": "광역(9404, 9503)"},
        "2번 출구": {"장소": "테헤란로, 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)"},
        "3번 출구": {"장소": "강남역사거리, 역삼 방면", "door": "교대 2-4, 역삼 9-1", "coord": [37.4981, 127.0286], "esc": True, "transit": "없음", "bus": "없음"},
        "4번 출구": {"장소": "뱅뱅사거리", "door": "교대 2-4, 역삼 9-1", "coord": [37.4981, 127.0286], "esc": True, "transit": "없음", "bus": "없음"},
        "5번 출구": {"장소": "서초동 우성아파트", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True, "transit": "광역버스 정류장", "bus": "M버스(6427)"},
        "6번 출구": {"장소": "강남역사거리, 역삼 방면", "door": "교대 2-4, 역삼 9-1", "coord": [37.4981, 127.0286], "esc": True, "transit": "없음", "bus": "없음"},
        "7번 출구": {"장소": "KDB산업은행", "door": "교대 2-4, 역삼 9-1", "coord": [37.4981, 127.0286], "esc": True, "transit": "없음", "bus": "없음"},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True, "transit": "지하 연결통로", "bus": "순환(41)"},
        "9번 출구": {"장소": "메가박스, 서초동", "door": "교대 9-2, 역삼 2-3", "coord": [37.4988, 127.0263], "esc": True, "transit": "서초동 방면", "bus": "간선(740)"},
        "10번 출구": {"장소": "교보타워, 강남대로", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "transit": "중앙버스차로", "bus": "심야(N13)"},
        "11번 출구": {"장소": "강남역 사거리", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "transit": "택시 승강장", "bus": "직행(1100, 2000)"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "transit": "국기원 방면", "bus": "간선(421)"}
    },
    "train_env": {
        "공지": "🚨 [실시간] 2호선 외선순환 차량 고장으로 약 5분 지연 중"
    }
}

WEEKDAY_WEIGHTS = {"월요일": 1.05, "화요일": 1.0, "수요일": 1.0, "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9}

def get_safe_int(val):
    try: return int(str(val).replace(',', ''))
    except: return 0

def get_next_train_time():
    now = datetime.now()
    minute = now.minute
    headway = STATION_DB["general"]["headway"]
    next_inner = headway - (minute % headway)
    next_outer = headway - ((minute + 2) % headway)
    return next_inner, next_outer

def generate_full_timetable(start_hour=5, end_hour=24):
    headway = STATION_DB["general"]["headway"]
    timetable = []
    for h in range(start_hour, end_hour + 1):
        for m in range(0, 60, headway):
            if h == 24 and m > 0: break
            timetable.append(f"{h:02d}:{m:02d}")
    return timetable

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v6.5")
    
    # --- 상단 실시간 열차 도착 정보 ---
    next_inner, next_outer = get_next_train_time()
    t_col1, t_col2, t_col3 = st.columns([1, 1, 2])
    with t_col1:
        st.info(f"🟢 **잠실 방면(내선)**\n\n**{next_inner}분 후** 도착 예정")
    with t_col2:
        st.info(f"⚪ **신도림 방면(외선)**\n\n**{next_outer}분 후** 도착 예정")
    with t_col3:
        st.warning(STATION_DB["train_env"]["공지"])

    # --- 사이드바 ---
    st.sidebar.header("🕹️ 제어 센터")
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    day_weight = WEEKDAY_WEIGHTS[current_day]
    weather_multiplier = 1.2 if weather == "🌧️ 비/눈" else 1.0
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = get_safe_int(data[col_off])
    
    final_congestion = min((base_count / 150000) * day_weight * weather_multiplier, 1.0)
    selected_exit_time = (4.0 + (final_congestion * 12)) * weather_multiplier
    is_crowded = final_congestion > 0.65

    tabs = st.tabs(["🚀 실시간 동선 최적화", "🏢 역 정보 & 시간표"])

    with tabs[0]:
        # --- 우회로 연산 로직 ---
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
            detour_time = (4.0 + (final_congestion * 0.5 * 12)) * weather_multiplier + 1.0

        time_difference = selected_exit_time - detour_time

        m1, m2, m3 = st.columns(3)
        m1.metric("선택 출구 예상 시간", f"{selected_exit_time:.1f} 분")
        if is_crowded and best_detour != selected_exit:
            m2.metric("우회 경로 예상 시간", f"{detour_time:.1f} 분")
            m3.metric("단축 가능 시간", f"{time_difference:.1f} 분", delta=f"-{time_difference:.1f}m", delta_color="normal")
        else:
            m2.metric("우회 경로 예상 시간", "-")
            m3.metric("상태", "최적 경로 이용 중")

        st.divider()

        # --- 지도 및 출구 정보 비교 (수정된 섹션) ---
        col_map, col_info = st.columns([1.5, 1])
        
        with col_map:
            center = [37.4979, 127.0276]
            m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
            final_target = best_detour if is_crowded else selected_exit
            
            # 선택한 경로 (파란색)
            folium.PolyLine([center, target_coords], color="blue", weight=4, opacity=0.6, dash_array='5').add_to(m)
            folium.Marker(target_coords, popup=f"선택: {selected_exit}", icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)
            
            # 우회 경로 (있을 경우만 초록색 표시)
            if is_crowded and best_detour != selected_exit:
                detour_coords = STATION_DB["exits"][best_detour]["coord"]
                folium.PolyLine([center, detour_coords], color="green", weight=7).add_to(m)
                folium.Marker(detour_coords, popup=f"추천: {best_detour}", icon=folium.Icon(color='green', icon='star')).add_to(m)
                
            st_folium(m, width="100%", height=500)

        with col_info:
            # 1. 선택 출구 정보
            st.markdown(f"### 📍 선택: {selected_exit}")
            st.caption(f"주요 장소: {STATION_DB['exits'][selected_exit]['장소']}")
            st.write(f"**최적 하차문:** {STATION_DB['exits'][selected_exit]['door']}")
            st.write(f"**연계 교통:** {STATION_DB['exits'][selected_exit]['bus']}")
            
            st.write("---")
            
            # 2. 우회 출구 정보 (조건부 렌더링)
            if is_crowded and best_detour != selected_exit:
                st.markdown(f"### 🚀 추천 우회: {best_detour}")
                st.success(f"현재 {selected_exit}보다 **{time_difference:.1f}분** 더 빠릅니다.")
                st.caption(f"주요 장소: {STATION_DB['exits'][best_detour]['장소']}")
                st.write(f"**최적 하차문:** {STATION_DB['exits'][best_detour]['door']}")
                st.write(f"**연계 교통:** {STATION_DB['exits'][best_detour]['bus']}")
                if STATION_DB['exits'][best_detour]['esc']:
                    st.write("✅ 에스컬레이터 이용 가능")
            else:
                st.write("✅ **현재 선택하신 출구가 가장 효율적입니다.**")

    with tabs[1]:
        st.subheader("🏢 역 상세 정보")
        inf1, inf2, inf3 = st.columns(3)
        with inf1: st.markdown(f"**📍 주소**\n\n{STATION_DB['general']['주소']}")
        with inf2: st.markdown(f"**📞 대표 전화**\n\n{STATION_DB['general']['전화번호']}")
        with inf3: st.markdown(f"**📦 분실물 센터**\n\n{STATION_DB['general']['분실물센터']}")
        
        st.divider()
        st.subheader("🏁 첫차 / 막차 시간표")
        st.table(pd.DataFrame(STATION_DB["general"]["first_last"], index=["첫차", "막차"]))
        
        st.divider()
     
except Exception as e:
    st.error(f"시스템 오류: {e}")
