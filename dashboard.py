import pandas as pd 
import streamlit as st
import plotly.express as px
import os
import google.generativeai as genai
import PyPDF2  # ✅ PDF 파일 처리 라이브러리 필요
import subprocess
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 데이터 집계 함수 (캐싱)
@st.cache_data
def load_data():
    data_folder = 'Data'
    df_2023 = pd.read_excel(os.path.join(data_folder, '2023_산업재해통계_마이크로데이터_merged.xlsx'))
    df_2022 = pd.read_csv(os.path.join(data_folder, '2022_산업재해통계_마이크로데이터_merged.csv'))
    df_2021 = pd.read_csv(os.path.join(data_folder, '2021_산업재해통계_마이크로데이터_merged.csv'))
    중업종리스트_df = pd.read_csv(os.path.join(data_folder, '중업종리스트.csv'))
    
    df = pd.concat([df_2023, df_2022, df_2021], axis=0, ignore_index=True)
    df['통계기준년'] = df['통계기준년월'].astype(str).str[:4].astype(int)
    df['대업종'] = df['대업종'].str.replace(r'\s+', '', regex=True)
    df['대업종'] = df['대업종'].str.replace('전기·가스·증기및수도사업', '전기·가스·증기·수도사업')
    df['중업종'] = df['중업종'].str.replace('출판·인쇄·제본또는인쇄물가공업', '출판·인쇄·제본업')
    df['중업종'] = df['중업종'].str.replace('전기·가스·증기및수도사업', '전기·가스·증기·수도사업')
    df['규모'] = df['규모'].str.replace('10~19인', '10~29인')
    df['규모'] = df['규모'].str.replace('20~29인', '10~29인')

    severity_mapping = {
        '사망자': 400,
        '6개월 이상': 200.0,
        '91~180일': 135.5,
        '29~90일': 59.5,
        '15~28일': 21.5,
        '8~14일': 11,
        '4~7일': 5.5
    }

    df['재해정도_숫자'] = df['재해정도'].map(severity_mapping)
   
    # 근로자수 데이터 추가
    df_rate = pd.read_csv(os.path.join(data_folder, '전체_재해_현황_및_분석규모별_산업별_중분류.csv'))
    df_rate = df_rate[df_rate['중업종'] != '소계']
    df_rate = df_rate[df_rate['항목'] == '근로자수 (명)']
    # 중업종 값 정리
    df_rate['중업종'] = df_rate['중업종'].str.replace(' ', '', regex=True)
    df_rate['중업종'] = df_rate['중업종'].str.replace('전기·가스·증기및수도사업', '전기·가스·증기·수도사업')
    # 대업종 값 정리 (공백 제거 부터)
    df_rate['대업종'] = df_rate['대업종'].str.replace(r'\s+', '', regex=True)
    df_rate['대업종'] = df_rate['대업종'].replace({
        '전기·가스·증기및수도사업': '전기·가스·증기·수도사업',
        '운수·창고및통신업': '운수·창고·통신업',
    })
    # 항목 열 제거
    df_rate = df_rate.drop(columns=['항목'])
    # 규모 관련 열 목록 정의
    scale_columns = ['5인 미만', '5~9인', '10~29인', '30~49인', '50~99인',
                    '100~299인', '300~499인', '500~999인', '1000인 이상']
    # melt를 사용해 '규모'라는 이름으로 그룹화
    df_rate_melted = df_rate.melt(
        id_vars=['통계기준년', '대업종', '중업종'],
        value_vars=scale_columns,
        var_name='규모',
        value_name='근로자수'
    )
    # 규모 값 정리, 근로자수 형태 변환
    df_rate_melted['규모'] = df_rate_melted['규모'].str.replace('1000인 이상', '1,000인 이상')
    df_rate_melted['근로자수'] = pd.to_numeric(df_rate_melted['근로자수'], errors='coerce')

    return df, 중업종리스트_df, df_rate_melted

# 데이터 로딩
df, 중업종리스트_df, df_rate_melted = load_data()

# Streamlit 대시보드 설정
st.title('재해현황 대시보드')

# 규모 매핑
scale_mapping = {
    '5인 미만': 1,
    '5~9인': 2,
    '10~29인': 3,
    '30~49인': 4,
    '50~99인': 5,
    '100~299인': 6,
    '300~499인': 7,
    '500~999인': 8,
    '1,000인 이상': 9  # Assuming 1,000 as the minimum for this range
}

