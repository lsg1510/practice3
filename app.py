import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np
from datetime import datetime

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="강남역 스마트 내비게이션",
    page_icon="🚉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 전역 CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

/* ── 전체 배경/폰트 */
html, body, [class*="css"] {
    font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
}
.main .block-container {
    padding: 1.6rem 2.2rem 2rem;
    max-width: 1280px;
}

/* ── 사이드바 */
[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8 !important;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="stSidebar"] hr {
    border-color: #1e293b;
}

/* ── KPI 카드 */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 22px;
    text-align: left;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.kpi-label {
    color: #64748b;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.kpi-value {
    color: #0f172a;
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.1;
    font-family: 'JetBrains Mono', monospace;
}
.kpi-sub {
    color: #94a3b8;
    font-size: 0.75rem;
    margin-top: 4px;
}
.kpi-badge-green  { color: #16a34a; font-weight: 700; }
.kpi-badge-amber  { color: #d97706; font-weight: 700; }
.kpi-badge-red    { color: #dc2626; font-weight: 700; }

/* ── 섹션 헤더 */
.section-title {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #64748b;
    margin: 0 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #f1f5f9;
}

/* ── 출구 카드 */
.exit-card {
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.exit-card.recommended {
    background: #f0fdf4;
    border-color: #86efac;
}
.exit-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
}
.exit-card-place {
    font-size: 0.8rem;
    color: #475569;
    margin-bottom: 8px;
}
.exit-tag {
    display: inline-block;
    background: #e2e8f0;
    color: #475569;
    font-size: 0.7rem;
    font-weight: 600;
    border-radius: 5px;
    padding: 2px 7px;
    margin-right: 4px;
    margin-top: 2px;
}
.exit-tag.green {
    background: #dcfce7;
    color: #15803d;
}
.exit-tag.blue {
    background: #dbeafe;
    color: #1d4ed8;
}

/* ── 혼잡도 바 */
.congestion-bar-bg {
    background: #e2e8f0;
    border-radius: 99px;
    height: 8px;
    margin-top: 6px;
    overflow: hidden;
}
.congestion-bar-fill {
    height: 100%;
    border-radius: 99px;
    transition: width .4s ease;
}

/* ── 열차 도착 배너 */
.train-banner {
    background: #0f172a;
    border-radius: 12px;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 20px;
}
.train-direction {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.train-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.4rem;
    font-weight: 600;
    color: #34d399;
}
.train-separator { color: #334155; font-size: 1.6rem; }
.train-notice {
    flex: 1;
    background: #1e293b;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.8rem;
    color: #fbbf24;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── 시간표 테이블 */
.timetable-table th {
    background: #f1f5f9;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 10px 14px;
}
.timetable-table td {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #0f172a;
    padding: 8px 14px;
}

/* ── 탭 스타일 오버라이드 */
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    padding: 8px 18px;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #0f172a;
    border-bottom: 2px solid #0f172a;
}

/* ── 사이드바 타이틀 */
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 20px;
}
.sidebar-logo-icon {
    font-size: 1.8rem;
}
.sidebar-logo-text {
    font-size: 1rem;
    font-weight: 700;
    color: #f1f5f9 !important;
    line-height: 1.2;
}
.sidebar-logo-sub {
    font-size: 0.68rem;
    color: #64748b !important;
    font-weight: 400;
}

/* ── 정보 행 */
.info-row {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    align-items: flex-start;
}
.info-row-icon { color: #64748b; font-size: 0.9rem; flex-shrink: 0; margin-top: 1px; }
.info-row-label { font-size: 0.72rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
.info-row-value { font-size: 0.88rem; color: #1e293b; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ── 데이터 & 상수 ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    import glob, os
    candidates = glob.glob(os.path.join(os.path.dirname(__file__), "*.csv"))
    if not candidates:
        return None
    fp = candidates[0]
    try:
        df = pd.read_csv(fp, encoding="utf-8")
    except Exception:
        df = pd.read_csv(fp, encoding="cp949")
    rows = df[(df["지하철역"] == "강남") & (df["호선명"] == "2호선")]
    return rows.iloc[0] if not rows.empty else None


STATION_DB = {
    "general": {
        "주소": "서울특별시 강남구 강남대로 지하 396 (역삼동)",
        "전화번호": "02-6110-2221",
        "분실물센터": "02-6110-1122",
        "시설": "수유실(B1), 무인민원발급기(2·7번), 엘리베이터(1·4·5·8·9·11·12번)",
        "first_last": {
            "평일 (내선·잠실)":   ["05:30", "00:51"],
            "평일 (외선·신도림)": ["05:30", "00:48"],
            "휴일 (내선·잠실)":   ["05:30", "23:55"],
            "휴일 (외선·신도림)": ["05:30", "23:50"],
        },
        "headway": 4,
    },
    "exits": {
        "1번 출구":  {"장소": "특허청, 역삼세무서",      "door": "교대 1-1 / 역삼 10-4", "coord": [37.4981, 127.0286], "esc": True,  "bus": "광역 9404·9503"},
        "2번 출구":  {"장소": "테헤란로, 주민센터",      "door": "교대 2-3 / 역삼 9-2",  "coord": [37.4983, 127.0282], "esc": False, "bus": "간선 146·341"},
        "3번 출구":  {"장소": "강남역사거리, 역삼 방면", "door": "교대 2-4 / 역삼 9-1",  "coord": [37.4981, 127.0278], "esc": True,  "bus": "—"},
        "4번 출구":  {"장소": "뱅뱅사거리",              "door": "교대 2-4 / 역삼 9-1",  "coord": [37.4979, 127.0271], "esc": True,  "bus": "—"},
        "5번 출구":  {"장소": "서초동 우성아파트",        "door": "교대 5-2 / 역삼 6-3",  "coord": [37.4961, 127.0275], "esc": True,  "bus": "M버스 6427"},
        "6번 출구":  {"장소": "강남역사거리, 역삼 방면", "door": "교대 2-4 / 역삼 9-1",  "coord": [37.4981, 127.0276], "esc": True,  "bus": "—"},
        "7번 출구":  {"장소": "KDB산업은행",              "door": "교대 2-4 / 역삼 9-1",  "coord": [37.4982, 127.0274], "esc": True,  "bus": "—"},
        "8번 출구":  {"장소": "삼성전자 서초사옥",        "door": "교대 8-3 / 역삼 3-2",  "coord": [37.4979, 127.0262], "esc": True,  "bus": "순환 41"},
        "9번 출구":  {"장소": "메가박스, 서초동",         "door": "교대 9-2 / 역삼 2-3",  "coord": [37.4988, 127.0263], "esc": True,  "bus": "간선 740"},
        "10번 출구": {"장소": "교보타워, 강남대로",       "door": "교대 10-4 / 역삼 1-1", "coord": [37.4986, 127.0272], "esc": False, "bus": "심야 N13"},
        "11번 출구": {"장소": "강남역 사거리",            "door": "교대 10-4 / 역삼 1-1", "coord": [37.4989, 127.0275], "esc": True,  "bus": "직행 1100·2000"},
        "12번 출구": {"장소": "국립어린이청소년도서관",   "door": "교대 7-3 / 역삼 4-2",  "coord": [37.4991, 127.0281], "esc": True,  "bus": "간선 421"},
    },
    "notice": "⚠  2호선 외선순환 차량 고장으로 약 5분 지연 운행 중",
}

WEEKDAY_WEIGHTS = {
    "월요일": 1.05, "화요일": 1.00, "수요일": 1.00,
    "목요일": 1.02, "금요일": 1.15, "토요일": 1.25, "일요일": 0.90,
}


# ── 유틸 함수 ─────────────────────────────────────────────────────────────────
def safe_int(val) -> int:
    try:
        return int(str(val).replace(",", ""))
    except Exception:
        return 0


def next_train_minutes():
    now = datetime.now()
    hw = STATION_DB["general"]["headway"]
    inner = hw - (now.minute % hw)
    outer = hw - ((now.minute + 2) % hw)
    return inner if inner else hw, outer if outer else hw


def congestion_color(ratio: float) -> str:
    if ratio < 0.40:
        return "#22c55e"   # 초록
    elif ratio < 0.65:
        return "#f59e0b"   # 노랑
    else:
        return "#ef4444"   # 빨강


def congestion_label(ratio: float) -> str:
    if ratio < 0.40:
        return ("여유", "kpi-badge-green")
    elif ratio < 0.65:
        return ("보통", "kpi-badge-amber")
    else:
        return ("혼잡", "kpi-badge-red")


# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon">🚉</div>
        <div>
            <div class="sidebar-logo-text">강남역 내비게이션</div>
            <div class="sidebar-logo-sub">2호선 실시간 정보 시스템</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    weekdays = list(WEEKDAY_WEIGHTS.keys())
    today_idx = min(datetime.now().weekday(), 6)
    current_day = st.selectbox("요일", weekdays, index=today_idx)
    current_hour = st.slider("시간대", 4, 23, datetime.now().hour,
                             format="%d시")
    selected_exit = st.selectbox("목표 출구", list(STATION_DB["exits"].keys()))
    weather = st.radio("날씨", ["☀️ 맑음", "🌧️ 비 / 눈"])

    st.markdown("---")
    st.markdown(
        "<div style='font-size:.7rem;color:#475569;line-height:1.8'>"
        "데이터: 서울시 지하철 승하차 인원 정보<br>"
        f"업데이트: {datetime.now().strftime('%H:%M')} 기준"
        "</div>",
        unsafe_allow_html=True,
    )


# ── 메인 콘텐츠 ───────────────────────────────────────────────────────────────
data = load_data()
if data is None:
    st.error("CSV 파일을 찾을 수 없습니다. 앱과 같은 디렉터리에 CSV 파일을 위치시켜 주세요.")
    st.stop()

# 계산
day_weight = WEEKDAY_WEIGHTS[current_day]
weather_mult = 1.25 if "비" in weather else 1.0
col_off = f"{current_hour:02d}시-{current_hour + 1:02d}시 하차인원"
base_count = safe_int(data[col_off])
congestion_ratio = min((base_count / 150_000) * day_weight * weather_mult, 1.0)
exit_time = (4.0 + congestion_ratio * 12) * weather_mult
is_crowded = congestion_ratio > 0.65

# 우회 경로 계산
target_coords = np.array(STATION_DB["exits"][selected_exit]["coord"])
best_detour = selected_exit
detour_time = exit_time

if is_crowded:
    candidates = []
    for name, info in STATION_DB["exits"].items():
        if name == selected_exit:
            continue
        dist = np.linalg.norm(target_coords - np.array(info["coord"]))
        score = dist * (0.5 if ("비" in weather and info["esc"]) else 1.0)
        candidates.append((name, score))
    best_detour = sorted(candidates, key=lambda x: x[1])[0][0]
    detour_time = (4.0 + congestion_ratio * 0.5 * 12) * weather_mult + 1.0

time_saved = exit_time - detour_time
cong_label, cong_cls = congestion_label(congestion_ratio)
next_inner, next_outer = next_train_minutes()

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.5rem;font-weight:800;color:#0f172a;margin-bottom:4px;'>"
    "🚉 강남역 스마트 내비게이션"
    "</h1>"
    "<p style='color:#64748b;font-size:.85rem;margin-bottom:16px;'>"
    f"2호선 · {current_day} · {current_hour:02d}:00 기준 실시간 혼잡도 분석"
    "</p>",
    unsafe_allow_html=True,
)

# ── 열차 도착 배너 ────────────────────────────────────────────────────────────
inner_color = "#34d399" if next_inner > 2 else "#f87171"
outer_color = "#34d399" if next_outer > 2 else "#f87171"

st.markdown(f"""
<div class="train-banner">
    <div>
        <div class="train-direction" style="color:#94a3b8;">잠실 방면 (내선)</div>
        <div class="train-time" style="color:{inner_color};">{next_inner}분 후</div>
    </div>
    <div class="train-separator">|</div>
    <div>
        <div class="train-direction" style="color:#94a3b8;">신도림 방면 (외선)</div>
        <div class="train-time" style="color:{outer_color};">{next_outer}분 후</div>
    </div>
    <div class="train-notice">
        {STATION_DB['notice']}
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI 카드 행 ───────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

bar_color = congestion_color(congestion_ratio)
bar_pct = int(congestion_ratio * 100)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">현재 혼잡도</div>
        <div class="kpi-value {cong_cls}">{cong_label}</div>
        <div class="congestion-bar-bg">
            <div class="congestion-bar-fill" style="width:{bar_pct}%;background:{bar_color};"></div>
        </div>
        <div class="kpi-sub">{bar_pct}% · 하차 {base_count:,}명</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">선택 출구 소요 시간</div>
        <div class="kpi-value">{exit_time:.1f}<span style="font-size:.9rem;font-weight:500;color:#64748b;"> 분</span></div>
        <div class="kpi-sub">{selected_exit} → 지상</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    if is_crowded and best_detour != selected_exit:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">우회 경로 소요 시간</div>
            <div class="kpi-value">{detour_time:.1f}<span style="font-size:.9rem;font-weight:500;color:#64748b;"> 분</span></div>
            <div class="kpi-sub">{best_detour} 이용 시</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-label">우회 경로 소요 시간</div>
            <div class="kpi-value" style="color:#94a3b8;">—</div>
            <div class="kpi-sub">현재 경로가 최적입니다</div>
        </div>
        """, unsafe_allow_html=True)

with k4:
    if is_crowded and best_detour != selected_exit:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">단축 가능 시간</div>
            <div class="kpi-value kpi-badge-green">−{time_saved:.1f}<span style="font-size:.9rem;font-weight:500;"> 분</span></div>
            <div class="kpi-sub">우회 시 절약 가능</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">날씨 영향</div>
            <div class="kpi-value">{'+25%' if weather_mult > 1 else '—'}</div>
            <div class="kpi-sub">{'우천으로 혼잡 가중' if weather_mult > 1 else '날씨 영향 없음'}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 ───────────────────────────────────────────────────────────────────────
tab_nav, tab_info = st.tabs(["🗺  동선 최적화", "🏢  역 정보 & 시간표"])

# ════════════════════════════════════════════════════════════════════════════
with tab_nav:
    col_map, col_cards = st.columns([3, 2], gap="large")

    # 지도
    with col_map:
        st.markdown('<div class="section-title">출구 위치 지도</div>', unsafe_allow_html=True)

        center = [37.4979, 127.0276]
        m = folium.Map(
            location=center, zoom_start=17,
            tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
            attr="Google",
        )

        # 모든 출구 작은 마커
        for name, info in STATION_DB["exits"].items():
            if name in (selected_exit, best_detour if is_crowded else None):
                continue
            folium.CircleMarker(
                location=info["coord"],
                radius=5,
                color="#94a3b8",
                fill=True,
                fill_color="#94a3b8",
                fill_opacity=0.6,
                tooltip=name,
            ).add_to(m)

        # 선택 출구 (파랑)
        sel_coord = STATION_DB["exits"][selected_exit]["coord"]
        folium.PolyLine(
            [center, sel_coord], color="#3b82f6", weight=3, opacity=0.7, dash_array="6"
        ).add_to(m)
        folium.Marker(
            sel_coord,
            popup=f"선택: {selected_exit}",
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(m)

        # 우회 경로 (초록)
        if is_crowded and best_detour != selected_exit:
            det_coord = STATION_DB["exits"][best_detour]["coord"]
            folium.PolyLine(
                [center, det_coord], color="#22c55e", weight=5
            ).add_to(m)
            folium.Marker(
                det_coord,
                popup=f"추천: {best_detour}",
                icon=folium.Icon(color="green", icon="star"),
            ).add_to(m)

        # 역 중심
        folium.CircleMarker(
            location=center,
            radius=8,
            color="#0f172a",
            fill=True,
            fill_color="#0f172a",
            fill_opacity=1,
            tooltip="강남역",
        ).add_to(m)

        st_folium(m, width="100%", height=440, returned_objects=[])

    # 출구 카드
    with col_cards:
        st.markdown('<div class="section-title">출구 상세 정보</div>', unsafe_allow_html=True)

        # 선택 출구
        sel_info = STATION_DB["exits"][selected_exit]
        esc_tag = '<span class="exit-tag green">에스컬레이터</span>' if sel_info["esc"] else ""
        st.markdown(f"""
        <div class="exit-card">
            <div class="exit-card-title">📍 {selected_exit} <span style="font-size:.75rem;color:#64748b;font-weight:400;">선택</span></div>
            <div class="exit-card-place">{sel_info['장소']}</div>
            <div>
                <span class="exit-tag blue">하차문 {sel_info['door']}</span>
                <span class="exit-tag">{sel_info['bus']}</span>
                {esc_tag}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 우회 출구
        if is_crowded and best_detour != selected_exit:
            det_info = STATION_DB["exits"][best_detour]
            det_esc = '<span class="exit-tag green">에스컬레이터</span>' if det_info["esc"] else ""
            st.markdown(f"""
            <div class="exit-card recommended">
                <div class="exit-card-title">🚀 {best_detour}
                    <span style="font-size:.72rem;color:#16a34a;font-weight:700;margin-left:6px;">
                        추천 · {time_saved:.1f}분 단축
                    </span>
                </div>
                <div class="exit-card-place">{det_info['장소']}</div>
                <div>
                    <span class="exit-tag blue">하차문 {det_info['door']}</span>
                    <span class="exit-tag">{det_info['bus']}</span>
                    {det_esc}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="exit-card recommended">
                <div class="exit-card-title" style="color:#16a34a;">✅ 현재 선택 출구가 최적입니다</div>
                <div class="exit-card-place">별도 우회 경로가 필요하지 않습니다.</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">시간대별 혼잡도 추이</div>', unsafe_allow_html=True)

        # 미니 혼잡도 차트
        hours_range = list(range(5, 24))
        counts = []
        for h in hours_range:
            col = f"{h:02d}시-{h + 1:02d}시 하차인원"
            try:
                counts.append(safe_int(data[col]))
            except Exception:
                counts.append(0)
        
        chart_df = pd.DataFrame({
            "시간": [f"{h}시" for h in hours_range],
            "하차인원": counts,
        })
        
        st.bar_chart(chart_df.set_index("시간"), height=180, color="#3b82f6")


# ════════════════════════════════════════════════════════════════════════════
with tab_info:
    info_a, info_b = st.columns(2, gap="large")

    with info_a:
        st.markdown('<div class="section-title">역 기본 정보</div>', unsafe_allow_html=True)

        gen = STATION_DB["general"]
        for icon, label, val in [
            ("📍", "주소", gen["주소"]),
            ("📞", "대표 전화", gen["전화번호"]),
            ("📦", "분실물 센터", gen["분실물센터"]),
            ("🏗️", "편의 시설", gen["시설"]),
            ("🕐", "배차 간격", f"약 {gen['headway']}분"),
        ]:
            st.markdown(f"""
            <div class="info-row">
                <div class="info-row-icon">{icon}</div>
                <div>
                    <div class="info-row-label">{label}</div>
                    <div class="info-row-value">{val}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">첫차 · 막차</div>', unsafe_allow_html=True)

        timetable_df = pd.DataFrame(
            gen["first_last"],
            index=["첫차", "막차"],
        ).T.reset_index()
        timetable_df.columns = ["구분", "첫차", "막차"]
        st.dataframe(
            timetable_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "구분": st.column_config.TextColumn("운행 구분", width="large"),
                "첫차": st.column_config.TextColumn("첫차"),
                "막차": st.column_config.TextColumn("막차"),
            },
        )

    with info_b:
        st.markdown('<div class="section-title">출구 목록</div>', unsafe_allow_html=True)

        exit_rows = []
        for name, info in STATION_DB["exits"].items():
            exit_rows.append({
                "출구": name,
                "주요 장소": info["장소"],
                "연계 버스": info["bus"],
                "에스컬레이터": "✅" if info["esc"] else "—",
            })

        exit_df = pd.DataFrame(exit_rows)
        st.dataframe(
            exit_df,
            use_container_width=True,
            hide_index=True,
            height=460,
            column_config={
                "출구": st.column_config.TextColumn("출구", width="small"),
                "주요 장소": st.column_config.TextColumn("주요 장소", width="large"),
                "연계 버스": st.column_config.TextColumn("연계 버스"),
                "에스컬레이터": st.column_config.TextColumn("에스컬", width="small"),
            },
        )
