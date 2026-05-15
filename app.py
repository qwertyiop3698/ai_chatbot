import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from google import genai
from google.genai import types


DEFAULT_MODEL_NAME = "gemini-3-flash-preview"
WELCOME_MESSAGE = "안녕하세요. 질문과 프롬프트 조건을 바꿔가며 AI 답변 차이를 실험해보세요."

ROLE_PROMPTS = {
    "기본 도우미": "너는 사용자의 질문에 균형 있고 명확하게 답하는 AI 도우미야.",
    "초보자 튜터": "너는 초보자를 가르치는 친절한 튜터야. 어려운 개념은 쉬운 말과 예시로 설명해.",
    "비판적 리뷰어": "너는 사용자의 글, 아이디어, 코드, 기획을 비판적으로 검토하는 리뷰어야. 장점보다 개선점과 보완점을 중심으로 제안해.",
    "아이디어 브레인스토머": "너는 창의적인 아이디어를 제안하는 브레인스토밍 파트너야. 다양한 관점과 대안을 제시해.",
    "정리 전문가": "너는 사용자의 내용을 보기 좋게 분류하고 핵심을 정돈하는 정리 전문가야.",
    "요약 전문가": "너는 긴 내용을 핵심만 간결하게 정리하는 요약 전문가야. 불필요한 설명은 줄이고 핵심 위주로 답해.",
}

LENGTH_PROMPTS = {
    "100자 이내": "답변은 100자 이내로 작성해.",
    "300자 이내": "답변은 300자 이내로 작성해.",
    "500자 이내": "답변은 500자 이내로 작성해.",
    "1000자 이내": "답변은 1000자 이내로 작성해.",
    "제한 없음": "답변 길이에 엄격한 제한을 두지 마.",
}

FORMAT_PROMPTS = {
    "일반 문장": "답변은 자연스러운 문장 형태로 작성해.",
    "체크리스트": "답변은 체크리스트 형태로 작성해.",
    "표": "가능하면 답변을 표 형태로 정리해.",
    "단계별 설명": "답변은 번호를 붙여 단계별로 설명해.",
}

TONE_PROMPTS = {
    "친절하게": "말투는 친절하고 편안하게 유지해.",
    "전문적으로": "말투는 전문적이고 신뢰감 있게 유지해.",
    "간단명료하게": "말투는 군더더기 없이 간단명료하게 유지해.",
    "비판적으로": "말투는 근거를 들어 비판적으로 유지해.",
}

SAMPLE_QUESTIONS = [
    "오늘 할 일을 우선순위에 따라 정리해줘",
    "면접에서 자기소개를 자연스럽게 말할 수 있게 도와줘",
    "이 글을 더 짧고 명확하게 고쳐줘",
    "Python을 처음 배우는 사람에게 공부 순서를 추천해줘",
    "여행 계획을 2박 3일 일정표로 만들어줘",
    "다이어트 식단을 현실적으로 짜줘",
    "회의 내용을 핵심만 요약해줘",
    "영어 이메일을 정중한 표현으로 작성해줘",
]


def load_api_key():
    load_dotenv(Path(__file__).with_name(".env"))
    return os.getenv("GEMINI_API_KEY")


def load_model_name():
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)


def reset_messages():
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "feedback": None,
        }
    ]


def init_session_state():
    if "messages" not in st.session_state:
        reset_messages()

    if "selected_sample_question" not in st.session_state:
        st.session_state.selected_sample_question = ""

    if "ai_configured" not in st.session_state:
        st.session_state.ai_configured = False

    if "active_system_prompt" not in st.session_state:
        st.session_state.active_system_prompt = ""

    if "active_temperature" not in st.session_state:
        st.session_state.active_temperature = 0.5

    if "active_mode_message" not in st.session_state:
        st.session_state.active_mode_message = ""


def resolve_prompt(selection, prompt_map, custom_value):
    if selection != "직접 입력":
        return prompt_map[selection]

    custom_value = custom_value.strip()
    if custom_value:
        return custom_value

    return ""