규모_list = sorted(df['규모'].unique().tolist(), key=lambda x: scale_mapping.get(x, 0))  # 정렬 추가
대업종_list = df['대업종'].unique().tolist()
중업종_list = df['중업종'].unique().tolist()
발생형태_list = df['발생형태'].unique().tolist()
년도_list = df['통계기준년'].unique().tolist()

# 사용자 입력 multiselect
# 규모 선택
select_all_규모 = st.checkbox("전체 규모 선택")
selected_규모 = st.multiselect(
    '규모 선택', 규모_list, default=규모_list if select_all_규모 else []
)

# 대업종 선택
select_all_대업종 = st.checkbox("전체 대업종 선택")
selected_대업종 = st.multiselect(
    '대업종 선택', 대업종_list, default=대업종_list if select_all_대업종 else []
)

# 중업종 필터 (대업종에 따라 중업종 필터링)
if selected_대업종:
    filtered_middle_industries = df[df['대업종'].isin(selected_대업종)]['중업종'].unique().tolist()
else:
    filtered_middle_industries = 중업종_list

# 중업종 선택
select_all_중업종 = st.checkbox("전체 중업종 선택")
selected_중업종 = st.multiselect(
    '중업종 선택', filtered_middle_industries,
    default=filtered_middle_industries if select_all_중업종 else ['건설업']
)

# 발생형태 선택
select_all_발생형태 = st.checkbox("전체 발생형태 선택")
selected_발생형태 = st.multiselect(
    '발생형태 선택', 발생형태_list,
    default=발생형태_list if select_all_발생형태 else []
)

# 연도 선택
select_all_년도 = st.checkbox("전체 연도 선택")
selected_년도 = st.multiselect(
    '년도 선택', 년도_list,
    default=년도_list if select_all_년도 else []
)

# 필터 적용 함수
@st.cache_data
def filter_and_select_columns(df, selected_규모, selected_대업종, selected_중업종, selected_발생형태, selected_년도):
    filtered_df = df.copy()
    selected_columns = ['통계기준년', '규모', '대업종', '중업종', '발생형태']

    # 다중 선택 필터링 (선택 항목이 비어있지 않은 경우만 적용)
    if selected_규모:
        filtered_df = filtered_df[filtered_df['규모'].isin(selected_규모)]
    else:
        selected_columns.remove('규모')

    if selected_대업종:
        filtered_df = filtered_df[filtered_df['대업종'].isin(selected_대업종)]
    else:
        selected_columns.remove('대업종')

    if selected_중업종:
        filtered_df = filtered_df[filtered_df['중업종'].isin(selected_중업종)]
    else:
        selected_columns.remove('중업종')

    if selected_발생형태:
        filtered_df = filtered_df[filtered_df['발생형태'].isin(selected_발생형태)]
    else:
        selected_columns.remove('발생형태')

    if selected_년도:
        filtered_df = filtered_df[filtered_df['통계기준년'].isin(selected_년도)]
    else:
        selected_columns.remove('통계기준년')

    return filtered_df, selected_columns


# 필터링 및 그룹화 기준 설정 (df: 원본 데이터 - 필터링 후 동적 그룹화용)
filtered_df, selected_columns = filter_and_select_columns(
    df, selected_규모, selected_대업종, selected_중업종, selected_발생형태, selected_년도
)

# 전체 위험지수 합계 계산
total_risk = df['재해정도_숫자'].sum()

# 그룹화 및 정규화된 위험지수 계산
try:
    if len(selected_columns) == 0:
        st.warning("선택된 필터가 없어 그룹화할 수 없습니다.")
        df_group = pd.DataFrame()
    else:
        df_group = filtered_df.groupby(selected_columns).agg(
            위험지수=('재해정도_숫자', 'sum'),
            재해자수=('재해정도_숫자', 'count')
        ).reset_index()

        df_group['정규화된_위험지수'] = (df_group['위험지수'] / total_risk) * 10000

        # st.subheader("그룹화된 재해 통계")
        # st.dataframe(df_group.head(100).reset_index(drop=True))

except Exception as e:
    st.error(f"그룹화 중 오류 발생: {e}")
    df_group = pd.DataFrame()


