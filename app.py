import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="강남역 실시간 동선 시뮬레이터", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='cp949')
    
    # 2호선 강남역 데이터 추출
    gangnam = df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]
    return gangnam

try:
    data = load_data()
    
    st.title("🚉 강남역 실시간 동선 최적화 & 대기행렬 시뮬레이터")
    st.sidebar.header("🕹️ 컨트롤 패널")
    
    # 시간대 선택
    selected_hour = st.sidebar.slider("시뮬레이션 시간대 (시)", 4, 23, 8)
    
    # 가변 게이트 설정 (대기행렬 시뮬레이션용)
    st.sidebar.subheader("⚙️ 운영 설정")
    active_gates = st.sidebar.number_input("현재 운영 개찰구 수", min_value=1, max_value=30, value=10)
    gate_capacity_per_min = st.sidebar.slider("개찰구당 분당 처리 능력", 10, 50, 30)

    # 데이터 추출
    col_on = f"{selected_hour:02d}시-{selected_hour+1:02d}시 승차인원"
    col_off = f"{selected_hour:02d}시-{selected_hour+1:02d}시 하차인원"
    val_on = int(data[col_on])
    val_off = int(data[col_off])

    # 1. 대기행렬 분석 (Queuing Theory) 로직
    # 현재 주요 흐름 파악 (출근-하차, 퇴근-승차)
    is_peak_morning = 7 <= selected_hour <= 9
    is_peak_evening = 17 <= selected_hour <= 19
    
    # 분석 대상 인원 설정
    current_target_flow = val_on if is_peak_evening else val_off
    lambda_per_sec = current_target_flow / 3600  # 초당 유입량
    mu_per_sec = (active_gates * gate_capacity_per_min) / 60  # 초당 처리 용량
    
    # 이용률(rho) 및 대기 시간 계산
    rho = lambda_per_sec / mu_per_sec if mu_per_sec > 0 else 9.9
    
    if rho < 1:
        # M/M/1 대기행렬 공식 기반 대기시간(W) 예측
        wait_time_sec = 1 / (mu_per_sec - lambda_per_sec)
    else:
        wait_time_sec = float('inf')

    # 상단 대시보드 지표
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 시각", f"{selected_hour:02d}:00")
    m2.metric("시간당 유입(Peak)", f"{current_target_flow:,}명")
    
    if wait_time_sec == float('inf'):
        m3.metric("예상 대기 시간", "측정 불가", delta="용량 초과", delta_color="inverse")
    else:
        m3.metric("예상 대기 시간", f"{wait_time_sec:.1f}초", 
                  delta="정상" if wait_time_sec < 30 else "혼잡", 
                  delta_color="normal" if wait_time_sec < 30 else "inverse")
        
    m4.metric("시스템 이용률", f"{min(rho*100, 100):.1f}%")

    st.divider()

    # 메인 시각화 레이아웃
    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        st.subheader("📍 실시간 동선 흐름 및 가변 운영 상태")
        
        # 역사 흐름도 시각화
        fig = go.Figure()
        # 역사 구역 레이아웃
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=5, line_color="black", fillcolor="white", opacity=0.1)
        
        # 출근 시간 로직 (2, 8번 출구 유도)
        if is_peak_morning:
            st.info("💡 **출근 피크 알림:** 하차 인원 분산을 위해 2번, 8번 출구를 '하차 전용'으로 운영 중입니다.")
            fig.add_annotation(x=2, y=5.2, text="2번 출구 (하차전용)", font=dict(color="red", size=15), showarrow=True)
            fig.add_annotation(x=8, y=5.2, text="8번 출구 (하차전용)", font=dict(color="red", size=15), showarrow=True)
            flow_color = "orange"
        # 퇴근 시간 로직 (가변 게이트 확대)
        elif is_peak_evening:
            st.warning("💡 **퇴근 피크 알림:** 승차 게이트를 '가변 확대 운영'하여 병목 현상을 최소화합니다.")
            fig.add_annotation(x=5, y=-0.5, text=f"가변 게이트 ({active_gates}개 가동 중)", font=dict(color="blue", size=15), showarrow=True)
            flow_color = "blue"
        else:
            st.success("💡 **평시 운영:** 역사 내 흐름이 안정적입니다.")
            flow_color = "green"

        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=450, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📊 대기행렬 예측 시뮬레이션")
        
        # 게이지 차트: 개찰구 통과 압박 지수
        gauge_val = min(rho * 100, 120)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = gauge_val,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "개찰구 혼잡도 (%)"},
            gauge = {
                'axis': {'range': [0, 120]},
                'bar': {'color': "darkblue" if rho < 1 else "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgreen"},
                    {'range': [50, 85], 'color': "yellow"},
                    {'range': [85, 120], 'color': "red"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 100}
            }
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

        if rho >= 1:
            st.error("🚨 **임계치 도달!** 현재 처리 용량이 유입량을 감당하지 못합니다. 개찰구 수를 즉시 늘리거나 유입 동선을 차단해야 합니다.")
        elif wait_time_sec > 40:
            st.warning("⚠️ **지체 발생:** 대기 시간이 40초를 초과했습니다. 보조 게이트 개방을 권장합니다.")

    # 하단: 데이터 시트 및 트렌드
    with st.expander("📝 강남역 원본 데이터 및 시간별 추이 보기"):
        st.write(f"선택된 시간 데이터: 승차 {val_on:,}명 / 하차 {val_off:,}명")
        hours = [f"{i:02d}시" for i in range(4, 24)]
        on_data = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
        off_data = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
        trend_df = pd.DataFrame({"시간": hours, "승차": on_data, "하차": off_data})
        st.line_chart(trend_df.set_index("시간"))

except Exception as e:
    st.error(f"파일을 로드할 수 없습니다: {e}")
    st.info("파일 이름이 '강남역 시간대별 승하차 인원 정보.csv'인지 확인해주세요.")
