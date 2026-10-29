import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st
import requests

st.set_page_config(page_title='JOB INSIGHT | 지역별 취업 분석', page_icon='💼', layout='wide')
BASE = Path(__file__).parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
MAP_BASE = 'https://raw.githubusercontent.com/KnellBalm/kr-admin-geojson/main/'
SOURCES = {'공식 고용 통계': 'https://kosis.kr', '시군구 고용조사': 'https://www.korea.kr/briefing/policyBriefingView.do?newsId=156745645', '고용24': 'https://www.work24.go.kr', '지도 원본': 'https://github.com/KnellBalm/kr-admin-geojson'}

st.markdown('''<style>
.stApp {background: #0b1220; color: #edf4ff}
[data-testid="stMetric"] {background: #18263b; padding: 18px; border-radius: 14px; border: 1px solid #29415e}
h1,h2,h3 {color: #eaf5ff !important}
</style>''', unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner=False)
def load_map(name):
    local = DATA / name
    if local.exists():
        with open(local, encoding='utf-8') as f:
            return json.load(f)
    response = requests.get(MAP_BASE + name, timeout=20)
    response.raise_for_status()
    return response.json()

@st.cache_data(show_spinner=False)
def read_csv_bytes(content):
    import io
    for encoding in ('utf-8-sig', 'cp949', 'utf-8'):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('CSV 인코딩을 확인해 주세요.')

def load_stats(upload):
    if upload is not None:
        df = read_csv_bytes(upload.getvalue())
    elif (DATA / 'employment.csv').exists():
        df = read_csv_bytes((DATA / 'employment.csv').read_bytes())
    else:
        return None, '통계 CSV가 아직 없습니다.'
    required = ['연도', '시도', '시군구', '고용률', '실업률', '취업자수']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return None, 'CSV에 필요한 열이 없습니다: ' + ', '.join(missing)
    for col in ['연도', '고용률', '실업률', '취업자수']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['시도'] = df['시도'].fillna('').astype(str).str.strip()
    df['시군구'] = df['시군구'].fillna('').astype(str).str.strip()
    df = df.dropna(subset=['연도'])
    df['연도'] = df['연도'].astype(int)
    return df, None

def make_map(geo, name_key, names, selected, key):
    features = []
    for f in geo.get('features', []):
        name = f.get('properties', {}).get(name_key, '')
        if name in names:
            features.append(f)
    if not features:
        st.warning('표시할 지역 경계가 없습니다.')
        return None
    filtered = {'type': 'FeatureCollection', 'features': features}
    df = pd.DataFrame({'지역': [f['properties'][name_key] for f in features]})
    df['선택'] = df['지역'].apply(lambda x: 2 if x == selected else 1)
    fig = px.choropleth_mapbox(df, geojson=filtered, locations='지역', featureidkey=f'properties.{name_key}', color='선택',
        color_continuous_scale=['#2b8cbe', '#8fe1ff'], mapbox_style='carto-darkmatter',
        center={'lat': 36.3, 'lon': 127.8}, zoom=5.4, opacity=0.75, hover_name='지역', height=570)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), coloraxis_showscale=False,
        clickmode='event+select', paper_bgcolor='#0b1220')
    event = st.plotly_chart(fig, use_container_width=True, key=key, on_select='rerun', selection_mode='points')
    points = event.selection.points if event is not None else []
    if points:
        return points[0].get('location')
    return None

