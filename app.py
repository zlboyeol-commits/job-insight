import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from urllib.parse import quote

st.set_page_config(page_title='JOB INSIGHT | 지역별 취업 분석', page_icon='💼', layout='wide')
st.markdown('''<style>.block-container{padding-top:2rem;max-width:1200px}h1{color:#173b70}.stMetric{background:#f3f7ff;padding:15px;border-radius:12px}</style>''', unsafe_allow_html=True)
st.title('💼 JOB INSIGHT')
st.caption('대한민국 지역별 고용 통계 분석 · 채용정보 탐색')

REGIONS = ['서울특별시','부산광역시','대구광역시','인천광역시','광주광역시','대전광역시','울산광역시','세종특별자치시','경기도','강원특별자치도','충청북도','충청남도','전북특별자치도','전라남도','경상북도','경상남도','제주특별자치도']

@st.cache_data
def read_statistics(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    required = {'연도','시도','시군구','고용률','실업률','취업자수'}
    if not required.issubset(df.columns):
        raise ValueError('CSV 필수 열: ' + ', '.join(sorted(required)))
    for col in ['연도','고용률','실업률','취업자수']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['연도','시도','시군구'])
    df['연도'] = df['연도'].astype(int)
    return df

@st.cache_data
def read_map(path):
    import json
    with open(path, encoding='utf-8') as f:
        return json.load(f)

st.sidebar.header('🔎 지역 탐색')
region = st.session_state.get('region', REGIONS[8])
if region not in REGIONS:
    region = REGIONS[8]
region = st.sidebar.selectbox('시도', REGIONS, index=REGIONS.index(region))
st.session_state.region = region

st.subheader('🗺️ 전국 지도')
st.caption('지도 파일(data/korea_sido.geojson)을 넣으면 시도를 클릭할 수 있습니다. 파일이 없다면 왼쪽 메뉴에서 선택하세요.')
geo_path = Path('data/korea_sido.geojson')
if geo_path.exists():
    try:
        geo = read_map(str(geo_path))
        names = [f.get('properties', {}).get('name') for f in geo.get('features', [])]
        names = [n for n in names if n in REGIONS]
        if not names:
            st.warning('지도 GeoJSON의 properties.name에 시도 전체 이름이 필요합니다.')
        else:
            map_df = pd.DataFrame({'시도': names, '표시값': [1] * len(names)})
            fig = px.choropleth(map_df, geojson=geo, locations='시도', featureidkey='properties.name', color='표시값', hover_name='시도', color_continuous_scale='Blues')
            fig.update_geos(fitbounds='locations', visible=False)
            fig.update_layout(height=500, margin=dict(l=0,r=0,t=0,b=0), coloraxis_showscale=False)
            event = st.plotly_chart(fig, use_container_width=True, on_select='rerun', selection_mode='points', key='sido_map')
            points = event.selection.points if event and event.selection else []
            if points:
                selected = points[0].get('location')
                if selected in REGIONS and selected != region:
                    st.session_state.region = selected
                    st.rerun()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f'지도 데이터를 읽지 못했습니다: {exc}')
else:
    st.info('지도 파일이 아직 없습니다. 왼쪽에서 지역을 선택해 다른 기능을 먼저 확인할 수 있습니다.')

st.divider()
st.subheader(f'📍 {region} 상세 분석')
stat_path = Path('data/employment.csv')
if stat_path.exists():
    try:
        df = read_statistics(str(stat_path))
        local = df[df['시도'] == region].copy()
        districts = sorted(local['시군구'].dropna().astype(str).unique().tolist())
        if not districts:
            st.warning('이 시도의 통계 자료가 없습니다.')
        else:
            district = st.selectbox('시군구 선택', districts)
            area = local[local['시군구'] == district].sort_values('연도')
            year = st.selectbox('분석 연도', sorted(area['연도'].unique(), reverse=True))
            row = area[area['연도'] == year].iloc[-1]
            a,b,c = st.columns(3)
            a.metric('고용률', f"{row['고용률']:.1f}%" if pd.notna(row['고용률']) else '자료 없음')
            b.metric('실업률', f"{row['실업률']:.1f}%" if pd.notna(row['실업률']) else '자료 없음')
            c.metric('취업자 수', f"{row['취업자수']:,.0f}명" if pd.notna(row['취업자수']) else '자료 없음')
            chart = area.dropna(subset=['고용률'])
            if not chart.empty:
                st.plotly_chart(px.line(chart, x='연도', y='고용률', markers=True, title=f'{district} 연도별 고용률'), use_container_width=True)
            else:
                st.info('고용률 그래프를 그릴 수 있는 수치가 없습니다.')
            st.dataframe(area, use_container_width=True, hide_index=True)
            st.caption('통계 출처와 조사 기준은 CSV 데이터의 원출처를 확인해 보고서에 명시하세요. 서로 다른 조사 기준의 지표는 직접 비교하면 안 됩니다.')
    except (OSError, ValueError, UnicodeError, pd.errors.ParserError, IndexError) as exc:
        st.error(f'통계 파일 오류: {exc}')
else:
    st.info('실제 통계 CSV를 data/employment.csv로 추가하면 시군구별 상세 통계가 표시됩니다.')
    st.code('연도,시도,시군구,고용률,실업률,취업자수', language='text')

st.divider()
st.subheader('💼 지역별 채용공고 찾기')
keyword = st.text_input('희망 직무', placeholder='예: 개발자, 사무직, 디자이너', max_chars=40)
search_text = f'{region} {keyword}'.strip()
st.write('고용24에서 선택한 지역과 직무를 검색할 수 있습니다.')
st.link_button('🔎 고용24 채용정보 검색', 'https://www.work24.go.kr')
st.caption(f'검색어 추천: {search_text} (고용24에서 직접 입력해 주세요. 현재 버전은 실시간 API를 연결하지 않았습니다.)')

with st.expander('🧪 테스트 체크리스트'):
    st.checkbox('시도를 바꿨을 때 제목이 변경된다')
    st.checkbox('CSV 파일이 없을 때 오류 없이 안내가 나온다')
    st.checkbox('잘못된 CSV 열 이름일 때 오류 메시지가 나온다')
    st.checkbox('시군구와 연도를 바꾸면 수치와 그래프가 갱신된다')

st.caption('JOB INSIGHT · 학교 프로그래밍 수행평가 프로젝트')
