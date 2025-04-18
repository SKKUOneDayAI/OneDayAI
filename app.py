# app.py (Full Code - All Features Integrated)

import streamlit as st
import os
import io
import time # 버튼 클릭 후 메시지 표시 시간용

# --- 페이지 설정 (가장 먼저!) ---
st.set_page_config(
    page_title="멀티 페르소나 야구 챗봇", # <-- 야구 테마
    page_icon="⚾",                     # <-- 야구 아이콘
    layout="wide",
    initial_sidebar_state="collapsed" # 3단 컬럼 사용
)

# --- 필수 사용자 정의 모듈 임포트 ---
# 사용자가 선호하는 파일 이름 사용 (GetAnswer.py, SpeakAnswer.py)
# 각 파일은 이전에 논의된 대로 리팩토링되어 있어야 함!
try:
    import GetAnswer as ga             # QA 로직 (initialize_qa_system, get_answer 함수 포함)
    from SpeakAnswer import generate_tts_bytes # TTS 로직 (bytes 반환 함수 포함)
    from tts_styles import get_style_params, get_available_styles # 스타일 정의
except ImportError as e:
    st.error(f"필수 모듈 임포트 오류: {e}")
    st.error("GetAnswer.py, SpeakAnswer.py, tts_styles.py 파일을 확인하세요.")
    st.stop()
except AttributeError as ae:
     st.error(f"모듈 내부 속성 오류: {ae} - GetAnswer.py 또는 SpeakAnswer.py 내부 확인 필요")
     st.stop()
# OpenAI 라이브러리
try:
    from openai import OpenAI, OpenAIError
except ImportError:
    st.error("OpenAI 라이브러리가 설치되지 않았습니다. (pip install openai)")
    st.stop()

# --- 기본 설정 및 환경 변수 ---
# <<< 사용자의 실제 야구 데이터 CSV 경로로 수정 필요! >>>
CSV_FILE_PATH = r"C:\Users\skku07\Documents\GitHub\OneDayAI\dummy_basketball.csv" # 야구 CSV 경로로!
DEFAULT_TTS_STYLE = "calm_female"
# <<< 실제 OpenAI API 키 설정 필수! (환경 변수 또는 Secrets 권장) >>>
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE") # 실제 키로 대체!