def stats_view(df, province, city):
    if df is None:
        st.info('실제 통계 CSV를 연결하면 이곳에 고용률·실업률·취업자 수와 그래프가 표시됩니다.')
        return
    subset = df[df['시도'] == province]
    if city != '시도 전체':
        subset = subset[subset['시군구'] == city]
    else:
        # 시도 전체 행이 명시된 경우에만 사용. 시군구 고용률을 단순 평균하지 않음.
        subset = subset[subset['시군구'].isin(['', '전체', '시도 전체'])]
    if subset.empty:
        st.warning('선택한 지역의 공식 통계가 없습니다. 다른 지역을 선택하거나 CSV를 추가하세요.')
        return
    latest_year = int(subset['연도'].max())
    latest = subset[subset['연도'] == latest_year].iloc[-1]
    st.caption(f'자료 기준: {latest_year}년 · CSV에 기록된 원자료 기준 확인 필요')
    cols = st.columns(3)
    for col, label, field, unit in zip(cols, ['고용률', '실업률', '취업자 수'], ['고용률', '실업률', '취업자수'], ['%', '%', '명']):
        value = latest[field]
        col.metric(label, f'{value:,.1f}{unit}' if pd.notna(value) and unit == '%' else (f'{value:,.0f}{unit}' if pd.notna(value) else '자료 없음'))
    trend = subset.sort_values('연도').dropna(subset=['고용률'])
    if not trend.empty:
        st.plotly_chart(px.line(trend, x='연도', y='고용률', markers=True, title='연도별 고용률 변화'), use_container_width=True)
    st.dataframe(subset.sort_values('연도', ascending=False), use_container_width=True, hide_index=True)
    st.download_button('📥 이 지역 통계 CSV 다운로드', subset.to_csv(index=False).encode('utf-8-sig'), 'region_stats.csv', 'text/csv')

st.title('💼 JOB INSIGHT')
st.caption('대한민국 지역별 고용 통계 분석 · 지도 탐색 · 채용정보 검색')
with st.sidebar:
    st.header('⚙️ 데이터 설정')
    upload = st.file_uploader('공식 고용통계 CSV 업로드', type='csv')
    st.caption('또는 GitHub의 data/employment.csv에 넣어도 됩니다.')
    st.divider()
    for label, url in SOURCES.items():
        st.markdown(f'[{label}]({url})')
try:
    stats, error = load_stats(upload)
except Exception as e:
    stats, error = None, f'통계 파일 읽기 오류: {e}'
if error:
    st.sidebar.warning(error)

try:
    province_geo = load_map('ctprvn.geojson')
    city_geo = load_map('sig.geojson')
    map_ok = True
except (requests.RequestException, ValueError, OSError, json.JSONDecodeError) as e:
    province_geo, city_geo, map_ok = None, None, False
    st.warning('지도 파일을 불러오지 못했습니다. 인터넷 연결을 확인하거나 data 폴더에 ctprvn.geojson과 sig.geojson을 넣어주세요.')
    st.caption(str(e))

provinces = sorted({f['properties']['CTP_KOR_NM'] for f in province_geo['features']}) if map_ok else [
    '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시',
    '세종특별자치시', '경기도', '강원특별자치도', '충청북도', '충청남도', '전북특별자치도',
    '전라남도', '경상북도', '경상남도', '제주특별자치도']
if 'province' not in st.session_state or st.session_state.province not in provinces:
    st.session_state.province = '경기도' if '경기도' in provinces else provinces[0]
if 'city' not in st.session_state:
    st.session_state.city = '시도 전체'

tab1, tab2, tab3, tab4 = st.tabs(['🗺️ 지역 탐색', '📊 지역 비교', '💼 채용정보', '📖 이용 안내'])
with tab1:
    st.subheader('1단계 · 시도 선택')
    province = st.selectbox('시도', provinces, index=provinces.index(st.session_state.province))
    if province != st.session_state.province:
        st.session_state.province = province
        st.session_state.city = '시도 전체'
    if map_ok:
        clicked = make_map(province_geo, 'CTP_KOR_NM', provinces, province, 'province_map')
        if clicked and clicked != province:
            st.session_state.province = clicked
            st.session_state.city = '시도 전체'
            st.rerun()
    st.subheader('2단계 · 시군구 선택')
    if map_ok:
        city_features = [f for f in city_geo['features'] if f['properties'].get('SIDO_NM') == province]
        cities = sorted({f['properties'].get('SIG_KOR_NM', '') for f in city_features if f['properties'].get('SIG_KOR_NM')})
    else:
        cities = sorted(stats.loc[stats['시도'] == province, '시군구'].dropna().unique().tolist()) if stats is not None else []
    choices = ['시도 전체'] + cities
    current = st.session_state.city if st.session_state.city in choices else '시도 전체'
    city = st.selectbox('시군구', choices, index=choices.index(current))
    st.session_state.city = city
    if map_ok and cities:
        clicked_city = make_map(city_geo, 'SIG_KOR_NM', cities, city, 'city_map')
        if clicked_city and clicked_city != city:
            st.session_state.city = clicked_city
            st.rerun()
    st.subheader(f'📍 {province} {city if city != "시도 전체" else ""} 고용 분석')
    stats_view(stats, province, city)
    st.info('지도 경계는 2023년 기반 공개 자료로, 최신 행정구역과 일부 다를 수 있습니다.')

