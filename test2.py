import streamlit as st
import pandas as pd
import subprocess
import json
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="재해정보 + Gemini 분석", layout="wide")
st.title("📡 Gemini로 재해 정보 API 데이터 분석")

# 1️⃣ Gemini API 키 입력 받기
st.sidebar.header("🔐 Gemini API 설정")
user_api_key = st.sidebar.text_input("Gemini API 키 입력", type="password")

if user_api_key:
    genai.configure(api_key=user_api_key)

    # ✅ 사용자 입력: 요청할 재해 데이터 수
    disaster_number = st.number_input(
        "재해 데이터 수 (numOfRows)", min_value=1, max_value=1000, value=100, step=100
    )

    # 🔘 버튼 클릭 시 동작
    if st.button("📥 재해 정보 불러오기"):
        with st.spinner("재해 정보를 불러오는 중입니다..."):
            try:
                SERVICE_KEY = "XtjiWbPLxexBDUbR5RjQLsQ6M77Nrjt99CAFTlyV7CzsjfImD3yIqp7E9IGa%2Br2EFc%2F0FhabrGQ4AM%2Fc5uMOWg%3D%3D"
                cmd = f"""
                curl -X 'GET' \
                'https://apis.data.go.kr/B552468/disaster_api01/getdisaster_api?serviceKey={SERVICE_KEY}&pageNo=1&numOfRows={disaster_number}' \
                -H 'accept: */*'
                """
                output = subprocess.check_output(cmd, shell=True, text=True)

                try:
                    data = json.loads(output)
                    items = data['body']['items']['item']
                    df_disaster = pd.DataFrame(items)

                    st.success("✅ 재해 정보 수집 성공!")
                    st.dataframe(df_disaster)

                    # 3️⃣ Gemini 분석 프롬프트 생성
                    preview = df_disaster.to_csv(index=False)
                    prompt = f"""
                    아래는 산업재해 API에서 가져온 일부 재해 정보입니다. 이 데이터를 보고 주요 특징이나 인사이트를 요약해주세요. 
                    (예: 빈도 높은 사고 유형, 특정 업종, 경향 등)

                    ```
                    {preview}
                    ```
                    """

                    model = genai.GenerativeModel("gemini-2.0-flash")
                    with st.spinner("Gemini가 데이터를 분석 중입니다..."):
                        response = model.generate_content(prompt)
                        st.subheader("Gemini 분석 결과")
                        st.markdown(response.text)

                except json.JSONDecodeError:
                    st.error("❌ JSON 파싱 오류! 응답 내용을 확인하세요.")
                    st.code(output)
                except KeyError as e:
                    st.error(f"❌ 응답 JSON에서 키 오류 발생: {e}")

            except subprocess.CalledProcessError as e:
                st.error(f"❌ 명령어 실행 실패: {e}")

else:
    st.warning("👈 좌측 사이드바에 Gemini API 키를 입력해주세요.")
