import pandas as pd 
import streamlit as st
import plotly.express as px
import os

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
st.title('재해정도 분석 대시보드')

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
selected_규모 = st.multiselect('규모 선택', 규모_list, default=[])
selected_대업종 = st.multiselect('대업종 선택', 대업종_list, default=[])

if selected_대업종:
    filtered_middle_industries = df[df['대업종'].isin(selected_대업종)]['중업종'].unique().tolist()
else:
    filtered_middle_industries = 중업종_list

selected_중업종 = st.multiselect('중업종 선택', filtered_middle_industries, default=['건설업'])
selected_발생형태 = st.multiselect('발생형태 선택', 발생형태_list, default=발생형태_list)
selected_년도 = st.multiselect('년도 선택', 년도_list, default=[])

# 필터 적용 함수
@st.cache_data
def filter_and_select_columns(df, selected_규모, selected_대업종, selected_중업종, selected_발생형태, selected_년도):
    filtered_df = df.copy()
    selected_columns = ['통계기준년', '규모', '대업종', '중업종', '발생형태']

    # ⬇️ 다중 선택 필터링 (선택 항목이 비어있지 않은 경우만 적용)
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

# 그룹화 기준이 없는 경우 에러 방지
if len(selected_columns) == 0:
    st.error("선택된 그룹화 기준이 없습니다. 적어도 하나의 기준을 선택하세요.")
else:
    # 그룹화 처리 (사용자가 필터링한 데이터를 사용)
    df_group = filtered_df.groupby(selected_columns).agg(
        위험지수=('재해정도_숫자', 'sum'),
        재해자수=('재해정도_숫자', 'count')
    ).reset_index()

    # 정규화된 위험지수 다시 계산
    df_group['정규화된_위험지수'] = (df_group['위험지수'] / total_risk) * 10000
    # df_group = df_group.sort_values(by='정규화된_위험지수', ascending=False)

st.subheader(selected_columns)

# df_group과 같은 구조로 근로자수 그룹화
# ✅ df_rate_melted를 df_group과 동일한 조건으로 필터링하려면
merge_keys = [col for col in selected_columns if col != '발생형태']

# merge_keys 기준으로 filtered_df에서 필터링된 조건만 추출
filtered_keys_df = filtered_df[merge_keys].drop_duplicates()

# df_rate_melted에 merge로 조건 적용
filtered_rate_df = pd.merge(df_rate_melted, filtered_keys_df, on=merge_keys, how='inner')

# 근로자수 그룹화
df_rate_melted_grouped = filtered_rate_df.groupby(merge_keys).sum(numeric_only=True).reset_index()
df_rate_melted_grouped = df_rate_melted_grouped[merge_keys + ['근로자수']]

merged = df_rate_melted_grouped.merge(df_group, on=merge_keys, how='outer')
# merged = merged.dropna()
merged['위험지수/근로자수'] = (merged['위험지수'] / merged['근로자수'])
merged['재해만인율'] = (merged['재해자수'] / merged['근로자수'])*10000
merged = merged.sort_values(by='위험지수/근로자수', ascending=False)
# 1중업종, 1발생형태 당 평균 정규화된_위험지수 계산
risk_average = 10000/df['중업종'].nunique()/df['발생형태'].nunique()

# 표
st.subheader(f"표 (1 중업종, 1 발생형태 당 평균 정규화된_위험지수 = {risk_average:.2f})")
st.dataframe(df_group.head(100).reset_index(drop = True))
# st.dataframe(df_rate_melted_grouped.head(100).reset_index(drop = True))
st.dataframe(merged.head(100).reset_index(drop = True))
# st.dataframe(merged.drop(columns=['위험지수']).head(100).reset_index(drop = True))

