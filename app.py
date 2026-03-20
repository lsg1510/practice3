import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션 v5.0", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 강남역 2호선 데이터만 필터링
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- UI 헤더 ---
    st.title("📱 강남역 스마트 내비게이션 (Passenger Beta)")
    st.caption("실시간 역내 혼잡도 및 최적 경로 가이드 시스템")

    # --- 사이드바: 승객 설정 ---
    st.sidebar.header("📍 내 위치 설정")
    current_hour = st.sidebar.slider("현재 시간 설정", 4, 23, 8)
    car_num = st.sidebar.selectbox("현재 탑승 칸 (1~10호차)", range(1, 11))
    target_exit = st.sidebar.selectbox("목적지 출구", [f"{i}번 출구" for i in range(1, 13)])

    # 데이터 추출
    col_on = f"{current_hour:02d}시-{current_hour+1:02d}시 승차인원"
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_on, val_off = int(data[col_on]), int(data[col_off])
    
    # 혼잡도 로직 (피크 시간대 기준 가중치 계산)
    is_morning_peak = 7 <= current_hour <= 9
    is_evening_peak = 17 <= current_hour <= 19
    flow_intensity = val_off if is_morning_peak else val_on
    congestion_score = min(flow_intensity / 150000, 1.0) # 임계치 15만명 기준

    # --- 1. 실시간 게이트/출구 혼잡도 '신호등' ---
    st.subheader("🚦 출구별 실시간 혼잡도")
    cols = st.columns(4)
    exits = ["2번(테헤란로)", "8번(삼성전자)", "10번(강남대로)", "11번(강남대로)"]
    
    for i, ex in enumerate(exits):
        # 특정 출구 쏠림 현상 랜덤 시뮬레이션 (실제 데이터 연동 시 개별 컬럼 활용)
        gate_status = "🔴 매우혼잡" if congestion_score > 0.7 and i > 1 else ("🟡 보통" if congestion_score > 0.4 else "🟢 원활")
        cols[i].metric(ex, gate_status)

    st.divider()

    # --- 2 & 3. Door-to-Gate 및 다이내믹 우회 경로 ---
    col_map, col_guide = st.columns([1.5, 1])

    with col_map:
        st.subheader("🗺️ 최적 우회 경로 가이드")
        
        # Plotly를 이용한 경로 시각화
        fig = go.Figure()
        # 역사 간략 도면
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=5, line_color="black", fillcolor="white", opacity=0.1)
        
        # 10, 11번 출구 마비 시나리오
        if is_morning_peak and congestion_score > 0.6:
            # 레드 존 (마비)
            fig.add_trace(go.Scatter(x=[9, 10], y=[4, 5], mode="lines+text", name="혼잡구간", line=dict(color="red", width=6)))
            # 우회 경로 (점선)
            fig.add_trace(go.Scatter(x=[car_num, 5, 2], y=[1, 2, 5], mode="lines+markers", 
                                     name="최적 우회로", line=dict(color="green", width=4, dash="dash")))
            route_msg = "⚠️ 10번 출구 마비! 9번 출구 우회 시 4분 단축"
        else:
            fig.add_trace(go.Scatter(x=[car_num, 9], y=[1, 5], mode="lines+markers", name="추천 경로", line=dict(color="blue", width=4)))
            route_msg = "✅ 현재 추천 경로로 이동하세요."

        fig.update_layout(showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_guide:
        st.subheader("⏱️ 예상 소요 시간")
        # 대기행렬 예측 계산 (Little's Law 응용)
        base_walk = 3 # 기본 보행 3분
        wait_penalty = congestion_score * 15 # 혼잡도에 따른 추가 대기 (최대 15분)
        total_time = base_walk + wait_penalty
        
        st.metric("현재 위치 ➔ 지상 출구", f"{total_time:.1f} 분")
        st.progress(congestion_score, text=f"역사 내 밀집도: {congestion_score*100:.1f}%")
        st.info(route_msg)

# --- [기능 1, 6, 7] 통합 데이터베이스 구축 ---
STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396",
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
        "2번 출구": {"장소": "테헤란로, 역삼1동 주민센터", "door": "교대 2-3, 역삼 9-2", "coord": [37.4983, 127.0282], "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)", "recommend": "B 브런치 (대기 적음)"},
        "5번 출구": {"장소": "서초동 우성아파트, 서초2동", "door": "교대 5-2, 역삼 6-3", "coord": [37.4961, 127.0275], "esc": True, "transit": "광역버스 정류장 밀집", "bus": "M버스(6427), 직행(1550-1)", "recommend": "E 식당 (혼밥 가능)"},
        "8번 출구": {"장소": "삼성전자 서초사옥", "door": "교대 8-3, 역삼 3-2", "coord": [37.4979, 127.0262], "esc": True, "transit": "지하 연결통로 이용가능", "bus": "순환(41)", "recommend": "F 라운지 (매우 쾌적)"},
        "10번 출구": {"장소": "교보타워, 서초동", "door": "교대 10-4, 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "transit": "중앙버스차로 인접", "bus": "심야(N13, N75)", "recommend": "G 술집 (항상 혼잡)"},
        "11번 출구": {"장소": "강남역 사거리, 역삼동", "door": "교대 10-4, 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True, "transit": "택시 승강장(대기 김)", "bus": "직행(1100, 2000, 7007)", "recommend": "H 베이커리 (인기 많음)"},
        "12번 출구": {"장소": "국립어린이청소년도서관", "door": "교대 7-3, 역삼 4-2", "coord": [37.4991, 127.0281], "esc": True, "transit": "국기원 방면 도보", "bus": "간선(740, 421)", "recommend": "I 북카페 (독서 최적)"}
    },
    "train_env": {
        "여름(약냉방)": "4, 7호차",
        "겨울(강한히터)": "1, 10호차 (양 끝 칸)",
        "공지": "🚨 [긴급] 2호선 외선순환 차량 고장으로 약 5분 지연 중 (실시간 관제 데이터 연동)"
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
    st.title("🚉 강남역 스마트 내비게이션 v5.0")
    
    # --- [기능 4] 실시간 긴급 알림 서비스 ---
    st.warning(STATION_DB["train_env"]["공지"])

    # --- 사이드바: 제어 센터 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("작동 모드", ["일반 모드", "AI 챗봇 인터페이스 (Vibe)"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("나갈 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # --- [기능 2] 연산 로직 (기상 상황 반영) ---
    day_weight = WEEKDAY_WEIGHTS[current_day]
    weather_impact = 1.2 if weather == "🌧️ 비/눈" else 1.0
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_count = get_safe_int(data[col_off])
    
    # 혼잡도 계산 (기상 상황에 따른 체감 혼잡도 가중치)
    final_congestion = min((base_count / 150000) * day_weight * weather_impact, 1.0)
    is_crowded = final_congestion > 0.65

    if mode == "일반 모드":
        tabs = st.tabs(["🚀 실시간 분석 가이드", "🍱 주변 추천 (Smart)", "🏢 역 정보 & 시간표"])

        # --- [기능 1, 2, 7] 실시간 분석 가이드 ---
        with tabs[0]:
            m1, m2, m3 = st.columns(3)
            m1.metric("예상 혼잡도", f"{final_congestion*100:.1f}%")
            m2.metric("최적 하차문", STATION_DB["exits"][selected_exit]["door"])
            # 계절별 냉난방 가이드
            season_info = STATION_DB["train_env"]["여름(약냉방)"] if 5 <= datetime.now().month <= 9 else STATION_DB["train_env"]["겨울(강한히터)"]
            m3.metric("쾌적 칸 안내", season_info, delta="추천")

            col_l, col_r = st.columns([2, 1])
            with col_l:
                m = folium.Map(location=[37.4979, 127.0276], zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                folium.Marker(STATION_DB["exits"][selected_exit]["coord"], tooltip=selected_exit, icon=folium.Icon(color='blue')).add_to(m)
                st_folium(m, width="100%", height=400)
            with col_r:
                st.info(f"📍 **출구 정보**\n- {STATION_DB['exits'][selected_exit]['장소']}")
                st.success(f"🚍 **교통 연동**\n- 버스: {STATION_DB['exits'][selected_exit]['bus']}\n- 시설: {STATION_DB['exits'][selected_exit]['transit']}")
                if weather == "🌧️ 비/눈" and not STATION_DB["exits"][selected_exit]["esc"]:
                    st.error("⚠️ 주의: 해당 출구는 계단이 많습니다. 비 오는 날 미끄럼 주의!")

        # --- [기능 3] 혼잡도 기반 장소 추천 (Smart Curation) ---
        with tabs[1]:
            st.subheader("📍 데이터 기반 추천 가이드")
            if is_crowded:
                # 혼잡 시 우회 출구 로직
                alt_exit = "8번 출구" if "10" in selected_exit or "11" in selected_exit else "12번 출구"
                st.warning(f"⚠️ {selected_exit}은 현재 매우 혼잡합니다! ({int(base_count):,}명 하차 중)")
                st.success(f"💡 **역발상 제안:** 상대적으로 여유로운 {alt_exit} 근처 **'{STATION_DB['exits'][alt_exit]['recommend']}'**에서 잠시 대기하시는 건 어떨까요?")
            else:
                st.write(f"✨ 현재 {selected_exit} 주변 흐름이 원활합니다. **'{STATION_DB['exits'][selected_exit]['recommend']}'**를 방문해보세요.")

        # --- [기능 6] 역 정보 & 시간표 ---
        with tabs[2]:
            st.subheader("🏢 강남역 통합 정보")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**📞 고객지원:** {STATION_DB['general']['전화번호']}")
                st.markdown(f"**🎒 분실물센터:** {STATION_DB['general']['분실물센터']}")
                st.markdown(f"**🚻 시설안내:** {STATION_DB['general']['시설']}")
            with c2:
                st.markdown("**🏁 첫차/막차 시간**")
                st.table(pd.DataFrame(STATION_DB["general"]["first_last"], index=["첫차", "막차"]))

    # --- [기능 5] AI 챗봇 인터페이스 (Vibe Coding) ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        st.caption("자연어로 질문하면 데이터 기반으로 답변해 드립니다.")
        user_query = st.text_input("무엇을 도와드릴까요?", placeholder="지금 비 오는데 11번 출구 많이 막혀?")
        
        if user_query:
            if any(word in user_query for word in ["막혀", "혼잡", "사람", "많아"]):
                status = "현재 발 디딜 틈이 없어요! ⚠️" if is_crowded else "쾌적하게 이동 가능합니다. ✨"
                weather_msg = "비가 오니 에스컬레이터가 있는 출구를 강력 추천해요." if weather == "🌧️ 비/눈" else "날씨가 좋으니 이동하기 딱 좋네요!"
                st.write(f"🤖 **Vibe 분석:** {status} {weather_msg} 현재 예상 유입 인원은 {base_count:,}명입니다.")
            elif "버스" in user_query or "타야" in user_query:
                st.write(f"🤖 **Vibe 분석:** {selected_exit}로 나가시면 {STATION_DB['exits'][selected_exit]['bus']}를 타기 가장 좋습니다. 환승 안내: {STATION_DB['exits'][selected_exit]['transit']}")
            elif "추천" in user_query or "어디" in user_query:
                target = STATION_DB['exits'][selected_exit]['recommend']
                st.write(f"🤖 **Vibe 분석:** {selected_exit} 근처라면 **{target}**을 추천드려요. 현재 혼잡도를 고려한 최적의 장소입니다!")
            else:
                st.write("🤖 **Vibe 분석:** 강남역의 '바이브'를 측정 중입니다. 요일, 시간, 날씨를 종합할 때 현재 컨디션은 나쁘지 않네요!")

except Exception as e:
    st.error(f"시스템 오류: {e}")
