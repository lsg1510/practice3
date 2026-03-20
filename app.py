import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="강남역 동선 최적화 시뮬레이터", layout="wide")

@st.cache_data
def load_data():
    # 파일 읽기 (사용자가 업로드한 파일명과 일치해야 함)
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
   
    st.title("🚉 강남역 실시간 동선 최적화 시뮬레이터")
    st.info("데이터 분석 결과에 따른 시간대별 최적 동선 가이드를 제공합니다.")

    # 사이드바: 시뮬레이션 시간 선택
    st.sidebar.header("🕒 시뮬레이션 설정")
    selected_hour = st.sidebar.slider("시뮬레이션 시간대 (시)", 4, 23, 8)

    # 선택된 시간의 승하차 데이터 추출
    col_on = f"{selected_hour:02d}시-{selected_hour+1:02d}시 승차인원"
    col_off = f"{selected_hour:02d}시-{selected_hour+1:02d}시 하차인원"
    val_on = data[col_on]
    val_off = data[col_off]

    # 상단 지표
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 시간", f"{selected_hour:02d}:00")
    c2.metric("승차 인원", f"{val_on:,} 명", delta_color="normal")
    c3.metric("하차 인원", f"{val_off:,} 명", delta_color="inverse")

    st.markdown("---")

    # 메인 시뮬레이션 영역
    left_col, right_col = st.columns([1.5, 1])

    with left_col:
        st.subheader("📍 역사 내 실시간 흐름 모니터링")
       
        # 단순화된 역사 맵 시각화 (Plotly 활용)
        fig = go.Figure()
       
        # 배경 (역사 구역)
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=5, line_color="RoyalBlue", fillcolor="LightSkyBlue", opacity=0.2)
       
        # 출구 및 게이트 표시
        if 7 <= selected_hour <= 9:  # 출근 시간
            status_text = "하차 승객 급증: 2, 8번 출구 집중 유도 중"
            fig.add_annotation(x=2, y=5.5, text="2번 출구 (하차전용)", showarrow=True, arrowhead=2, font=dict(color="red"))
            fig.add_annotation(x=8, y=5.5, text="8번 출구 (하차전용)", showarrow=True, arrowhead=2, font=dict(color="red"))
            color = "orange"
        elif 17 <= selected_hour <= 19:  # 퇴근 시간
            status_text = "승차 승객 급증: 가변 게이트 1~5번 승차 전용 운영"
            fig.add_annotation(x=5, y=-0.5, text="가변 게이트 (승차확대)", showarrow=True, arrowhead=2, font=dict(color="blue"))
            color = "blue"
        else:
            status_text = "정상 운영 모드"
            color = "green"

        fig.update_layout(title=status_text, xaxis=dict(visible=False), yaxis=dict(visible=False), height=400)
        st.plotly_chart(fig, use_container_width=True)

    with right_col:
        st.subheader("📢 시스템 권고 사항")
       
        if 7 <= selected_hour <= 9:
            st.warning(f"**[출근 피크]** 현재 하차 인원이 승차 인원의 {round(val_off/val_on, 1)}배입니다.")
            st.markdown("""
            - **조치 1:** 2번, 8번 출구 에스컬레이터 상향 전용 가동
            - **조치 2:** 역내 안내 방송 '우회로 이용' 송출
            - **조치 3:** 인근 오피스 빌딩 연결 통로 개방 확대
            """)
        elif 17 <= selected_hour <= 19:
            st.error(f"**[퇴근 피크]** 현재 승차 인원이 시간당 {val_on:,}명에 달합니다.")
            st.markdown("""
            - **조치 1:** 가변 게이트 1~5번을 **'승차 전용'**으로 전환
            - **조치 2:** 승강장 밀집도 분산을 위한 진입 통제 실시
            - **조치 3:** 우측 보행 및 동선 분리 유도선 활성화
            """)
        else:
            st.success("현재 역사 내 유동인구가 안정적입니다.")
            st.write("시설 점검 및 상시 모니터링을 유지하십시오.")

    # 하단 전체 트렌드 그래프
    st.subheader("📈 강남역 24시간 승하차 패턴 분석")
    hours = [f"{i:02d}시" for i in range(4, 24)]
    on_trends = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
    off_trends = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
   
    trend_df = pd.DataFrame({'시간': hours, '승차': on_trends, '하차': off_trends})
    fig_line = px.line(trend_df, x='시간', y=['승차', '하차'], markers=True,
                       title="시간대별 인원 추이", color_discrete_sequence=["#636EFA", "#EF553B"])
    st.plotly_chart(fig_line, use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.write("파일 이름이 '강남역 시간대별 승하차 인원 정보.csv'인지 확인해주세요.")
