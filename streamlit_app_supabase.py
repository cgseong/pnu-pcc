import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from supabase import create_client, Client

# Supabase 클라이언트 초기화
@st.cache_resource
def init_supabase():
    """Supabase 클라이언트 초기화"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# 페이지 설정
st.set_page_config(
    page_title="닥치고 코딩",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# 로그인 함수
def login():
    st.sidebar.markdown("### 🔐 관리자 로그인")
    username = st.sidebar.text_input("아이디")
    password = st.sidebar.text_input("비밀번호", type="password")

    if st.sidebar.button("로그인"):
        # secrets에서 관리자 정보 가져오기
        if (username == st.secrets["admin"]["username"] and
            password == st.secrets["admin"]["password"]):
            st.session_state.authenticated = True
            st.session_state.is_admin = True
            st.sidebar.success("관리자로 로그인되었습니다.")
            st.rerun()
        else:
            st.sidebar.error("아이디 또는 비밀번호가 올바르지 않습니다.")

# 로그아웃 함수
def logout():
    if st.sidebar.button("로그아웃"):
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.rerun()

# 스타일 설정
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 0.25rem solid #1f77b4;
        margin: 0.5rem 0;
    }
    .filter-section {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Supabase에서 데이터 로딩
@st.cache_data(ttl=600)  # 10분 캐시
def load_data_from_supabase():
    """Supabase에서 데이터 로드 및 전처리"""
    try:
        supabase = init_supabase()

        # 모든 데이터 가져오기
        response = supabase.table('pcc_result').select("*").execute()

        # DataFrame으로 변환
        df = pd.DataFrame(response.data)

        if df.empty:
            st.error("데이터베이스에 데이터가 없습니다.")
            return None

        # 컬럼명 통일 (등급 → 등급(Lv.))
        if '등급' in df.columns:
            df['등급(Lv.)'] = df['등급']

        # 데이터 전처리
        if '합격여부' in df.columns:
            df['합격여부_binary'] = df['합격여부'].map({'합격': 1, '불합격': 0})

        if '학년' in df.columns:
            df['학년'] = df['학년'].astype(str)

        if '회차' in df.columns:
            df['회차'] = df['회차'].astype(int)

        if '총점' in df.columns:
            df['총점'] = pd.to_numeric(df['총점'], errors='coerce')

        # 등급 컬럼이 없으면 생성, 있으면 결측치 처리
        if '등급(Lv.)' not in df.columns:
            df['등급(Lv.)'] = '없음'
        else:
            df['등급(Lv.)'] = df['등급(Lv.)'].fillna('없음')

        return df
    except Exception as e:
        st.error(f"데이터 로딩 중 오류가 발생했습니다: {e}")
        return None

# 데이터 삽입 함수 (관리자용)
def insert_pcc_result(supabase: Client, data: dict):
    """새로운 PCC 결과 삽입"""
    try:
        response = supabase.table('pcc_result').insert(data).execute()
        return True, "데이터가 성공적으로 추가되었습니다."
    except Exception as e:
        return False, f"데이터 추가 중 오류 발생: {e}"

# 데이터 업데이트 함수 (관리자용)
def update_pcc_result(supabase: Client, record_id: int, data: dict):
    """PCC 결과 업데이트"""
    try:
        response = supabase.table('pcc_result').update(data).eq('id', record_id).execute()
        return True, "데이터가 성공적으로 수정되었습니다."
    except Exception as e:
        return False, f"데이터 수정 중 오류 발생: {e}"

# 데이터 삭제 함수 (관리자용)
def delete_pcc_result(supabase: Client, record_id: int):
    """PCC 결과 삭제"""
    try:
        response = supabase.table('pcc_result').delete().eq('id', record_id).execute()
        return True, "데이터가 성공적으로 삭제되었습니다."
    except Exception as e:
        return False, f"데이터 삭제 중 오류 발생: {e}"

# 메인 애플리케이션
def main():
    st.markdown('<h1 class="main-header">🏆 부산대학교 PCC 응시현황</h1>', unsafe_allow_html=True)

    # 데이터 로딩
    df = load_data_from_supabase()
    if df is None:
        return

    # 사이드바 - 데이터 필터링 메뉴
    st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.sidebar.header("🔍 데이터 필터링")

    # 학과 선택 (다중선택)
    departments = st.sidebar.multiselect(
        "학과 선택",
        options=sorted(df['학과'].unique()),
        default=sorted(df['학과'].unique()),
        help="분석할 학과를 선택하세요"
    )

    # 학년 선택
    grades = st.sidebar.multiselect(
        "학년 선택",
        options=sorted(df['학년'].unique()),
        default=sorted(df['학년'].unique()),
        help="분석할 학년을 선택하세요"
    )

    # 합격 여부 선택
    pass_status = st.sidebar.multiselect(
        "합격 여부 선택",
        options=['합격', '불합격'],
        default=['합격', '불합격'],
        help="분석할 합격 여부를 선택하세요"
    )

    # 등급 선택
    levels = st.sidebar.multiselect(
        "등급 선택",
        options=sorted(df['등급(Lv.)'].unique()),
        default=sorted(df['등급(Lv.)'].unique()),
        help="분석할 등급을 선택하세요"
    )

    # 시험과목 선택
    subjects = st.sidebar.multiselect(
        "시험과목 선택",
        options=sorted(df['시험과목'].unique()),
        default=sorted(df['시험과목'].unique()),
        help="분석할 시험과목을 선택하세요"
    )

    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # 데이터 새로고침 버튼
    if st.sidebar.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

    # 관리자 로그인 섹션
    login()
    if st.session_state.is_admin:
        logout()

    # 데이터 필터링 적용
    filtered_df = df[
        (df['학과'].isin(departments)) &
        (df['학년'].isin(grades)) &
        (df['합격여부'].isin(pass_status)) &
        (df['등급(Lv.)'].isin(levels)) &
        (df['시험과목'].isin(subjects))
    ]

    if filtered_df.empty:
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
        return

    # 탭 생성
    if st.session_state.is_admin:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "📊 전체 정보",
            "📈 정보컴퓨터공학부 회차별 응시자 현황",
            "🎓 정보컴퓨터공학부 학년별 통계",
            "📚 PCCP 레벨 정보",
            "👨‍🎓 학생별 성과 분석",
            "📋 상세 데이터",
            "📈 성장 추이 분석",
            "🔄 정보컴퓨터공학부 3회차-5회차 비교 분석",
            "➕ 데이터 관리"  # 새로운 탭
        ])
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 전체 정보",
            "📈 정보컴퓨터공학부 회차별 응시자 현황",
            "🎓 정보컴퓨터공학부 학년별 통계",
            "📚 PCCP 레벨 정보"
        ])

    # 탭 1: 전체 정보
    with tab1:
        st.header("📊 전체 응시 정보")

        # 주요 지표
        col1, col2, col3, col4 = st.columns(4)

        total_applicants = len(filtered_df)
        total_passed = len(filtered_df[filtered_df['합격여부'] == '합격'])
        total_pass_rate = (total_passed / total_applicants * 100) if total_applicants > 0 else 0
        avg_score = filtered_df['총점'].mean()

        with col1:
            st.metric(
                label="전체 응시자수",
                value=f"{total_applicants:,}명"
            )

        with col2:
            st.metric(
                label="전체 합격률",
                value=f"{total_pass_rate:.1f}%"
            )

        with col3:
            st.metric(
                label="전체 평균점수",
                value=f"{avg_score:.1f}점"
            )

        with col4:
            st.metric(
                label="합격자수",
                value=f"{total_passed:,}명"
            )

        st.markdown("---")

        # 상세 통계
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 학과별 통계")
            dept_stats = filtered_df.groupby('학과').agg({
                '이름': 'count',
                '합격여부_binary': ['sum', 'mean'],
                '총점': 'mean'
            }).round(2)
            dept_stats.columns = ['응시자수', '합격자수', '합격률', '평균점수']
            dept_stats['합격률'] = (dept_stats['합격률'] * 100).round(1).astype(str) + '%'
            dept_stats = dept_stats.sort_values('응시자수', ascending=False)
            st.dataframe(dept_stats, use_container_width=True)

        with col2:
            st.subheader("📊 시험과목별 통계")
            subject_stats = filtered_df.groupby('시험과목').agg({
                '이름': 'count',
                '합격여부_binary': ['sum', 'mean'],
                '총점': 'mean'
            }).round(2)
            subject_stats.columns = ['응시자수', '합격자수', '합격률', '평균점수']
            subject_stats['합격률'] = (subject_stats['합격률'] * 100).round(1).astype(str) + '%'
            st.dataframe(subject_stats, use_container_width=True)

    # 탭 2: 정보컴퓨터공학부 회차별 응시자 현황
    with tab2:
        st.header("📈 정보컴퓨터공학부 회차별 응시자 현황")

        # 정보컴퓨터공학부/전기컴퓨터공학부 데이터만 필터링
        cse_df = filtered_df[
            (filtered_df['학과'] == '정보컴퓨터공학부') |
            (filtered_df['학과'] == '전기컴퓨터공학부 정보컴퓨터공학전공') |
            (filtered_df['학과'] == '전기컴퓨터공학부')
        ]

        if cse_df.empty:
            st.warning("정보컴퓨터공학부/전기컴퓨터공학부 데이터가 없습니다.")
        else:
            # 회차별 통계 계산
            round_stats = cse_df.groupby('회차').agg({
                '이름': 'count',
                '합격여부_binary': 'sum',
                '총점': 'mean'
            }).reset_index()
            round_stats.columns = ['회차', '총_응시자수', '합격자수', '평균점수']
            round_stats['불합격자수'] = round_stats['총_응시자수'] - round_stats['합격자수']
            round_stats['합격률'] = (round_stats['합격자수'] / round_stats['총_응시자수'] * 100).round(1)

            # 직전 회차 대비 변화 카드
            st.subheader("📌 직전 회차 대비 변화")
            round_stats_sorted = round_stats.sort_values('회차')

            if len(round_stats_sorted) >= 2:
                latest = round_stats_sorted.iloc[-1]
                previous = round_stats_sorted.iloc[-2]

                delta_applicants = int(latest['총_응시자수'] - previous['총_응시자수'])
                delta_pass_rate = latest['합격률'] - previous['합격률']
                delta_avg_score = latest['평균점수'] - previous['평균점수']
                delta_passed = int(latest['합격자수'] - previous['합격자수'])

                st.caption(f"**{int(previous['회차'])}회차 → {int(latest['회차'])}회차** 변화")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        label=f"{int(latest['회차'])}회차 응시자수",
                        value=f"{int(latest['총_응시자수'])}명",
                        delta=f"{delta_applicants:+d}명"
                    )
                with col2:
                    st.metric(
                        label=f"{int(latest['회차'])}회차 합격률",
                        value=f"{latest['합격률']:.1f}%",
                        delta=f"{delta_pass_rate:+.1f}%p"
                    )
                with col3:
                    st.metric(
                        label=f"{int(latest['회차'])}회차 평균점수",
                        value=f"{latest['평균점수']:.1f}점",
                        delta=f"{delta_avg_score:+.1f}점"
                    )
                with col4:
                    st.metric(
                        label=f"{int(latest['회차'])}회차 합격자수",
                        value=f"{int(latest['합격자수'])}명",
                        delta=f"{delta_passed:+d}명"
                    )

                st.markdown("---")
            else:
                st.info("비교할 수 있는 직전 회차 데이터가 없습니다.")

            # Lv.별 인원수 통계 계산
            level_stats = cse_df.groupby(['회차', '등급(Lv.)']).size().reset_index(name='인원수')
            level_pivot = level_stats.pivot(index='회차', columns='등급(Lv.)', values='인원수').fillna(0)

            # 그래프 생성
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('회차별 응시자수', '회차별 합격률', '회차별 합격/불합격', '회차별 평균점수'),
                specs=[[{"type": "scatter"}, {"type": "scatter"}],
                       [{"type": "bar"}, {"type": "scatter"}]]
            )

            # 응시자수 추이
            fig.add_trace(
                go.Scatter(x=round_stats['회차'], y=round_stats['총_응시자수'],
                          mode='lines+markers+text', name='응시자수',
                          line=dict(color='blue', width=3),
                          text=round_stats['총_응시자수'],
                          textposition='top center'),
                row=1, col=1
            )

            # 합격률 추이
            fig.add_trace(
                go.Scatter(x=round_stats['회차'], y=round_stats['합격률'],
                          mode='lines+markers+text', name='합격률(%)',
                          line=dict(color='green', width=3),
                          text=[f"{x:.1f}%" for x in round_stats['합격률']],
                          textposition='top center'),
                row=1, col=2
            )

            # 합격/불합격 현황
            fig.add_trace(
                go.Bar(x=round_stats['회차'], y=round_stats['합격자수'],
                      name='합격자수', marker_color='lightgreen',
                      text=round_stats['합격자수'],
                      textposition='inside'),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(x=round_stats['회차'], y=round_stats['불합격자수'],
                      name='불합격자수', marker_color='lightcoral',
                      text=round_stats['불합격자수'],
                      textposition='inside'),
                row=2, col=1
            )

            # 평균점수 추이
            fig.add_trace(
                go.Scatter(x=round_stats['회차'], y=round_stats['평균점수'],
                          mode='lines+markers+text', name='평균점수',
                          line=dict(color='orange', width=3),
                          text=[f"{x:.1f}" for x in round_stats['평균점수']],
                          textposition='top center'),
                row=2, col=2
            )

            fig.update_layout(
                height=800,
                showlegend=True,
                title_text="정보컴퓨터공학부 회차별 종합 현황",
                xaxis=dict(dtick=1),
                xaxis2=dict(dtick=1),
                xaxis3=dict(dtick=1),
                xaxis4=dict(dtick=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            # 상세 통계 테이블
            st.subheader("📋 회차별 상세 통계")
            round_stats_sorted = round_stats.sort_values('회차', ascending=False)
            st.dataframe(round_stats_sorted, use_container_width=True, hide_index=True)

            # Lv.별 상세 통계
            st.subheader("📊 회차별 Lv. 상세 통계")
            level_pivot_sorted = level_pivot.sort_index(ascending=False)
            st.dataframe(level_pivot_sorted, use_container_width=True)

            # 회차별 점수 분포 Box Plot
            st.subheader("📦 회차별 점수 분포 (Box Plot)")
            st.caption("중앙값, 사분위수, 이상치를 통해 각 회차의 난이도와 점수 집중도를 파악할 수 있습니다.")

            fig_box = go.Figure()

            for round_num in sorted(cse_df['회차'].unique()):
                round_data = cse_df[cse_df['회차'] == round_num]['총점']
                fig_box.add_trace(go.Box(
                    y=round_data,
                    name=f'{round_num}회차',
                    boxmean='sd',  # 평균과 표준편차도 표시
                    marker_color=px.colors.qualitative.Set2[int(round_num) % len(px.colors.qualitative.Set2)],
                    boxpoints='outliers',  # 이상치만 표시
                    jitter=0.3,
                    pointpos=-1.8
                ))

            fig_box.update_layout(
                title_text="회차별 점수 분포",
                yaxis_title="총점",
                xaxis_title="회차",
                height=500,
                showlegend=False,
                yaxis=dict(zeroline=False)
            )

            # 합격선 표시 (400점)
            fig_box.add_hline(
                y=400, line_dash="dash", line_color="red",
                annotation_text="합격선 (400점)",
                annotation_position="top left"
            )

            st.plotly_chart(fig_box, use_container_width=True)

            # 회차별 분포 요약 통계
            st.markdown("**📋 회차별 분포 요약**")
            box_stats = cse_df.groupby('회차')['총점'].describe().round(1)
            box_stats.columns = ['응시자수', '평균', '표준편차', '최솟값', '25%', '중앙값(50%)', '75%', '최댓값']
            box_stats['IQR'] = box_stats['75%'] - box_stats['25%']
            box_stats['변동계수(%)'] = ((box_stats['표준편차'] / box_stats['평균']) * 100).round(1)
            st.dataframe(box_stats, use_container_width=True)

            # 난이도 인사이트 자동 생성
            hardest_round = box_stats['평균'].idxmin()
            easiest_round = box_stats['평균'].idxmax()
            most_spread = box_stats['IQR'].idxmax()

            st.info(f"""
            💡 **인사이트 요약**
            - 🔴 **가장 어려웠던 회차**: {hardest_round}회차 (평균 {box_stats.loc[hardest_round, '평균']}점)
            - 🟢 **가장 쉬웠던 회차**: {easiest_round}회차 (평균 {box_stats.loc[easiest_round, '평균']}점)
            - 📊 **점수 편차가 가장 큰 회차**: {most_spread}회차 (IQR: {box_stats.loc[most_spread, 'IQR']}점) — 학생 간 실력 차이가 가장 큼
            """)

            # 회차별 학년 구성 비율 (Stacked Bar)
            st.subheader("🎓 회차별 학년 구성 비율")
            st.caption("각 회차에 1~4학년이 어떤 비율로 참여했는지 확인하여 저학년 참여도 증가 트렌드 및 홍보 효과를 파악할 수 있습니다.")

            # 회차-학년별 인원수 집계
            grade_composition = cse_df.groupby(['회차', '학년']).size().reset_index(name='인원수')
            grade_composition_pivot = grade_composition.pivot(index='회차', columns='학년', values='인원수').fillna(0)

            # 비율 계산
            grade_composition_pct = grade_composition_pivot.div(grade_composition_pivot.sum(axis=1), axis=0) * 100

            # Stacked Bar (비율)
            fig_stacked = go.Figure()

            grade_colors = {'1': '#FF6B6B', '2': '#FFA94D', '3': '#51CF66', '4': '#339AF0'}

            for grade in sorted(grade_composition_pct.columns):
                fig_stacked.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in grade_composition_pct.index],
                    y=grade_composition_pct[grade],
                    name=f'{grade}학년',
                    marker_color=grade_colors.get(str(grade), '#868E96'),
                    text=[f'{v:.1f}%' for v in grade_composition_pct[grade]],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

            fig_stacked.update_layout(
                title_text="회차별 학년 구성 비율 (%)",
                xaxis_title="회차",
                yaxis_title="비율 (%)",
                barmode='stack',
                height=450,
                showlegend=True,
                yaxis=dict(range=[0, 100]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )

            st.plotly_chart(fig_stacked, use_container_width=True)

            # Stacked Bar (실제 인원수)
            fig_stacked_count = go.Figure()

            for grade in sorted(grade_composition_pivot.columns):
                fig_stacked_count.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in grade_composition_pivot.index],
                    y=grade_composition_pivot[grade],
                    name=f'{grade}학년',
                    marker_color=grade_colors.get(str(grade), '#868E96'),
                    text=[f'{int(v)}명' for v in grade_composition_pivot[grade]],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

            fig_stacked_count.update_layout(
                title_text="회차별 학년 구성 (인원수)",
                xaxis_title="회차",
                yaxis_title="인원수",
                barmode='stack',
                height=450,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )

            st.plotly_chart(fig_stacked_count, use_container_width=True)

            # 저학년(1~2학년) 참여도 추이 분석
            st.markdown("**📈 저학년(1~2학년) 참여도 추이**")

            lower_grades = [col for col in grade_composition_pivot.columns if str(col) in ['1', '2']]
            if lower_grades:
                lower_grade_count = grade_composition_pivot[lower_grades].sum(axis=1)
                total_count = grade_composition_pivot.sum(axis=1)
                lower_grade_pct = (lower_grade_count / total_count * 100).round(1)

                fig_lower = go.Figure()

                fig_lower.add_trace(go.Scatter(
                    x=[f'{int(r)}회차' for r in lower_grade_pct.index],
                    y=lower_grade_pct.values,
                    mode='lines+markers+text',
                    name='저학년 비율',
                    line=dict(color='#FF6B6B', width=3),
                    marker=dict(size=10),
                    text=[f'{v:.1f}%' for v in lower_grade_pct.values],
                    textposition='top center'
                ))

                fig_lower.update_layout(
                    title_text="저학년(1~2학년) 참여 비율 추이",
                    xaxis_title="회차",
                    yaxis_title="저학년 비율 (%)",
                    height=350,
                    showlegend=False,
                    yaxis=dict(range=[0, max(lower_grade_pct.values) * 1.3])
                )

                st.plotly_chart(fig_lower, use_container_width=True)

                # 저학년 참여도 인사이트
                first_round_pct = lower_grade_pct.iloc[0]
                last_round_pct = lower_grade_pct.iloc[-1]
                pct_change = last_round_pct - first_round_pct

                if pct_change > 0:
                    st.success(f"✅ 저학년 참여 비율이 {first_round_pct:.1f}% → {last_round_pct:.1f}%로 **{pct_change:+.1f}%p 증가**했습니다. 홍보 효과가 나타나고 있습니다!")
                elif pct_change < 0:
                    st.warning(f"⚠️ 저학년 참여 비율이 {first_round_pct:.1f}% → {last_round_pct:.1f}%로 **{pct_change:+.1f}%p 감소**했습니다. 저학년 대상 홍보 강화가 필요합니다.")
                else:
                    st.info(f"ℹ️ 저학년 참여 비율이 {last_round_pct:.1f}%로 유지되고 있습니다.")

            # 상세 테이블
            st.markdown("**📋 회차별 학년 구성 상세**")
            display_composition = grade_composition_pivot.copy()
            display_composition['합계'] = display_composition.sum(axis=1)
            for col in grade_composition_pivot.columns:
                display_composition[f'{col}학년(%)'] = (grade_composition_pct[col]).round(1).astype(str) + '%'
            st.dataframe(display_composition, use_container_width=True)

            # 회차별 신규 응시자 vs 재응시자 비율
            st.subheader("🔄 회차별 신규 응시자 vs 재응시자 비율")
            st.caption("처음 시험을 보는 학생과 재도전 학생의 비율 변화를 통해 '도전 문화' 형성 여부와 재시도 동기를 파악할 수 있습니다.")

            # 회차별 신규/재응시자 분류
            sorted_rounds = sorted(cse_df['회차'].unique())
            new_vs_retake_data = []

            # 각 회차별로 해당 회차 이전에 응시한 적 있는지 판별
            for round_num in sorted_rounds:
                current_round_students = cse_df[cse_df['회차'] == round_num][['이름', '학번']].drop_duplicates()
                previous_rounds_students = cse_df[cse_df['회차'] < round_num][['이름', '학번']].drop_duplicates()

                if previous_rounds_students.empty:
                    # 첫 회차는 모두 신규
                    new_count = len(current_round_students)
                    retake_count = 0
                else:
                    # 이전 회차에 응시한 적 있는 학생 = 재응시자
                    merged = current_round_students.merge(
                        previous_rounds_students, on=['이름', '학번'], how='left', indicator=True
                    )
                    retake_count = len(merged[merged['_merge'] == 'both'])
                    new_count = len(merged[merged['_merge'] == 'left_only'])

                total = new_count + retake_count
                new_vs_retake_data.append({
                    '회차': round_num,
                    '신규응시자': new_count,
                    '재응시자': retake_count,
                    '전체': total,
                    '신규비율': (new_count / total * 100) if total > 0 else 0,
                    '재응시비율': (retake_count / total * 100) if total > 0 else 0
                })

            new_retake_df = pd.DataFrame(new_vs_retake_data)

            # Stacked Bar (비율)
            col1, col2 = st.columns(2)

            with col1:
                fig_nr_pct = go.Figure()

                fig_nr_pct.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in new_retake_df['회차']],
                    y=new_retake_df['신규비율'],
                    name='신규 응시자',
                    marker_color='#4ECDC4',
                    text=[f'{v:.1f}%' for v in new_retake_df['신규비율']],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

                fig_nr_pct.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in new_retake_df['회차']],
                    y=new_retake_df['재응시비율'],
                    name='재응시자',
                    marker_color='#FF6B6B',
                    text=[f'{v:.1f}%' for v in new_retake_df['재응시비율']],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

                fig_nr_pct.update_layout(
                    title_text="회차별 신규/재응시자 비율 (%)",
                    xaxis_title="회차",
                    yaxis_title="비율 (%)",
                    barmode='stack',
                    height=400,
                    showlegend=True,
                    yaxis=dict(range=[0, 100]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )

                st.plotly_chart(fig_nr_pct, use_container_width=True)

            with col2:
                # Stacked Bar (인원수)
                fig_nr_count = go.Figure()

                fig_nr_count.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in new_retake_df['회차']],
                    y=new_retake_df['신규응시자'],
                    name='신규 응시자',
                    marker_color='#4ECDC4',
                    text=[f'{int(v)}명' for v in new_retake_df['신규응시자']],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

                fig_nr_count.add_trace(go.Bar(
                    x=[f'{int(r)}회차' for r in new_retake_df['회차']],
                    y=new_retake_df['재응시자'],
                    name='재응시자',
                    marker_color='#FF6B6B',
                    text=[f'{int(v)}명' for v in new_retake_df['재응시자']],
                    textposition='inside',
                    insidetextanchor='middle'
                ))

                fig_nr_count.update_layout(
                    title_text="회차별 신규/재응시자 인원수",
                    xaxis_title="회차",
                    yaxis_title="인원수",
                    barmode='stack',
                    height=400,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )

                st.plotly_chart(fig_nr_count, use_container_width=True)

            # 재응시자 비율 추이 라인차트
            fig_retake_trend = go.Figure()

            fig_retake_trend.add_trace(go.Scatter(
                x=[f'{int(r)}회차' for r in new_retake_df['회차']],
                y=new_retake_df['재응시비율'],
                mode='lines+markers+text',
                name='재응시자 비율',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=10),
                text=[f'{v:.1f}%' for v in new_retake_df['재응시비율']],
                textposition='top center'
            ))

            fig_retake_trend.update_layout(
                title_text="재응시자 비율 추이 — 도전 문화 형성 지표",
                xaxis_title="회차",
                yaxis_title="재응시자 비율 (%)",
                height=350,
                showlegend=False,
                yaxis=dict(range=[0, max(new_retake_df['재응시비율'].max() * 1.3, 10)])
            )

            st.plotly_chart(fig_retake_trend, use_container_width=True)

            # 도전 문화 인사이트
            if len(new_retake_df) >= 2:
                first_retake_pct = new_retake_df.iloc[1]['재응시비율']  # 2회차부터 의미있음
                last_retake_pct = new_retake_df.iloc[-1]['재응시비율']
                retake_trend = last_retake_pct - first_retake_pct

                max_retake_round = new_retake_df.loc[new_retake_df['재응시비율'].idxmax()]
                total_retakers = new_retake_df['재응시자'].sum()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "최근 회차 재응시자 비율",
                        f"{last_retake_pct:.1f}%",
                        delta=f"{retake_trend:+.1f}%p (vs 2회차)"
                    )
                with col2:
                    st.metric(
                        "재응시자 가장 많은 회차",
                        f"{int(max_retake_round['회차'])}회차",
                        delta=f"{int(max_retake_round['재응시자'])}명"
                    )
                with col3:
                    st.metric(
                        "누적 재응시 건수",
                        f"{total_retakers}건"
                    )

                if retake_trend > 5:
                    st.success(f"🔥 재응시자 비율이 {first_retake_pct:.1f}% → {last_retake_pct:.1f}%로 증가! **도전 문화가 활발히 형성**되고 있습니다.")
                elif retake_trend > 0:
                    st.info(f"📈 재응시자 비율이 소폭 증가({retake_trend:+.1f}%p)하고 있습니다. 재도전 동기가 형성되고 있는 긍정적 신호입니다.")
                elif retake_trend == 0:
                    st.info("ℹ️ 재응시자 비율이 안정적으로 유지되고 있습니다.")
                else:
                    st.warning(f"⚠️ 재응시자 비율이 감소({retake_trend:+.1f}%p)하고 있습니다. 재도전 독려 방안이 필요할 수 있습니다.")

            # 상세 테이블
            st.markdown("**📋 회차별 신규/재응시자 상세**")
            display_nr = new_retake_df.copy()
            display_nr['신규비율'] = display_nr['신규비율'].round(1).astype(str) + '%'
            display_nr['재응시비율'] = display_nr['재응시비율'].round(1).astype(str) + '%'
            display_nr.columns = ['회차', '신규 응시자(명)', '재응시자(명)', '전체(명)', '신규 비율', '재응시 비율']
            st.dataframe(display_nr, use_container_width=True, hide_index=True)

    # 탭 3: 정보컴퓨터공학부 학년별 통계
    with tab3:
        st.header("🎓 정보컴퓨터공학부 학년별 통계")

        cse_df = filtered_df[
            (filtered_df['학과'] == '정보컴퓨터공학부') |
            (filtered_df['학과'] == '전기컴퓨터공학부 정보컴퓨터공학전공') |
            (filtered_df['학과'] == '전기컴퓨터공학부')
        ]

        if cse_df.empty:
            st.warning("정보컴퓨터공학부/전기컴퓨터공학부 데이터가 없습니다.")
        else:
            # 회차별 학년별 통계 계산
            grade_round_stats = cse_df.groupby(['회차', '학년']).agg({
                '이름': 'count',
                '합격여부_binary': ['sum', 'mean'],
                '총점': 'mean'
            }).reset_index()

            grade_round_stats.columns = ['회차', '학년', '응시자수', '합격자수', '합격률', '평균점수']
            grade_round_stats['합격률'] = (grade_round_stats['합격률'] * 100).round(1)
            grade_round_stats['평균점수'] = grade_round_stats['평균점수'].round(1)

            grade_colors = {'1': '#FF6B6B', '2': '#FFA94D', '3': '#51CF66', '4': '#339AF0'}

            # ===== 1. 응시자수 + 합격자수 (Grouped Bar) =====
            st.subheader("📊 회차별 학년별 응시자수 & 합격자수")

            col1, col2 = st.columns(2)

            with col1:
                fig_applicants = go.Figure()
                for grade in sorted(grade_round_stats['학년'].unique()):
                    grade_data = grade_round_stats[grade_round_stats['학년'] == grade]
                    fig_applicants.add_trace(go.Bar(
                        x=grade_data['회차'],
                        y=grade_data['응시자수'],
                        name=f'{grade}학년',
                        marker_color=grade_colors.get(str(grade), '#868E96'),
                        text=grade_data['응시자수'].astype(int),
                        textposition='outside'
                    ))

                fig_applicants.update_layout(
                    title_text="회차별 학년별 응시자수",
                    xaxis_title="회차",
                    yaxis_title="응시자수 (명)",
                    barmode='group',
                    height=400,
                    showlegend=True,
                    xaxis=dict(dtick=1),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_applicants, use_container_width=True)

            with col2:
                fig_passed = go.Figure()
                for grade in sorted(grade_round_stats['학년'].unique()):
                    grade_data = grade_round_stats[grade_round_stats['학년'] == grade]
                    fig_passed.add_trace(go.Bar(
                        x=grade_data['회차'],
                        y=grade_data['합격자수'],
                        name=f'{grade}학년',
                        marker_color=grade_colors.get(str(grade), '#868E96'),
                        text=grade_data['합격자수'].astype(int),
                        textposition='outside'
                    ))

                fig_passed.update_layout(
                    title_text="회차별 학년별 합격자수",
                    xaxis_title="회차",
                    yaxis_title="합격자수 (명)",
                    barmode='group',
                    height=400,
                    showlegend=True,
                    xaxis=dict(dtick=1),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_passed, use_container_width=True)

            # ===== 2. 합격률 추이 (라인차트) =====
            st.subheader("📈 회차별 학년별 합격률 추이")

            fig_pass_rate = go.Figure()
            for grade in sorted(grade_round_stats['학년'].unique()):
                grade_data = grade_round_stats[grade_round_stats['학년'] == grade]
                fig_pass_rate.add_trace(go.Scatter(
                    x=grade_data['회차'],
                    y=grade_data['합격률'],
                    mode='lines+markers+text',
                    name=f'{grade}학년',
                    line=dict(color=grade_colors.get(str(grade), '#868E96'), width=3),
                    marker=dict(size=9),
                    text=[f'{v:.1f}%' for v in grade_data['합격률']],
                    textposition='top center'
                ))

            fig_pass_rate.update_layout(
                title_text="학년별 합격률 추이",
                xaxis_title="회차",
                yaxis_title="합격률 (%)",
                height=420,
                showlegend=True,
                xaxis=dict(dtick=1),
                yaxis=dict(range=[0, 105]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )

            # 전체 평균 합격률 참고선
            overall_pass_rate = (cse_df['합격여부_binary'].mean() * 100)
            fig_pass_rate.add_hline(
                y=overall_pass_rate, line_dash="dot", line_color="gray",
                annotation_text=f"전체 평균 {overall_pass_rate:.1f}%",
                annotation_position="bottom right"
            )

            st.plotly_chart(fig_pass_rate, use_container_width=True)

            # ===== 3. 평균점수 추이 (라인차트) =====
            st.subheader("📈 회차별 학년별 평균점수 추이")

            fig_avg_score = go.Figure()
            for grade in sorted(grade_round_stats['학년'].unique()):
                grade_data = grade_round_stats[grade_round_stats['학년'] == grade]
                fig_avg_score.add_trace(go.Scatter(
                    x=grade_data['회차'],
                    y=grade_data['평균점수'],
                    mode='lines+markers+text',
                    name=f'{grade}학년',
                    line=dict(color=grade_colors.get(str(grade), '#868E96'), width=3),
                    marker=dict(size=9),
                    text=[f'{v:.0f}' for v in grade_data['평균점수']],
                    textposition='top center'
                ))

            fig_avg_score.update_layout(
                title_text="학년별 평균점수 추이",
                xaxis_title="회차",
                yaxis_title="평균점수",
                height=420,
                showlegend=True,
                xaxis=dict(dtick=1),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )

            # 합격선 표시
            fig_avg_score.add_hline(
                y=400, line_dash="dash", line_color="red",
                annotation_text="합격선 (400점)",
                annotation_position="bottom right"
            )

            st.plotly_chart(fig_avg_score, use_container_width=True)

            # ===== 4. 히트맵 (합격률) =====
            st.subheader("🗺️ 합격률 히트맵 (회차 × 학년)")
            st.caption("색상이 진할수록 합격률이 높습니다. 어느 학년이 어느 시점에 성과가 좋았는지 한눈에 파악할 수 있습니다.")

            heatmap_data = grade_round_stats.pivot(index='회차', columns='학년', values='합격률').fillna(0)

            fig_heatmap = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=[f'{g}학년' for g in heatmap_data.columns],
                y=[f'{int(r)}회차' for r in heatmap_data.index],
                colorscale='RdYlGn',
                zmin=0,
                zmax=100,
                text=[[f'{v:.1f}%' for v in row] for row in heatmap_data.values],
                texttemplate='%{text}',
                textfont=dict(size=14),
                colorbar=dict(title='합격률(%)')
            ))

            fig_heatmap.update_layout(
                title_text="회차 × 학년 합격률 히트맵",
                xaxis_title="학년",
                yaxis_title="회차",
                height=350,
                yaxis=dict(autorange='reversed')
            )

            st.plotly_chart(fig_heatmap, use_container_width=True)

            # ===== 5. 학년별 종합 통계 =====
            st.subheader("🎓 학년별 종합 통계")

            grade_stats = cse_df.groupby('학년').agg({
                '이름': 'count',
                '합격여부_binary': ['sum', 'mean'],
                '총점': ['mean', 'std']
            }).round(2)
            grade_stats.columns = ['응시자수', '합격자수', '합격률', '평균점수', '점수표준편차']
            grade_stats['합격률_pct'] = (grade_stats['합격률'] * 100).round(1)

            col1, col2 = st.columns(2)

            with col1:
                fig_summary = make_subplots(specs=[[{"secondary_y": True}]])

                fig_summary.add_trace(
                    go.Bar(x=grade_stats.index, y=grade_stats['응시자수'],
                          name='응시자수', marker_color='lightblue',
                          text=grade_stats['응시자수'].astype(int),
                          textposition='inside'),
                    secondary_y=False,
                )

                fig_summary.add_trace(
                    go.Scatter(x=grade_stats.index, y=grade_stats['합격률_pct'],
                              mode='lines+markers+text', name='합격률(%)',
                              line=dict(color='red', width=3),
                              text=[f"{x:.1f}%" for x in grade_stats['합격률_pct']],
                              textposition='top center'),
                    secondary_y=True,
                )

                fig_summary.update_xaxes(title_text="학년")
                fig_summary.update_yaxes(title_text="응시자수", secondary_y=False)
                fig_summary.update_yaxes(title_text="합격률(%)", secondary_y=True)
                fig_summary.update_layout(
                    title_text="학년별 응시자수 및 합격률",
                    showlegend=True,
                    height=400
                )

                st.plotly_chart(fig_summary, use_container_width=True)

            with col2:
                fig_score = px.bar(x=grade_stats.index, y=grade_stats['평균점수'],
                             title="학년별 평균점수",
                             labels={'x': '학년', 'y': '평균점수'})
                fig_score.update_traces(
                    marker_color='lightgreen',
                    text=grade_stats['평균점수'].round(1),
                    textposition='inside'
                )
                fig_score.update_layout(
                    showlegend=False,
                    yaxis_title="평균점수",
                    height=400
                )
                st.plotly_chart(fig_score, use_container_width=True)

            # ===== 6. 상세 데이터 테이블 =====
            st.subheader("📋 회차별 학년별 상세 통계")
            display_stats = grade_round_stats.copy()
            display_stats['합격률'] = display_stats['합격률'].astype(str) + '%'
            display_stats = display_stats.sort_values(['회차', '학년'], ascending=[False, True])
            st.dataframe(display_stats, use_container_width=True, hide_index=True)

            # 학년별 종합 테이블
            st.subheader("📋 학년별 종합 상세 통계")
            display_grade_stats = grade_stats.copy()
            display_grade_stats['합격률'] = display_grade_stats['합격률_pct'].astype(str) + '%'
            display_grade_stats = display_grade_stats.drop('합격률_pct', axis=1)
            st.dataframe(display_grade_stats, use_container_width=True)

    # 탭 4: PCCP 레벨 정보
    with tab4:
        st.header("📚 PCCP 레벨 정보")

        # 1. PCCP 레벨별 점수 및 의미
        st.subheader("📊 PCCP 레벨별 점수 및 의미")

        # PCCP 레벨별 점수 및 의미 테이블
        pccp_levels_data = {
            'PCCP 레벨': ['Lv.1', 'Lv.2', 'Lv.3', 'Lv.4', 'Lv.5'],
            '점수 구간': ['400~499점', '500~599점', '600~749점', '750~899점', '900~1000점'],
            '의미': ['프로그래밍 기초 문법 이해', '기본 알고리즘 이해', '중급 알고리즘 활용', '고급 알고리즘 구현', '전문가 수준'],
            '상세 설명': [
                '기본 입출력, 조건문, 반복문, 배열 다루기',
                '기본 정렬, 탐색, 스택/큐, 재귀 기초',
                'BFS/DFS, 동적계획법, 그리디, 이분탐색',
                '고급 그래프, 세그먼트 트리, 최단경로',
                '네트워크 플로우, 문자열 알고리즘, 고급 자료구조'
            ],
            '합격 전략': ['2문제 완전 해결', '2.5문제 해결', '3문제 해결', '3.5문제 해결', '4문제 완전 해결']
        }

        pccp_levels_df = pd.DataFrame(pccp_levels_data)
        st.dataframe(pccp_levels_df, use_container_width=True)

        # 2. 기업별 요구 수준 비교
        st.subheader("🏢 기업별 요구 수준 비교")

        company_requirements_data = {
            '기업 분류': ['스타트업/중소기업', '대기업/금융권', '네카라쿠배', '해외 빅테크'],
            '백준 티어 요구': ['Silver ~ Gold', 'Gold ~ Platinum', 'Platinum ~ Diamond', 'Diamond+'],
            'PCCP 레벨 요구': ['Lv.2 ~ Lv.3', 'Lv.3 ~ Lv.4', 'Lv.4 ~ Lv.5', 'Lv.5']
        }

        company_requirements_df = pd.DataFrame(company_requirements_data)
        st.dataframe(company_requirements_df, use_container_width=True)

        # 3. 추가 설명
        st.info("💡 **참고사항**: PCCP 레벨은 프로그래밍 역량을 객관적으로 평가하는 지표로, 취업 시 기업에서 요구하는 코딩 역량 수준을 파악하는 데 도움이 됩니다.")

        # 4. 학습 가이드
        st.subheader("🎯 학습 가이드")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **초급 (Lv.1-2)**
            - 프로그래밍 언어 기초 문법
            - 기본 자료구조 (배열, 문자열)
            - 간단한 알고리즘 (정렬, 탐색)
            """)

            st.markdown("""
            **중급 (Lv.3)**
            - 그래프 알고리즘 (BFS/DFS)
            - 동적계획법 기초
            - 그리디 알고리즘
            """)

        with col2:
            st.markdown("""
            **고급 (Lv.4)**
            - 고급 그래프 알고리즘
            - 세그먼트 트리
            - 최단경로 알고리즘
            """)

            st.markdown("""
            **전문가 (Lv.5)**
            - 네트워크 플로우
            - 문자열 알고리즘
            - 고급 자료구조
            """)

    # 관리자 전용 탭들
    if st.session_state.is_admin:
        # 탭 5: 학생별 성과 분석
        with tab5:
            st.header("👨‍🎓 학생별 성과 분석")

            # 3회 이상 응시자 찾기
            student_attempts = filtered_df.groupby(['이름', '이메일', '학번']).size().reset_index(name='응시횟수')
            frequent_test_takers = student_attempts[student_attempts['응시횟수'] >= 3]

            if frequent_test_takers.empty:
                st.info("3회 이상 응시한 학생이 없습니다.")
            else:
                st.subheader(f"📋 3회 이상 응시자 목록 ({len(frequent_test_takers)}명)")

                # 3회 이상 응시자의 상세 정보
                detailed_info = []
                for _, row in frequent_test_takers.iterrows():
                    student_data = filtered_df[
                        (filtered_df['이름'] == row['이름']) &
                        (filtered_df['이메일'] == row['이메일']) &
                        (filtered_df['학번'] == row['학번'])
                    ].sort_values('회차')

                    passes = len(student_data[student_data['합격여부'] == '합격'])
                    avg_score = student_data['총점'].mean()
                    max_score = student_data['총점'].max()

                    detailed_info.append({
                        '이름': row['이름'],
                        '이메일': row['이메일'],
                        '학번': row['학번'],
                        '학과': student_data.iloc[0]['학과'],
                        '학년': student_data.iloc[0]['학년'],
                        '응시횟수': row['응시횟수'],
                        '합격횟수': passes,
                        '평균점수': round(avg_score, 1),
                        '최고점수': max_score
                    })

                detailed_df = pd.DataFrame(detailed_info)
                st.dataframe(detailed_df, use_container_width=True)

                # 점수 추이 분석
                st.subheader("📈 점수 추이 분석")

                # 학생 선택
                selected_student = st.selectbox(
                    "분석할 학생 선택",
                    options=[(f"{row['이름']} ({row['학번']}) - {row['이메일']}") for _, row in frequent_test_takers.iterrows()],
                    help="점수 추이를 확인할 학생을 선택하세요"
                )

                if selected_student:
                    # 선택된 학생의 정보 파싱
                    parts = selected_student.split(' - ')
                    email = parts[1]
                    name_and_id = parts[0]
                    student_name = name_and_id.split(' (')[0]
                    student_id = name_and_id.split('(')[1].split(')')[0]

                    student_history = filtered_df[
                        (filtered_df['이름'] == student_name) &
                        (filtered_df['이메일'] == email) &
                        (filtered_df['학번'] == student_id)
                    ].sort_values('회차')

                    # 점수 추이 그래프
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=student_history['회차'],
                        y=student_history['총점'],
                        mode='lines+markers',
                        name='점수',
                        line=dict(color='blue', width=3),
                        marker=dict(size=10)
                    ))

                    # 합격선 표시 (일반적으로 400점 이상을 합격으로 가정)
                    fig.add_hline(y=400, line_dash="dash", line_color="red",
                                 annotation_text="합격선 (추정)")

                    fig.update_layout(
                        title=f"{student_name}({student_id}) 점수 추이",
                        xaxis_title="회차",
                        yaxis_title="점수",
                        height=400,
                        xaxis=dict(dtick=1)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # 상세 데이터
                    st.subheader("📋 회차별 상세 데이터")
                    display_history = student_history[['회차', '시험과목', '총점', '합격여부', '등급(Lv.)']].copy()
                    st.dataframe(display_history, use_container_width=True)

        # 탭 6: 상세 데이터
        with tab6:
            st.header("📋 전체 상세 데이터")

            # 데이터 요약
            st.subheader("📊 필터링된 데이터 요약")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("총 레코드 수", len(filtered_df))
            with col2:
                st.metric("고유 학생 수", filtered_df.groupby(['이름', '학번']).ngroups)
            with col3:
                st.metric("회차 범위", f"{filtered_df['회차'].min()} - {filtered_df['회차'].max()}")

            # 검색 기능
            st.subheader("🔍 데이터 검색")
            search_term = st.text_input("학생 이름 또는 학번으로 검색", placeholder="예: 김철수 또는 202155619")

            display_df = filtered_df.copy()
            if search_term:
                display_df = display_df[
                    (display_df['이름'].str.contains(search_term, case=False, na=False)) |
                    (display_df['학번'].astype(str).str.contains(search_term, case=False, na=False))
                ]

            # 정렬 옵션
            sort_col = st.selectbox(
                "정렬 기준",
                options=['회차', '총점', '이름', '학과', '학년'],
                index=0
            )
            sort_order = st.radio("정렬 순서", ["오름차순", "내림차순"], horizontal=True)

            ascending = True if sort_order == "오름차순" else False
            display_df = display_df.sort_values(sort_col, ascending=ascending)

            # 데이터 표시
            st.dataframe(
                display_df[['회차', '시험과목', '이름', '학과', '학년', '총점', '합격여부', '등급(Lv.)']],
                use_container_width=True,
                height=400
            )

            # 다운로드 기능
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 필터링된 데이터 다운로드 (CSV)",
                data=csv,
                file_name=f"pcc_filtered_data_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        # 탭 7: 성장 추이 분석
        with tab7:
            st.header("📈 성장 추이 분석")

            # 1. 전체 성적 추이
            st.subheader("📊 전체 성적 추이")

            # 회차별 평균 점수 추이
            round_trend = filtered_df.groupby('회차').agg({
                '총점': ['mean', 'std'],
                '합격여부_binary': 'mean'
            }).reset_index()
            round_trend.columns = ['회차', '평균점수', '표준편차', '합격률']
            round_trend['합격률'] = round_trend['합격률'] * 100

            fig_trend = make_subplots(specs=[[{"secondary_y": True}]])

            fig_trend.add_trace(
                go.Scatter(
                    x=round_trend['회차'],
                    y=round_trend['평균점수'],
                    mode='lines+markers+text',
                    name='평균점수',
                    line=dict(color='blue', width=3),
                    text=round_trend['평균점수'].round(1),
                    textposition='top center'
                ),
                secondary_y=False
            )

            fig_trend.add_trace(
                go.Scatter(
                    x=round_trend['회차'],
                    y=round_trend['합격률'],
                    mode='lines+markers+text',
                    name='합격률(%)',
                    line=dict(color='green', width=3),
                    text=round_trend['합격률'].round(1).astype(str) + '%',
                    textposition='bottom center'
                ),
                secondary_y=True
            )

            fig_trend.update_layout(
                title_text="회차별 평균점수 및 합격률 추이",
                showlegend=True,
                xaxis=dict(tickmode='linear', tick0=1, dtick=1)
            )

            fig_trend.update_xaxes(title_text="회차")
            fig_trend.update_yaxes(title_text="평균점수", secondary_y=False)
            fig_trend.update_yaxes(title_text="합격률(%)", secondary_y=True)

            st.plotly_chart(fig_trend, use_container_width=True)

            # 2. 재응시 학생 분석
            st.subheader("🔄 재응시 학생 분석")

            # 재응시 학생 식별
            retake_students = filtered_df.groupby(['이름', '학번']).filter(lambda x: len(x) > 1)

            if not retake_students.empty:
                # 재응시 학생들의 점수 변화
                student_progress = retake_students.groupby(['이름', '학번']).agg({
                    '총점': ['first', 'last', 'mean'],
                    '회차': ['first', 'last']
                }).reset_index()

                student_progress.columns = ['이름', '학번', '첫시험점수', '최근시험점수', '평균점수', '첫시험회차', '최근시험회차']
                student_progress['점수향상도'] = student_progress['최근시험점수'] - student_progress['첫시험점수']

                col1, col2 = st.columns(2)

                with col1:
                    # 점수 향상도 분포
                    fig_improvement = go.Figure()

                    fig_improvement.add_trace(go.Histogram(
                        x=student_progress['점수향상도'],
                        nbinsx=20,
                        name='점수 향상도 분포'
                    ))

                    fig_improvement.update_layout(
                        title_text="재응시 학생 점수 향상도 분포",
                        xaxis_title="점수 향상도",
                        yaxis_title="학생 수",
                        xaxis=dict(tickmode='linear', dtick=5)
                    )

                    st.plotly_chart(fig_improvement, use_container_width=True)

                with col2:
                    # 향상도 통계
                    improvement_stats = {
                        '평균 향상도': student_progress['점수향상도'].mean(),
                        '최대 향상도': student_progress['점수향상도'].max(),
                        '최소 향상도': student_progress['점수향상도'].min(),
                        '향상도 표준편차': student_progress['점수향상도'].std(),
                        '향상한 학생 비율': (student_progress['점수향상도'] > 0).mean() * 100
                    }

                    for key, value in improvement_stats.items():
                        st.metric(key, f"{value:.1f}")

                # 상세 통계
                st.subheader("📋 재응시 학생 상세 통계")
                st.dataframe(
                    student_progress.sort_values('점수향상도', ascending=False),
                    use_container_width=True
                )
            else:
                st.info("재응시 학생 데이터가 없습니다.")

            # 3. 학년별 성적 추이
            st.subheader("🎓 학년별 성적 추이")

            # 학년-회차별 통계
            grade_round_stats = filtered_df.groupby(['학년', '회차']).agg({
                '총점': 'mean',
                '합격여부_binary': 'mean'
            }).reset_index()

            # 학년별 평균점수 추이
            fig_grade_trend = go.Figure()

            for grade in sorted(grade_round_stats['학년'].unique()):
                grade_data = grade_round_stats[grade_round_stats['학년'] == grade]
                fig_grade_trend.add_trace(go.Scatter(
                    x=grade_data['회차'],
                    y=grade_data['총점'],
                    mode='lines+markers+text',
                    name=f'{grade}학년',
                    text=grade_data['총점'].round(1),
                    textposition='top center'
                ))

            fig_grade_trend.update_layout(
                title_text="학년별 평균점수 추이",
                xaxis_title="회차",
                yaxis_title="평균점수",
                showlegend=True,
                xaxis=dict(tickmode='linear', tick0=1, dtick=1)
            )

            st.plotly_chart(fig_grade_trend, use_container_width=True)

            # 학년별 상세 통계
            st.subheader("📊 학년별 상세 통계")
            grade_stats = filtered_df.groupby('학년').agg({
                '총점': ['mean', 'std', 'min', 'max'],
                '합격여부_binary': 'mean'
            }).round(2)
            grade_stats.columns = ['평균점수', '표준편차', '최저점수', '최고점수', '합격률']
            grade_stats['합격률'] = (grade_stats['합격률'] * 100).round(1).astype(str) + '%'
            st.dataframe(grade_stats, use_container_width=True)

        # 탭 8: 정보컴퓨터공학부 3회차-5회차 비교 분석
        with tab8:
            st.header("🔄 정보컴퓨터공학부 3회차-5회차 비교 분석")

            # 정보컴퓨터공학부/전기컴퓨터공학부 데이터만 필터링
            cse_df = filtered_df[
                (filtered_df['학과'] == '정보컴퓨터공학부') |
                (filtered_df['학과'] == '전기컴퓨터공학부 정보컴퓨터공학전공') |
                (filtered_df['학과'] == '전기컴퓨터공학부')
            ]

            # 3회차와 5회차 데이터 필터링
            round3_df = cse_df[cse_df['회차'] == 3]
            round5_df = cse_df[cse_df['회차'] == 5]

            if not round3_df.empty and not round5_df.empty:
                # 1. 전체 성적 비교
                st.subheader("📊 전체 성적 비교")

                col1, col2 = st.columns(2)

                with col1:
                    # 3회차 통계
                    round3_stats = {
                        '응시자수': len(round3_df),
                        '평균점수': round3_df['총점'].mean(),
                        '합격률': (round3_df['합격여부_binary'].mean() * 100),
                        '최고점수': round3_df['총점'].max(),
                        '최저점수': round3_df['총점'].min()
                    }

                    st.metric("3회차 응시자수", f"{round3_stats['응시자수']}명")
                    st.metric("3회차 평균점수", f"{round3_stats['평균점수']:.1f}점")
                    st.metric("3회차 합격률", f"{round3_stats['합격률']:.1f}%")
                    st.metric("3회차 최고점수", f"{round3_stats['최고점수']:.1f}점")
                    st.metric("3회차 최저점수", f"{round3_stats['최저점수']:.1f}점")

                with col2:
                    # 5회차 통계
                    round5_stats = {
                        '응시자수': len(round5_df),
                        '평균점수': round5_df['총점'].mean(),
                        '합격률': (round5_df['합격여부_binary'].mean() * 100),
                        '최고점수': round5_df['총점'].max(),
                        '최저점수': round5_df['총점'].min()
                    }

                    st.metric("5회차 응시자수", f"{round5_stats['응시자수']}명")
                    st.metric("5회차 평균점수", f"{round5_stats['평균점수']:.1f}점")
                    st.metric("5회차 합격률", f"{round5_stats['합격률']:.1f}%")
                    st.metric("5회차 최고점수", f"{round5_stats['최고점수']:.1f}점")
                    st.metric("5회차 최저점수", f"{round5_stats['최저점수']:.1f}점")

                # 2. 학년별 성적 비교
                st.subheader("🎓 학년별 성적 비교")

                # 학년별 통계 계산
                grade_stats = pd.DataFrame()

                for grade in sorted(cse_df['학년'].unique()):
                    grade3_df = round3_df[round3_df['학년'] == grade]
                    grade5_df = round5_df[round5_df['학년'] == grade]

                    if not grade3_df.empty and not grade5_df.empty:
                        grade_stats = pd.concat([grade_stats, pd.DataFrame({
                            '학년': [grade],
                            '3회차_응시자수': [len(grade3_df)],
                            '3회차_평균점수': [grade3_df['총점'].mean()],
                            '3회차_합격률': [grade3_df['합격여부_binary'].mean() * 100],
                            '5회차_응시자수': [len(grade5_df)],
                            '5회차_평균점수': [grade5_df['총점'].mean()],
                            '5회차_합격률': [grade5_df['합격여부_binary'].mean() * 100],
                            '평균점수_변화': [grade5_df['총점'].mean() - grade3_df['총점'].mean()],
                            '합격률_변화': [(grade5_df['합격여부_binary'].mean() - grade3_df['합격여부_binary'].mean()) * 100]
                        })])

                # 학년별 평균점수 비교 그래프
                fig_grade_score = go.Figure()

                fig_grade_score.add_trace(go.Bar(
                    x=grade_stats['학년'],
                    y=grade_stats['3회차_평균점수'],
                    name='3회차',
                    text=grade_stats['3회차_평균점수'].round(1),
                    textposition='auto'
                ))

                fig_grade_score.add_trace(go.Bar(
                    x=grade_stats['학년'],
                    y=grade_stats['5회차_평균점수'],
                    name='5회차',
                    text=grade_stats['5회차_평균점수'].round(1),
                    textposition='auto'
                ))

                fig_grade_score.update_layout(
                    title_text="학년별 평균점수 비교",
                    xaxis_title="학년",
                    yaxis_title="평균점수",
                    barmode='group',
                    showlegend=True
                )

                st.plotly_chart(fig_grade_score, use_container_width=True)

                # 학년별 합격률 비교 그래프
                fig_grade_pass = go.Figure()

                fig_grade_pass.add_trace(go.Bar(
                    x=grade_stats['학년'],
                    y=grade_stats['3회차_합격률'],
                    name='3회차',
                    text=grade_stats['3회차_합격률'].round(1).astype(str) + '%',
                    textposition='auto'
                ))

                fig_grade_pass.add_trace(go.Bar(
                    x=grade_stats['학년'],
                    y=grade_stats['5회차_합격률'],
                    name='5회차',
                    text=grade_stats['5회차_합격률'].round(1).astype(str) + '%',
                    textposition='auto'
                ))

                fig_grade_pass.update_layout(
                    title_text="학년별 합격률 비교",
                    xaxis_title="학년",
                    yaxis_title="합격률(%)",
                    barmode='group',
                    showlegend=True
                )

                st.plotly_chart(fig_grade_pass, use_container_width=True)

                # 3. 주요 인사이트
                st.subheader("💡 주요 인사이트")

                # 평균점수 변화 분석
                avg_score_change = round5_stats['평균점수'] - round3_stats['평균점수']
                st.metric(
                    "전체 평균점수 변화",
                    f"{avg_score_change:+.1f}점",
                    delta=f"{avg_score_change:+.1f}점"
                )

                # 합격률 변화 분석
                pass_rate_change = round5_stats['합격률'] - round3_stats['합격률']
                st.metric(
                    "전체 합격률 변화",
                    f"{pass_rate_change:+.1f}%",
                    delta=f"{pass_rate_change:+.1f}%"
                )

                # 학년별 변화 분석
                st.subheader("📊 학년별 변화 분석")
                grade_stats['평균점수_변화'] = grade_stats['평균점수_변화'].round(1)
                grade_stats['합격률_변화'] = grade_stats['합격률_변화'].round(1)
                grade_stats['3회차_합격률'] = grade_stats['3회차_합격률'].round(1).astype(str) + '%'
                grade_stats['5회차_합격률'] = grade_stats['5회차_합격률'].round(1).astype(str) + '%'
                grade_stats['합격률_변화'] = grade_stats['합격률_변화'].astype(str) + '%'

                st.dataframe(
                    grade_stats[[
                        '학년', '3회차_응시자수', '3회차_평균점수', '3회차_합격률',
                        '5회차_응시자수', '5회차_평균점수', '5회차_합격률',
                        '평균점수_변화', '합격률_변화'
                    ]],
                    use_container_width=True
                )

            else:
                if round3_df.empty:
                    st.warning("3회차 데이터가 없습니다.")
                if round5_df.empty:
                    st.warning("5회차 데이터가 없습니다.")

    # 탭 9: 데이터 관리 (관리자 전용)
    if st.session_state.is_admin:
        with tab9:
            st.header("➕ 데이터 관리")

            supabase = init_supabase()

            # 데이터 추가 섹션
            st.subheader("📝 새 데이터 추가")

            with st.form("add_data_form"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    new_round = st.number_input("회차", min_value=1, value=1)
                    new_no = st.number_input("번호", min_value=1, value=1)
                    new_subject = st.text_input("시험과목")
                    new_name = st.text_input("이름")

                with col2:
                    new_email = st.text_input("이메일")
                    new_pass_status = st.selectbox("합격여부", ["합격", "불합격"])
                    new_score = st.number_input("총점", min_value=0, max_value=1000, value=0)

                with col3:
                    new_level = st.text_input("등급", value="")
                    new_department = st.text_input("학과", value="")
                    new_student_id = st.text_input("학번", value="")
                    new_grade = st.number_input("학년", min_value=1, max_value=4, value=1)

                submitted = st.form_submit_button("추가")

                if submitted:
                    new_data = {
                        "회차": int(new_round),
                        "no": int(new_no),
                        "시험과목": new_subject,
                        "이름": new_name,
                        "이메일": new_email,
                        "합격여부": new_pass_status,
                        "총점": int(new_score),
                        "등급": new_level if new_level else None,
                        "학과": new_department if new_department else None,
                        "학번": new_student_id if new_student_id else None,
                        "학년": int(new_grade) if new_grade else None
                    }

                    success, message = insert_pcc_result(supabase, new_data)

                    if success:
                        st.success(message)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(message)

            st.markdown("---")

            # 데이터베이스 통계
            st.subheader("📊 데이터베이스 통계")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("총 레코드 수", len(df))
            with col2:
                st.metric("고유 학생 수", df['학번'].nunique())
            with col3:
                st.metric("최근 업데이트", pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'))

if __name__ == "__main__":
    main()