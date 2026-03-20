import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="강남역 실시간 동선 최적화 시뮬레이터", layout="wide")

@st.cache_data
def load_data():
    file_path = '강남역 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    
    # 2호선 강남역 데이터 필터링
    gangnam = df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]
    return gangnam

try:
    data = load_data()
    
    st.title("🚉 강남역 실시간 동선 최적화 & 스마트 사이니지 시뮬레이터")
    
    # 사이드바 컨트롤 시스템
    st.sidebar.header("🕹️ 관제 시스템 설정")
    selected_hour = st.sidebar.slider("시뮬레이션 시간대 선택", 4, 23, 8)
    
    st.sidebar.subheader("⚙️ 운영 자원 설정")
    base_gates = st.sidebar.number_input("기본 운영 개찰구", 1, 30, 10)
    flex_gates = st.sidebar.slider("가변(승차전용) 게이트 개방", 0, 15, 0)
    total_gates = base_gates + flex_gates
    
    # 데이터 추출
    col_on = f"{selected_hour:02d}시-{selected_hour+1:02d}시 승차인원"
    col_off = f"{selected_hour:02d}시-{selected_hour+1:02d}시 하차인원"
    val_on = int(data[col_on])
    val_off = int(data[col_off])

    # --- 핵심 로직: 대기행렬 및 동선 최적화 ---
    is_morning = 7 <= selected_hour <= 9
    is_evening = 17 <= selected_hour <= 19
    
    # 피크 타임 대상 인원 설정
    flow_target = val_off if is_morning else val_on
    lambda_sec = flow_target / 3600  # 초당 유입량
    mu_sec = (total_gates * 35) / 60  # 초당 처리 용량 (분당 35명 기준)
    
    # 이용률 및 대기시간 계산
    rho = lambda_sec / mu_sec
    wait_time = 1 / (mu_sec - lambda_sec) if rho < 1 else float('inf')

    # 상단 대시보드
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("시뮬레이션 시점", f"{selected_hour:02d}:00")
    m2.metric("피크 방향 유입량", f"{flow_target:,}명/h")
    m3.metric("가용 게이트", f"{total_gates}개", f"가변 +{flex_gates}")
    
    wait_display = f"{wait_time:.1f}초" if wait_time != float('inf') else "용량 초과"
    m4.metric("예상 통과 시간", wait_display, delta="혼잡" if wait_time > 30 else "원활", delta_color="inverse")

    st.divider()

    # 메인 시뮬레이션 영역
    col_map, col_stat = st.columns([1.5, 1])

    with col_map:
        st.subheader("📍 실시간 동선 및 스마트 사이니지 모니터링")
        
        fig = go.Figure()
        # 역사 레이아웃
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=6, line_color="black", fillcolor="rgba(0,0,0,0.05)")

        # [출근 시간 로직]
        if is_morning:
            st.info("💡 **출근 모드:** 하차 승객 분산 및 출구 안내 최적화 실행 중")
            # 2, 8번 출구 혼잡도에 따른 우회 표시
            if wait_time > 25:
                # 혼잡 경로 (빨간색)
                fig.add_annotation(x=2, y=6.5, text="2번 출구 (매우혼잡)", font=dict(color="red"), showarrow=True)
                fig.add_annotation(x=8, y=6.5, text="8번 출구 (매우혼잡)", font=dict(color="red"), showarrow=True)
                # 우회 경로 안내 (초록색 사이니지)
                fig.add_annotation(x=4, y=6.5, text="7번 출구 (우회로:원활)", font=dict(color="green", size=14), showarrow=True, arrowhead=2)
                fig.add_annotation(x=6, y=6.5, text="11번 출구 (우회로:원활)", font=dict(color="green", size=14), showarrow=True, arrowhead=2)
                fig.add_annotation(x=5, y=3, text="📢 실시간 사이니지: '7, 11번 출구 이용 시 통과 5분 단축'", 
                                   bgcolor="green", font=dict(color="white"))
            else:
                fig.add_annotation(x=2, y=6.5, text="2번 출구", font=dict(color="orange"), showarrow=True)
                fig.add_annotation(x=8, y=6.5, text="8번 출구", font=dict(color="orange"), showarrow=True)

        # [퇴근 시간 로직]
        elif is_evening:
            st.warning("💡 **퇴근 모드:** 승차 전용 가변 게이트 및 진입 동선 제어 중")
            # 게이트 영역 시각화
            gate_color = "blue" if flex_gates > 5 else "lightblue"
            fig.add_shape(type="rect", x0=3, y0=0.5, x1=7, y1=1.2, fillcolor=gate_color, opacity=0.5)
            fig.add_annotation(x=5, y=0.1, text=f"가변 승차전용 게이트 {flex_gates}개 작동 중", font=dict(color="blue", size=14))
            
            if wait_time > 30:
                fig.add_annotation(x=5, y=4, text="⚠️ 승강장 밀집도 상승: 진입 속도 조절 사이니지 가동", 
                                   bgcolor="red", font=dict(color="white"))

        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), height=500, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_stat:
        st.subheader("📊 시스템 상태 예측")
        
        # 이용률 게이지
        gauge_val = min(rho * 100, 100)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = gauge_val,
            title = {'text': "개찰구 점유율 (%)"},
            gauge = {'axis': {'range': [0, 100]},
                     'bar': {'color': "red" if rho > 0.8 else "darkblue"},
                     'steps': [{'range': [0, 50], 'color': "lightgreen"},
                               {'range': [50, 80], 'color': "yellow"},
                               {'range': [80, 100], 'color': "red"}]}))
        st.plotly_chart(fig_gauge, use_container_width=True)

        # 대기행렬 분석 결과 보고
        st.write("---")
        if wait_time == float('inf'):
            st.error("🚨 **CRITICAL:** 처리 한계 초과. 즉시 추가 게이트 개방이 필요합니다.")
        elif wait_time > 40:
            st.warning(f"⚠️ **병목 주의:** 현재 통과 대기 {wait_time:.1f}초. 사이니지를 우회 모드로 전환합니다.")
        else:
            st.success("✅ **STABLE:** 현재 리소스로 수용 가능한 유입량입니다.")

    # 24시간 패턴 추이
    with st.expander("📈 강남역 일일 누적 패턴 확인"):
        hours = [f"{i:02d}시" for i in range(4, 24)]
        on_line = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
        off_line = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
        trend_df = pd.DataFrame({'시간': hours, '승차': on_line, '하차': off_line})
        st.line_chart(trend_df.set_index('시간'))

except Exception as e:
    st.error(f"오류 발생: {e}")
    st.info("CSV 파일명이 '강남역 시간대별 승하차 인원 정보.csv'인지 확인해 주세요.")
