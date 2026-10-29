# JOB INSIGHT
Streamlit 지역별 취업 통계 탐색 웹앱.

## 배포
GitHub에 app.py, requirements.txt, data 폴더를 업로드하고 Streamlit Community Cloud에서 app.py를 실행하세요.

## 실제 데이터
공식 KOSIS 통계를 아래 열 이름으로 정리하여 data/employment.csv에 저장하거나 앱에서 CSV 업로드:
연도,시도,시군구,고용률,실업률,취업자수
수치는 실제 통계로만 입력하세요. 광역 집계는 시군구에 '전체'를 넣습니다. 취업자수 단위는 '명'.

## 지도
지도는 실행 시 https://github.com/KnellBalm/kr-admin-geojson 의 ctprvn.geojson, sig.geojson을 요청합니다. 오프라인 운영 시 data 폴더에 두 파일을 저장하세요. 지도는 2023년 기반이며 최신 경계와 다를 수 있습니다.

## 채용공고
고용24 공식 사이트 연결만 제공하며 실시간 API 통합은 포함되지 않습니다.

## 테스트
1. 지역 선택 시 시군구 목록 변경 확인
2. CSV 누락 시 안내 메시지 확인
3. CSV 형식 오류 시 경고 확인
4. 두 지역 비교 그래프 확인
5. 지도 네트워크 장애 시 선택 상자 동작 확인

## AI 활용 기록 예시
도구: ChatGPT. 질문: '대한민국 지역별 취업 통계와 시군구 클릭 지도를 Streamlit으로 만들고 예외 처리를 구현해줘.' AI 코드를 이해하고 직접 수정한 항목을 기록하세요.
