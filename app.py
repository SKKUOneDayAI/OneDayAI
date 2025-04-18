#****************

#pip install -r requirements.txt
#를 치면 필요한 모듈이 설치됨
#환경변수는 별도입니다.

#************



# app.py (Settings for Chunk, Overlap, Temp added)

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
    initial_sidebar_state="expanded" # 설정이 중요해졌으므로 expanded로 시작
)

# --- 필수 사용자 정의 모듈 임포트 ---
try:
    import GetAnswer as ga
    from SpeakAnswer import generate_tts_bytes
except ImportError as e:
    st.error(f"필수 모듈 임포트 오류: {e}")
    # ... (이하 동일) ...
    st.stop()
# ... (기타 모듈 임포트 및 API 키 설정은 이전과 동일) ...
try:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        st.warning("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다. 기능이 제한됩니다.")
        OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"
except KeyError:
     st.error("Streamlit Secrets에 'OPENAI_API_KEY'가 설정되지 않았습니다.")
     OPENAI_API_KEY = "INVALID_KEY_PLACEHOLDER"

api_key_valid = bool(OPENAI_API_KEY and OPENAI_API_KEY != "INVALID_KEY_PLACEHOLDER" and OPENAI_API_KEY != "YOUR_API_KEY_HERE")
if not api_key_valid:
     st.warning("⚠️ OpenAI API 키가 유효하지 않아 RAG 및 TTS 기능이 비활성화됩니다.")


