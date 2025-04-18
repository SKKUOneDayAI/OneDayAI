# SpeakAnswer_Bytes.py
# 목적: OpenAI TTS API를 사용하여 텍스트를 음성으로 변환하고,
#       재생 가능한 오디오 데이터(bytes)를 반환합니다.
#       Streamlit과 같은 웹 프레임워크에서 사용하기 적합합니다.

import os
import io                     # 바이트 데이터를 다루기 위해 필요할 수 있음 (현재 코드에선 직접 사용X)
from openai import OpenAI, OpenAIError # OpenAI 클라이언트 및 오류 클래스

# --- 사용자 정의 모듈 임포트 ---
# tts_styles.py 파일이 같은 경로에 있다고 가정합니다.
try:
    from tts_styles import get_style_params, get_available_styles # 스타일 정보 가져오기
except ImportError:
    print("경고: 'tts_styles.py' 모듈을 찾을 수 없어 기본 스타일만 사용합니다.")
    # tts_styles.py가 없을 경우를 대비한 임시 함수/데이터
    def get_style_params(style_name="default"):
        """tts_styles.py가 없을 때 사용할 기본 파라미터 반환"""
        # 실제 OpenAI에 존재하는 목소리 중 하나를 기본값으로 지정
        return {"voice": "alloy", "model": "tts-1", "description": "기본 (alloy)"}
    def get_available_styles():
        """tts_styles.py가 없을 때 사용할 기본 스타일 목록"""
        return {"default": "기본 (alloy)"}

# --- OpenAI API 키 설정 ---
# 보안을 위해 환경 변수나 Streamlit Secrets 사용을 강력히 권장합니다.
# 예: OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# 로컬 테스트용 임시 설정 (실제 사용 시 YOUR_API_KEY_HERE 부분 대체 또는 환경변수 사용)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")

if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
     # API 키가 없으면 경고 메시지를 출력합니다.
     # 실제 서비스에서는 이 경우 오류를 발생시키거나 TTS 기능을 비활성화해야 할 수 있습니다.
     print("경고: OpenAI API 키가 설정되지 않았습니다. TTS 기능이 작동하지 않을 수 있습니다.")
     # 필요하다면 아래 줄의 주석을 해제하여 오류를 발생시킬 수 있습니다.
     # raise ValueError("OpenAI API 키가 설정되지 않았습니다. 환경 변수 또는 구성을 확인하세요.")

# --- TTS 생성 함수 (Bytes 반환) ---
def generate_tts_bytes(text_to_speak, style_name="default"):
    """
    OpenAI TTS API를 호출하여 텍스트를 음성으로 변환하고,
    결과 오디오 데이터를 MP3 형식의 bytes 객체로 반환합니다.

    Args:
        text_to_speak (str): 음성으로 변환할 텍스트 문자열.
        style_name (str): 'tts_styles.py'에 정의된 스타일 이름. 기본값은 'default'.

    Returns:
        bytes or None: 성공 시 MP3 오디오 데이터(bytes). 실패 시 None 반환.
    """
    # 입력 텍스트 유효성 검사
    if not text_to_speak:
        print("오류: 음성으로 변환할 텍스트가 비어 있습니다.")
        return None

    # API 키 유효성 검사
    if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_API_KEY_HERE":
        print("오류: OpenAI API 키가 유효하지 않아 TTS를 생성할 수 없습니다.")
        return None

    try:
        # OpenAI 클라이언트 인스턴스 생성 (API 키 사용)
        # 참고: 매번 생성하는 대신, 클래스 멤버나 캐싱된 객체로 관리하면 더 효율적일 수 있습니다.
        client = OpenAI(api_key=OPENAI_API_KEY)

        # 선택된 스타일에 맞는 파라미터 가져오기
        style_params = get_style_params(style_name) # tts_styles 모듈의 함수 사용
        voice = style_params.get("voice", "alloy") # voice 파라미터 (없으면 alloy)
        model = style_params.get("model", "tts-1") # model 파라미터 (없으면 tts-1)
        style_desc = style_params.get("description", style_name) # 스타일 설명 (로그용)

        # TTS 생성 요청 로그 (디버깅에 유용)
        print(f"TTS 생성 요청 시작: 스타일='{style_desc}', 모델='{model}', 목소리='{voice}'")
        # print(f"변환할 텍스트 (앞부분): '{text_to_speak[:40]}...'") # 필요 시 로그 추가

        # OpenAI Text-to-Speech API 호출
        response = client.audio.speech.create(
            model=model,          # 사용할 모델 (예: "tts-1", "tts-1-hd")
            voice=voice,          # 사용할 목소리 (예: "alloy", "shimmer")
            input=text_to_speak   # 변환할 텍스트
            # format="mp3",       # 기본값이 mp3이므로 생략 가능
            # speed=1.0           # 속도 조절 (현재 API에서 지원하는지 확인 필요)
        )

        # API 응답에서 오디오 데이터를 bytes 형태로 읽어옴
        # response.read() 또는 response.content 사용 가능
        audio_bytes = response.read()

        print(f"TTS 오디오 데이터 ({len(audio_bytes)} bytes) 생성 성공.")
        # 성공 시 오디오 데이터(bytes) 반환
        return audio_bytes

    except OpenAIError as api_err:
        # OpenAI API 자체에서 발생한 오류 처리 (예: 인증 실패, 잘못된 요청 등)
        print(f"OpenAI API 오류 발생 (TTS): {api_err}")
        return None # 실패 시 None 반환
    except Exception as e:
        # 네트워크 오류, 라이브러리 내부 오류 등 기타 예상치 못한 오류 처리
        print(f"TTS 오디오 생성 중 예상치 못한 오류 발생: {e}")
        return None # 실패 시 None 반환

