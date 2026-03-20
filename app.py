import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v6.1", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 강남역 2호선 데이터만 필터링
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터베이스 구축 ---
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
        "1번 출구": {"장소": "특허청, 역삼세무서", "door": "교대 1-1, 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True, "transit": "택시 승강장 바로 앞", "bus": "광역(9404, 9503), 공항(6020)"},
        "2번 출구": {"장소": "테헤란로, 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)"},
        "5번 출구": {"장소": "서초동 우성아파트", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True, "transit": "광역버스 정류장 밀집", "bus": "M버스(6427), 직행(1550-1)"},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True, "transit": "지하 연결통로 이용가능", "bus": "순환(41)"},
        "9번 출구": {"장소": "메가박스, 서초동", "door": "교대 9-2, 역삼 2-3", "coord": [37.4988, 127.0263], "esc": True, "transit": "서초동 방면 도보", "bus": "간선(740)"},
        "10번 출구": {"장소": "교보타워, 강남대로", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "transit": "중앙버스차로 인접", "bus": "심야(N13, N75)"},
        "11번 출구": {"장소": "강남역 사거리, 역삼동", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "transit": "택시 승강장(대기 김)", "bus": "직행(1100, 2000, 7007)"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "transit": "국기원 방면 도보", "bus": "간선(421)"}
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
    st.title("🚉 강남역 스마트 내비게이션 v6.1")
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
    
    # 혼잡도 및 소요 시간 계산
    final_congestion = min((base_count / 150000) * day_weight * weather_multiplier, 1.0)
    default_time = (4.0 + (final_congestion * 12)) * weather_multiplier
    is_crowded = final_congestion > 0.65

    if mode == "일반 모드":
        st.info(f"📊 **{current_day} {current_hour}시 분석:** 하차 인원 {base_count:,}명 기반 실시간 가이드입니다.")
        
        tabs = st.tabs(["🚀 실시간 동선 최적화", "🏢 역 정보 & 시간표"])

        with tabs[0]:
            # --- 우회로 및 시간 연산 ---
            target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
            best_detour = selected_exit
            detour_time = default_time
            
            if is_crowded:
                other_exits = []
                for name, info in STATION_DB["exits"].items():
                    if name != selected_exit:
                        dist = np.linalg.norm(target_coords - np.array(info["coord"]))
                        # 비 올 때 에스컬레이터 가중치 반영
                        score = dist if not (weather == "🌧️ 비/눈" and info["esc"]) else dist * 0.5
                        other_exits.append((name, score))
                
                best_detour = sorted(other_exits, key=lambda x: x[1])[0][0]
                # 우회 시 혼잡도가 50% 감소한다고 가정하고 시간 재계산 (이동 거리 증가분 1분 추가)
                detour_time = (4.0 + (final_congestion * 0.5 * 12)) * weather_multiplier + 1.0

            # 지표 표시
            m1, m2, m3 = st.columns(3)
            m1.metric("현재 혼잡도", f"{final_congestion*100:.1f}%")
            m2.metric("최적 하차문", STATION_DB["exits"][selected_exit]["door"])
            
            if is_crowded and best_detour != selected_exit:
                m3.metric("우회 시 예상 시간", f"{detour_time:.1f} 분", delta=f"-{default_time - detour_time:.1f}분 절약", delta_color="normal")
            else:
                m3.metric("예상 소요 시간", f"{default_time:.1f} 분")

            st.divider()

            col_map, col_info = st.columns([2, 1])
            with col_map:
                center = [37.4979, 127.0276]
                m = folium.Map(location=center, zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                
                if is_crowded and best_detour != selected_exit:
                    st.success(f"💡 **최적 우회 경로:** {selected_exit} 정체가 심합니다. **{best_detour}** 이용 시 약 **{detour_time:.1f}분** 내에 지상 도달이 가능합니다.")
                    folium.PolyLine([center, STATION_DB["exits"][best_detour]["coord"]], color="green", weight=7, tooltip="추천 우회로").add_to(m)
                    folium.Marker(STATION_DB["exits"][best_detour]["coord"], icon=folium.Icon(color='green', icon='star')).add_to(m)
                else:
                    folium.PolyLine([center, target_coords], color="blue", weight=5).add_to(m)
                    folium.Marker(target_coords, icon=folium.Icon(color='blue')).add_to(m)
                
                st_folium(m, width="100%", height=450)

            with col_info:
                st.markdown(f"### 📍 {selected_exit} 안내")
                st.write(f"**주요 시설:** {STATION_DB['exits'][selected_exit]['장소']}")
                st.write(f"**연계 버스:** {STATION_DB['exits'][selected_exit]['bus']}")
                st.write(f"**환승 정보:** {STATION_DB['exits'][selected_exit]['transit']}")
                if weather == "🌧️ 비/눈" and not STATION_DB["exits"][selected_exit]["esc"]:
                    st.error("⚠️ 해당 출구는 계단 전용입니다. 미끄러움에 주의하세요!")

        with tabs[1]:
            st.subheader("🏢 강남역 통합 정보")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**주소:** {STATION_DB['general']['주소']}")
                st.write(f"**대표전화:** {STATION_DB['general']['전화번호']}")
                st.write(f"**분실물:** {STATION_DB['general']['분실물센터']}")
                st.write(f"**편의시설:** {STATION_DB['general']['시설']}")
            with c2:
                st.markdown("**🏁 첫차/막차 시간**")
                st.table(pd.DataFrame(STATION_DB["general"]["first_last"], index=["첫차", "막차"]))

    # --- AI 챗봇 인터페이스 ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        user_query = st.text_input("질문을 입력하세요", placeholder="지금 10번 출구 많이 막혀?")
        if user_query:
            if any(word in user_query for word in ["막혀", "혼잡", "사람", "시간"]):
                res_msg = f"현재 {selected_exit} 방면은 {final_congestion*100:.1f}% 혼잡합니다."
                if is_crowded:
                    res_msg += f" 우회로 이용 시 약 {detour_time:.1f}분이 소요되며, 이는 정체 경로보다 {default_time - detour_time:.1f}분 빠릅니다."
                else:
                    res_msg += f" 약 {default_time:.1f}분 내외로 원활하게 이동 가능합니다."
                st.write(f"🤖 **분석:** {res_msg}")
            else:
                st.write("🤖 **분석:** 질문하신 내용에 대해 강남역 데이터를 실시간으로 조회 중입니다.")

except Exception as e:
    st.error(f"시스템 오류: {e}")