# API 키 유효성 검사
api_key_valid = bool(OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_API_KEY_HERE")
if not api_key_valid:
     st.warning("⚠️ OpenAI API 키가 설정되지 않았습니다. LLM 및 TTS 기능 사용이 제한됩니다.")

# --- 캐릭터 정보 정의 (System Prompt 포함) ---
CHARACTERS = {
    "친절한 비서": {
        "avatar": "😊",
        "description": "항상 친절하고 상세하게 답변합니다.",
        "system_prompt": "You are a very kind, polite, and helpful assistant. Always answer in Korean."
    },
    "야구봇": { # 야구봇
        "avatar": "⚾",
        "description": f"'{os.path.basename(CSV_FILE_PATH)}' 데이터 기반 야구 질문 답변",
        "system_prompt": None # RAG 사용
    },
    "시니컬한 친구": {
        "avatar": "😏",
        "description": "모든 것을 약간 삐딱하지만 재치있게 봅니다.",
        "system_prompt": "You are a cynical friend who answers questions with sarcasm and wit, but is ultimately helpful in your own way. Respond in Korean."
    },
    # 다른 캐릭터 예시
    "Eva Johnston": {"avatar": "🎨", "description": "is typing a message...", "system_prompt": "You are Eva, a creative artist. Respond in Korean."},
    "Lucinda McGuire": {"avatar": "👩‍💼", "description": "Sounds Great! See you next time", "system_prompt": "You are Lucinda, a professional colleague. Respond in Korean."},
    "Carl Willis": {"avatar": "👨‍🔬", "description": "Could you please take to the hosp...", "system_prompt": "You are Carl, a scientist. Respond in Korean."},
}

# --- CSS 주입 (디자인 개선용) ---
# 이전 답변에서 제공된 CSS 코드를 여기에 붙여넣거나 필요에 따라 수정하세요.
# 예시: st.markdown("""<style> ... CSS 규칙 ... </style>""", unsafe_allow_html=True)
st.markdown("""
<style>
    /* 여기에 이전 답변의 CSS 코드 또는 직접 작성한 CSS를 넣으세요 */
    /* 예시: 컬럼 배경, 버튼 스타일, 채팅창 스타일 등 */
    /* 컬럼 스타일 */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div[data-testid="stVerticalBlock"] { background-color: #f8f9fa; border-right: 1px solid #e9ecef; padding: 1rem; height: 100vh; overflow-y: auto; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div[data-testid="stVerticalBlock"] { background-color: #ffffff; border-right: 1px solid #e9ecef; padding: 1rem; height: 100vh; overflow-y: auto; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) > div[data-testid="stVerticalBlock"] { background-color: #ffffff; padding: 0rem; height: 100vh; display: flex; flex-direction: column; }
    /* 캐릭터 버튼 */
    div[data-testid="stVerticalBlock"] button[kind="secondary"], div[data-testid="stVerticalBlock"] button[kind="primary"] { display: flex !important; align-items: center !important; text-align: left !important; justify-content: start !important; background-color: transparent !important; border: none !important; padding: 10px 8px !important; margin-bottom: 5px !important; border-radius: 8px !important; color: #343a40 !important; width: 100%; font-size: 0.9rem; transition: background-color 0.2s ease; }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover { background-color: #e9ecef !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"] { background-color: #d1e7dd !important; color: #0f5132 !important; font-weight: 600 !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover { background-color: #badbcc !important; }
    div[data-testid="stVerticalBlock"] button > div { gap: 0.8rem !important; align-items: center !important; }
    /* 채팅 영역 */
    div[data-testid="stChatMessages"] { flex-grow: 1; overflow-y: auto; padding: 1rem; }
    div[data-testid="stChatMessage"] { margin-bottom: 1rem; }
    div[data-testid="stChatInput"] { background-color: #ffffff; border-top: 1px solid #dee2e6; padding: 0.75rem 1rem; }
    div[data-testid="stChatInput"] textarea { border-radius: 8px !important; border: 1px solid #ced4da !important; background-color: #f8f9fa !important; }
</style>
""", unsafe_allow_html=True)


# --- 핵심 기능 초기화 (캐싱) ---
@st.cache_resource
def load_baseball_qa_chain():
    """야구봇용 RAG QA 체인을 초기화하고 반환합니다."""
    if not api_key_valid: return None # API 키 없으면 로드 불가
    # st.write("야구봇 QA 시스템 초기화 중...") # 디버깅용
    try:
        # GetAnswer 모듈의 초기화 함수 사용
        # CSV_FILE_PATH가 올바른 야구 데이터 경로인지 확인!
        chain = ga.initialize_qa_system(csv_path=CSV_FILE_PATH)
        if chain: st.success("야구봇 QA 시스템 초기화 완료!") # 성공 메시지 (초기 로드 시 한 번)
        else: st.error("야구봇 QA 시스템 초기화 실패.")
        return chain
    except Exception as e:
        print(f"야구봇 초기화 오류: {e}")
        st.error(f"야구봇 QA 시스템 초기화 중 오류 발생: {e}")
        return None

baseball_qa_chain = load_baseball_qa_chain()

# LLM 클라이언트 초기화
llm_client = None
if api_key_valid:
    try:
        llm_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 실패: {e}")

# --- 세션 상태 초기화 ---
# 채팅 기록 (캐릭터별)
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {name: [] for name in CHARACTERS}
# 현재 선택된 캐릭터
if "selected_character" not in st.session_state:
    st.session_state.selected_character = None
# LLM Temperature
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
# TTS 스타일
if "tts_style" not in st.session_state:
    st.session_state.tts_style = DEFAULT_TTS_STYLE


# --- 3단 레이아웃 정의 ---
col_config, col_list, col_chat = st.columns([1, 2, 4]) # 비율: 설정 | 목록 | 채팅

# --- 컬럼 1: 설정 ---
with col_config:
    st.header("⚙️ 설정")
    # LLM Temperature 설정
    st.session_state.temperature = st.slider(
        "Temperature (창의성)", 0.0, 1.0, st.session_state.temperature, 0.05, key="temp_slider",
        help="LLM 답변의 다양성을 조절합니다 (야구봇 외)."
    )
    # RAG 관련 설정은 현재 UI에서 변경 불가 (필요 시 추가 구현)

    st.markdown("---")
    st.header("🔊 음성")
    # 음성 스타일 선택
    available_styles = get_available_styles()
    try:
        # 현재 스타일이 유효한지 확인하고 기본값 설정
        if st.session_state.tts_style not in available_styles:
             st.session_state.tts_style = next(iter(available_styles), "default")
        current_style_index = list(available_styles.keys()).index(st.session_state.tts_style)

        selected_style = st.radio(
            "음성 스타일:", options=list(available_styles.keys()),
            format_func=lambda name: available_styles.get(name, name), # Corrected
            index=current_style_index, key="tts_style_radio"
        )
        # 스타일 변경 시 세션 상태 업데이트 및 새로고침
        if selected_style != st.session_state.tts_style:
            st.session_state.tts_style = selected_style
            st.rerun()
    except Exception as e:
         st.error(f"음성 스타일 로딩 오류: {e}")

# --- 컬럼 2: 캐릭터 목록 ---
with col_list:
    st.header("대화 상대")
    # st.divider() # CSS 사용 시 불필요
    for name, details in CHARACTERS.items():
        button_type = "primary" if st.session_state.selected_character == name else "secondary"
        if st.button(f"{details['avatar']} {name}", key=f"char_btn_{name}", use_container_width=True, type=button_type):
            # 다른 캐릭터 선택 시 상태 업데이트 및 새로고침
            if st.session_state.selected_character != name:
                 st.session_state.selected_character = name
                 st.rerun()

# --- 컬럼 3: 채팅 영역 ---
with col_chat:
    if st.session_state.selected_character:
        selected_name = st.session_state.selected_character
        selected_details = CHARACTERS[selected_name]

        # --- 캐릭터 정보 및 대화 삭제 버튼 ---
        # 컬럼을 사용해 제목과 버튼을 같은 줄에 배치 (선택 사항)
        sub_col1, sub_col2 = st.columns([4, 1])
        with sub_col1:
             st.markdown(f"#### {selected_details['avatar']} {selected_name}")
             st.caption(selected_details['description'])
        with sub_col2:
             if st.button(f"🧹 기록 삭제", key=f"clear_btn_{selected_name}", help=f"'{selected_name}' 와(과)의 대화 내역을 지웁니다."):
                 if selected_name in st.session_state.chat_histories:
                     st.session_state.chat_histories[selected_name] = []
                     st.toast(f"'{selected_name}' 대화 기록 삭제 완료!", icon="🧹") # 토스트 메시지로 변경
                     time.sleep(0.5) # 짧게 대기
                     st.rerun()
        st.divider()
        # --- ----------------------------- ---

        # --- 채팅 메시지 표시 영역 ---
        chat_display_area = st.container() # 채팅 기록 영역
        with chat_display_area:
            messages = st.session_state.chat_histories.get(selected_name, [])
            for message in messages:
                avatar_display = selected_details['avatar'] if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar_display):
                    st.markdown(message["content"])
                    if message["role"] == "assistant" and message.get("audio"):
                         # 자동 재생 추가됨!
                         st.audio(message["audio"], format="audio/mp3", autoplay=True)

        # --- 채팅 입력 및 응답 처리 ---
        if prompt := st.chat_input(f"{selected_name}에게 메시지 보내기...", key=f"chat_input_{selected_name}"):
            # 1. 사용자 메시지 추가 (표시는 rerun 후 자동으로)
            current_chat_history = st.session_state.chat_histories.get(selected_name, [])
            current_chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_histories[selected_name] = current_chat_history

            # 2. 봇 응답 생성 및 추가
            response_text = None
            audio_bytes = None
            # 응답 생성 로직을 별도 컨테이너/메시지에 표시하지 않고 바로 처리
            with st.spinner("답변 생성 중..."): # 스피너는 그대로 사용
                try:
                    # ====[ 캐릭터별 응답 생성 로직 - 실제 기능 ]====
                    if selected_name == "야구봇":
                        if baseball_qa_chain:
                            response_text = ga.get_answer(baseball_qa_chain, prompt)
                        else:
                            response_text = "오류: 야구봇 QA 시스템 로드 실패."
                    elif selected_name in CHARACTERS: # LLM 기반 페르소나
                        system_prompt = CHARACTERS[selected_name].get("system_prompt")
                        if not system_prompt: response_text = f"[{selected_name}] 기본 응답."
                        elif llm_client:
                            messages_for_api = [{"role": "system", "content": system_prompt}]
                            # 이전 대화 포함 (audio 키 제외)
                            for msg in current_chat_history:
                                messages_for_api.append({"role": msg["role"], "content": msg["content"]})
                            try:
                                completion = llm_client.chat.completions.create(
                                    model="gpt-3.5-turbo", messages=messages_for_api,
                                    temperature=st.session_state.temperature
                                )
                                response_text = completion.choices[0].message.content
                            except OpenAIError as e: response_text = f"API 오류: {e}"
                            except Exception as e: response_text = f"LLM 처리 오류: {e}"
                        else: response_text = "[LLM 기능 사용 불가 (API 키 확인)]"
                    else: response_text = f"알 수 없는 캐릭터 응답."
                    # =========================================

                    # --- TTS Generation ---
                    if api_key_valid and response_text and not response_text.startswith("오류:") and not response_text.startswith("API 오류"):
                         audio_bytes = generate_tts_bytes(response_text, style_name=st.session_state.tts_style)
                    # --------------------

                except Exception as e:
                    st.error(f"응답 처리 오류: {e}")
                    response_text = f"오류: {e}"

            # 3. 봇 응답을 채팅 기록에 저장
            current_chat_history.append({
                "role": "assistant",
                "content": response_text if response_text else "오류 발생",
                "audio": audio_bytes
            })
            st.session_state.chat_histories[selected_name] = current_chat_history

            # 4. 응답 완료 후 스크립트 재실행하여 UI 완전 업데이트
            st.rerun()

    else: # 선택된 캐릭터 없을 때 초기 화면
        st.info("👈 **왼쪽 목록**에서 대화할 상대를 선택해주세요.")
        st.caption("⚙️ **설정**은 가장 왼쪽 열에서 조절할 수 있습니다.")