import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import random
import time

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

    # --- 4. 가변 운영 알림 ---
    if is_evening_peak:
        st.toast("📢 [가변 운영] 1~4번 게이트가 '승차 전용'으로 변경되었습니다.", icon="ℹ️")
        st.warning("⚠️ **퇴근 시간 안내:** 현재 일부 개찰구가 승차 전용으로 가변 운영 중입니다. 하차 승객은 반대편 게이트를 이용하세요.")

    # --- 5. 열차 칸별 근접도 정보 ---
    st.divider()
    st.subheader("🚃 하차 칸별 에스컬레이터 근접도")
    
    # 10개 칸의 하차 후 혼잡도 랜덤 생성 (데이터가 없을 시 시뮬레이션)
    car_data = pd.DataFrame({
        '호차': [f"{i}호차" for i in range(1, 11)],
        '혼잡도': [random.randint(20, 90) for _ in range(10)]
    })
    
    # 현재 내 칸 표시
    car_data.loc[car_num-1, '혼잡도'] = car_data.loc[car_num-1, '혼잡도'] # 강조용
    
    fig_car = px.bar(car_data, x='호차', y='혼잡도', color='혼잡도', 
                     color_continuous_scale=['green', 'yellow', 'red'],
                     title="칸별 하차 후 계단/에스컬레이터 혼잡도")
    st.plotly_chart(fig_car, use_container_width=True)
    
    best_car = car_data.loc[car_data['혼잡도'].idxmin(), '호차']
    st.success(f"💡 현재 **{best_car}** 앞 에스컬레이터가 가장 한산합니다. 이동하여 내리는 것을 추천합니다!")

except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
