import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 페이지 설정
st.set_page_config(page_title="강남역 스마트 내비게이션", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    # 2호선 강남역 데이터 추출
    return df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]

try:
    data = load_data()
    
    # --- UI 헤더 ---
    st.title("📱 강남역 스마트 내비게이션 (Passenger Beta)")
    st.caption("실시간 역사 내 혼잡도 분석 및 최적 우회 경로 가이드")

    # --- 사이드바: 승객 설정 ---
    st.sidebar.header("📍 실시간 위치 및 설정")
    current_hour = st.sidebar.slider("시뮬레이션 시간 설정", 4, 23, 8)
    car_num = st.sidebar.selectbox("현재 탑승 칸 (1~10호차)", range(1, 11))
    target_exit = st.sidebar.selectbox("목적지 출구", [f"{i}번 출구" for i in range(1, 13)])

    # 데이터 추출
    col_on = f"{current_hour:02d}시-{current_hour+1:02d}시 승차인원"
    col_off = f"{current_hour:02d}시-{current_hour+1:02d}시 하차인원"
    val_on, val_off = int(data[col_on]), int(data[col_off])
    
    # 혼잡도 엔진 (임계치 기반 정규화)
    is_morning_peak = 7 <= current_hour <= 9
    is_evening_peak = 17 <= current_hour <= 19
    # 출근시엔 하차, 퇴근시엔 승차 데이터에 가중치 부여
    flow_intensity = val_off if is_morning_peak else val_on
    congestion_score = min(flow_intensity / 150000, 1.0) 

    # --- 1. 실시간 게이트/출구 혼잡도 '신호등' ---
    st.subheader("🚦 출구별 실시간 혼잡도")
    cols = st.columns(4)
    exits = ["2번(테헤란로)", "8번(삼성전자)", "10번(강남대로)", "11번(강남대로)"]
    
    for i, ex in enumerate(exits):
        # 특정 출구 쏠림 현상 시뮬레이션
        if congestion_score > 0.7 and i >= 2: # 10, 11번 출구 집중 혼잡 상황
            status = "🔴 매우혼잡"
        elif congestion_score > 0.4:
            status = "🟡 보통"
        else:
            status = "🟢 원활"
        cols[i].metric(ex, status)

    st.divider()

    # --- 2 & 3. Door-to-Gate 및 다이내믹 우회 경로 ---
    col_map, col_guide = st.columns([1.5, 1])

    with col_map:
        st.subheader("🗺️ 실시간 최적 경로 가이드")
        
        fig = go.Figure()
        # 역사 간략 도면 배경
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=5, line_color="gray", fillcolor="rgba(0,0,0,0.05)")
        
        # 다이내믹 루팅 로직
        if is_morning_peak and congestion_score > 0.6:
            # 병목 구간 표시 (10, 11번 방향)
            fig.add_trace(go.Scatter(x=[8, 10], y=[4, 5], mode="lines", name="병목", line=dict(color="red", width=8)))
            # 우회 경로 (여유 있는 2, 7번 방향)
            fig.add_trace(go.Scatter(x=[car_num, 5, 2], y=[1, 2, 5], mode="lines+markers", 
                                     name="최적 우회로", line=dict(color="green", width=5, dash="dash")))
            route_msg = "⚠️ 강남대로 방향(10, 11번) 마비! **2번 출구 우회**를 강력 권장합니다."
            route_color = "red"
        else:
            # 일반 경로
            fig.add_trace(go.Scatter(x=[car_num, 9], y=[1, 5], mode="lines+markers", name="추천 경로", line=dict(color="blue", width=4)))
            route_msg = "✅ 현재 선택하신 출구까지 경로가 원활합니다."
            route_color = "green"

        fig.update_layout(showlegend=False, xaxis=dict(visible=False), yaxis=dict(visible=False), height=450, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_guide:
        st.subheader("⏱️ 예상 소요 시간 (Door-to-Gate)")
        
        # 리틀의 법칙을 응용한 대기 시간 예측
        # 기본 도보 4분 + (혼잡도에 따른 지연 가중치)
        base_walk_min = 4.0
        delay_factor = congestion_score * 12 # 최대 12분 지연 가정
        predicted_time = base_walk_min + delay_factor
        
        st.metric("현재 위치 ➔ 지상 출구", f"{predicted_time:.1f} 분")
        
        # 혼잡도 프로그레스 바
        bar_color = "red" if congestion_score > 0.7 else "orange" if congestion_score > 0.4 else "green"
        st.write(f"역사 내 밀집 지수: **{congestion_score*100:.1f}%**")
        st.progress(congestion_score)
        
        if route_color == "red":
            st.error(route_msg)
        else:
            st.success(route_msg)

    # --- 4. 가변 운영 알림 ---
    if is_evening_peak:
        st.sidebar.warning("📢 **공지: 가변 게이트 운영**\n퇴근 시간대 승차 효율을 위해 중앙 개찰구가 '승차 전용'으로 운영 중입니다.")
        if congestion_score > 0.8:
            st.toast("🚨 역사 내 밀집도가 위험 수준입니다. 안내 요원의 지시에 따라주세요.")

    # 하단 데이터 인사이트
    with st.expander("📊 시간대별 승하차 통계 확인"):
        hours = [f"{i:02d}시" for i in range(4, 24)]
        on_line = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
        off_line = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
        df_trend = pd.DataFrame({'시간': hours, '승차': on_line, '하차': off_line}).set_index('시간')
        st.line_chart(df_trend)

except Exception as e:
    st.error(f"데이터 파일 확인 필요: {e}")
    st.info("CSV 파일이 동일 경로에 있는지, 컬럼명이 데이터와 일치하는지 확인하십시오.")