# --- 스크립트 직접 실행 시 테스트 코드 ---
if __name__ == "__main__":
    # 이 블록은 'python SpeakAnswer_Bytes.py' 처럼 직접 실행했을 때만 동작합니다.
    # Streamlit 앱 등 다른 곳에서 import 할 때는 실행되지 않습니다.
    print("="*30)
    print(" SpeakAnswer_Bytes.py 직접 실행 테스트 ")
    print("="*30)

    # 테스트에 사용할 텍스트와 스타일 이름
    test_text_1 = "안녕하세요? Streamlit에서 사용할 바이트 데이터를 생성하는 테스트입니다."
    test_style_1 = "calm_female" # tts_styles.py에 정의된 이름 사용
    output_filename_1 = "test_output_calm.mp3"

    test_text_2 = "이번에는 다른 목소리로 테스트해 보겠습니다. 에너제틱한 남성 스타일입니다."
    test_style_2 = "energetic_male"
    output_filename_2 = "test_output_energetic.mp3"

    # 테스트 1: 차분한 여성 목소리
    print(f"\n--- 테스트 1 시작: 스타일 = {test_style_1} ---")
    generated_bytes_1 = generate_tts_bytes(test_text_1, style_name=test_style_1)

    if generated_bytes_1:
        print(f"테스트 1 성공: {len(generated_bytes_1)} 바이트 오디오 데이터 생성됨.")
        # 생성된 바이트 데이터를 로컬 파일로 저장하여 직접 들어볼 수 있도록 함 (테스트 목적)
        try:
            with open(output_filename_1, "wb") as audio_file:
                audio_file.write(generated_bytes_1)
            print(f"-> 테스트 결과 파일 저장 완료: '{output_filename_1}'")
            print(f"   (이 파일을 오디오 플레이어로 열어 확인해보세요.)")
        except IOError as save_err:
            print(f"오류: 테스트 결과를 파일로 저장하는 중 문제 발생: {save_err}")
    else:
        print("테스트 1 실패: 오디오 데이터 생성에 실패했습니다.")

    # 테스트 2: 에너제틱한 남성 목소리
    print(f"\n--- 테스트 2 시작: 스타일 = {test_style_2} ---")
    generated_bytes_2 = generate_tts_bytes(test_text_2, style_name=test_style_2)

    if generated_bytes_2:
        print(f"테스트 2 성공: {len(generated_bytes_2)} 바이트 오디오 데이터 생성됨.")
        # 생성된 바이트 데이터를 로컬 파일로 저장하여 직접 들어볼 수 있도록 함 (테스트 목적)
        try:
            with open(output_filename_2, "wb") as audio_file:
                audio_file.write(generated_bytes_2)
            print(f"-> 테스트 결과 파일 저장 완료: '{output_filename_2}'")
            print(f"   (이 파일을 오디오 플레이어로 열어 확인해보세요.)")
        except IOError as save_err:
            print(f"오류: 테스트 결과를 파일로 저장하는 중 문제 발생: {save_err}")
    else:
        print("테스트 2 실패: 오디오 데이터 생성에 실패했습니다.")

    print("\n테스트 완료.")