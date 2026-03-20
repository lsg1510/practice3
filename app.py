import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 페이지 설정
st.set_page_config(page_title="강남역 실시간 동선 시뮬레이터", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        # 다양한 인코딩 시도
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    
    # 2호선 강남역 데이터 필터링
    gangnam = df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]
    return gangnam

try:
    data = load_data()
    
    st.title("🚉 강남역 실시간 동선 최적화 & 대기행렬 시뮬레이터")
    
    # 사이드바 컨트롤러
    st.sidebar.header("🕹️ 관제 시스템 설정")
    selected_hour = st.sidebar.slider("시뮬레이션 시간대 선택", 4, 23, 8)
    
    st.sidebar.subheader("⚙️ 가변 게이트 설정")
    base_gates = st.sidebar.number_input("기본 운영 개찰구 수", 1, 30, 10)
    flex_gates = st.sidebar.slider("가변(추가) 개찰구 개방", 0, 10, 0)
    total_gates = base_gates + flex_gates
    
    # 데이터 추출 및 가공
    col_on = f"{selected_hour:02d}시-{selected_hour+1:02d}시 승차인원"
    col_off = f"{selected_hour:02d}시-{selected_hour+1:02d}시 하차인원"
    val_on = int(data[col_on])
    val_off = int(data[col_off])

    # --- 핵심 분석 로직 (대기행렬 및 우회) ---
    is_morning_peak = 7 <= selected_hour <= 9
    is_evening_peak = 17 <= selected_hour <= 19
    
    # 분석 대상 설정 (출근 시 하차인원 위주, 퇴근 시 승차인원 위주)
    target_flow = val_off if is_morning_peak else val_on
    lambda_sec = target_flow / 3600  # 초당 유입량
    
    # 개찰구 처리 능력 (분당 30명 가정)
    mu_sec = (total_gates * 30) / 60
    
    # 대기 시간 계산 (리틀의 법칙 기반 단순화)
    rho = lambda_sec / mu_sec
    if rho < 1:
        wait_time = 1 / (mu_sec - lambda_sec)
    else:
        wait_time = float('inf')

    # 상단 대시보드 지표
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("시뮬레이션 시점", f"{selected_hour:02d}:00")
    m2.metric("시간당 유입(Peak)", f"{target_flow:,}명")
    m3.metric("운영 게이트", f"{total_gates}개", f"가변 +{flex_gates}")
    
    if wait_time == float('inf'):
        m4.metric("예상 통과 시간", "용량 초과", delta="위험", delta_color="inverse")
    else:
        m4.metric("예상 통과 시간", f"{wait_time:.1f}초", 
                  delta="혼잡" if wait_time > 30 else "정상",
                  delta_color="inverse" if wait_time > 30 else "normal")

    st.divider()

    # 메인 섹션
    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        st.subheader("🌐 역사 내 실시간 흐름 모니터링 & 사이니지")
        
        # 역사 맵 추상화 (Plotly)
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=6, line_color="black", fillcolor="rgba(0,0,0,0)")

        # 출근 시간대 로직: 출구 분산 안내
        if is_morning_peak:
            # 2, 8번 출구 혼잡 시 7, 11번 우회 유도
            is_overloaded = wait_time > 20
            color_2_8 = "red" if is_overloaded else "orange"
            color_7_11 = "green"
            
            fig.add_annotation(x=2, y=6.5, text="2번 출구 (혼잡)", font=dict(color=color_2_8), showarrow=True)
            fig.add_annotation(x=8, y=6.5, text="8번 출구 (혼잡)", font=dict(color=color_2_8), showarrow=True)
            
            if is_overloaded:
                fig.add_annotation(x=5, y=3, text="📢 안내: 7, 11번 출구 이용 시 5분 단축", 
                                   font=dict(size=15, color="green"), bordercolor="green", borderpad=4)
                fig.add_annotation(x=4, y=6.5, text="7번 출구 (여유)", font=dict(color=color_7_11), showarrow=True)
                fig.add_annotation(x=6, y=6.5, text="11번 출구 (여유)", font=dict(color=color_7_11), showarrow=True)
        
        # 퇴근 시간대 로직: 가변 게이트 시각화
        elif is_evening_peak:
            fig.add_annotation(x=5, y=-0.8, text=f"🔵 가변 게이트 {flex_gates}개 '승차 전용' 전환 중", 
                               font=dict(size=14, color="blue"), showarrow=False)
            # 게이트 영역 표시
            fig.add_shape(type="rect", x0=3, y0=0.5, x1=7, y1=1, fillcolor="blue", opacity=0.3)

        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=500, margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📊 가변 운영 시뮬레이션 결과")
        
        # 혼잡도 게이지
        gauge_val = min(rho * 100, 100)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = gauge_val,
            title = {'text': "개찰구 점유율 (%)"},
            gauge = {'axis': {'range': [0, 100]},
                     'bar': {'color': "red" if rho > 0.8 else "darkblue"},
                     'steps': [
                         {'range': [0, 50], 'color': "lightgreen"},
                         {'range': [50, 80], 'color': "yellow"},
                         {'range': [80, 100], 'color': "red"}]}
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 시스템 메시지
        if wait_time == float('inf') or rho > 1:
            st.error("🚨 **긴급:** 대기행렬이 무한히 늘어나고 있습니다. 가변 게이트를 즉시 최대 개방하십시오.")
        elif wait_time > 30:
            st.warning(f"⚠️ **병목 발생:** 현재 경로 대기 {wait_time:.1f}초. 우회 안내 사이니지를 활성화합니다.")
            st.info("**최적 우회 경로:** 7번, 11번 출구 방향 안내선 점등")
        else:
            st.success("✅ **정상 운영:** 현재 유입 인원을 안정적으로 처리하고 있습니다.")

    # 하단 24시간 분석
    st.subheader("📅 강남역 시간대별 승하차 추이")
    hours = [f"{i:02d}시" for i in range(4, 24)]
    on_trends = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
    off_trends = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
    
    trend_df = pd.DataFrame({'시간': hours, '승차': on_trends, '하차': off_trends})
    fig_trend = px.area(trend_df, x='시간', y=['승차', '하차'], 
                        title="24시간 유동인구 패턴", 
                        color_discrete_map={'승차': '#1f77b4', '하차': '#ff7f0e'})
    st.plotly_chart(fig_trend, use_container_width=True)

except Exception as e:
    st.error(f"데이터 파일 오류: {e}")
    st.info("폴더 내에 '강남역 시간대별 승하차 인원 정보.csv' 파일이 있는지 확인해 주세요.")
