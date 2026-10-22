import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import urllib.parse # 네이버 검색 URL을 안전하게 만들기 위해 추가

# 페이지 기본 설정
st.set_page_config(page_title="일별 박스오피스", page_icon="🎬", layout="wide")
st.title("🎬 일별 박스오피스 조회")

# 1. 날짜 계산 및 달력 위젯
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst)
yesterday_kst = today_kst - timedelta(days=1)

selected_date = st.date_input(
    "조회할 날짜를 선택하세요",
    value=yesterday_kst.date(),
    max_value=yesterday_kst.date()
)

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
        
    if "boxOfficeResult" not in data or not data["boxOfficeResult"]["dailyBoxOfficeList"]:
        st.warning("📭 그날은 아직 집계 전이거나 데이터가 없습니다.")
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

numeric_columns = ['audiCnt', 'audiAcc', 'scrnCnt', 'rank', 'rankInten']
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col])

def format_rank_inten(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔽 {abs(val)}"
    else:
        return "-"

def format_movie_name(row):
    name = row['movieNm']
    if row['audiAcc'] >= 1000000:
        return f"{name} 🏆"
    return name

# 네이버 검색 URL을 만들어주는 함수
def make_naver_link(movie_name):
    # '영화명 + 영화' 로 검색어를 만들어 정확도를 높임 (예: 파묘 영화)
    query = urllib.parse.quote(movie_name + " 영화")
    return f"https://search.naver.com/search.naver?query={query}"

df['순위 증감'] = df['rankInten'].apply(format_rank_inten)
df['영화명(포맷)'] = df.apply(format_movie_name, axis=1)
# 검색 URL 컬럼 추가
df['네이버 검색'] = df['movieNm'].apply(make_naver_link) 

# 화면에 보여줄 컬럼 선택 (네이버 검색 포함)
display_df = df[['rank', '순위 증감', '영화명(포맷)', '네이버 검색', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
display_df.columns = ['순위', '순위 증감', '영화명', '네이버 검색', '개봉일', '관객수', '누적관객', '스크린수']
display_df = display_df.set_index('순위')


# 5. 화면에 그리기

st.subheader(f"🥇 {selected_date.strftime('%Y년 %m월 %d일')} 1위 영화")
top1_movie = df.iloc[0] 
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
st.bar_chart(data=top5_df, x='영화명(포맷)', y='audiCnt')

st.divider()

st.subheader("📋 전체 박스오피스")
with st.expander("👉 1위부터 10위까지 전체 순위표 열어보기", expanded=False):
    st.caption("※ 영화진흥위원회 API 정책상 매일 상위 10편의 데이터만 제공됩니다.")
    
    # st.column_config를 사용해 URL 텍스트를 클릭 가능한 예쁜 링크로 바꿈
    st.dataframe(
        display_df, 
        use_container_width=True,
        column_config={
            "네이버 검색": st.column_config.LinkColumn(
                "네이버 검색",
                display_text="🔍 검색하기" # 화면에는 주소 대신 이 글자가 보임
            )
        }
    )