# df_group과 같은 구조로 근로자수 그룹화
# df_rate_melted를 df_group과 동일한 조건으로 필터링하려면
try:
    # 그룹 키 지정
    merge_keys = [col for col in selected_columns if col != '발생형태']

    if not df_group.empty:
        # merge를 위한 키만 추출
        filtered_keys_df = filtered_df[merge_keys].drop_duplicates()
        filtered_rate_df = pd.merge(df_rate_melted, filtered_keys_df, on=merge_keys, how='inner')

        # 근로자수 그룹화
        df_rate_melted_grouped = filtered_rate_df.groupby(merge_keys).sum(numeric_only=True).reset_index()
        df_rate_melted_grouped = df_rate_melted_grouped[merge_keys + ['근로자수']]

        # 병합
        merged = df_rate_melted_grouped.merge(df_group, on=merge_keys, how='outer')

        # 파생 지표 계산
        merged['위험지수/근로자수'] = merged['위험지수'] / merged['근로자수']
        merged['재해만인율'] = (merged['재해자수'] / merged['근로자수']) * 10000
        merged = merged.sort_values(by='위험지수/근로자수', ascending=False)

        st.subheader("재해 통계")
        st.dataframe(merged.head(100).reset_index(drop=True))
    else:
        st.warning("병합할 그룹 데이터가 없습니다.")
        merged = pd.DataFrame()

except Exception as e:
    st.error(f"병합 또는 파생 변수 계산 중 오류 발생: {e}")
    merged = pd.DataFrame()

# 1중업종, 1발생형태 당 평균 정규화된_위험지수 계산
risk_average = 10000/df['중업종'].nunique()/df['발생형태'].nunique()

# 그래프 설정 옵션 제공
st.subheader(f"그래프 설정")
columns_for_x_and_color = ['없음', '발생형태', '대업종', '중업종', '규모', '통계기준년']
metrics = ['위험지수/근로자수', '정규화된_위험지수', '재해자수', '재해만인율']
graph_types = ['Bar',
                #  'Line', 
                #  'Scatter'
                ]

metric = st.multiselect('그래프를 표시할 통계 값 선택', metrics, default=['위험지수/근로자수'])
x_axis = st.selectbox('X축 선택', columns_for_x_and_color[1:], index=0)  # X축은 '없음' 선택 옵션 없이 설정
color_axis = st.selectbox('Color 기준 선택', columns_for_x_and_color, index=1)
graph_type = st.selectbox('그래프 유형 선택', graph_types, index=0)

# 그래프를 그릴 때는 merged를 사용해야 함
if x_axis == '규모':
    # 규모 열이 선택되었을 때는 scale_mapping 순서대로 정렬
    merged['규모_숫자'] = merged['규모'].map(scale_mapping)
    merged = merged.sort_values(by='규모_숫자')
    
# # 그래프 그리기
# if graph_type == 'Bar':
#     if color_axis == '없음':
#         fig = px.bar(merged, x=x_axis, y=metric, title=f'{metric} Bar 그래프')
#     else:
#         fig = px.bar(merged, x=x_axis, y=metric, color=color_axis, title=f'{metric} Bar 그래프')
            
# st.plotly_chart(fig)

# Subplot 방식 그래프

if len(metric) >= 1: 
    rows = len(metric)
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.1,
        subplot_titles=metric
    )

    for i, m in enumerate(metric):
        if color_axis == '없음':
            # 색상 기준 없음
            fig.add_trace(
                go.Bar(x=merged[x_axis], y=merged[m], name=m),
                row=i+1, col=1
            )
        else:
            # 색상 기준이 있을 경우: 각 카테고리별 색상 표현
            for category in merged[color_axis].dropna().unique():
                df_filtered = merged[merged[color_axis] == category]
                fig.add_trace(
                    go.Bar(
                        x=df_filtered[x_axis],
                        y=df_filtered[m],
                        name=str(category),
                        showlegend=(i == 0)  # 첫 row에만 범례 표시
                    ),
                    row=i+1, col=1
                )
        fig.update_yaxes(title_text=m, row=i+1, col=1)
    barmode = st.radio(
    "막대그래프 표시 방식 선택",
    ("group", "overlay"),
    index=0
    )
    fig.update_layout(height=500 * rows, title_text=f"{x_axis} 기준 지표별 Subplot 비교", barmode=barmode)
    st.plotly_chart(fig)
else:
    st.warning("1개 이상의 지표를 선택해주세요.")



# Gemini API 키 입력 받기
st.sidebar.header("Gemini API 설정")
user_api_key = st.sidebar.text_input("Gemini API 키 입력", type="password")