def build_system_prompt(role_prompt, tone_prompt, answer_length, format_prompt, extra_instruction):
    prompt_parts = []

    for prompt in (role_prompt, tone_prompt, format_prompt):
        if prompt:
            prompt_parts.append(prompt)

    if answer_length != "제한 없음":
        prompt_parts.append(LENGTH_PROMPTS[answer_length])

    if extra_instruction:
        prompt_parts.append(f"추가 지시사항: {extra_instruction}")

    return "\n".join(prompt_parts)


def build_mode_message(role, tone, answer_length, output_format):
    if not any([role, tone, output_format]) and answer_length == "제한 없음":
        return "🤖 기본 LLM 모드로 답변합니다."

    role_label = role or "AI"
    tone_label = tone or ""
    format_label = output_format or ""
    length_label = answer_length if answer_length != "제한 없음" else "길이 제한 없이"

    mode_words = []
    if tone_label:
        mode_words.extend([tone_label, "말하는"])
    if format_label:
        mode_words.append(format_label)
    mode_words.append(role_label)

    if answer_length == "제한 없음":
        return f"🤖 {' '.join(mode_words)} 모드로 {length_label} 답변합니다."

    return f"🤖 {' '.join(mode_words)} 모드로 {length_label}로 답변합니다."


def clear_welcome_message():
    st.session_state.messages = [
        message
        for message in st.session_state.messages
        if message.get("content") != WELCOME_MESSAGE
    ]


def resolve_display_value(selection, custom_value):
    if selection != "직접 입력":
        return selection

    return custom_value.strip()


def build_contents(user_input):
    recent_history = []
    for message in st.session_state.messages[-8:]:
        if message["role"] == "user":
            recent_history.append(f"User: {message['content']}")
        elif message["role"] == "assistant":
            recent_history.append(f"Assistant: {message['content']}")

    parts = []
    if recent_history:
        parts.append("Conversation so far:\n" + "\n\n".join(recent_history))
    parts.append(f"Current user question:\n{user_input}")
    return "\n\n".join(parts)


def get_gemini_response(api_key, model_name, system_prompt, user_input, temperature):
    client = genai.Client(api_key=api_key)
    config_options = {
        "max_output_tokens": 2048,
        "response_mime_type": "text/plain",
    }

    if temperature is not None:
        config_options["temperature"] = temperature

    if system_prompt:
        config_options["system_instruction"] = system_prompt

    response = client.models.generate_content(
        model=model_name,
        contents=build_contents(user_input),
        config=types.GenerateContentConfig(**config_options),
    )
    return response.text or ""


def render_chat_history():
    for index, message in enumerate(st.session_state.messages):
        avatar = "🤖" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])

            if message["role"] == "assistant":
                _, feedback_col = st.columns([7, 1.2])
                with feedback_col:
                    up_col, down_col = st.columns(2)
                    with up_col:
                        if st.button("👍", key=f"up_{index}", help="좋아요"):
                            st.session_state.messages[index]["feedback"] = "좋아요"
                    with down_col:
                        if st.button("👎", key=f"down_{index}", help="아쉬워요"):
                            st.session_state.messages[index]["feedback"] = "아쉬워요"

                feedback = st.session_state.messages[index].get("feedback")
                if feedback:
                    st.caption(f"피드백: {feedback}")


def render_sidebar():
    with st.sidebar:
        st.header("대화 관리")

        if st.button("대화 초기화", type="primary", use_container_width=True):
            reset_messages()
            st.rerun()


def render_sample_question_picker():
    selected = st.selectbox(
        "샘플 질문",
        ["직접 입력"] + SAMPLE_QUESTIONS,
        help="샘플 질문을 선택하면 입력창 placeholder로 표시됩니다.",
    )

    st.session_state.selected_sample_question = "" if selected == "직접 입력" else selected
    return st.session_state.selected_sample_question


def render_question_input(sample_question):
    placeholder = sample_question or "질문을 입력하세요."
    patch_chat_input_shortcuts()
    user_input = st.chat_input(placeholder)
    return user_input.strip() if user_input else ""


