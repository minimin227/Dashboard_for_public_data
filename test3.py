import streamlit as st
import pandas as pd
import subprocess
import json
import google.generativeai as genai

# 사이드바에 Gemini API 키 입력 받기
st.sidebar.header("🔐 Gemini API 설정")
user_api_key = st.sidebar.text_input("Gemini API 키 입력", type="password")

if user_api_key:
    genai.configure(api_key=user_api_key)

    st.title("📥 사고유형별 산업재해 자료")

    # 사고유형 코드 선택
    ctgr03_dict = {
        "떨어짐": "11000001",
        "넘어짐": "11000002",
        "깔림.뒤집힘": "11000003",
        "부딪힘": "11000004",
        "물체에맞음": "11000005",
        "무너짐": "11000006",
        "끼임": "11000007",
        "절단베임찔림": "11000008",
        "감전": "11000009",
        "폭발파열": "11000010",
        "화재": "11000011",
        "불균형및무리한동작": "11000012",
        "이상온도물체접촉": "11000013",
        "화학물질누출접촉": "11000014",
        "산소결핍": "11000015",
        "빠짐익사": "11000016",
        "사업장내교통사고": "11000017",
        "체육행사": "11000018",
        "폭력행위": "11000019",
        "동물상해": "11000020",
        "기타": "11000021",
        "사업장외교통사고": "11000022",
        "업무상질병": "11000023",
        "진폐등": "11000024",
        "작업관련질병(뇌심등)": "11000025",
        "분류불능": "11000026"
    }

    selected_type = st.selectbox("사고 유형 선택", list(ctgr03_dict.keys()))
    ctgr03 = ctgr03_dict[selected_type]

    number = st.number_input(
        "링크 개수 (numOfRows)", min_value=1, max_value=1000, value=100, step=100
    )

    if st.button("📡 링크 수집 및 분석"):
        with st.spinner("링크를 불러오는 중입니다..."):
            try:
                SERVICE_KEY = "XtjiWbPLxexBDUbR5RjQLsQ6M77Nrjt99CAFTlyV7CzsjfImD3yIqp7E9IGa%2Br2EFc%2F0FhabrGQ4AM%2Fc5uMOWg%3D%3D"
                cmd = f"""
                curl -X 'GET' \
                'https://apis.data.go.kr/B552468/selectMediaList/getselectMediaList?serviceKey={SERVICE_KEY}&ctgr03={ctgr03}&pageNo=1&numOfRows={number}' \
                -H 'accept: */*'
                """
                output = subprocess.check_output(cmd, shell=True, text=True)

                try:
                    data = json.loads(output)
                    items = data['body']['items']['item']
                    df_news = pd.DataFrame(items)

                    st.success("링크수집 성공!")
                    st.dataframe(df_news)

                    # Gemini 프롬프트 생성
                    preview = df_news.head(5).to_csv(index=False)
                    prompt = f"""
                    아래는 '{selected_type}' 사고유형에 해당하는 산업재해 링크 리스트입니다.
                    이 리스트 내에서 숙박업종에 적용될만 한 자료를 찾아서 그 링크를 최대 3개 제시하고 요약해 주세요.

                    ```
                    {preview}
                    ```
                    """

                    model = genai.GenerativeModel("gemini-2.0-flash")
                    with st.spinner("Gemini가 분석 중입니다..."):
                        response = model.generate_content(prompt)
                        st.subheader("📑 Gemini 요약 결과")
                        st.markdown(response.text)

                except json.JSONDecodeError:
                    st.error("❌ JSON 파싱 오류. 응답 내용을 확인하세요.")
                    st.code(output)
                except KeyError as e:
                    st.error(f"❌ JSON 키 오류: {e}")

            except subprocess.CalledProcessError as e:
                st.error(f"❌ 명령 실행 실패: {e}")

else:
    st.warning("👈 Gemini API 키를 좌측에 입력하세요.")