# --- 캐릭터 정보 정의 (변경 없음) ---
CHARACTERS = {
    # ... (이전과 동일, voice 포함) ...
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

# --- CSS 주입 (카카오톡 스타일 적용 - 원본) ---
st.markdown("""
<style>
    /* --- 3단 컬럼 스타일 --- */
    /* 컬럼 1: 설정 */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(1) { /* :nth-of-type(1) 도 가능 */
        background-color: #f8f9fa; /* 설정 배경은 유지 */
        border-right: 1px solid #e9ecef;
        padding: 1rem;
        height: 100vh;
        overflow-y: auto;
    }
    /* 컬럼 2: 캐릭터 목록 */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(2) { /* :nth-of-type(2) 도 가능 */
        background-color: #ffffff; /* 목록 배경은 유지 */
        border-right: 1px solid #e9ecef;
        padding: 1rem;
        height: 100vh;
        overflow-y: auto;
    }
    /* 컬럼 3: 채팅 영역 전체 */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"]:nth-child(3) { /* :nth-of-type(3) 도 가능 */
        background-color: #b2c7d9 !important; /* 카톡 배경색 느낌 (하늘색 계열) */
        padding: 0rem; /* 내부 패딩 제거 */
        height: 100vh;
        display: flex;
        flex-direction: column;
    }
    /* 캐릭터 버튼 스타일 (큰 문제 없었으므로 유지) */
    div[data-testid="stVerticalBlock"] button[kind="secondary"], div[data-testid="stVerticalBlock"] button[kind="primary"] { display: flex !important; align-items: center !important; text-align: left !important; justify-content: start !important; background-color: transparent !important; border: none !important; padding: 10px 8px !important; margin-bottom: 5px !important; border-radius: 8px !important; color: #343a40 !important; width: 100%; font-size: 0.9rem; transition: background-color 0.2s ease; }
    div[data-testid="stVerticalBlock"] button[kind="secondary"]:hover { background-color: #e9ecef !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"] { background-color: #d1e7dd !important; color: #0f5132 !important; font-weight: 600 !important; }
    div[data-testid="stVerticalBlock"] button[kind="primary"]:hover { background-color: #badbcc !important; }
    div[data-testid="stVerticalBlock"] button > div { gap: 0.8rem !important; align-items: center !important; }

    /* --- 카카오톡 스타일 적용 --- */

    /* 채팅 메시지 전체 영역 */
    /* 컬럼 3 내부의 stChatMessages 사용 */
     div[data-testid="stChatMessages"] {
         background-color: transparent; /* 상위 요소 배경색 사용 */
         padding: 1rem 0.5rem; /* 좌우 패딩 약간 줄임 */
         flex-grow: 1;
         overflow-y: auto;
     }

    /* 각 메시지 컨테이너 (메시지 간 간격 추가) */
    div[data-testid="stChatMessage"] {
         margin-bottom: 0.8rem !important; /* 메시지 간 세로 간격 */
         display: flex; /* 내부 요소 정렬 위해 */
         width: 100%;
         align-items: flex-start; /* 아바타와 말풍선 상단 정렬 */
         gap: 8px; /* 아바타와 말풍선 간격 */
    }

     /* 메시지 컨텐츠 래퍼 (아바타 제외) - flex 정렬 위해 추가 가능성 있음 */
     /* div[data-testid="stChatMessage"] > div { ... } */ /* 이 부분은 구조에 따라 조정 */

    /* 메시지 버블 기본 스타일 (실제 내용 감싸는 부분) */
    div[data-testid="stChatMessageContent"] {
         border-radius: 15px !important; /* 말풍선 둥글게 */
         padding: 10px 12px !important; /* 내부 패딩 */
         max-width: 75%; /* 말풍선 최대 너비 */
         width: fit-content; /* 내용물에 맞게 너비 조절 */
         box-shadow: 0 1px 2px rgba(0,0,0,0.1);
         word-wrap: break-word; /* 긴 단어 줄바꿈 */
         order: 1; /* 기본 순서 */
    }

    /* 아바타 기본 스타일 */
    span[data-testid="stAvatar"] {
        order: 0; /* 아바타가 먼저 오도록 */
        line-height: 1; /* 아이콘 수직 정렬 도움 */
    }

    /* 상대방(Assistant) 메시지 스타일 */
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="assistant avatar"]) {
        /* 특별한 정렬 불필요 (기본 왼쪽) */
        /* justify-content: flex-start; */
    }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="assistant avatar"]) div[data-testid="stChatMessageContent"] {
        background-color: white !important; /* 흰색 배경 */
        color: #333 !important; /* 글자색 */
        /* margin-right: auto; */ /* flex 사용 시 불필요 */
    }

    /* 사용자(User) 메시지 스타일 */
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) {
         justify-content: flex-end; /* flex 컨테이너 오른쪽 정렬 */
         /* flex-direction: row-reverse; */ /* 이 방식 대신 order 사용 */
    }
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) div[data-testid="stChatMessageContent"] {
         background-color: #FFEB33 !important; /* 카톡 노란색 배경 */
         color: #3C1E1E !important; /* 글자색 */
         /* margin-left: auto; */ /* flex 사용 시 불필요 */
         order: 0; /* 사용자 메시지는 말풍선이 먼저 오도록 */
    }

    /* 사용자 아바타 숨기기 */
    div[data-testid="stChatMessage"]:has(span[data-testid="stAvatar"][aria-label="user avatar"]) span[data-testid="stAvatar"] {
         display: none !important; /* 아바타 숨김 */
    }


    /* 채팅 입력창 영역 */
    /* stChatInputContainer 또는 stChatInput 사용 확인 */
    div[data-testid="stChatInput"] { /* stChatInputContainer 일 수도 있음 */
         background-color: #ffffff; /* 흰색 배경 */
         border-top: 1px solid #e0e0e0; /* 경계선 색상 변경 */
         padding: 0.5rem 0.8rem; /* 패딩 조절 */
    }
    /* 채팅 입력창 내부 textarea */
    div[data-testid="stChatInput"] textarea { /* 혹은 하위의 다른 testid */
         background-color: #ffffff !important; /* 흰색 배경 */
         border: 1px solid #e0e0e0 !important; /* 테두리 */
         border-radius: 18px !important; /* 둥글게 */
         padding: 8px 12px;
    }

    /* 오디오 플레이어 */
    div[data-testid="stAudio"] {
          margin-top: 5px;
    }

</style>
""", unsafe_allow_html=True)

# --- 핵심 기능 초기화 ---
llm_client = None
if api_key_valid:
    try:
        if "llm_client" not in st.session_state:
            st.session_state.llm_client = OpenAI(api_key=OPENAI_API_KEY)
        llm_client = st.session_state.llm_client # 세션에서 가져오기
    except Exception as e:
        st.error(f"OpenAI 클라이언트 초기화 실패: {e}")
        api_key_valid = False # 실패 시 키 무효 처리

# --- RAG 체인 재생성 함수 ---
# @st.cache_data # 벡터스토어 로딩/생성 부분만 캐싱 고려 가능 (복잡도 증가)
def recreate_active_chain():
    """현재 설정값으로 RAG 체인을 다시 생성하고 세션에 저장합니다."""
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

        status_placeholder = st.empty() # 상태 메시지 표시 영역
        status_placeholder.info(f"{selected_name} 대화 준비 중 (T={temp}, C={c_size}, O={c_overlap})... 인덱스 생성 시 시간이 걸릴 수 있습니다.")
        try:
            # 업데이트된 설정값으로 체인 초기화
            st.session_state.active_chain = ga.initialize_qa_system(
                character_system_prompt=char_prompt,
                temperature=temp,
                chunk_size=c_size,
                chunk_overlap=c_overlap
            )
            if not st.session_state.active_chain:
                 status_placeholder.error(f"{selected_name} RAG 체인 생성 실패. 터미널 로그를 확인하세요.")
            else:
                 # 성공 메시지는 짧게 토스트로 표시하거나 생략
                 # status_placeholder.success(f"{selected_name} 대화 준비 완료!")
                 # time.sleep(1)
                 status_placeholder.empty() # 성공 시 메시지 제거
                 print(f"Active chain recreated for {selected_name} with settings T={temp}, C={c_size}, O={c_overlap}")

        except Exception as chain_e:
            status_placeholder.error(f"체인 생성 중 오류: {chain_e}")
            print(f"!!! Chain recreation error: {chain_e}")
            traceback.print_exc() # 상세 오류 로그
            st.session_state.active_chain = None # 실패 시 None 설정
    else:
         print("캐릭터가 선택되지 않아 체인을 재생성하지 않습니다.")
         st.session_state.active_chain = None # 캐릭터 미선택 시 체인 없음


# --- 세션 상태 초기화 (설정값 추가) ---
if "chat_histories" not in st.session_state:
    st.session_state.chat_histories = {name: [] for name in CHARACTERS}
if "selected_character" not in st.session_state:
    st.session_state.selected_character = None
if "active_chain" not in st.session_state:
     st.session_state.active_chain = None
if "autoplay_next_audio" not in st.session_state:
     st.session_state.autoplay_next_audio = False

# 설정 기본값 정의 및 세션 상태 초기화
default_temp = 0.7
default_chunk_size = 1000
default_chunk_overlap = 100

if "temperature" not in st.session_state:
    st.session_state.temperature = default_temp
if "chunk_size" not in st.session_state:
    st.session_state.chunk_size = default_chunk_size
if "chunk_overlap" not in st.session_state:
    st.session_state.chunk_overlap = default_chunk_overlap


# --- 3단 레이아웃 정의 ---
col_config, col_list, col_chat = st.columns([1.2, 2, 4]) # 설정 컬럼 약간 넓게

# --- 컬럼 1: 설정 ---
with col_config:
    st.header("⚙️ 설정")
    settings_disabled = not api_key_valid # API 키 없으면 설정 비활성화

    # Temperature 슬라이더 (이제 RAG LLM에 적용됨)
    st.session_state.temperature = st.slider(
        "Temperature (답변 다양성)", 0.0, 1.0, st.session_state.temperature, 0.05,
        key="temp_slider",
        help="RAG 답변 생성 시 LLM의 다양성을 조절합니다. 높을수록 창의적이지만 부정확할 수 있습니다.",
        on_change=recreate_active_chain, # 값 변경 시 체인 재생성 콜백
        disabled=settings_disabled
    )

    st.markdown("---")
    st.subheader("RAG 설정")
    # Chunk Size 슬라이더
    st.session_state.chunk_size = st.slider(
        "Chunk Size (청크 크기)", min_value=100, max_value=2000, value=st.session_state.chunk_size, step=50,
        key="chunk_size_slider",
        help="문서를 나눌 기준 크기(글자 수). 변경 시 데이터 재처리가 필요할 수 있습니다.",
        on_change=recreate_active_chain, # 값 변경 시 체인 재생성 콜백
        disabled=settings_disabled
    )

    # Chunk Overlap 슬라이더
    # overlap은 chunk_size보다 작아야 함
    max_overlap = st.session_state.chunk_size - 50 if st.session_state.chunk_size > 100 else 50
    st.session_state.chunk_overlap = st.slider(
        "Chunk Overlap (청크 중첩)", min_value=0, max_value=max_overlap, value=min(st.session_state.chunk_overlap, max_overlap), step=10, # 현재 값이 최대값 초과하지 않도록
        key="chunk_overlap_slider",
        help="나눠진 청크끼리 겹치는 글자 수. 검색 정확도에 영향을 줄 수 있습니다. 변경 시 데이터 재처리가 필요할 수 있습니다.",
        on_change=recreate_active_chain, # 값 변경 시 체인 재생성 콜백
        disabled=settings_disabled
    )
    # 도움말 추가
    st.caption("Chunk Size 또는 Overlap 변경 시, 해당 설정에 맞는 데이터 인덱스를 처음 로드할 때 시간이 소요될 수 있습니다.")


# --- 컬럼 2: 캐릭터 목록 ---
with col_list:
    st.header("대화 상대")
    for name, details in CHARACTERS.items():
        is_disabled = not api_key_valid
        button_type = "primary" if st.session_state.selected_character == name else "secondary"

        if st.button(f"{details['avatar']} {name}", key=f"char_btn_{name}", use_container_width=True, type=button_type, disabled=is_disabled):
            if st.session_state.selected_character != name:
                 st.session_state.selected_character = name
                 st.session_state.autoplay_next_audio = False
                 # 캐릭터 변경 시에도 체인 재생성 함수 호출
                 recreate_active_chain()
                 st.rerun() # 체인 생성 후 UI 업데이트

        if is_disabled:
             st.caption("(API 키 필요)")


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
             # 체인이 로드되지 않았거나 API 키가 없을 때도 삭제는 가능하도록 함
             delete_disabled = selected_name not in st.session_state.chat_histories or not st.session_state.chat_histories[selected_name]
             if st.button(f"🧹 기록 삭제", key=f"clear_btn_{selected_name}", help=f"'{selected_name}' 와(과)의 대화 내역을 지웁니다.", disabled=delete_disabled):
                 if selected_name in st.session_state.chat_histories:
                     st.session_state.chat_histories[selected_name] = []
                     if hasattr(st.session_state.active_chain, 'memory'):
                          try: # 체인이 None일 수도 있으므로 try-except
                               st.session_state.active_chain.memory.clear()
                               print(f"{selected_name} 체인 메모리 초기화됨.")
                          except AttributeError:
                               print("활성 체인 또는 메모리 없음, 초기화 건너뜀.")
                     st.toast(f"'{selected_name}' 대화 기록 삭제 완료!", icon="🧹")
                     st.session_state.autoplay_next_audio = False
                     time.sleep(0.5)
                     st.rerun()
        st.divider()


        # --- 채팅 메시지 표시 영역 ---
        # ... (이전과 동일, 최신 메시지만 자동 재생) ...
        chat_display_area = st.container()
        with chat_display_area:
            messages = st.session_state.chat_histories.get(selected_name, [])
            for index, message in enumerate(messages):
                avatar_display = selected_details['avatar'] if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar_display):
                    st.markdown(message["content"])
                    is_last_message = (index == len(messages) - 1)
                    if is_last_message and message["role"] == "assistant" and message.get("audio") and st.session_state.get("autoplay_next_audio", False):
                        st.audio(message["audio"], format="audio/mp3", autoplay=True)
                        st.session_state.autoplay_next_audio = False


        # --- 채팅 입력 및 응답 처리 ---
        # 활성 체인이 준비되었는지 + API 키 유효성 동시 확인
        chat_input_disabled = not st.session_state.get("active_chain") or not api_key_valid

        if prompt := st.chat_input(f"{selected_name}에게 메시지 보내기...", key=f"chat_input_{selected_name}", disabled=chat_input_disabled):

            current_chat_history = st.session_state.chat_histories.get(selected_name, [])
            current_chat_history.append({"role": "user", "content": prompt})
            st.session_state.chat_histories[selected_name] = current_chat_history

            response_text = None
            audio_bytes = None
            st.session_state.autoplay_next_audio = False

            with st.spinner("답변 생성 중..."):
                try:
                    if st.session_state.active_chain:
                        # get_answer 호출 시 체인 전달
                        response_text = ga.get_answer(st.session_state.active_chain, prompt)
                    else:
                        response_text = "오류: RAG 시스템 준비 안됨. 캐릭터를 다시 선택하거나 설정을 확인하세요."

                    # --- TTS Generation ---
                    if api_key_valid and response_text and not response_text.startswith(("오류:", "API 오류", "[LLM", "[{", "알 수 없는", "답변을 찾을 수 없습니다", "답변 형식 오류")):
                        try:
                            character_voice = selected_details.get("voice", "nova")
                            print(f"--- TTS 호출 시도: 캐릭터='{selected_name}', 목소리='{character_voice}', 텍스트='{response_text[:50]}...'")
                            # TTS 생성 시 llm_client 직접 사용 대신 SpeakAnswer 모듈 사용
                            audio_bytes = generate_tts_bytes(response_text, style_name=character_voice)
                            print(f"--- TTS 결과: {'Bytes 생성됨 (길이: ' + str(len(audio_bytes)) + ')' if audio_bytes else 'None'}")
                            if audio_bytes:
                                st.session_state.autoplay_next_audio = True
                        except Exception as tts_e:
                            st.warning(f"TTS 생성 중 오류 발생: {tts_e}")
                            print(f"!!! TTS Generation Error: {tts_e}")
                            audio_bytes = None
                    # ... (TTS 건너뛰기 로그) ...

                except Exception as e:
                    st.error(f"응답 처리 중 예외 발생: {e}")
                    print(f"!!! Top Level Response Processing Error: {e}")
                    traceback.print_exc()
                    response_text = f"오류: 응답 처리 중 문제가 발생했습니다."

            # 봇 응답 저장 및 UI 업데이트
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