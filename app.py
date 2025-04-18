# app.py (Autoplay only the latest audio)

import streamlit as st
import os
import io
import time

# --- 페이지 설정 (가장 먼저!) ---
st.set_page_config(
    page_title="멀티 페르소나 야구 챗봇",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 필수 사용자 정의 모듈 임포트 ---
try:
    import GetAnswer as ga
    from SpeakAnswer import generate_tts_bytes
    # tts_styles는 이제 TTS 생성 시 내부적으로만 사용됨
except ImportError as e:
    st.error(f"필수 모듈 임포트 오류: {e}")
    st.error("GetAnswer.py, SpeakAnswer.py, tts_styles.py 파일을 확인하세요.")
    st.stop()
except AttributeError as ae:
     st.error(f"모듈 내부 속성 오류: {ae} - GetAnswer.py, SpeakAnswer.py 또는 tts_styles.py 내부 확인 필요")
     st.stop()
# OpenAI 라이브러리
try:
    from openai import OpenAI, OpenAIError
except ImportError:
    st.error("OpenAI 라이브러리가 설치되지 않았습니다. (pip install openai)")
    st.stop()

# --- 기본 설정 및 환경 변수 ---
try:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        st.warning("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다. 모든 기능이 제한됩니다.")
        OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"
except KeyError:
     st.error("Streamlit Secrets에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
     OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"

api_key_valid = bool(OPENAI_API_KEY and OPENAI_API_KEY != "INVALID_KEY_PLACEHOLDER" and OPENAI_API_KEY != "YOUR_API_KEY_HERE")
if not api_key_valid:
     st.warning("⚠️ OpenAI API 키가 유효하지 않아 RAG 및 TTS 기능이 비활성화됩니다.")

# --- 캐릭터 정보 정의 (voice 추가) ---
CHARACTERS = {
    "친절한 비서": {
        "avatar": "😊",
        "description": "항상 친절하고 상세하게 답변 (CSV 기반)",
        "system_prompt": "You are a very kind, polite, and helpful assistant providing answers based on the provided CSV data context. Always answer in Korean.",
        "voice": "nova"
    },
    "야구봇 (기본)": {
        "avatar": "⚾",
        "description": f"{ga.get_data_source_description() if api_key_valid else '데이터 기반 야구 질문 답변 (키 필요)'}",
        "system_prompt": "You are a helpful assistant providing answers based on the provided CSV data context. Answer factually based on the data. If the information is not in the context, say so. Respond in Korean.",
        "voice": "alloy"
    },
    "시니컬한 친구": {
        "avatar": "😏",
        "description": "모든 것을 약간 삐딱하지만 재치있게 답변 (CSV 기반)",
        "system_prompt": "You are a cynical friend who answers questions based on the provided CSV data context with sarcasm and wit, but is ultimately helpful in your own way. If the information is not in the context, mock the user for asking about something not present. Respond in Korean.",
        "voice": "echo"
    },
    "전문 분석가": {
         "avatar": "👩‍💼",
         "description": "데이터에 기반하여 전문가적으로 분석 (CSV 기반)",
         "system_prompt": "You are a professional data analyst. Provide answers based strictly on the provided CSV data context. Use formal language and provide insights where possible based on the data. If the information is not in the context, state that clearly. Respond in Korean.",
         "voice": "shimmer"
    },
}

# --- CSS 주입 (변경 없음) ---
st.markdown("""
<style>
    /* ... CSS ... */
</style>
""", unsafe_allow_html=True)


# --- 핵심 기능 초기화 ---
llm_client = None
if api_key_valid:
    try:
        llm_client = OpenAI(api_key=OPENAI_API_KEY)
        if "llm_client" not in st.session_state: # 클라이언트 한 번만 생성하여 세션에 저장
             st.session_state.llm_client = llm_client
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 실패: {e}")
        api_key_valid = False

# --- 세션 상태 초기화 ---
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {name: [] for name in CHARACTERS}
if "selected_character" not in st.session_state:
    st.session_state.selected_character = None
# temperature는 현재 사용되지 않음
# if "temperature" not in st.session_state:
#     st.session_state.temperature = 0.7
if "active_chain" not in st.session_state:
     st.session_state.active_chain = None
# --- 자동 재생 플래그 추가 ---
if "autoplay_next_audio" not in st.session_state:
     st.session_state.autoplay_next_audio = False
# ---------------------------

# --- 3단 레이아웃 정의 ---
col_config, col_list, col_chat = st.columns([1, 2, 4])

# --- 컬럼 1: 설정 ---
with col_config:
    st.header("⚙️ 설정")
    st.info("LLM 온도는 RAG 시스템 내부에 고정되어 있습니다.")
    st.markdown("---")
    st.header("🔊 음성")
    st.info("음성 스타일은 선택된 캐릭터에 따라 자동으로 지정됩니다.")

# --- 컬럼 2: 캐릭터 목록 ---
with col_list:
    st.header("대화 상대")
    for name, details in CHARACTERS.items():
        is_disabled = not api_key_valid
        button_type = "primary" if st.session_state.selected_character == name else "secondary"

        if st.button(f"{details['avatar']} {name}", key=f"char_btn_{name}", use_container_width=True, type=button_type, disabled=is_disabled):
            if st.session_state.selected_character != name:
                 st.session_state.selected_character = name
                 # 캐릭터 변경 시 자동 재생 플래그 초기화
                 st.session_state.autoplay_next_audio = False
                 with st.spinner(f"{name} 대화 준비 중..."):
                      try:
                           st.session_state.active_chain = ga.initialize_qa_system(
                               character_system_prompt=details["system_prompt"]
                           )
                           if not st.session_state.active_chain:
                                st.error(f"{name} RAG 체인 생성 실패.")
                           # else: st.success(f"{name} 대화 준비 완료!") # 성공 메시지 너무 자주 나올 수 있어 제거
                      except Exception as chain_e:
                           st.error(f"체인 생성 중 오류: {chain_e}")
                           st.session_state.active_chain = None
                 st.rerun()

        if is_disabled:
             st.caption("(API 키 필요)")

# --- 컬럼 3: 채팅 영역 ---
with col_chat:
    if st.session_state.selected_character:
        selected_name = st.session_state.selected_character
        selected_details = CHARACTERS[selected_name]

        # --- 캐릭터 정보 및 대화 삭제 버튼 ---
        sub_col1, sub_col2 = st.columns([4, 1])
        with sub_col1:
             st.markdown(f"#### {selected_details['avatar']} {selected_name}")
             st.caption(selected_details['description'])
        with sub_col2:
             if st.button(f"🧹 기록 삭제", key=f"clear_btn_{selected_name}", help=f"'{selected_name}' 와(과)의 대화 내역을 지웁니다."):
                 if selected_name in st.session_state.chat_histories:
                     st.session_state.chat_histories[selected_name] = []
                     if hasattr(st.session_state.active_chain, 'memory'):
                          st.session_state.active_chain.memory.clear()
                     st.toast(f"'{selected_name}' 대화 기록 삭제 완료!", icon="🧹")
                     st.session_state.autoplay_next_audio = False # 기록 삭제 시 플래그 초기화
                     time.sleep(0.5)
                     st.rerun()
        st.divider()

        # --- 채팅 메시지 표시 영역 ---
        chat_display_area = st.container()
        with chat_display_area:
            messages = st.session_state.chat_histories.get(selected_name, [])
            # enumerate를 사용하여 메시지 인덱스 가져오기
            for index, message in enumerate(messages):
                avatar_display = selected_details['avatar'] if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar_display):
                    st.markdown(message["content"])

                    # --- 최신 메시지만 자동 재생하는 로직 ---
                    is_last_message = (index == len(messages) - 1)
                    # 마지막 메시지이고, assistant 역할이며, audio 데이터가 있고, 자동 재생 플래그가 True일 때만 실행
                    if is_last_message and message["role"] == "assistant" and message.get("audio") and st.session_state.get("autoplay_next_audio", False):
                        st.audio(message["audio"], format="audio/mp3", autoplay=True)
                        # 자동 재생 후 플래그를 즉시 False로 바꿔서 다음 rerun 시 재생 안 되도록 함
                        st.session_state.autoplay_next_audio = False
                    # --- 과거 메시지의 오디오 바는 표시하지 않음 (autoplay=False도 호출 안 함) ---
                    # -----------------------------------------

        # --- 채팅 입력 및 응답 처리 ---
        chat_input_disabled = not st.session_state.active_chain

        if prompt := st.chat_input(f"{selected_name}에게 메시지 보내기...", key=f"chat_input_{selected_name}", disabled=chat_input_disabled):

            current_chat_history = st.session_state.chat_histories.get(selected_name, [])
            current_chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_histories[selected_name] = current_chat_history

            response_text = None
            audio_bytes = None
            # --- 자동 재생 플래그 초기화 (새 응답 생성 전에) ---
            st.session_state.autoplay_next_audio = False
            # -----------------------------------------------

            with st.spinner("답변 생성 중..."):
                try:
                    if st.session_state.active_chain:
                        response_text = ga.get_answer(st.session_state.active_chain, prompt)
                    else:
                        response_text = "오류: 현재 캐릭터의 RAG 대화 시스템이 준비되지 않았습니다."

                    # --- TTS Generation ---
                    if api_key_valid and response_text and not response_text.startswith(("오류:", "API 오류", "[LLM", "[{", "알 수 없는", "답변을 찾을 수 없습니다")):
                        try:
                            character_voice = selected_details.get("voice", "nova")
                            print(f"--- TTS 호출 시도: 캐릭터='{selected_name}', 목소리='{character_voice}', 텍스트='{response_text[:50]}...'")
                            audio_bytes = generate_tts_bytes(response_text, style_name=character_voice)
                            print(f"--- TTS 결과: {'Bytes 생성됨 (길이: ' + str(len(audio_bytes)) + ')' if audio_bytes else 'None'}")
                            # --- TTS 성공 시 자동 재생 플래그 설정 ---
                            if audio_bytes:
                                st.session_state.autoplay_next_audio = True
                            # ---------------------------------------
                        except Exception as tts_e:
                            st.warning(f"TTS 생성 중 오류 발생: {tts_e}")
                            print(f"!!! TTS Generation Error: {tts_e}")
                            audio_bytes = None
                    else:
                         # TTS 건너뛴 이유 로그
                         if api_key_valid and response_text:
                              print(f"--- TTS 건너뜀 (조건 불충족): 응답 시작 = '{response_text[:20]}...'")
                         # ... (다른 건너뛰기 로그 생략) ...

                except Exception as e:
                    st.error(f"응답 처리 중 예외 발생: {e}")
                    print(f"!!! Top Level Response Processing Error: {e}")
                    response_text = f"오류: 응답 처리 중 문제가 발생했습니다."

            # 봇 응답 저장
            current_chat_history.append({
                "role": "assistant",
                "content": response_text if response_text else "응답 생성 실패",
                "audio": audio_bytes
            })
            st.session_state.chat_histories[selected_name] = current_chat_history
            # st.rerun() 호출 전에 autoplay_next_audio 플래그가 설정되어 있어야 함
            st.rerun()

    else: # 선택된 캐릭터 없을 때
        st.info("👈 **왼쪽 목록**에서 대화할 상대를 선택해주세요.")
        st.caption("⚙️ **설정**은 가장 왼쪽 열에서 조절할 수 있습니다.")