def patch_chat_input_shortcuts():
    components.html(
        """
        <script>
        const marker = "data-ctrl-enter-newline";

        function insertTextAtCursor(element, text) {
          const start = element.selectionStart;
          const end = element.selectionEnd;
          const value = element.value;
          element.value = value.slice(0, start) + text + value.slice(end);
          element.selectionStart = start + text.length;
          element.selectionEnd = start + text.length;
          element.dispatchEvent(new InputEvent("input", {
            bubbles: true,
            inputType: "insertLineBreak",
            data: text
          }));
        }

        function patchChatInput() {
          const root = window.parent.document.querySelector('[data-testid="stChatInput"]');
          const textarea = root ? root.querySelector("textarea") : null;

          if (!textarea || textarea.getAttribute(marker) === "1") {
            return;
          }

          textarea.setAttribute(marker, "1");
          textarea.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && event.ctrlKey && !event.altKey && !event.metaKey) {
              event.preventDefault();
              event.stopImmediatePropagation();
              insertTextAtCursor(textarea, "\\n");
            }
          }, true);
        }

        patchChatInput();
        window.setInterval(patchChatInput, 500);
        </script>
        """,
        height=0,
    )


def patch_selectbox_interactions():
    components.html(
        """
        <script>
        const marker = "data-toggle-close-selectbox";

        function closeOpenSelectbox() {
          const active = window.parent.document.activeElement;
          if (active) {
            active.dispatchEvent(new KeyboardEvent("keydown", {
              key: "Escape",
              code: "Escape",
              keyCode: 27,
              which: 27,
              bubbles: true
            }));
            active.blur();
          }
        }

        function patchSelectboxes() {
          const doc = window.parent.document;
          const comboboxes = doc.querySelectorAll('[role="combobox"]');

          comboboxes.forEach((combobox) => {
            if (combobox.getAttribute(marker) === "1") {
              return;
            }

            combobox.setAttribute(marker, "1");
            combobox.addEventListener("mousedown", (event) => {
              if (combobox.getAttribute("aria-expanded") === "true") {
                event.preventDefault();
                event.stopPropagation();
                closeOpenSelectbox();
              }
            }, true);
          });
        }

        patchSelectboxes();
        window.setInterval(patchSelectboxes, 500);
        </script>
        """,
        height=0,
    )


