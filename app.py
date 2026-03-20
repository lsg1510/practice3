import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v4.0", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 강남역 2호선 데이터 추출
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터셋 (버스, 택시, 냉난방, 맛집 데이터 추가) ---
STATION_DB = {
    "exits": {
        "1번 출구": {"coord": [37.4981, 127.0286], "장소": "특허청", "door": "교대 1-1", "esc": True, "transit": "택시 승강장 인접", "bus": "광역버스(9404, 9503)", "recommend": "A 카페 (한적)"},
        "2번 출구": {"coord": [37.4983, 127.0282], "장소": "테헤란로", "door": "교대 2-3", "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)", "recommend": "B 브런치 (보통)"},
        "3번 출구": {"coord": [37.4972, 127.0284], "장소": "강남대로", "door": "교대 3-2", "esc": False, "transit": "공항버스 6009", "bus": "직행(1550, 1570)", "recommend": "C 맛집 (여유)"},
        "4번 출구": {"coord": [37.4965, 127.0281], "장소": "대치동 방면", "door": "교대 4-1", "esc": True, "transit": "택시 상시 대기", "bus": "간선(340, 420)", "recommend": "D 베이커리 (한적)"},
        "5번 출구": {"coord": [37.4961, 127.0275], "장소": "우성아파트", "door": "교대 5-2", "esc": True, "transit": "광역버스 정류장", "bus": "M버스(6427)", "recommend": "E 식당 (보통)"},
        "8번 출구": {"coord": [37.4979, 127.0262], "장소": "삼성전자 사옥", "door": "역삼 3-2", "esc": True, "transit": "지하 연결통로", "bus": "순환(41)", "recommend": "F 카페 (매우한적)"},
        "10번 출구": {"coord": [37.4986, 127.0272], "장소": "교보타워", "door": "역삼 1-1", "esc": False, "transit": "심야버스 N13", "bus": "광역(9711A)", "recommend": "G 술집 (매우혼잡)"},
        "11번 출구": {"coord": [37.4989, 127.0275], "장소": "강남역 사거리", "door": "역삼 1-1", "esc": True, "transit": "택시 승강장(대기 김)", "bus": "직행(1100, 2000)", "recommend": "H 카페 (혼잡)"},
    },
    "train_info": {
        "약냉방칸": "4호차, 7호차",
        "강한히터": "1호차, 10호차",
        "현재공지": "🚨 [실시간] 2호선 외선순환 차량 고장으로 약 5분 지연 운행 중 (13:05 기준)"
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
    st.title("🚉 강남역 스마트 내비게이션 v4.0")
    
    # --- 기능 5: 긴급 사고 및 지연 공지 (RSS/API 모사) ---
    st.warning(STATION_DB["train_info"]["현재공지"])

    # --- 사이드바: 제어 센터 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("작동 모드", ["일반 모드", "AI 챗봇 인터페이스 (Vibe)"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # 연산 로직
    day_weight = WEEKDAY_WEIGHTS[current_day]
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = get_safe_int(data[col_off])
    final_congestion = min(base_count / 160000 * day_weight, 1.0)
    is_crowded = final_congestion > 0.6

    if mode == "일반 모드":
        tabs = st.tabs(["🚀 실시간 가이드", "🍱 주변 추천", "🏢 역 시설 정보"])

        # --- 기능 1, 2, 6: 실시간 가이드 (버스/택시/냉난방) ---
        with tabs[0]:
            m1, m2, m3 = st.columns(3)
            m1.metric("실시간 혼잡도", f"{final_congestion*100:.1f}%")
            m2.metric("추천 하차문", STATION_DB["exits"][selected_exit]["door"])
            m3.metric("냉난방 정보", "쾌적", delta=f"약냉방: {STATION_DB['train_info']['약냉방칸']}")

            col_l, col_r = st.columns([2, 1])
            with col_l:
                m = folium.Map(location=[37.4979, 127.0276], zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                folium.Marker(STATION_DB["exits"][selected_exit]["coord"], tooltip=selected_exit, icon=folium.Icon(color='blue')).add_to(m)
                st_folium(m, width="100%", height=400)
            with col_r:
                st.info(f"🚍 **연계 교통 정보**\n\n- **환승 안내:** {STATION_DB['exits'][selected_exit]['transit']}\n- **주요 버스:** {STATION_DB['exits'][selected_exit]['bus']}")
                st.success(f"🌡️ **시즌 팁:** 겨울철엔 {STATION_DB['train_info']['강한히터']}가 가장 따뜻합니다.")

        # --- 기능 4: 주변 혼잡도 연동 맛집/카페 추천 ---
        with tabs[1]:
            st.subheader("📍 맞춤형 장소 제안")
            if is_crowded:
                alt_exit = "8번 출구" if "10" in selected_exit or "11" in selected_exit else "1번 출구"
                st.warning(f"⚠️ {selected_exit}은 현재 매우 혼잡합니다! 인파를 피해 상대적으로 한적한 {alt_exit} 근처 **'{STATION_DB['exits'][alt_exit]['recommend']}'**에서 잠시 대기하시는 건 어떨까요?")
            else:
                st.write(f"✨ 현재 {selected_exit} 근처는 여유롭습니다. **'{STATION_DB['exits'][selected_exit]['recommend']}'** 방문을 추천드려요.")

        with tabs[2]:
            st.write("📍 **강남역 기본 정보:** 서울특별시 강남구 강남대로 지하 396")
            st.write("🚽 **시설:** 수유실(지하1층), 무인민원발급기(2, 7번 출구 인근)")

    # --- 기능 7: Vibe Coding 기반 AI 챗봇 ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        st.write("바쁜 현대인을 위해 자연어로 현재 상황을 요약해 드립니다.")
        user_query = st.text_input("질문을 입력하세요", placeholder="지금 비 오는데 11번 출구 많이 막혀?")
        
        if user_query:
            if any(word in user_query for word in ["막혀", "혼잡", "사람"]):
                status = "지옥철 수준이에요. 우회로를 찾으세요!" if is_crowded else "생각보다 널널해요. 바로 가셔도 됩니다."
                weather_msg = "비가 오니 계단 조심하시고 에스컬레이터가 있는 출구를 이용하세요." if weather == "🌧️ 비/눈" else "날씨가 좋으니 가볍게 이동하시죠!"
                st.write(f"🤖 **AI 분석:** {status} {weather_msg} 현재 예상 하차 인원은 {base_count:,}명입니다.")
            elif "버스" in user_query or "타야" in user_query:
                st.write(f"🤖 **AI 분석:** {selected_exit}로 나가시면 {STATION_DB['exits'][selected_exit]['bus']}를 타기 가장 좋습니다.")
            else:
                st.write("🤖 **AI 분석:** 강남역의 '바이브'를 측정 중입니다. 현재 혼잡도는 B+ 등급으로 무난한 편이네요!")

except Exception as e:
    st.error(f"시스템 오류: {e}")