if user_api_key:
    genai.configure(api_key=user_api_key)

    st.subheader("사고유형별 맞춤형 교육 자료")

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
    # 상위 3개 발생형태 자동 선택
    top3_발생형태 = (
        merged['발생형태']
        .value_counts()
        .head(3)
        .index
        .tolist()
    )

    # 멀티셀렉트로 사용자 수정 가능
    selected_types = st.multiselect(
        "사고 유형 선택 (다중 선택 가능)",
        options=list(ctgr03_dict.keys()),
        default=[t for t in ctgr03_dict if t in top3_발생형태]
    )

    number = st.number_input(
        "링크 개수 (numOfRows)", min_value=1, max_value=1000, value=100, step=100
    )

    if st.button("📡 선택된 모든 유형에 대해 링크 수집 및 분석 실행"):
        SERVICE_KEY = "XtjiWbPLxexBDUbR5RjQLsQ6M77Nrjt99CAFTlyV7CzsjfImD3yIqp7E9IGa%2Br2EFc%2F0FhabrGQ4AM%2Fc5uMOWg%3D%3D"

        for selected_type in selected_types:
            ctgr03 = ctgr03_dict[selected_type]

            st.markdown(f"---\n### **{selected_type}** 자료 요약")

            try:
                cmd = f"""
                curl -X 'GET' \
                'https://apis.data.go.kr/B552468/selectMediaList/getselectMediaList?serviceKey={SERVICE_KEY}&ctgr03={ctgr03}&pageNo=1&numOfRows={number}' \
                -H 'accept: */*'
                """
                output = subprocess.check_output(cmd, shell=True, text=True)

                try:
                    data = json.loads(output)
                    items = data['body']['items']['item']
                    df_links = pd.DataFrame(items)

                    # st.success(f"{selected_type} 링크 수집 성공")
                    # st.dataframe(df_links)

                    preview = df_links.head(5).to_csv(index=False)
                    중업종 = ", ".join(selected_중업종) if 'selected_중업종' in locals() and selected_중업종 else "전체 업종"

                    prompt = f"""
                    아래는 '{selected_type}' 사고유형에 해당하는 산업재해 링크 리스트입니다.
                    이 리스트 내에서 {중업종}에 적용될만 한 자료를 찾아서 그 링크를 가장 적합한 1개만 제시하고 요약해 주세요.

                    ```
                    {preview}
                    ```
                    """

                    model = genai.GenerativeModel("gemini-2.0-flash")
                    with st.spinner(f"Gemini가 {selected_type} 사고유형을 분석 중입니다..."):
                        response = model.generate_content(prompt)
                        # st.subheader(f"{selected_type} 자료 요약")
                        st.markdown(response.text)

                except json.JSONDecodeError:
                    st.error(f"❌ JSON 파싱 오류 ({selected_type})")
                    st.code(output)
                except KeyError as e:
                    st.error(f"❌ JSON 키 오류 ({selected_type}): {e}")

            except subprocess.CalledProcessError as e:
                st.error(f"❌ 명령 실행 실패 ({selected_type}): {e}")


    st.subheader("안전보건관리 체크리스트 만들기")
    if st.button("체크리스트 생성하기"): 
        try:
            # 1. merged DataFrame → CSV 문자열
            preview1 = merged.to_csv(index=False)

            # 2. PDF 파일을 텍스트로 변환
            pdf_path = os.path.join("Data", "[2022-산업안전본부-105]_[첨부2] 소규모 사업장 안전보건관리체계 구축지원 가이드_내지.pdf")
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pdf_text = ""
                for page in reader.pages[:92]:
                    pdf_text += page.extract_text()
            # 2. PDF 파일을 텍스트로 변환2
            pdf_path2 = os.path.join("Data", "산업안전보건법(법률)(제19591호)(20240517).pdf")
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pdf_text2 = ""
                for page in reader.pages[:92]:
                    pdf_text2 += page.extract_text()
            # 3. Gemini 프롬프트 구성
            중업종 = ", ".join(selected_중업종) if selected_중업종 else "전체 업종"
            prompt = f"""
            선택된 중업종은 다음과 같습니다: **{중업종}**

            아래는 해당 업종에서 발생한 산업재해 통계이며, 발생형태별로 위험지수/근로자수 등의 지표를 포함합니다.
            또한, 소규모 사업장을 위한 안전보건관리체계 구축 가이드와 법령 요약본도 함께 제공됩니다.

            ---

            **요청사항**:

            선택한 중업종의 사업장에서 **중대재해 예방을 위해 반드시 갖춰야 할 안전보건관리 체크리스트**를 작성해 주세요.

            - 각 규모, 중업종에서 **위험지수/근로자수 지표가 선택한 규모, 중업종별 평균 위험지수/근로자수 지표보다 높은 발생형태**를 기준으로 위험요소별 맞춤형 점검항목을 작성해 주세요.
            - 동일한 발생형태에 해당하는 항목들은 **점검항목 열을 병합한 형태**로 작성해 주세요. (`rowspan` 속성 사용)
            - **점검내용**은 **법령 요약** 지침을 따르고, 만약 지침 내용이 없다면 선택한 **중업종**과 **점검항목**이 연관성 있게 **점검내용**을 작성해주세요. 
            - 제작 완료된 **점검내용**은 (법령 제OO조)로 명시하지 않습니다.
            - 표는 반드시 **HTML `<table>` 형식**으로 출력해 주세요. 마크다운 표(`|` 형태)는 절대 사용하지 마세요.
            - **점검상태**는 `<select>`나 `<input>` 태그 없이, 반드시 `"미흡 / 보통 / 양호"`라는 **텍스트로만** 표기해 주세요.
            - HTML 표 바로 위에는 다음 문장을 포함해 주세요:  
            **{중업종}에서 위험지수가 높은 사고를 안전하게 예방합니다.**
            - 아래는 참고용 형식 예시입니다. 실제 내용은 중업종과 위험형태에 따라 자유롭게 구성해 주세요.

            예시:
            <table border="1">
            <thead>
                <tr>
                <th>점검항목</th>
                <th>점검내용</th>
                <th>점검상태</th>
                <th>비고</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                <td rowspan="2">넘어짐 재해 예방</td>
                <td>작업장 바닥은 미끄럼 방지 처리가 되어 있나요?</td>
                <td>미흡 / 보통 / 양호</td>
                <td></td>
                </tr>
                <tr>
                <td>작업 통로는 정리정돈이 잘 되어 있나요?</td>
                <td>미흡 / 보통 / 양호</td>
                <td></td>
                </tr>
            </tbody>
            </table>

            ---

            **재해 통계 (중업종: {중업종})**

            ```
            {preview1}
            ```

            안전보건관리 가이드 요약:            
            ```
            {pdf_text}
            ```
            법령 요약:
            ```
            {pdf_text2}
            ```
            """
            # {pdf_text[:20000]}  # 최대 약 2,000자만 발췌
            model = genai.GenerativeModel("gemini-2.0-flash")
            with st.spinner("Gemini가 데이터를 분석 중입니다..."):
                response = model.generate_content(prompt)
                # st.subheader("Gemini 분석 결과: 체크리스트 제안")
                
                st.markdown(response.text, unsafe_allow_html=True) # unsafe_allow_html=True 추가
        except Exception as e:
            st.error(f"❌ 오류 발생: {e}")
                
                
    st.subheader(f"사망 뉴스 수집")
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

                st.success("사망 뉴스 수집 성공!")
                # st.dataframe(df_news)

                preview2 = df_news.to_csv(index=False)
                today_str = datetime.today().strftime("%Y. %m. %d. (%a)")
                prompt = f"""
                {preview2}에서 오늘 날짜 기준으로 최근 일주일 동안 발생한 사망사고를 요약하고, 사고유형별로 구분하여 간결히 정리해 주세요.
                {preview2} content열에 <br />2025. 4. 18. (금), 14:56경<br /><br /> 형식을 날짜가 표시되어 있습니다.
                오늘은 {today_str}입니다.
                """
                # {pdf_text[:20000]}  # 최대 약 2,000자만 발췌
                model = genai.GenerativeModel("gemini-2.0-flash")
                with st.spinner("Gemini가 데이터를 분석 중입니다..."):
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            except subprocess.CalledProcessError as e:
                st.error(f"❌ 명령어 실행 실패: {e}")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 파싱 오류: {e}")
            except KeyError as e:
                st.error(f"❌ 응답 JSON에서 키 오류 발생: {e}")
            except Exception as e:
                st.error(f"❌ 예외 발생: {e}")                    

else:
    st.warning("👈 좌측 사이드바에 Gemini API 키를 입력해주세요.")

# 중업종 링크 표시 기능
if selected_중업종:
    filtered_links = 중업종리스트_df[중업종리스트_df['중업종'].isin(selected_중업종)]

    if not filtered_links.empty:
        st.subheader(f"안전보건관리체계 구축 가이드")

        def make_hyperlink(link):
            if pd.notna(link):
                return f"[링크]({link})"
            else:
                return "없음" 

        for idx, row in filtered_links.iterrows():
            st.markdown(f"#### {row['중업종']}")
            st.markdown(f"- 링크 1: {make_hyperlink(row['링크1'])}")
            st.markdown(f"- 링크 2: {make_hyperlink(row['링크2'])}")
            st.markdown(f"- 링크 3: {make_hyperlink(row['링크3'])}")
    else:
        st.warning("선택한 중업종에 대한 링크 정보가 없습니다.")       