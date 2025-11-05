"""
취업 현황 분석 시스템 (Supabase 연동 버전)
Employment Status Analysis System - Supabase Integration

버전: 3.0 (Supabase 연동)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
import warnings
from datetime import datetime
import logging
import os

# 환경 변수 로드 시도 (local 개발 환경에서만)
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, ModuleNotFoundError):
    # Streamlit Cloud 또는 python-dotenv가 없는 환경에서는 스킵
    pass

# =====================
# 설정 클래스 (로컬 import 실패 시 대비)
# =====================

class AppConfig:
    """애플리케이션 설정"""
    APP_TITLE = "정보컴퓨터공학부 취업 현황"
    APP_ICON = "📊"
    APP_VERSION = "v3.0 (Supabase 연동)"

    # 제외 대상 카테고리
    EXCLUDE_CATEGORIES = ['진학', '외국인']

    COLORS = {
        'primary': '#007bff',
        'success': '#28a745',
        'warning': '#ffc107',
        'danger': '#dc3545',
        'info': '#17a2b8',
        'light': '#f8f9fa',
        'dark': '#343a40'
    }


class SupabaseConfig:
    """Supabase 설정"""
    GRADUATES_TABLE = "graduation_employment"
    _url_cache = None
    _key_cache = None

    @classmethod
    def _get_url(cls):
        """URL 가져오기 (환경변수, top-level secrets, nested secrets 지원)"""
        if cls._url_cache is not None:
            return cls._url_cache

        # 1. 환경변수 우선
        url = os.getenv("SUPABASE_URL", "").strip()
        if url:
            cls._url_cache = url
            return url

        # 2. Top-level secrets: SUPABASE_URL = "..."
        try:
            url = st.secrets.get("SUPABASE_URL", "").strip()
            if url:
                cls._url_cache = url
                return url
        except:
            pass

        # 3. Nested secrets: [supabase] url = "..."
        try:
            url = st.secrets.supabase.url
            if url:
                cls._url_cache = url
                return url
        except:
            pass

        cls._url_cache = ""
        return ""

    @classmethod
    def _get_key(cls):
        """Key 가져오기 (환경변수, top-level secrets, nested secrets 지원)"""
        if cls._key_cache is not None:
            return cls._key_cache

        # 1. 환경변수 우선
        key = os.getenv("SUPABASE_KEY", "").strip()
        if key:
            cls._key_cache = key
            return key

        # 2. Top-level secrets: SUPABASE_KEY = "..."
        try:
            key = st.secrets.get("SUPABASE_KEY", "").strip()
            if key:
                cls._key_cache = key
                return key
        except:
            pass

        # 3. Nested secrets: [supabase] key = "..."
        try:
            key = st.secrets.supabase.key
            if key:
                cls._key_cache = key
                return key
        except:
            pass

        cls._key_cache = ""
        return ""

    @property
    def SUPABASE_URL(self):
        return self._get_url()

    @property
    def SUPABASE_KEY(self):
        return self._get_key()

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls._get_url() and cls._get_key())


# 로컬 모듈 import 시도
try:
    from config import app_config, supabase_config
except (ImportError, ModuleNotFoundError):
    # 모듈 로드 실패 시 인라인 정의 사용
    app_config = AppConfig()
    supabase_config = SupabaseConfig()

# Supabase DB 모듈 import 시도
try:
    from supabase_db import get_supabase_client, SupabaseDB
except Exception:
    # 모듈을 찾을 수 없으면 더미 클래스와 함수 제공
    class SupabaseDB:
        """Fallback SupabaseDB 클래스"""
        def __init__(self):
            self.error_message = "Supabase 모듈을 찾을 수 없습니다"

        def is_connected(self):
            return False

        def get_all_graduates(self):
            return None

        def get_yearly_stats(self):
            return None

        def get_regional_stats(self):
            return None

        def get_company_stats(self):
            return None, None

    @st.cache_resource
    def get_supabase_client():
        return SupabaseDB()

warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================
# 데이터 클래스
# =====================

@dataclass
class EmploymentStats:
    """취업 통계 정보"""
    total: int = 0
    employed: int = 0
    unemployed: int = 0
    employment_rate: float = 0.0
    year: Optional[str] = None

    @property
    def employment_rate_str(self) -> str:
        return f"{self.employment_rate:.1f}%"


@dataclass
class TrendAnalysis:
    """트렌드 분석 결과"""
    best_year: str = ""
    worst_year: str = ""
    best_rate: float = 0.0
    worst_rate: float = 0.0
    average_rate: float = 0.0
    trend_direction: str = ""

    @property
    def trend_emoji(self) -> str:
        if self.trend_direction == "상승":
            return "📈"
        elif self.trend_direction == "하락":
            return "📉"
        else:
            return "📊"


# =====================
# 유틸리티 함수
# =====================

def init_app():
    """앱 초기 설정"""
    st.set_page_config(
        page_title=app_config.APP_TITLE,
        page_icon=app_config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )


def load_css():
    """CSS 스타일 로드"""
    css = f"""
    <style>
        .main-header {{
            text-align: center;
            padding: 1rem 0;
            background: linear-gradient(90deg, {app_config.COLORS['primary']} 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .metric-card {{
            background: linear-gradient(135deg, {app_config.COLORS['light']} 0%, #e9ecef 100%);
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid {app_config.COLORS['primary']};
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }}

        .insight-box {{
            background: linear-gradient(135deg, #e8f4f8 0%, #d1ecf1 100%);
            padding: 1.2rem;
            border-radius: 12px;
            border-left: 4px solid {app_config.COLORS['info']};
            margin: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .status-box {{
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
        }}

        .success-box {{
            background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            border-left-color: {app_config.COLORS['success']};
        }}

        .warning-box {{
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            border-left-color: {app_config.COLORS['warning']};
        }}

        .error-box {{
            background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
            border-left-color: {app_config.COLORS['danger']};
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def show_message(message: str, msg_type: str = "info"):
    """스타일된 메시지 표시"""
    icon_map = {
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'info': 'ℹ️'
    }

    icon = icon_map.get(msg_type, 'ℹ️')
    class_name = f"{msg_type}-box"

    st.markdown(f'''
    <div class="status-box {class_name}">
        {icon} {message}
    </div>
    ''', unsafe_allow_html=True)


def safe_divide(numerator, denominator, default=0):
    """안전한 나눗셈"""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


# =====================
# 데이터 분석 함수
# =====================

def get_overall_stats(db: SupabaseDB) -> EmploymentStats:
    """전체 취업 통계 계산"""
    df = db.get_all_graduates()
    if df is None or df.empty:
        return EmploymentStats()

    # 제외 대상 필터링
    df_filtered = df[~df['employment_status'].isin(app_config.EXCLUDE_CATEGORIES)]

    total = len(df_filtered)
    employed = len(df_filtered[df_filtered['employment_status'] == '취업'])
    unemployed = total - employed
    employment_rate = (employed / total * 100) if total > 0 else 0

    return EmploymentStats(total, employed, unemployed, employment_rate)


def get_yearly_stats(db: SupabaseDB) -> pd.DataFrame:
    """연도별 취업 통계 계산"""
    yearly_stats = db.get_yearly_stats()
    return yearly_stats if yearly_stats is not None else pd.DataFrame()


def get_regional_stats(db: SupabaseDB) -> pd.DataFrame:
    """지역별 취업 통계 계산"""
    regional_stats = db.get_regional_stats()
    return regional_stats if regional_stats is not None else pd.DataFrame()


def get_company_stats(db: SupabaseDB) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """기업 통계 계산"""
    company_type_stats, company_size_stats = db.get_company_stats()
    return (
        company_type_stats if company_type_stats is not None else pd.DataFrame(),
        company_size_stats if company_size_stats is not None else pd.DataFrame()
    )


def get_trend_analysis(yearly_stats: pd.DataFrame) -> TrendAnalysis:
    """트렌드 분석"""
    if yearly_stats.empty:
        return TrendAnalysis()

    best_idx = yearly_stats['취업률'].idxmax()
    worst_idx = yearly_stats['취업률'].idxmin()

    best_year = str(yearly_stats.loc[best_idx, '연도'])
    worst_year = str(yearly_stats.loc[worst_idx, '연도'])
    best_rate = yearly_stats.loc[best_idx, '취업률']
    worst_rate = yearly_stats.loc[worst_idx, '취업률']
    average_rate = yearly_stats['취업률'].mean()

    # 트렌드 방향
    if len(yearly_stats) >= 2:
        recent_change = yearly_stats.iloc[-1]['취업률'] - yearly_stats.iloc[-2]['취업률']
        if recent_change > 1:
            trend_direction = "상승"
        elif recent_change < -1:
            trend_direction = "하락"
        else:
            trend_direction = "보합"
    else:
        trend_direction = "데이터 부족"

    return TrendAnalysis(best_year, worst_year, best_rate, worst_rate, average_rate, trend_direction)


# =====================
# 시각화 함수
# =====================

def create_kpi_metrics(stats: EmploymentStats):
    """KPI 메트릭 카드 생성"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="🎓 전체 졸업자",
            value=f"{stats.total:,}명",
            help="진학자 및 외국인 제외"
        )

    with col2:
        st.metric(
            label="✅ 취업자",
            value=f"{stats.employed:,}명",
            delta=f"{stats.employment_rate:.1f}% 취업률"
        )

    with col3:
        st.metric(
            label="❌ 미취업자",
            value=f"{stats.unemployed:,}명",
            delta=f"{100 - stats.employment_rate:.1f}% 미취업률"
        )

    with col4:
        rate_color = "🟢" if stats.employment_rate >= 80 else "🟡" if stats.employment_rate >= 60 else "🔴"
        st.metric(
            label=f"{rate_color} 취업률",
            value=f"{stats.employment_rate:.1f}%"
        )


def create_yearly_trend_chart(yearly_stats: pd.DataFrame) -> go.Figure:
    """연도별 취업률 트렌드 차트"""
    if yearly_stats.empty:
        return go.Figure()

    yearly_stats_copy = yearly_stats.copy()
    yearly_stats_copy['연도'] = yearly_stats_copy['연도'].astype(int)

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('연도별 취업률 추이', '연도별 취업자/미취업자 현황'),
        vertical_spacing=0.15
    )

    # 취업률 라인 차트
    fig.add_trace(
        go.Scatter(
            x=yearly_stats_copy['연도'],
            y=yearly_stats_copy['취업률'],
            mode='lines+markers+text',
            name='취업률',
            text=[f"{rate}%" for rate in yearly_stats_copy['취업률']],
            textposition="top center",
            line=dict(color=app_config.COLORS['primary'], width=3),
            marker=dict(size=10, color=app_config.COLORS['primary'])
        ),
        row=1, col=1
    )

    # 취업자/미취업자 스택 바
    fig.add_trace(
        go.Bar(
            x=yearly_stats_copy['연도'],
            y=yearly_stats_copy['취업자수'],
            name='취업자',
            marker_color=app_config.COLORS['success']
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Bar(
            x=yearly_stats_copy['연도'],
            y=yearly_stats_copy['미취업자수'],
            name='미취업자',
            marker_color=app_config.COLORS['danger']
        ),
        row=2, col=1
    )

    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="📈 연도별 취업 현황 분석",
        barmode='stack'
    )

    fig.update_yaxes(title_text="취업률 (%)", row=1, col=1)
    fig.update_yaxes(title_text="인원 수", row=2, col=1)

    return fig


def create_regional_chart(regional_stats: pd.DataFrame) -> Tuple[go.Figure, go.Figure]:
    """지역별 분석 차트"""
    if regional_stats.empty:
        return go.Figure(), go.Figure()

    # 막대 차트
    bar_fig = px.bar(
        regional_stats.head(10),
        x='지역',
        y='취업자수',
        text='비율',
        title='🗺️ 상위 10개 지역별 취업자 분포',
        labels={'취업자수': '취업자 수 (명)', '지역': '지역'},
        color='취업자수',
        color_continuous_scale='viridis'
    )
    bar_fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    bar_fig.update_layout(height=400, showlegend=False)

    # 파이 차트
    top_regions = regional_stats.head(8)
    other_count = regional_stats.iloc[8:]['취업자수'].sum() if len(regional_stats) > 8 else 0

    if other_count > 0:
        other_row = pd.DataFrame({'지역': ['기타'], '취업자수': [other_count]})
        pie_data = pd.concat([top_regions, other_row], ignore_index=True)
    else:
        pie_data = top_regions

    pie_fig = px.pie(
        pie_data,
        values='취업자수',
        names='지역',
        title='지역별 취업자 비율',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    pie_fig.update_traces(textposition='inside', textinfo='percent+label')

    return bar_fig, pie_fig


def create_company_charts(
    company_type_stats: pd.DataFrame,
    company_size_stats: pd.DataFrame
) -> Tuple[go.Figure, go.Figure]:
    """기업 분석 차트"""
    type_fig = go.Figure()
    size_fig = go.Figure()

    if not company_type_stats.empty:
        type_fig = px.pie(
            company_type_stats,
            values='취업자수',
            names='기업구분',
            title='🏢 기업 유형별 취업자 분포',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        type_fig.update_traces(textposition='inside', textinfo='percent+label')

    if not company_size_stats.empty:
        size_fig = px.pie(
            company_size_stats,
            values='취업자수',
            names='회사규모',
            title='🏭 회사 규모별 취업자 분포',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        size_fig.update_traces(textposition='inside', textinfo='percent+label')

    return type_fig, size_fig


# =====================
# UI 렌더링 함수
# =====================

def show_header():
    """헤더 섹션"""
    st.markdown(f'''
    <div class="main-header">
        <h1>{app_config.APP_TITLE}</h1>
        <p>Employment Status Analysis Dashboard</p>
        <p>📅 분석 기간: 2020년 ~ 2024년 | 🎯 대상: 학부 졸업자 (진학자/외국인 제외)</p>
    </div>
    ''', unsafe_allow_html=True)


def show_insights(trend: TrendAnalysis, stats: EmploymentStats):
    """주요 인사이트 표시"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f'''
        <div class="insight-box">
            <h4>📊 주요 통계 인사이트</h4>
            <ul>
                <li><strong>최고 취업률:</strong> {trend.best_year}년 {trend.best_rate:.1f}%</li>
                <li><strong>최저 취업률:</strong> {trend.worst_year}년 {trend.worst_rate:.1f}%</li>
                <li><strong>평균 취업률:</strong> {trend.average_rate:.1f}%</li>
                <li><strong>최근 트렌드:</strong> {trend.trend_emoji} {trend.trend_direction}</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)

    with col2:
        if stats.employment_rate >= 80:
            status = "우수"
            color = app_config.COLORS['success']
            recommendation = "현재 수준을 유지하고 질적 향상에 집중하세요."
        elif stats.employment_rate >= 60:
            status = "양호"
            color = app_config.COLORS['warning']
            recommendation = "취업률 향상을 위한 추가 프로그램 검토가 필요합니다."
        else:
            status = "개선 필요"
            color = app_config.COLORS['danger']
            recommendation = "취업 지원 프로그램의 전면적인 검토와 개선이 시급합니다."

        st.markdown(f'''
        <div class="insight-box">
            <h4>💡 개선 방향 제안</h4>
            <p><strong>현재 상태:</strong> <span style="color: {color};">{status}</span></p>
            <p><strong>권장사항:</strong> {recommendation}</p>
        </div>
        ''', unsafe_allow_html=True)


def setup_sidebar():
    """사이드바 설정"""
    with st.sidebar:
        st.markdown(f"""
        ### {app_config.APP_TITLE} {app_config.APP_VERSION}

        **📊 주요 기능**
        - 연도별 취업률 분석
        - 지역별 취업 현황
        - 기업 유형별 분석

        **📅 분석 기간**
        2020년 ~ 2024년

        **🎯 분석 대상**
        학부 졸업자 (진학자/외국인 제외)

        **🗄️ 데이터 저장소**
        Supabase PostgreSQL
        """)

        st.markdown("---")

        # 데이터베이스 연결 상태
        db = get_supabase_client()
        if db.is_connected():
            show_message("Supabase 연결됨", "success")
        else:
            show_message(f"Supabase 미연결: {db.error_message}", "error")


def render_yearly_analysis(db: SupabaseDB):
    """연도별 분석 탭"""
    st.subheader("📈 연도별 취업 현황 분석")

    yearly_stats = get_yearly_stats(db)
    if yearly_stats.empty:
        show_message("연도별 데이터가 없습니다.", "warning")
        return

    # 차트
    yearly_chart = create_yearly_trend_chart(yearly_stats)
    st.plotly_chart(yearly_chart, use_container_width=True)

    # 상세 테이블
    st.subheader("📋 연도별 상세 통계")
    styled_df = yearly_stats.style.background_gradient(
        subset=['취업률'], cmap='RdYlGn'
    ).format({
        '취업률': '{:.1f}%',
        '전체인원': '{:,}명',
        '취업자수': '{:,}명',
        '미취업자수': '{:,}명'
    })
    st.dataframe(styled_df, use_container_width=True)


def render_regional_analysis(db: SupabaseDB):
    """지역별 분석 탭"""
    st.subheader("🗺️ 지역별 취업 현황 분석")

    regional_stats = get_regional_stats(db)
    if regional_stats.empty:
        show_message("지역별 데이터가 없습니다.", "warning")
        return

    bar_chart, pie_chart = create_regional_chart(regional_stats)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(bar_chart, use_container_width=True)
    with col2:
        st.plotly_chart(pie_chart, use_container_width=True)


def render_company_analysis(db: SupabaseDB):
    """기업 분석 탭"""
    st.subheader("🏢 기업 유형별 취업 현황 분석")

    company_type_stats, company_size_stats = get_company_stats(db)

    if not company_type_stats.empty:
        type_chart, size_chart = create_company_charts(company_type_stats, company_size_stats)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(type_chart, use_container_width=True)
        with col2:
            if not company_size_stats.empty:
                st.plotly_chart(size_chart, use_container_width=True)

        # 데이터 표
        st.subheader("📊 상세 데이터")

        col1, col2 = st.columns(2)
        with col1:
            st.write("**🏢 기업 유형별 취업자 분포**")
            styled_company_type = company_type_stats.style.background_gradient(
                subset=['취업자수'], cmap='Blues'
            ).format({
                '취업자수': '{:,}명',
                '비율': '{:.1f}%'
            })
            st.dataframe(styled_company_type, use_container_width=True)

        with col2:
            if not company_size_stats.empty:
                st.write("**🏭 회사 규모별 취업자 분포**")
                styled_company_size = company_size_stats.style.background_gradient(
                    subset=['취업자수'], cmap='Greens'
                ).format({
                    '취업자수': '{:,}명',
                    '비율': '{:.1f}%'
                })
                st.dataframe(styled_company_size, use_container_width=True)
    else:
        show_message("기업 분석 데이터가 없습니다.", "warning")


def render_footer():
    """푸터"""
    st.markdown(f'''
    <div style="text-align: center; padding: 2rem 0; color: #999; border-top: 1px solid #eee;">
        <p>📊 {app_config.APP_TITLE} {app_config.APP_VERSION} |
        ⚡ Powered by Streamlit & Plotly & Supabase |
        📅 2020 ~ 2024</p>
    </div>
    ''', unsafe_allow_html=True)


# =====================
# 메인 함수
# =====================

def main():
    """메인 애플리케이션"""
    # 초기화
    init_app()
    load_css()

    # Supabase 연결
    db = get_supabase_client()

    if not db.is_connected():
        st.error(f"🔴 Supabase 연결 실패")
        st.error(f"오류: {db.error_message}")
        st.info("""
        ### 설정 방법:
        1. Supabase 프로젝트 생성 (https://supabase.com)
        2. .env 파일 생성 후 SUPABASE_URL과 SUPABASE_KEY 입력
        3. 다음 명령어 실행:
           - `python init_database.py` (데이터베이스 초기화)
           - `python load_csv_data.py` (CSV 데이터 로드)
        4. Streamlit 앱 재실행
        """)
        st.stop()

    # 헤더
    show_header()

    # 사이드바
    setup_sidebar()

    # 데이터 로드
    stats = get_overall_stats(db)
    yearly_stats = get_yearly_stats(db)
    trend = get_trend_analysis(yearly_stats)

    # KPI 메트릭
    create_kpi_metrics(stats)

    # 인사이트
    show_insights(trend, stats)

    # 탭 구성
    tabs = st.tabs(["📈 연도별 분석", "🗺️ 지역별 분석", "🏢 기업별 분석"])

    with tabs[0]:
        render_yearly_analysis(db)

    with tabs[1]:
        render_regional_analysis(db)

    with tabs[2]:
        render_company_analysis(db)

    # 푸터
    render_footer()


if __name__ == "__main__":
    main()
