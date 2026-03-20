import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v4.2", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    
    # 2호선 강남역 데이터 추출
    target_data = df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]
    return target_data

# --- 통합 데이터셋 ---
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
        "강한히터/냉방": "1호차, 10호차",
        "현재공지": "🚨 2호선 외선순환 차량 고장으로 약 5분 지연 운행 중 (12:45 기준)"
    }
}

WEEKDAY_WEIGHTS = {
    "월요일": 1.05, "화요일": 1.0, "수요일": 1.0, "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.9
}

# 안전한 정수 변환 헬퍼
def get_safe_int(val):
    try:
        if isinstance(val, str):
            val = val.replace(',', '')
        return int(float(val))
    except:
        return 0

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v4.2")
    st.warning(STATION_DB["train_info"]["현재공지"])

    # --- 사이드바 설정 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("모드 선택", ["일반 가이드 모드", "AI 챗봇 인터페이스 (Vibe)"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, int(datetime.now().hour))
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # 연산 로직
    day_weight = WEEKDAY_WEIGHTS[current_day]
    next_hour = current_hour + 1
    col_off = f"{current_hour:02d}시-{next_hour:02d}시 하차인원"
    
    current_passengers = get_safe_int(data[col_off])
    base_congestion = min(current_passengers / 160000, 1.0)
    final_congestion = min(base_congestion * day_weight, 1.0)
    is_crowded = final_congestion > 0.6

    if mode == "일반 가이드 모드":
        # 대시보드 탭을 삭제하고 실시간 가이드와 추천 탭만 유지
        tabs = st.tabs(["🚀 실시간 가이드", "🍱 주변 추천"])

        # --- TAB 1: 실시간 가이드 ---
        with tabs[0]:
            m1, m2, m3 = st.columns(3)
            m1.metric("실시간 혼잡도", f"{final_congestion*100:.1f}%")
            m2.metric("추천 하차칸", STATION_DB["exits"][selected_exit]["door"])
            m3.metric("냉난방 정보", "쾌적", delta="약냉방: 4,7호차")

            col_l, col_r = st.columns([2, 1])
            with col_l:
                m = folium.Map(location=[37.4979, 127.0276], zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                folium.Marker(STATION_DB["exits"][selected_exit]["coord"], tooltip=selected_exit, icon=folium.Icon(color='blue')).add_to(m)
                st_folium(m, width="100%", height=450)
            
            with col_r:
                st.info(f"🚍 **연계 교통 정보**\n\n- **인접:** {STATION_DB['exits'][selected_exit]['transit']}\n- **버스:** {STATION_DB['exits'][selected_exit]['bus']}")
                st.success(f"🌡️ **열차 팁:** {STATION_DB['train_info']['약냉방칸']}는 약냉방칸입니다.")

        # --- TAB 2: 주변 추천 ---
        with tabs[1]:
            st.subheader("📍 혼잡도 기반 장소 추천")
            if is_crowded:
                st.warning(f"⚠️ {selected_exit}은 현재 매우 혼잡합니다!")
                # 혼잡 시 대안 출구 로직
                alt_exit = "8번 출구" if "10번" in selected_exit or "11번" in selected_exit else "1번 출구"
                st.success(f"💡 인파를 피해 상대적으로 한적한 {alt_exit} 근처 **'{STATION_DB['exits'][alt_exit]['recommend']}'**에서 잠시 대기하는 건 어떨까요?")
            else:
                st.write(f"✨ {selected_exit} 근처는 현재 쾌적합니다. **'{STATION_DB['exits'][selected_exit]['recommend']}'**를 방문해보세요.")

    # --- AI 챗봇 모드 ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        user_input = st.text_input("질문을 입력하세요 (예: 11번 출구 버스 뭐 있어?)", key="chat_input")
        if user_input:
            if any(word in user_input for word in ["막혀", "혼잡", "사람"]):
                status = "지금 사람이 정말 많아요!" if is_crowded else "생각보다 여유롭습니다."
                st.write(f"🤖 **AI 답변:** {status} 현재 {selected_exit} 예상 하차 인원은 약 {current_passengers:,}명입니다.")
            elif "버스" in user_input:
                st.write(f"🤖 **AI 답변:** {selected_exit} 인근에는 {STATION_DB['exits'][selected_exit]['bus']} 노선이 운행 중입니다.")
            else:
                st.write("🤖 **AI 답변:** 강남역 현재 상태를 분석 중입니다. 다른 궁금한 점이 있으신가요?")

except Exception as e:
    st.error(f"⚠️ 시스템 오류: {e}")
