import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="일별 박스오피스", page_icon="🎬", layout="wide")
st.title("🎬 일별 박스오피스 조회")

# 1. 날짜 계산 및 달력 위젯 (한국 시간 기준 가장 늦은 날짜는 '어제')
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst)
yesterday_kst = today_kst - timedelta(days=1)

# 달력(date_input)에서 날짜를 선택받습니다. 
# max_value를 어제로 설정하여 미래나 오늘(집계 전)은 선택할 수 없게 막습니다.
selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=yesterday_kst.date(),
    max_value=yesterday_kst.date()
)

# 선택된 날짜를 API 요청용 8자리 문자열(YYYYMMDD)로 변환
target_dt = selected_date.strftime('%Y%m%d')
st.divider()

# 2. 인증키 불러오기
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정에 KOBIS_KEY를 추가해 주세요.")
    st.stop()

API_KEY = st.secrets["KOBIS_KEY"]

# 3. KOBIS API 데이터 요청
url = "http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": API_KEY,
    "targetDt": target_dt
}

try:
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error(f"📡 서버 응답에 문제가 있습니다. (상태 코드: {response.status_code}) 잠시 후 다시 시도해 주세요.")
        st.stop()
        
    data = response.json()
    
    if "faultInfo" in data:
        fault_message = data["faultInfo"].get("message", "알 수 없는 오류")
        st.error(f"❌ API 요청 오류가 발생했습니다. 메시지: {fault_message}")
        st.stop()
        
    # 고른 날짜에 영화 목록이 비어서 올 경우의 안내 메시지
    if "boxOfficeResult" not in data or not data["boxOfficeResult"]["dailyBoxOfficeList"]:
        st.warning("📭 그날은 아직 집계 전입니다.")
        st.stop()

    movie_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

except requests.exceptions.RequestException as e:
    st.error(f"🌐 인터넷 연결에 문제가 발생했습니다. 에러: {e}")
    st.stop()
except ValueError:
    st.error("🧩 API 응답을 해석할 수 없습니다. 영화진흥위원회 서버 상태를 확인해 주세요.")
    st.stop()

# 4. 데이터 가공 (Pandas DataFrame)
df = pd.DataFrame(movie_list)

# 필요한 컬럼들을 숫자형(int)으로 변환
numeric_columns = ['audiCnt', 'audiAcc', 'scrnCnt', 'rank', 'rankInten']
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col])

# 순위 증감(rankInten)에 따라 위/아래 화살표를 붙여주는 함수
def format_rank_inten(val):
    if val > 0:
        return f"🔺 {val}"  # 빨간 위 화살표 (양수)
    elif val < 0:
        return f"🔽 {abs(val)}"  # 파란 아래 화살표 (음수)
    else:
        return "-"  # 변동 없음

# 영화명 옆에 100만 관객 돌파 트로피 이모지를 붙여주는 함수
def format_movie_name(row):
    name = row['movieNm']
    if row['audiAcc'] >= 1000000:
        return f"{name} 🏆"
    return name

# 함수들을 적용하여 새로운 컬럼 데이터를 만듭니다.
df['순위 증감'] = df['rankInten'].apply(format_rank_inten)
df['영화명(포맷)'] = df.apply(format_movie_name, axis=1)

# 화면에 보여줄 컬럼만 선택하고 이름을 바꿉니다.
display_df = df[['rank', '순위 증감', '영화명(포맷)', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
display_df.columns = ['순위', '순위 증감', '영화명', '개봉일', '관객수', '누적관객', '스크린수']
display_df = display_df.set_index('순위')


# 5. 화면에 그리기

st.subheader(f"🥇 {selected_date.strftime('%Y년 %m월 %d일')} 1위 영화 하이라이트")
top1_movie = df.iloc[0] 

# 트로피가 포함된 영화명을 화면에 표시합니다.
st.markdown(f"### **{top1_movie['영화명(포맷)']}**")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="일일 관객수", value=f"{top1_movie['audiCnt']:,}명")
with col2:
    st.metric(label="누적 관객수", value=f"{top1_movie['audiAcc']:,}명")
with col3:
    st.metric(label="스크린수", value=f"{top1_movie['scrnCnt']:,}개")

st.divider()

st.subheader("📊 관객수 TOP 5")
top5_df = df.head(5)
# 막대그래프의 x축을 트로피가 적용된 영화명으로 설정합니다.
st.bar_chart(data=top5_df, x='영화명(포맷)', y='audiCnt')

st.divider()

st.subheader("📋 전체 박스오피스 순위")
st.dataframe(display_df, use_container_width=True)
