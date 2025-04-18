# tts_styles.py

"""
사용 가능한 OpenAI TTS 목소리:
- alloy (남성 추정, 표준적)
- echo (남성 추정, 깊음)
- fable (남성 추정, 동화 구연가)
- onyx (남성 추정, 깊고 전문적)
- nova (여성 추정, 밝고 표현적)
- shimmer (여성 추정, 낮고 부드러움)
"""

TTS_STYLES = {
    "calm_female": {
        "voice": "shimmer",  # 낮고 부드러운 여성 목소리 -> '차분한 여성'으로 매핑
        "model": "tts-1",
        "description": "차분한 여성 목소리 (shimmer)" # 설명 추가
    },
    "energetic_male": {
        "voice": "alloy",    # 표준적인 남성 목소리 -> '에너제틱한 남성'으로 매핑 (완벽히 일치하진 않음)
        "model": "tts-1",
        "description": "에너제틱한 남성 목소리 (alloy)"
    },
    # 필요시 여기에 다른 스타일 추가 가능
    # 예: "professional_male": {"voice": "onyx", "model": "tts-1", "description": "전문적인 남성 목소리 (onyx)"}
    "default": {
        "voice": "alloy",    # 기본값은 alloy로 설정
        "model": "tts-1",
        "description": "기본 목소리 (alloy)"
    }
}

def get_style_params(style_name="default"):
    """
    스타일 이름을 기반으로 TTS 파라미터 딕셔너리를 반환합니다.
    스타일 이름이 유효하지 않으면 기본 스타일 파라미터를 반환합니다.
    """
    # .get() 메서드를 사용하여 키가 없으면 기본값을 반환하도록 함
    return TTS_STYLES.get(style_name, TTS_STYLES["default"])

def get_available_styles():
    """사용 가능한 스타일 이름과 설명을 딕셔너리로 반환합니다."""
    return {name: style.get("description", name) for name, style in TTS_STYLES.items()}