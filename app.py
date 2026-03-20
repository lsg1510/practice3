import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(page_title="강남역 동선 최적화 시뮬레이터", layout="wide")

@st.cache_data
def load_data():
    # 업로드된 파일 경로 (사용자 환경에 맞춰 파일명 확인 필요)
    file_path = '서울시 지하철 호선별 역별 시간대별 승하차 인원 정보.csv'
    try:
        df = pd.read_csv(file_path, encoding='cp949')
    except:
        df = pd.read_csv(file_path, encoding='utf-8')
    
    # 강남역 데이터만 필터링 (2호선 기준)
    gangnam_df = df[(df['지하철역'] == '강남') & (df['호선명'] == '2호선')].iloc[0]
    return gangnam_df

try:
    data = load_data()
    
    st.title("🚉 강남역 실시간 동선 최적화 시뮬레이터")
    st.markdown("### 데이터 기반 출퇴근 시간대 우회로 및 가변 게이트 운영 제안")

    # 사이드바: 시간 설정
    st.sidebar.header("🕒 시뮬레이션 설정")
    selected_hour = st.sidebar.slider("분석 시간대 선택 (시)", 4, 23, 8)

    # 데이터 추출 로직
    col_on = f"{selected_hour:02d}시-{selected_hour+1:02d}시 승차인원"
    col_off = f"{selected_hour:02d}시-{selected_hour+1:02d}시 하차인원"
    
    val_on = data[col_on]
    val_off = data[col_off]

    # 메인 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 시간대", f"{selected_hour:02d}:00 ~ {selected_hour+1:02d}:00")
    col2.metric("승차 인원", f"{val_on:,} 명")
    col3.metric("하차 인원", f"{val_off:,} 명")

    st.divider()

    # 좌우 레이아웃: 시각화 및 제안 로직
    left_column, right_column = st.columns([2, 1])

    with left_column:
        st.subheader("📊 승하차 인원 비중 및 혼잡도")
        fig = go.Figure(data=[
            go.Bar(name='승차', x=[f"{selected_hour}시"], y=[val_on], marker_color='#1f77b4'),
            go.Bar(name='하차', x=[f"{selected_hour}시"], y=[val_off], marker_color='#ff7f0e')
        ])
        fig.update_layout(barmode='group', height=400)
        st.plotly_chart(fig, use_container_width=True)

    with right_column:
        st.subheader("💡 최적화 권고 사항")
        
        # 1. 출근 시간대 로직 (07시~09시)
        if 7 <= selected_hour <= 9:
            st.warning("⚠️ **출근 피크: 하차 집중 발생**")
            st.info("""
            **[우회로 운영 제안]**
            - 2, 8번 출구 방면 계단을 **'하차 전용'**으로 일시 전환
            - 승차 승객은 7, 11번 출구 우회 유도
            - 병목 지수: 고위험
            """)
            
        # 2. 퇴근 시간대 로직 (17시~19시)
        elif 17 <= selected_hour <= 19:
            st.error("🚨 **퇴근 피크: 승차 집중 발생**")
            st.success("""
            **[가변 게이트 운영 제안]**
            - 중앙 개찰구 5개소를 **'승차 전용'**으로 가변 운영
            - 승차 처리 용량 +40% 증대 예상
            - 플랫폼 밀집도 모니터링 강화
            """)
            
        else:
            st.write("✅ 현재 원활한 흐름을 유지하고 있습니다. 상시 모니터링 모드입니다.")

    # 하단: 전체 시간대 흐름 시각화
    st.subheader("📈 강남역 24시간 승하차 패턴")
    time_labels = [f"{i:02d}시" for i in range(4, 24)]
    all_on = [data[f"{i:02d}시-{i+1:02d}시 승차인원"] for i in range(4, 24)]
    all_off = [data[f"{i:02d}시-{i+1:02d}시 하차인원"] for i in range(4, 24)]
    
    trend_df = pd.DataFrame({
        '시간': time_labels,
        '승차': all_on,
        '하차': all_off
    })
    
    fig_trend = px.line(trend_df, x='시간', y=['승차', '하차'], 
                        title="일일 승하차 추이",
                        color_discrete_map={'승차': '#1f77b4', '하차': '#ff7f0e'})
    st.plotly_chart(fig_trend, use_container_width=True)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("CSV 파일이 'app.py'와 같은 폴더에 있는지, 파일명이 올바른지 확인해주세요.")
