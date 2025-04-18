# tts_styles.py (음성 스타일 이름과 파라미터 제공 역할)

_AVAILABLE_STYLES = {
    "alloy": "Alloy (기본 남성)",
    "echo": "Echo (강조 남성)",
    "fable": "Fable (스토리텔링)",
    "onyx": "Onyx (깊은 남성)",
    "nova": "Nova (밝은 여성)", # <- 기본값으로 사용될 수 있음
    "shimmer": "Shimmer (부드러운 여성)",
    # 사용자 정의 예시 (실제 목소리 매핑 필요 시 get_style_params 수정)
    "calm_female": "차분한 여성 (Shimmer 사용)",
    "cheerful_male": "활기찬 남성 (Echo 사용)"
}

# 기본 스타일 이름 (이제 app.py에서 직접 사용하지 않음)
_DEFAULT_TTS_STYLE_NAME = "nova"

def get_available_styles():
    """사용 가능한 스타일 이름과 설명을 담은 딕셔너리 반환 (app.py에서 사용 안 함)"""
    return _AVAILABLE_STYLES.copy()

def get_default_style_name():
    """기본 스타일 이름 반환 (app.py에서 사용 안 함)"""
    return _DEFAULT_TTS_STYLE_NAME

def get_style_params(style_name):
    """스타일 이름에 해당하는 TTS 파라미터(목소리 이름) 반환"""
    # 실제 OpenAI voice 파라미터 값으로 매핑
    voice_map = {
        "alloy": "alloy",
        "echo": "echo",
        "fable": "fable",
        "onyx": "onyx",
        "nova": "nova",
        "shimmer": "shimmer",
        "calm_female": "shimmer", # 사용자 정의 -> 실제 목소리
        "cheerful_male": "echo",  # 사용자 정의 -> 실제 목소리
    }
    # 유효한 이름이면 해당 목소리, 아니면 기본 목소리(예: nova) 반환
    voice = voice_map.get(style_name, _DEFAULT_TTS_STYLE_NAME)
    return {"voice": voice}