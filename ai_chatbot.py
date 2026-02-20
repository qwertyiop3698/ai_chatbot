# google에서 제공하는 LLM API를 사용하기
# google ai studio 키발급
# 우리의 챗봇을 streamlit cloud에 배포할 예정. 하지만 이곳은 .env를 설정할 수 없음.
# 그래서 streamlit에서 제공하는 비밀값을 저장하는 속성 secrets을 활용 [secrets에 등록된 닶들은 .streamlit 폴더 안에 secrets.toml파일로 등록]
import streamlit as st
if "GEMINI_API_KEY" in st.secrets:
    api_key=st.secrets["GEMINI_API_KEY"]
from google import genai
# 요청 사용자 객체
client = genai.Client(api_key=api_key)

# 응답제어를 위한 하이퍼 파라미터 설정
from google.genai import types
config=types.GenerateContentConfig(
    max_output_tokens=10000,
    response_mime_type='text/plain',
    # system_instruction='넌 만물박사야 최대 100글자 이내로 설명해',
    # system_instruction='넌 모든 대답을 개조식으로 해'
    system_instruction= '넌 아이디어뱅크야 아이디어 위주로 설명하고, 여러가지 다양한 아이디어를 100글자 이내로 제시해'
)
# 답변에 참고할 데이터를 리턴해주는 함수 만들기
import datetime
def get_today():
    ''' 이 함수는 오늘의 날짜에 대한 답변에 사용됩니다. '''
    now=datetime.datetime.now()
    return {'location':'korea seoul'}


# '질문'을 파라미터로 받아서 GENAI로 응답한 글씨를 리턴해주는 기능함수 만들기
def get_ai_response(question):
    response=client._models.generate_content(
        model="gemini-3-flash-preview",
        # model="gemini-2.5-flash",
        contents=question,
        # 모델의 응답방법을 설정하기 - 하이퍼 파라미터 설정
        config=config
    )
    return response.text
    


# 3. 채팅 UI만들기

# 페이지 기본 설정 -- 브라우저의 탭 영역에 표시되는 내용.
st.set_page_config(
    page_title='AI 아이디어 연금술사',
    page_icon='./logo/logo.png'
    )
# HEADER 영역 (레이아웃 : 이미지 + 제목 영역 가로 배치)
col1,col2=st.columns([1.2,4.8])

with col1:
    st.image('./logo/logo.png',width=200)

with col2:
    # 제목(h1) + 서브 안내 글씨(p) [색상을 다르게 하려면 HTML코드 구현]
    st.markdown(
        """
            <h1 style='margin-bottom:0;'>아이디어 연금술사</h1>
            <p style='margin-top:0; color=gray'>이 챗봇은 아이디어를 만들어내는 AI 연금술사 입니다.<p/>
        """,
        unsafe_allow_html=True,
    )
st.markdown("---")

# 채팅 UI구현
# messages라는 이름의 변수가 session_state에 존재하는지 확인 후 없으면 첫 문자 지정
if "messages" not in st.session_state:
    st.session_state.messages=[
        {'role':'assistant','content':'어떤 아이디어를 제공 해드릴까요?'}
    ]

# session_state에 저장된 "messages"의 메세지들을  채팅 UI로 그려내기
for msg in st.session_state.messages:
    st.chat_message(msg['role']).write(msg['content'])

# 사용자 채팅메세지를 입력 받아 session_state에 저장하고 UI 갱신
question=st.chat_input('아이디어 구상 시작하기')
if question:
    question=question.replace('\n','  \n')
    st.session_state.messages.append({'role':'user','content':question})
    st.chat_message('user').write(question)

    # 응답 - AI 응답요구 기능 호출.. 대기 시간동안 보여줄 스피너 progress
    with st.spinner('아이디어 공장 가동중.'):
        response=get_ai_response(question)
        st.session_state.messages.append({'role':'assistant','content':response})
        st.chat_message('assistant').write(response)

# ===================================================================================================

# streamlit 웹앱 배포
# 1. streamlit community cloud 배포
# 2. GITHUB에 프로젝트를 업로드
# 3. new app을 통해 앱을 만들어 GITHUB저장소와 연결
# 4. 자동 배포됨.
# from google import genai 모듈 에러
# streamlit cloud에서 자동으로 설치하도록. requirements.txt 문서에 설치할 모듈 업로드
















