import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
import plotly.express as px
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
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

# --- 통합 데이터셋 (버스, 택시, 냉난방, 맛집 데이터 추가) ---
STATION_DB = {
    "exits": {
        "1번 출구": {"장소": "특허청", "door": "교대 1-1", "esc": True, "transit": "택시 승강장 인접", "bus": "광역버스(9404, 9503)", "recommend": "A 카페 (한적)"},
        "2번 출구": {"장소": "테헤란로", "door": "교대 2-3", "esc": False, "transit": "마을버스 서초03", "bus": "간선(146, 341)", "recommend": "B 브런치 (보통)"},
        "3번 출구": {"장소": "강남대로", "door": "교대 3-2", "esc": False, "transit": "공항버스 6009", "bus": "직행(1550, 1570)", "recommend": "C 맛집 (여유)"},
        "4번 출구": {"장소": "대치동 방면", "door": "교대 4-1", "esc": True, "transit": "택시 상시 대기", "bus": "간선(340, 420)", "recommend": "D 베이커리 (한적)"},
        "5번 출구": {"장소": "우성아파트", "door": "교대 5-2", "esc": True, "transit": "광역버스 정류장", "bus": "M버스(6427)", "recommend": "E 식당 (보통)"},
        "8번 출구": {"장소": "삼성전자 사옥", "door": "역삼 3-2", "esc": True, "transit": "지하 연결통로", "bus": "순환(41)", "recommend": "F 카페 (매우한적)"},
        "10번 출구": {"장소": "교보타워", "door": "역삼 1-1", "esc": False, "transit": "심야버스 N13", "bus": "광역(9711A)", "recommend": "G 술집 (매우혼잡)"},
        "11번 출구": {"장소": "강남역 사거리", "door": "역삼 1-1", "esc": True, "transit": "택시 승강장(대기 김)", "bus": "직행(1100, 2000)", "recommend": "H 카페 (혼잡)"},
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

try:
    data = load_data()
    st.title("🚉 강남역 스마트 내비게이션 v4.0")
    
    # --- 5. 긴급 사고 공지 (상단 배너) ---
    st.warning(STATION_DB["train_info"]["현재공지"])

    # --- 사이드바 및 환경 설정 ---
    st.sidebar.header("🕹️ 제어 센터")
    mode = st.sidebar.radio("모드 선택", ["일반 모드", "AI 챗봇 인터페이스 (Vibe)"])
    current_day = st.sidebar.selectbox("요일", list(WEEKDAY_WEIGHTS.keys()), index=datetime.now().weekday() if datetime.now().weekday() < 7 else 0)
    current_hour = st.sidebar.slider("시간대", 4, 23, datetime.now().hour)
    selected_exit = st.sidebar.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.sidebar.radio("날씨", ["☀️ 맑음", "🌧️ 비/눈"])

    # 연산 로직
    day_weight = WEEKDAY_WEIGHTS[current_day]
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    base_congestion = min(int(data[col_off]) / 160000, 1.0)
    final_congestion = min(base_congestion * day_weight, 1.0)
    is_crowded = final_congestion > 0.6

    if mode == "일반 모드":
        tabs = st.tabs(["📊 분석 대시보드", "🚀 실시간 가이드", "🍱 주변 추천"])

        # --- 3. 실시간 승하차 트렌드 대시보드 (Plotly) ---
        with tabs[0]:
            st.subheader("📈 시간대별 혼잡도 트렌드")
            hours = [f"{i:02d}시" for i in range(5, 24)]
            counts = [int(data[f"{i:02d}시-{i+1:02d}시 하차인원"]) * day_weight for i in range(5, 24)]
            
            df_trend = pd.DataFrame({"시간": hours, "예상 인원": counts})
            fig = px.line(df_trend, x="시간", y="예상 인원", markers=True, 
                          title=f"{current_day} 강남역 시간대별 유동인구 추이",
                          color_discrete_sequence=['#4285F4'])
            fig.add_vline(x=f"{current_hour:02d}시", line_dash="dash", line_color="red", annotation_text="현재 시뮬레이션")
            st.plotly_chart(fig, use_container_width=True)
            
            st.write(f"💡 **분석 결과:** 현재 {'피크 타임에 진입 중' if 17 <= current_hour <= 19 else '안정적인 흐름'}을 보이고 있습니다.")

        # --- 1, 2, 6. 가이드 (버스/택시/광역버스/냉난방) ---
        with tabs[1]:
            m1, m2, m3 = st.columns(3)
            m1.metric("실시간 혼잡도", f"{final_congestion*100:.1f}%")
            m2.metric("추천 하차칸", STATION_DB["exits"][selected_exit]["door"])
            m3.metric("냉난방 정보", "쾌적", delta="약냉방: 4,7호차")

            col_l, col_r = st.columns([2, 1])
            with col_l:
                m = folium.Map(location=[37.4979, 127.0276], zoom_start=18, tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
                folium.Marker(STATION_DB["exits"][selected_exit]["coord"], tooltip="목표 출구", icon=folium.Icon(color='blue')).add_to(m)
                st_folium(m, width="100%", height=400)

            with col_r:
                st.info(f"🚍 **연계 교통 정보**\n\n- **인접 정류장:** {STATION_DB['exits'][selected_exit]['transit']}\n- **주요 버스:** {STATION_DB['exits'][selected_exit]['bus']}")
                st.success(f"🌡️ **열차 팁:** {STATION_DB['train_info']['약냉방칸']}는 약냉방칸입니다.")

        # --- 4. 주변 혼잡도 연동 추천 ---
        with tabs[2]:
            st.subheader("📍 혼잡도 기반 장소 추천")
            if is_crowded:
                st.warning(f"⚠️ {selected_exit}은 현재 매우 혼잡합니다! 도보 3분 거리의 한적한 장소를 추천합니다.")
                alt_exit = "8번 출구" if selected_exit in ["10번 출구", "11번 출구"] else "1번 출구"
                st.write(f"✅ **대안 추천:** {alt_exit} 근처 **'{STATION_DB['exits'][alt_exit]['recommend']}'**")
            else:
                st.write(f"✨ {selected_exit} 근처는 현재 쾌적합니다. **'{STATION_DB['exits'][selected_exit]['recommend']}'**를 방문해보세요.")

    # --- 7. AI 챗봇 인터페이스 (Vibe Coding) ---
    else:
        st.subheader("💬 강남역 Vibe-AI")
        user_input = st.text_input("질문을 입력하세요 (예: 지금 비 오는데 11번 출구 많이 막혀?)", key="chat")
        if user_input:
            if "막혀" in user_input or "혼잡" in user_input:
                status = "지옥철 수준이에요. 우회로를 찾으세요!" if is_crowded else "생각보다 널널해요. 바로 가셔도 됩니다."
                weather_msg = "비가 와서 다들 출구 쪽에 몰려있으니 계단 조심하세요." if weather == "🌧️ 비/눈" else "날씨도 좋은데 가뿐하게 이동하시죠!"
                st.write(f"🤖 **AI 답변:** {status} {weather_msg} 현재 {selected_exit} 예상 하차 인원은 약 {int(data[col_off]):,}명입니다.")
            elif "버스" in user_input:
                st.write(f"🤖 **AI 답변:** {selected_exit}로 나가시면 {STATION_DB['exits'][selected_exit]['bus']}를 타기 가장 좋습니다.")
            else:
                st.write("🤖 **AI 답변:** 강남역의 '바이브'를 측정 중입니다. 요일, 시간, 날씨를 고려할 때 현재 컨디션은 'B+' 정도네요!")

except Exception as e:
    st.error(f"시스템 오류: {e}")