def inject_selectbox_styles():
    st.markdown(
        """
        <style>
        div[data-baseweb="select"] > div {
            cursor: pointer;
            transition: border-color 120ms ease, box-shadow 120ms ease, background-color 120ms ease;
        }

        div[data-baseweb="select"] > div:hover {
            border-color: #4f8cff;
            box-shadow: 0 0 0 1px rgba(79, 140, 255, 0.18);
            background-color: rgba(79, 140, 255, 0.04);
        }

        div[data-baseweb="select"] svg {
            transition: transform 120ms ease, color 120ms ease;
        }

        div[data-baseweb="select"] > div:hover svg {
            color: #4f8cff;
            transform: translateY(1px);
        }

        div[data-baseweb="select"] input {
            caret-color: transparent;
            cursor: pointer;
        }

        div[data-baseweb="select"] input::selection {
            background: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_prompt_settings():
    inject_selectbox_styles()
    patch_selectbox_interactions()

    with st.expander("프롬프트 설정", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            role = st.selectbox(
                "역할",
                ["직접 입력"] + list(ROLE_PROMPTS.keys()),
                help="직접 입력을 선택하면 아래 입력칸에 원하는 역할을 쓸 수 있습니다.",
            )
            custom_role = st.text_input(
                "역할 직접 입력",
                placeholder="비워두면 역할을 따로 지정하지 않습니다.",
                disabled=role != "직접 입력",
                label_visibility="collapsed",
            )
            answer_length = st.radio(
                "길이",
                ["제한 없음"] + [label for label in LENGTH_PROMPTS if label != "제한 없음"],
                horizontal=True,
            )
        with col2:
            tone = st.selectbox(
                "말투",
                ["직접 입력"] + list(TONE_PROMPTS.keys()),
                help="직접 입력을 선택하면 아래 입력칸에 원하는 말투를 쓸 수 있습니다.",
            )
            custom_tone = st.text_input(
                "말투 직접 입력",
                placeholder="비워두면 말투를 따로 지정하지 않습니다.",
                disabled=tone != "직접 입력",
                label_visibility="collapsed",
            )

            output_format = st.selectbox(
                "형식",
                ["직접 입력"] + list(FORMAT_PROMPTS.keys()),
                help="직접 입력을 선택하면 아래 입력칸에 원하는 형식을 쓸 수 있습니다.",
            )
            custom_format = st.text_input(
                "형식 직접 입력",
                placeholder="비워두면 형식을 따로 지정하지 않습니다.",
                disabled=output_format != "직접 입력",
                label_visibility="collapsed",
            )

        temperature = st.slider(
            "답변 온도",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="낮을수록 안정적이고, 높을수록 다양한 답변이 나옵니다.",
        )
        extra_instruction = st.text_area(
            "추가 지시사항",
            value="",
            placeholder="예: 초등학생도 이해할 수 있게 설명해줘",
            height=90,
        ).strip()

        role_display = resolve_display_value(role, custom_role)
        tone_display = resolve_display_value(tone, custom_tone)
        format_display = resolve_display_value(output_format, custom_format)

        setting_preview = build_mode_message(role_display, tone_display, answer_length, format_display)
        st.info(setting_preview)

        is_saved = st.button("설정 완료", type="primary", use_container_width=True)

    role_prompt = resolve_prompt(role, ROLE_PROMPTS, custom_role)
    tone_prompt = resolve_prompt(tone, TONE_PROMPTS, custom_tone)
    format_prompt = resolve_prompt(output_format, FORMAT_PROMPTS, custom_format)

    system_prompt = build_system_prompt(
        role_prompt=role_prompt,
        tone_prompt=tone_prompt,
        answer_length=answer_length,
        format_prompt=format_prompt,
        extra_instruction=extra_instruction,
    )
    role_display = resolve_display_value(role, custom_role)
    tone_display = resolve_display_value(tone, custom_tone)
    format_display = resolve_display_value(output_format, custom_format)
    mode_message = build_mode_message(role_display, tone_display, answer_length, format_display)
    return system_prompt, temperature, mode_message, is_saved


def main():
    st.set_page_config(page_title="프롬프트 실험실", page_icon="💬", layout="wide")
    init_session_state()

    api_key = load_api_key()
    model_name = load_model_name()
    render_sidebar()

    st.title("DIY 프롬프트 실험실")
    st.write("같은 질문이라도 역할, 답변 길이, 출력 형식, 답변 온도 값에 따라 답변이 어떻게 달라지는지 실험해보세요.")

    system_prompt, temperature, mode_message, is_saved = render_prompt_settings()

    if is_saved:
        with st.spinner("AI 설정중.."):
            clear_welcome_message()
            st.session_state.active_system_prompt = system_prompt
            st.session_state.active_temperature = temperature
            st.session_state.active_mode_message = mode_message
            st.session_state.ai_configured = True
            st.session_state.messages.append(
                {"role": "assistant", "content": mode_message, "feedback": None}
            )
        st.rerun()

    if not api_key:
        st.error("GEMINI_API_KEY가 설정되어 있지 않습니다. 프로젝트의 .env 파일에 GEMINI_API_KEY를 추가해주세요.")
        st.stop()

    sample_question = render_sample_question_picker()
    render_chat_history()

    if not st.session_state.ai_configured:
        st.warning("프롬프트 설정을 고른 뒤 설정 완료 버튼을 눌러주세요.")
        st.stop()

    user_input = render_question_input(sample_question)
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("답변을 생성하는 중입니다..."):
                try:
                    answer = get_gemini_response(
                        api_key,
                        model_name,
                        st.session_state.active_system_prompt,
                        user_input,
                        st.session_state.active_temperature,
                    )
                except Exception as error:
                    st.error(f"API 호출 중 오류가 발생했습니다: {error}")
                    return

                st.write(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "feedback": None}
                )


if __name__ == "__main__":
    main()