# 그래프 설정 옵션 제공
st.subheader(f"그래프 설정")
columns_for_x_and_color = ['없음', '발생형태', '대업종', '중업종', '규모', '통계기준년']
metrics = ['위험지수/근로자수', '정규화된_위험지수', '재해자수', '재해만인율']
graph_types = ['Bar', 'Line', 'Scatter']

metric = st.selectbox('그래프를 표시할 통계 값 선택', metrics)
x_axis = st.selectbox('X축 선택', columns_for_x_and_color[1:], index=0)  # X축은 '없음' 선택 옵션 없이 설정
color_axis = st.selectbox('Color 기준 선택', columns_for_x_and_color, index=1)
graph_type = st.selectbox('그래프 유형 선택', graph_types, index=0)

# 그래프 그리기 버튼
if st.button('그래프 그리기'):
    # 그래프를 그릴 때는 merged를 사용해야 함
    if x_axis == '규모':
        # 규모 열이 선택되었을 때는 scale_mapping 순서대로 정렬
        merged['규모_숫자'] = merged['규모'].map(scale_mapping)
        merged = merged.sort_values(by='규모_숫자')
    
    # 그래프 그리기
    if graph_type == 'Bar':
        if color_axis == '없음':
            fig = px.bar(merged, x=x_axis, y=metric, title=f'{metric} Bar 그래프')
        else:
            fig = px.bar(merged, x=x_axis, y=metric, color=color_axis, title=f'{metric} Bar 그래프')
            
    elif graph_type == 'Line':
        if color_axis == '없음':
            fig = px.line(merged, x=x_axis, y=metric, title=f'{metric} Line 그래프')
        else:
            fig = px.line(merged, x=x_axis, y=metric, color=color_axis, title=f'{metric} Line 그래프')
            
    elif graph_type == 'Scatter':
        if color_axis == '없음':
            fig = px.scatter(merged, x=x_axis, y=metric, title=f'{metric} Scatter 그래프')
        else:
            fig = px.scatter(merged, x=x_axis, y=metric, color=color_axis, title=f'{metric} Scatter 그래프')
        
    st.plotly_chart(fig)


# 중업종 링크 표시 기능
if selected_중업종:
    filtered_links = 중업종리스트_df[중업종리스트_df['중업종'].isin(selected_중업종)]

    if not filtered_links.empty:
        st.subheader("선택한 중업종의 안전보건관리체계 구축 가이드")

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



# 📂 발생형태 CSV 파일 경로 설정
csv_folder = os.path.join(os.getcwd(), '발생형태')  # 현재 디렉토리 아래 '발생형태' 폴더를 경로로 설정


# 발생형태 버튼 표시 함수 (정렬된 순서대로 표시)
def show_발생형태_buttons(sorted_발생형태_list):
    selected_file = None

    for 형태 in sorted_발생형태_list:
        if st.button(형태):
            selected_file = 형태
    return selected_file

# 📁 CSV 파일 불러오기 함수
def load_csv_file(file_name):
    file_path = os.path.join(csv_folder, f"{file_name}.csv")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            return df
        except Exception as e:
            st.error(f"파일을 불러오는 중 에러가 발생했습니다: {e}")
            return None
    else:
        st.warning(f"'{file_name}.csv' 파일을 찾을 수 없습니다.")
        return None


# ✅ 중업종 선택 및 발생형태 버튼 표시
if selected_중업종:
    filtered_df = merged[merged['중업종'].isin(selected_중업종)]

    sorted_발생형태_list = (
        filtered_df.sort_values(by='위험지수/근로자수', ascending=False)['발생형태']
        .dropna().unique().tolist()
    )

    st.subheader("선택한 중업종 관련 발생형태 예방 정보 링크")

    selected_발생형태_file = show_발생형태_buttons(sorted_발생형태_list)

    if selected_발생형태_file:
        st.subheader(f"{selected_발생형태_file}에 대한 교육 자료 링크")
        csv_df = load_csv_file(selected_발생형태_file)

        if csv_df is not None:
            st.dataframe(csv_df)