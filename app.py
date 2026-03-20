import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v6.0", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 강남역 2호선 데이터만 필터링
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터베이스 구축 (v3.0 + v5.0 데이터 통합) ---
STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "수유실(B1), 무인민원발급기(2, 7번 출구), 엘리베이터(1, 4, 5, 8, 9, 11, 12번)",
        "first_last": {
            "평일(내선)": ["05:30", "00:51"],
            "평일(외선)": ["05:30", "00:48"],
            "휴일(내선)": ["05:30", "23:55"],
            "휴일(외선)": ["05:30", "23:50"]
        }
    },
    "exits": {
        "1번 출구": {"장소": "특허청, 역삼세무서", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True, "transit": "택시 승강장 바로 앞", "bus": "광역(9404, 9503), 공항(6020)", "recommend": "A 카페 (조용함)"},
        "2번 출구": {"장소": "테헤란로, 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)", "recommend": "B 브런치 (대기 적음)"},
        "5번 출구": {"장소": "서초동 우성아파트", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True, "transit": "광역버스 정류장 밀집", "bus": "M버스(6427), 직행(1550-1)", "recommend": "E 식당 (혼밥 가능)"},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True, "transit": "지하 연결통로 이용가능", "bus": "순환(41)", "recommend": "F 라운지 (매우 쾌적)"},
        "9번 출구": {"장소": "메가박스, 서초동", "door": "교대 9-2, 역삼 2-3", "coord": [37.4988, 127.0263], "esc": True, "transit": "서초동 방면 도보", "bus": "간선(740)", "recommend": "영화관 내 카페"},
        "10번 출구": {"장소": "교보타워, 강남대로", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "transit": "중앙버스차로 인접", "bus": "심야(N13, N75)", "recommend": "G 술집 (항상 혼잡)"},
        "11번 출구": {"장소": "강남역 사거리, 역삼동", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "transit": "택시 승강장(대기 김)", "bus": "직행(1100, 2000, 7007)", "recommend": "H 베이커리 (인기 많음)"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "transit": "국기원 방면 도보", "bus": "간선(421)", "recommend": "I 북카페 (독서 최적)"}
    },
    "train_env": {
        "여름(약냉방)": "4, 7호차",
        "겨울(강한히터)": "1, 10호차",
        "공지": "🚨 [실시간] 2호선 외선순환 차량 고장으로 약 5분 지연 중 (관제 연동)"
    }
}

