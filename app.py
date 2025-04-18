# app.py (모든 식별된 약어 TTS 발음 수정 포함)

import streamlit as st
import os
import io
import time
import traceback # 오류 로깅용
from openai import OpenAI
# --- 페이지 설정 (가장 먼저!) ---
st.set_page_config(
    page_title="멀티 페르소나 야구 챗봇",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 필수 사용자 정의 모듈 임포트 ---
try:
    import GetAnswer as ga
    from SpeakAnswer import generate_tts_bytes
except ImportError as e:
    st.error(f"필수 모듈 임포트 오류: {e}")
    st.stop()

# --- OpenAI API 키 설정 ---
try:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        st.warning("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다. 기능이 제한됩니다.")
        OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"
except KeyError:
     st.error("Streamlit Secrets에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
     OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"

api_key_valid = bool(OPENAI_API_KEY and OPENAI_API_KEY != "INVALID_KEY_PLACEHOLDER" and not OPENAI_API_KEY.startswith("YOUR_API_KEY"))
if not api_key_valid:
     st.warning("⚠️ OpenAI API 키가 유효하지 않아 RAG 및 TTS 기능이 비활성화됩니다.")


# --- 캐릭터 정보 정의 ---
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

# --- CSS 주입 (카카오톡 스타일 적용 - 원본 기반) ---
# 참고: 여전히 채팅 배경/사용자 말풍선 색상 적용 문제가 있을 수 있음
st.markdown("""
<style>
    /* ... 이전과 동일한 CSS 코드 ... */
    /* --- 3단 컬럼 스타일 --- */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(1) { background-color: #f8f9fa; border-right: 1px solid #e9ecef; padding: 1rem; height: 100vh; overflow-y: auto; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2) { background-color: #ffffff; border-right: 1px solid #e9ecef; padding: 1rem; height: 100vh; overflow-y: auto; }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(3) { background-color: #b2c7d9 !important; padding: 0rem; height: 100vh; display: flex; flex-direction: column; }
    /* 캐릭터 버튼 스타일 */
    div[data-testid="stVerticalBlock"] button[kind="secondary"], div[data-testid="stVerticalBlock"] button[kind="primary"] { display: flex !important; align-items: center !important; text-align: left !important; justify-content: start !important; background-color: transparent !important; border: none !important; padding: 10px 8px !important; margin-bottom: 5px !important; border-radius: 8px !important; color: #343a40 !important; width: 100%; font-size: 0.9rem; transition: background-color 0.2s ease; }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover { background-color: #e9ecef !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"] { background-color: #d1e7dd !important; color: #0f5132 !important; font-weight: 600 !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover { background-color: #badbcc !important; }
    div[data-testid="stVerticalBlock"] button > div { gap: 0.8rem !important; align-items: center !important; }
    /* --- 카카오톡 스타일 적용 --- */
     div[data-testid="stChatMessages"] { background-color: #b2c7d9 !important; padding: 1rem 0.5rem; flex-grow: 1; overflow-y: auto; }
    div[data-testid="stChatMessage"] { margin-bottom: 0.8rem !important; display: flex; width: 100%; align-items: flex-start; gap: 8px; }
    div[data-testid="stChatMessageContent"] { border-radius: 15px !important; padding: 10px 12px !important; max-width: 75%; width: fit-content; box-shadow: 0 1px 2px rgba(0,0,0,0.1); word-wrap: break-word; order: 1; }
    span[data-testid="stAvatar"] { order: 0; line-height: 1; }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="assistant avatar"]) div[data-testid="stChatMessageContent"] { background-color: white !important; color: #333 !important; }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) { justify-content: flex-end; }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) div[data-testid="stChatMessageContent"] { background-color: #FFEB33 !important; color: #3C1E1E !important; order: 0; }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) span[data-testid="stAvatar"] { display: none !important; }
    div[data-testid="stChatInput"] { background-color: #ffffff; border-top: 1px solid #e0e0e0; padding: 0.5rem 0.8rem; }
    div[data-testid="stChatInput"] textarea { background-color: #ffffff !important; border: 1px solid #e0e0e0 !important; border-radius: 18px !important; padding: 8px 12px; }
    div[data-testid="stAudio"] { margin-top: 5px; }
</style>
""", unsafe_allow_html=True)


# --- 핵심 기능 초기화 ---
llm_client = None
if api_key_valid:
    try:
        if "llm_client" not in st.session_state:
            st.session_state.llm_client = OpenAI(api_key=OPENAI_API_KEY)
        llm_client = st.session_state.llm_client
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 실패: {e}")
        api_key_valid = False

# --- RAG 체인 재생성 함수 ---
def recreate_active_chain():
    # ... (이전과 동일) ...
    if not api_key_valid:
        st.warning("API 키가 유효하지 않아 RAG 체인을 생성할 수 없습니다.")
        st.session_state.active_chain = None
        return
    if st.session_state.selected_character:
        selected_name = st.session_state.selected_character
        selected_details = CHARACTERS[selected_name]
        char_prompt = selected_details["system_prompt"]
        temp = st.session_state.temperature
        c_size = st.session_state.chunk_size
        c_overlap = st.session_state.chunk_overlap
        status_placeholder = st.empty()
        status_placeholder.info(f"{selected_name} 대화 준비 중 (T={temp}, C={c_size}, O={c_overlap})... 인덱스 생성 시 시간이 걸릴 수 있습니다.")
        try:
            st.session_state.active_chain = ga.initialize_qa_system(
                character_system_prompt=char_prompt, temperature=temp, chunk_size=c_size, chunk_overlap=c_overlap
            )
            if not st.session_state.active_chain:
                 status_placeholder.error(f"{selected_name} RAG 체인 생성 실패. 터미널 로그를 확인하세요.")
            else:
                 status_placeholder.empty()
                 print(f"Active chain recreated for {selected_name} with settings T={temp}, C={c_size}, O={c_overlap}")
        except Exception as chain_e:
            status_placeholder.error(f"체인 생성 중 오류: {chain_e}")
            print(f"!!! Chain recreation error: {chain_e}")
            traceback.print_exc()
            st.session_state.active_chain = None
    else:
         print("캐릭터가 선택되지 않아 체인을 재생성하지 않습니다.")
         st.session_state.active_chain = None


# --- 세션 상태 초기화 ---
# ... (이전과 동일) ...
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {name: [] for name in CHARACTERS}
if "selected_character" not in st.session_state:
    st.session_state.selected_character = None
if "active_chain" not in st.session_state:
     st.session_state.active_chain = None
if "autoplay_next_audio" not in st.session_state:
     st.session_state.autoplay_next_audio = False
default_temp = 0.7
default_chunk_size = 1000
default_chunk_overlap = 100
if "temperature" not in st.session_state: st.session_state.temperature = default_temp
if "chunk_size" not in st.session_state: st.session_state.chunk_size = default_chunk_size
if "chunk_overlap" not in st.session_state: st.session_state.chunk_overlap = default_chunk_overlap


# --- 3단 레이아웃 정의 ---
col_config, col_list, col_chat = st.columns([1.2, 2, 4])

# --- 컬럼 1: 설정 ---
with col_config:
    # ... (이전과 동일) ...
    st.header("⚙️ 설정")
    settings_disabled = not api_key_valid
    st.session_state.temperature = st.slider(
        "Temperature (답변 다양성)", 0.0, 1.0, st.session_state.temperature, 0.05, key="temp_slider",
        help="RAG 답변 생성 시 LLM의 다양성을 조절합니다. 높을수록 창의적이지만 부정확할 수 있습니다.",
        on_change=recreate_active_chain, disabled=settings_disabled
    )
    st.markdown("---")
    st.subheader("RAG 설정")
    st.session_state.chunk_size = st.slider(
        "Chunk Size (청크 크기)", 100, 2000, st.session_state.chunk_size, 50, key="chunk_size_slider",
        help="문서를 나눌 기준 크기(글자 수). 변경 시 데이터 재처리가 필요할 수 있습니다.",
        on_change=recreate_active_chain, disabled=settings_disabled
    )
    max_overlap = st.session_state.chunk_size - 50 if st.session_state.chunk_size > 100 else 50
    st.session_state.chunk_overlap = st.slider(
        "Chunk Overlap (청크 중첩)", 0, max_overlap, min(st.session_state.chunk_overlap, max_overlap), 10, key="chunk_overlap_slider",
        help="나눠진 청크끼리 겹치는 글자 수. 검색 정확도에 영향을 줄 수 있습니다. 변경 시 데이터 재처리가 필요할 수 있습니다.",
        on_change=recreate_active_chain, disabled=settings_disabled
    )
    st.caption("Chunk Size 또는 Overlap 변경 시, 해당 설정에 맞는 데이터 인덱스를 처음 로드할 때 시간이 소요될 수 있습니다.")


# --- 컬럼 2: 캐릭터 목록 ---
with col_list:
    # ... (이전과 동일) ...
    st.header("대화 상대")
    for name, details in CHARACTERS.items():
        is_disabled = not api_key_valid
        button_type = "primary" if st.session_state.selected_character == name else "secondary"
        if st.button(f"{details['avatar']} {name}", key=f"char_btn_{name}", use_container_width=True, type=button_type, disabled=is_disabled):
            if st.session_state.selected_character != name:
                 st.session_state.selected_character = name
                 st.session_state.autoplay_next_audio = False
                 recreate_active_chain()
                 st.rerun()
        if is_disabled: st.caption("(API 키 필요)")


# --- 컬럼 3: 채팅 영역 ---
with col_chat:
    if st.session_state.selected_character:
        selected_name = st.session_state.selected_character
        selected_details = CHARACTERS[selected_name]

        # --- 캐릭터 정보 및 대화 삭제 버튼 ---
        # ... (이전과 동일) ...
        sub_col1, sub_col2 = st.columns([4, 1])
        with sub_col1:
             st.markdown(f"#### {selected_details['avatar']} {selected_name}")
             st.caption(selected_details['description'])
        with sub_col2:
             delete_disabled = selected_name not in st.session_state.chat_histories or not st.session_state.chat_histories[selected_name]
             if st.button(f"🧹 기록 삭제", key=f"clear_btn_{selected_name}", help=f"'{selected_name}' 와(과)의 대화 내역을 지웁니다.", disabled=delete_disabled):
                 if selected_name in st.session_state.chat_histories:
                     st.session_state.chat_histories[selected_name] = []
                     if hasattr(st.session_state.active_chain, 'memory') and st.session_state.active_chain:
                          try: st.session_state.active_chain.memory.clear(); print(f"{selected_name} 체인 메모리 초기화됨.")
                          except AttributeError: print("활성 체인에 메모리가 없거나 clear() 메소드 없음.")
                          except Exception as mem_e: print(f"메모리 초기화 중 오류: {mem_e}")
                     st.toast(f"'{selected_name}' 대화 기록 삭제 완료!", icon="🧹")
                     st.session_state.autoplay_next_audio = False
                     time.sleep(0.5)
                     st.rerun()
        st.divider()

        # --- 채팅 메시지 표시 영역 ---
        # ... (이전과 동일) ...
        chat_display_area = st.container()
        with chat_display_area:
            messages = st.session_state.chat_histories.get(selected_name, [])
            for index, message in enumerate(messages):
                avatar_display = selected_details['avatar'] if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar_display):
                    st.markdown(message["content"])
                    is_last_message = (index == len(messages) - 1)
                    if is_last_message and message["role"] == "assistant" and message.get("audio") and st.session_state.get("autoplay_next_audio", False):
                        try: st.audio(message["audio"], format="audio/mp3", autoplay=True)
                        except Exception as audio_e: st.warning(f"오디오 재생 중 오류: {audio_e}")
                        finally: st.session_state.autoplay_next_audio = False

        # --- 채팅 입력 및 응답 처리 ---
        chat_input_disabled = not st.session_state.get("active_chain") or not api_key_valid
        if prompt := st.chat_input(f"{selected_name}에게 메시지 보내기...", key=f"chat_input_{selected_name}", disabled=chat_input_disabled):

            current_chat_history = st.session_state.chat_histories.get(selected_name, [])
            current_chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_histories[selected_name] = current_chat_history
            st.session_state.autoplay_next_audio = False

            response_text = None
            audio_bytes = None

            with st.spinner("답변 생성 중..."):
                try:
                    if st.session_state.active_chain:
                        response_text = ga.get_answer(st.session_state.active_chain, prompt)
                    else:
                        response_text = "오류: RAG 시스템 준비 안됨. 캐릭터를 다시 선택하거나 설정을 확인하세요."

                    # --- TTS Generation ---
                    if api_key_valid and response_text and not response_text.startswith(("오류:", "API 오류", "[LLM", "[{", "알 수 없는", "답변을 찾을 수 없습니다", "답변 형식 오류")):
                        try:
                            character_voice = selected_details.get("voice", "nova")
                            print(f"--- TTS 호출 시도: 캐릭터='{selected_name}', 목소리='{character_voice}', 텍스트='{response_text[:50]}...'")

                            # --- TTS 입력 텍스트 전처리 (약어 발음 수정) ---
                            # 원본 텍스트 복사
                            tts_input_text = response_text

                            # 팀 약어 처리 (구체적인 것 먼저)
                            tts_input_text = tts_input_text.replace("LG트윈스", "엘 지 트윈스")
                            tts_input_text = tts_input_text.replace("SSG 랜더스", "에스 에스 지 랜더스")
                            tts_input_text = tts_input_text.replace("KT 위즈", "케이 티 위즈")
                            tts_input_text = tts_input_text.replace("NC 다이노스", "엔 씨 다이노스")

                            # 팀 약어 + 공백 처리
                            tts_input_text = tts_input_text.replace("LG ", "엘 지 ")
                            tts_input_text = tts_input_text.replace("SSG ", "에스 에스 지 ")
                            tts_input_text = tts_input_text.replace("KT ", "케이 티 ")
                            tts_input_text = tts_input_text.replace("NC ", "엔 씨 ")

                            # 팀 약어만 있는 경우 처리 (다른 약어 처리 전에)
                            tts_input_text = tts_input_text.replace("LG", "엘 지")
                            tts_input_text = tts_input_text.replace("SSG", "에스 에스 지")
                            tts_input_text = tts_input_text.replace("KT", "케이 티")
                            tts_input_text = tts_input_text.replace("NC", "엔 씨")

                            # 주요 통계 약어 처리 (긴 것, 특수한 것 먼저)
                            tts_input_text = tts_input_text.replace("rRA9pf", "알 알 에이 나인 피 에프")
                            tts_input_text = tts_input_text.replace("rRA9", "알 알 에이 나인")
                            tts_input_text = tts_input_text.replace("RA9", "알 에이 나인")
                            tts_input_text = tts_input_text.replace("ERA", "이 알 에이")
                            tts_input_text = tts_input_text.replace("oWAR", "오 더블유 에이 알")
                            tts_input_text = tts_input_text.replace("dWAR", "디 더블유 에이 알")
                            tts_input_text = tts_input_text.replace("WAR", "더블유 에이 알")
                            tts_input_text = tts_input_text.replace("WHIP", "더블유 에이치 아이 피")
                            tts_input_text = tts_input_text.replace("FIP", "에프 아이 피")
                            tts_input_text = tts_input_text.replace("TBF", "티 비 에프")
                            tts_input_text = tts_input_text.replace("IBB", "아이 비 비") # 혹시 IBB도 사용될 경우 대비
                            tts_input_text = tts_input_text.replace("IB", "아이 비")
                            tts_input_text = tts_input_text.replace("ROE", "알 오 이")
                            tts_input_text = tts_input_text.replace("SHO", "에스 에이치 오")
                            tts_input_text = tts_input_text.replace("wRC+", "더블유 알 씨 플러스")
                            tts_input_text = tts_input_text.replace("AVG", "에이 브이 지")
                            tts_input_text = tts_input_text.replace("OBP", "오 비 피")
                            tts_input_text = tts_input_text.replace("SLG", "에스 엘 지")
                            tts_input_text = tts_input_text.replace("OPS", "오 피 에스")
                            tts_input_text = tts_input_text.replace("RBI", "알 비 아이")
                            tts_input_text = tts_input_text.replace("GDP", "지 디 피")
                            tts_input_text = tts_input_text.replace("ePA", "이 피 에이")

                            # 나머지 약어들 (알파벳 순 또는 길이 순)
                            tts_input_text = tts_input_text.replace("GS", "지 에스")
                            tts_input_text = tts_input_text.replace("GR", "지 알")
                            tts_input_text = tts_input_text.replace("GF", "지 에프")
                            tts_input_text = tts_input_text.replace("CG", "씨 지")
                            tts_input_text = tts_input_text.replace("HD", "에이치 디")
                            tts_input_text = tts_input_text.replace("IP", "아이 피")
                            tts_input_text = tts_input_text.replace("ER", "이 알")
                            tts_input_text = tts_input_text.replace("HR", "에이치 알")
                            tts_input_text = tts_input_text.replace("BB", "비 비")
                            tts_input_text = tts_input_text.replace("HP", "에이치 피")
                            tts_input_text = tts_input_text.replace("SO", "에스 오")
                            tts_input_text = tts_input_text.replace("BK", "비 케이")
                            tts_input_text = tts_input_text.replace("WP", "더블유 피")
                            tts_input_text = tts_input_text.replace("PA", "피 에이")
                            tts_input_text = tts_input_text.replace("AB", "에이 비")
                            tts_input_text = tts_input_text.replace("TB", "티 비")
                            tts_input_text = tts_input_text.replace("SB", "에스 비")
                            tts_input_text = tts_input_text.replace("CS", "씨 에스")
                            tts_input_text = tts_input_text.replace("SH", "에스 에이치")
                            tts_input_text = tts_input_text.replace("SF", "에스 에프")
                            tts_input_text = tts_input_text.replace("2B", "이 루타") # 숫자는 한글로 읽도록 수정
                            tts_input_text = tts_input_text.replace("3B", "삼 루타") # 숫자는 한글로 읽도록 수정

                            # 한 글자 약어 (다른 약어 처리 후 마지막에)
                            tts_input_text = tts_input_text.replace(" G", " 게임") # G는 게임 수로 읽도록
                            tts_input_text = tts_input_text.replace(" W", " 승") # W는 승리로 읽도록
                            tts_input_text = tts_input_text.replace(" L", " 패") # L은 패배로 읽도록
                            tts_input_text = tts_input_text.replace(" S", " 세이브") # S는 세이브로 읽도록
                            tts_input_text = tts_input_text.replace(" R", " 득점") # R은 득점/실점으로 읽도록 (문맥 따라 다름 주의)
                            tts_input_text = tts_input_text.replace(" H", " 안타") # H는 안타로 읽도록

                            # ---------------------------------------------

                            # 수정된 텍스트로 TTS 호출
                            print(f"--- TTS 전처리 후 텍스트: '{tts_input_text[:50]}...'")
                            audio_bytes = generate_tts_bytes(tts_input_text, style_name=character_voice)
                            print(f"--- TTS 결과: {'Bytes 생성됨 (길이: ' + str(len(audio_bytes)) + ')' if audio_bytes else 'None'}")
                            if audio_bytes:
                                st.session_state.autoplay_next_audio = True
                        except Exception as tts_e:
                            st.warning(f"TTS 생성 중 오류 발생: {tts_e}")
                            print(f"!!! TTS Generation Error: {tts_e}")
                            traceback.print_exc()
                            audio_bytes = None
                    else:
                         if not api_key_valid: print("--- TTS 건너뜀: API 키 유효하지 않음")
                         elif not response_text: print("--- TTS 건너뜀: 응답 텍스트 없음")
                         else: print(f"--- TTS 건너뜀: 응답 텍스트 형식 부적합 ('{response_text[:20]}...')")

                except Exception as e:
                    st.error(f"응답 처리 중 예외 발생: {e}")
                    print(f"!!! Top Level Response Processing Error: {e}")
                    traceback.print_exc()
                    response_text = f"오류: 응답 처리 중 문제가 발생했습니다."

            # 봇 응답 저장
            current_chat_history.append({
                "role": "assistant",
                "content": response_text if response_text else "응답 생성 실패",
                "audio": audio_bytes
            })
            st.session_state.chat_histories[selected_name] = current_chat_history
            st.rerun()

    else: # 선택된 캐릭터 없을 때
        st.info("👈 **왼쪽 목록**에서 대화할 상대를 선택해주세요.")
        st.caption("⚙️ **설정**은 가장 왼쪽 열에서 조절할 수 있습니다.")