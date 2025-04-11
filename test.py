import streamlit as st
import subprocess
import json
import pandas as pd

st.title("📡 재해 정보 API 데이터 수집")

# ✅ 사용자 입력으로 요청할 데이터 수 설정
disaster_number = st.number_input("재해 데이터 수 (numOfRows)", min_value=1, max_value=8300, value=100, step=100, key="disaster_rows")

if st.button("재해 정보 불러오기"):
    with st.spinner("재해 정보를 불러오는 중입니다..."):
        try:
            cmd = f"""
            curl -X 'GET' \
            'https://apis.data.go.kr/B552468/disaster_api01/getdisaster_api?serviceKey=XtjiWbPLxexBDUbR5RjQLsQ6M77Nrjt99CAFTlyV7CzsjfImD3yIqp7E9IGa%2Br2EFc%2F0FhabrGQ4AM%2Fc5uMOWg%3D%3D&pageNo=1&numOfRows={disaster_number}' \
            -H 'accept: */*'
            """
            output = subprocess.check_output(cmd, shell=True, text=True)
            data = json.loads(output)
            items = data['body']['items']['item']
            df_disaster = pd.DataFrame(items)

            st.success("✅ 재해 정보 수집 성공!")
            st.dataframe(df_disaster)

        except subprocess.CalledProcessError as e:
            st.error(f"❌ 명령어 실행 실패: {e}")
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON 파싱 오류: {e}")
        except KeyError as e:
            st.error(f"❌ 응답 JSON에서 키 오류 발생: {e}")

# ----------------------------- #

st.title("📰 사망 정보 API 데이터 수집")

news_number = st.number_input("사망 뉴스 수 (numOfRows)", min_value=1, max_value=2480, value=100, step=100, key="news_rows")

if st.button("사망 뉴스 불러오기"):
    with st.spinner("사망 뉴스를 불러오는 중입니다..."):
        try:
            cmd = f"""
            curl -X 'GET' \
            'https://apis.data.go.kr/B552468/news_api01/getNews_api01?serviceKey=XtjiWbPLxexBDUbR5RjQLsQ6M77Nrjt99CAFTlyV7CzsjfImD3yIqp7E9IGa%2Br2EFc%2F0FhabrGQ4AM%2Fc5uMOWg%3D%3D&pageNo=1&numOfRows={news_number}' \
            -H 'accept: */*'
            """
            output2 = subprocess.check_output(cmd, shell=True, text=True)
            data2 = json.loads(output2)
            items2 = data2['body']['items']['item']
            df_news = pd.DataFrame(items2)

            st.success("✅ 사망 뉴스 수집 성공!")
            st.dataframe(df_news)

        except subprocess.CalledProcessError as e:
            st.error(f"❌ 명령어 실행 실패: {e}")
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON 파싱 오류: {e}")
        except KeyError as e:
            st.error(f"❌ 응답 JSON에서 키 오류 발생: {e}")
