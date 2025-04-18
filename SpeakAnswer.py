# SpeakAnswer.py

import os
from openai import OpenAI, OpenAIError
from tts_styles import get_style_params, get_default_style_name
# import streamlit as st # st를 사용하지 않는다면 이 import도 제거 가능

# --- 이 부분을 삭제하세요 ---
# st.set_page_config(   # <--- 삭제 시작
#     page_title="멀티 페르소나 야구 챗봇",
#     page_icon="⚾",
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )                     # <--- 삭제 끝
# -------------------------


def generate_tts_bytes(text, style_name=None):
    """텍스트를 음성으로 변환하여 bytes 객체로 반환합니다."""
    # ... (나머지 함수 코드는 그대로 유지) ...
    client = OpenAI() # API 키는 환경 변수에서 자동으로 로드됨

    if not style_name:
        style_name = get_default_style_name() # 스타일 이름이 없으면 기본값 사용

    # 스타일 이름으로부터 TTS 파라미터 가져오기
    tts_params = get_style_params(style_name)
    if not tts_params or "voice" not in tts_params:
         print(f"오류: 스타일 '{style_name}'에 대한 유효한 TTS 파라미터를 얻지 못했습니다.")
         # 대체 목소리 설정 또는 오류 반환
         tts_params = {"voice": "alloy"} # 안전한 기본값

    try:
        response = client.audio.speech.create(
            model="tts-1-hd",          # 또는 "tts-1-hd"
            voice=tts_params["voice"], # tts_styles에서 얻은 목소리 사용
            input=text,
            # 필요한 경우 speed, response_format 등 다른 파라미터 추가
        )
        # 오디오 데이터를 bytes로 반환
        audio_bytes = response.read()
        return audio_bytes

    except OpenAIError as e:
        print(f"OpenAI TTS API 오류: {e}")
        return None
    except Exception as e:
        print(f"TTS 생성 중 예상치 못한 오류: {e}")
        return None