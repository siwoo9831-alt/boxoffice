import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 페이지 기본 설정
st.set_page_config(page_title="일별 박스오피스", page_icon="🎬", layout="wide")

st.title("🎬 어제의 박스오피스")

# 1. 날짜 계산 (한국 시간 기준 '어제')
# 배포된 서버의 시간(UTC 등)과 무관하게 항상 한국 시간을 기준으로 합니다.
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst)
yesterday_kst = today_kst - timedelta(days=1)
target_dt = yesterday_kst.strftime('%Y%m%d') # API 요청용 포맷 (YYYYMMDD)
display_dt = yesterday_kst.strftime('%Y년 %m월 %d일') # 화면 출력용 포맷

st.write(f"**기준일:** {display_dt}")
st.divider()

# 2. 인증키 불러오기
# st.secrets를 사용해 Streamlit Cloud의 Secrets 설정에서 API 키를 가져옵니다.
if "KOBIS_KEY" not in st.secrets:
    st.error("🔑 API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정에 KOBIS_KEY를 추가해 주세요.")
    st.stop() # 실행 중단

API_KEY = st.secrets["KOBIS_KEY"]

# 3. KOBIS API 데이터 요청
url = "http://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": API_KEY,
    "targetDt": target_dt
}

try:
    response = requests.get(url, params=params)
    # HTTP 요청 자체가 실패한 경우
    if response.status_code != 200:
        st.error(f"📡 서버 응답에 문제가 있습니다. (상태 코드: {response.status_code}) 잠시 후 다시 시도해 주세요.")
        st.stop()
        
    data = response.json()
    
    # 인증키 오류 등으로 인해 정상 데이터 대신 faultInfo 상자가 온 경우
    if "faultInfo" in data:
        fault_message = data["faultInfo"].get("message", "알 수 없는 오류")
        st.error(f"❌ API 요청 오류가 발생했습니다. 메시지: {fault_message}\n\n인증키가 유효한지, 일일 요청 한도를 초과하지 않았는지 확인해 주세요.")
        st.stop()
        
    # 데이터가 정상적으로 수신되었으나 목록이 비어있는 경우 (아직 집계가 안 되었거나 데이터가 없는 날)
    if "boxOfficeResult" not in data or not data["boxOfficeResult"]["dailyBoxOfficeList"]:
        st.warning("📭 해당 날짜의 박스오피스 데이터가 아직 없거나 비어 있습니다.")
        st.stop()

    movie_list = data["boxOfficeResult"]["dailyBoxOfficeList"]

except requests.exceptions.RequestException as e:
    st.error(f"🌐 인터넷 연결에 문제가 발생했습니다. 에러: {e}")
    st.stop()
except ValueError:
    st.error("🧩 API 응답을 해석할 수 없습니다. (JSON 변환 실패) 영화진흥위원회 서버 상태를 확인해 주세요.")
    st.stop()

# 4. 데이터 가공 (Pandas DataFrame)
df = pd.DataFrame(movie_list)

# KOBIS API의 숫자 데이터는 문자열('100')로 오기 때문에 진짜 숫자(int)로 변환해 줍니다.
numeric_columns = ['audiCnt', 'audiAcc', 'scrnCnt', 'rank']
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col])

# 필요한 컬럼만 선택하고, 한국어로 이름을 바꿉니다.
display_df = df[['rank', 'movieNm', 'openDt', 'audiCnt', 'audiAcc', 'scrnCnt']].copy()
display_df.columns = ['순위', '영화명', '개봉일', '관객수', '누적관객', '스크린수']

# 순위를 기준으로 정렬하고 인덱스를 숨기기 위해 순위를 인덱스로 설정합니다.
display_df = display_df.set_index('순위')


# 5. 화면에 그리기

# 1위 영화 하이라이트 (지표 카드 3장)
st.subheader("🥇 1위 영화 하이라이트")
top1_movie = df.iloc[0] # 첫 번째 줄이 1위 영화입니다.
st.markdown(f"### **{top1_movie['movieNm']}**")

col1, col2, col3 = st.columns(3)
with col1:
    # {:,} 포맷을 사용해 천 단위마다 콤마(,)를 찍어줍니다.
    st.metric(label="일일 관객수", value=f"{top1_movie['audiCnt']:,}명")
with col2:
    st.metric(label="누적 관객수", value=f"{top1_movie['audiAcc']:,}명")
with col3:
    st.metric(label="스크린수", value=f"{top1_movie['scrnCnt']:,}개")

st.divider()

# 관객수 상위 5편 막대그래프
st.subheader("📊 관객수 TOP 5")
top5_df = df.head(5)
# x축은 영화명, y축은 관객수로 설정하여 막대 그래프를 그립니다.
st.bar_chart(data=top5_df, x='movieNm', y='audiCnt')

st.divider()

# 전체 표 보여주기
st.subheader("📋 전체 박스오피스 순위")
st.dataframe(display_df, use_container_width=True)