WEEKDAY_WEIGHTS = {"월요일": 1.05, "화요일": 1.0, "수요일": 1.0, "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9}

def get_safe_int(val):
    try:
        return int(str(val).replace(',', ''))
    except:
        return 0

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v6.0")
    
    # 상단 실시간 공지
    st.warning(STATION_DB["train_env"]["공지"])

    # --- 사이드바: 제어 센터 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("작동 모드", ["일반 모드", "AI 챗봇 인터페이스 (Vibe)"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # --- 연산 로직 (통합 가중치 적용) ---
    day_weight = WEEKDAY_WEIGHTS[current_day]
    weather_multiplier = 1.2 if weather == "🌧️ 비/눈" else 1.0
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = get_safe_int(data[col_off])
    
    # 최종 혼잡도 및 소요 시간 계산
    final_congestion = min((base_count / 150000) * day_weight * weather_multiplier, 1.0)
    total_time = (4.0 + (final_congestion * 12)) * weather_multiplier
    is_crowded = final_congestion > 0.65

    if mode == "일반 모드":
        st.info(f"📊 **{current_day} 분석:** 평소 대비 유동인구가 **{int((day_weight-1)*100)}%** 변동되는 날입니다. (하차: {base_count:,}명)")
        
        tabs = st.tabs(["🚀 실시간 분석 가이드", "🍱 주변 추천 (Smart)", "🏢 역 정보 & 시간표"])

        # --- TAB 1: 실시간 분석 및 우회 가이드 ---
        with tabs[0]:
            m1, m2, m3 = st.columns(3)
            m1.metric("최종 혼잡도", f"{final_congestion*100:.1f}%", delta=f"{current_day} 보정")
            m2.metric("최적 하차문", STATION_DB["exits"][selected_exit]["door"])
            m3.metric("예상 소요 시간", f"{total_time:.1f} 분")

            col_l, col_r = st.columns([2, 1])
            with col_l:
                # 스마트 우회로(Detour) 계산
                target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
                best_detour = selected_exit
                if is_crowded:
                    other_exits = []
                    for name, info in STATION_DB["exits"].items():
                        if name != selected_exit:
                            dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                            score = dist if not (weather == "🌧️ 비/눈" and info["esc"]) else dist * 0.5
                            other_exits.append((name, score))
                    best_detour = sorted(other_exits, key=lambda x: x[1])[0][0]

                # 지도 생성
                center = [37.4979, 127.0276]
                m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                
                if is_crowded and best_detour != selected_exit:
                    st.success(f"💡 **우회 제안:** {selected_exit} 혼잡! **{best_detour}**로 우회하세요.")
                    folium.PolyLine([center, STATION_DB["exits"][best_detour]["coord"]], color="green", weight=7, tooltip="추천 우회로").add_to(m)
                    folium.Marker(STATION_DB["exits"][best_detour]["coord"], icon=folium.Icon(color='green')).add_to(m)
                else:
                    folium.PolyLine([center, target_coords], color="blue", weight=5).add_to(m)
                    folium.Marker(target_coords, icon=folium.Icon(color='blue')).add_to(m)
                
                st_folium(m, width="100%", height=400)

            with col_r:
                st.info(f"📍 **출구 정보**\n- {STATION_DB['exits'][selected_exit]['장소']}")
                st.success(f"🚍 **교통 연동**\n- 버스: {STATION_DB['exits'][selected_exit]['bus']}\n- 시설: {STATION_DB['exits'][selected_exit]['transit']}")
                season_info = STATION_DB["train_env"]["여름(약냉방)"] if 5 <= datetime.now().month <= 9 else STATION_DB["train_env"]["겨울(강한히터)"]
                st.write(f"🌡️ **시즌 팁:** {season_info}가 쾌적합니다.")

        # --- TAB 2: 스마트 장소 추천 ---
        with tabs[1]:
            st.subheader("📍 맞춤형 장소 제안")
            if is_crowded:
                alt_exit = "8번 출구" if "10" in selected_exit or "11" in selected_exit else "1번 출구"
                st.warning(f"⚠️ {selected_exit}은 현재 혼잡합니다. 상대적으로 한적한 {alt_exit} 근처 **'{STATION_DB['exits'][alt_exit]['recommend']}'**은 어떠세요?")
            else:
                st.write(f"✨ 현재 {selected_exit} 주변은 원활합니다. **'{STATION_DB['exits'][selected_exit]['recommend']}'** 방문을 추천합니다.")

        # --- TAB 3: 역 정보 & 시간표 ---
        with tabs[2]:
            st.subheader("🏢 강남역 통합 정보")
            c1, c2 = st.columns(2)
            with c1:
                for k, v in STATION_DB["general"].items():
                    if k != "first_last": st.write(f"**{k}:** {v}")
            with c2:
                st.markdown("**🏁 첫차/막차 시간**")
                st.table(pd.DataFrame(STATION_DB["general"]["first_last"], index=["첫차", "막차"]))

    # --- AI 챗봇 인터페이스 (Vibe Coding) ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        user_query = st.text_input("질문을 입력하세요", placeholder="지금 11번 출구 많이 막혀?")
        if user_query:
            if any(word in user_query for word in ["막혀", "혼잡", "사람"]):
                status = "매우 혼잡해요! 우회를 권장합니다." if is_crowded else "생각보다 널널해요."
                st.write(f"🤖 **분석:** {status} 현재 예상 하차 인원은 {base_count:,}명이며, 출구까지 약 {total_time:.1f}분 소요됩니다.")
            elif "추천" in user_query or "어디" in user_query:
                st.write(f"🤖 **분석:** {selected_exit} 근처라면 **{STATION_DB['exits'][selected_exit]['recommend']}**를 추천드려요.")
            else:
                st.write("🤖 **분석:** 질문을 이해했습니다. 현재 강남역의 '바이브'는 전반적으로 양호한 상태입니다!")

except Exception as e:
    st.error(f"시스템 오류 발생: {e}")