with tab2:
    st.subheader('📊 두 지역 비교')
    if stats is None:
        st.info('지역 비교에는 실제 통계 CSV가 필요합니다.')
    else:
        year = st.selectbox('비교 연도', sorted(stats['연도'].unique(), reverse=True))
        df_year = stats[stats['연도'] == year].copy()
        df_year['지역'] = df_year['시도'] + ' ' + df_year['시군구'].replace({'': '전체'})
        choices = sorted(df_year['지역'].unique())
        if len(choices) >= 2:
            a, b = st.columns(2)
            left = a.selectbox('지역 A', choices, index=0)
            right = b.selectbox('지역 B', choices, index=1)
            compare = df_year[df_year['지역'].isin([left, right])]
            metric = st.selectbox('비교 항목', ['고용률', '실업률', '취업자수'])
            chart = px.bar(compare, x='지역', y=metric, color='지역', text_auto=True, title=f'{year}년 지역별 {metric}')
            st.plotly_chart(chart, use_container_width=True)
            st.dataframe(compare, hide_index=True, use_container_width=True)
        else:
            st.warning('비교할 지역이 2개 이상 필요합니다.')

with tab3:
    st.subheader('💼 지역별 채용공고 찾기')
    st.write(f'선택 지역: **{st.session_state.province} {st.session_state.city}**')
    keyword = st.text_input('관심 직종 또는 키워드', placeholder='예: 개발자, 간호사, 사무직')
    st.caption('고용24 공식 사이트에서 채용공고를 확인합니다. 현재 앱 안에서 실시간 공고를 직접 수집하지는 않습니다.')
    if st.button('🔎 채용정보 검색 방법 보기'):
        query = ' '.join(x for x in [st.session_state.province, st.session_state.city if st.session_state.city != '시도 전체' else '', keyword] if x)
        st.success(f'고용24에서 지역과 키워드를 검색하세요: {query}')
    st.link_button('🏢 고용24 채용정보로 이동', 'https://www.work24.go.kr')

with tab4:
    st.subheader('📖 데이터와 사용 방법')
    st.markdown('''**1. 지도**: 전국 지도에서 지역을 클릭하거나 선택 상자로 고르세요.\n\n**2. 상세 지도**: 시군구를 선택하면 해당 지역의 통계를 확인합니다.\n\n**3. 통계 연결**: 아래 형식으로 실제 공식 자료를 정리한 CSV를 업로드하세요.\n\n**4. 채용공고**: 고용24 공식 사이트에서 지역과 직종을 검색하세요.\n\n**주의**: 시군구 통계를 단순 평균해 시도 전체 고용률로 표시하지 않습니다. 조사 기준이 다른 수치를 섞지 마세요.''')
    template = pd.DataFrame(columns=['연도', '시도', '시군구', '고용률', '실업률', '취업자수'])
    st.download_button('📄 통계 CSV 빈 양식 다운로드', template.to_csv(index=False).encode('utf-8-sig'), 'employment_template.csv', 'text/csv')
    st.caption('예: 시도=경기도, 시군구=수원시. 광역 단위 공식 통계 행은 시군구=전체로 입력하세요. 취업자수 단위는 명으로 통일하세요.')
    st.markdown('**AI 사용 기록**: ChatGPT를 활용해 Streamlit 코드 초안을 작성하고, 직접 수정·테스트한 부분을 별도로 기록하세요.')
