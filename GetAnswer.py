# GetAnswer_Refactored.py (파일 이름 변경 또는 기존 파일 수정)

import os
# --- 필요한 라이브러리 임포트 ---
# (기존 GetAnswer.py와 동일하게 모든 import 구문 포함)
from langchain_community.document_loaders import CSVLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
# (SpeakAnswer, tts_styles 등 다른 필요한 모듈도 import)
try:
    from SpeakAnswer_Bytes import generate_tts_audio # TTS 함수가 바이트를 반환하도록 수정되었다고 가정
    from tts_styles import get_available_styles, get_style_params
except ImportError:
    print("Warning: SpeakAnswer_Bytes 또는 tts_styles 모듈 임포트 실패")
    # 임시 대체 함수/데이터 (Streamlit에서 직접 임포트할 것이므로 여기선 필수 아님)
    def generate_tts_audio(text, style): return None
    def get_available_styles(): return {"default": "기본"}

# --- 설정 ---
CSV_FILE_PATH = r"C:\Users\skku07\Documents\GitHub\OneDayAI\dummy_basketball.csv"
# (API 키 설정 등 필요시 포함)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")

# --- 핵심 기능 함수화 ---

# QA 시스템 초기화 함수
def initialize_qa_system(csv_path=CSV_FILE_PATH):
    """CSV 로드, 벡터화, QA 체인 생성을 수행하고 QA 체인을 반환합니다."""
    print(f"QA 시스템 초기화 시작 (데이터: {csv_path})...") # 콘솔 로그 (디버깅용)
    # (기존 GetAnswer.py의 초기화 로직: loader, docs, splitter, embeddings, vectorstore, retriever, llm 생성)
    # --- 이 부분은 이전 GetAnswer.py의 초기화 코드와 동일 ---
    if not os.path.exists(csv_path):
        print(f"오류: CSV 파일 없음 - {csv_path}")
        return None
    loader = CSVLoader(file_path=csv_path, encoding="utf-8")
    docs = loader.load()
    if not docs:
        print("오류: CSV 데이터 로드 실패")
        return None
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = text_splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={'k': 3})
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=retriever
    )
    # --- 초기화 코드 끝 ---
    print("QA 시스템 초기화 완료.")
    return qa_chain # 생성된 QA 체인 객체를 반환

# 질문으로 답변을 얻는 함수
def get_answer(qa_chain, query):
    """주어진 QA 체인과 질문으로 답변 텍스트를 얻어 반환합니다."""
    if not qa_chain:
        return "오류: QA 시스템이 초기화되지 않았습니다."
    try:
        print(f"질문 처리 중: {query}") # 콘솔 로그
        result = qa_chain({"query": query})
        answer = result.get('result', '죄송합니다, 답변을 찾지 못했습니다.')
        print(f"답변 생성됨: {answer[:50]}...") # 콘솔 로그
        return answer
    except Exception as e:
        print(f"답변 생성 오류: {e}") # 콘솔 로그
        return f"답변 생성 중 오류 발생: {e}"

# --- 스크립트로 직접 실행 시 동작할 부분 ---
if __name__ == "__main__":
    # 이 블록은 GetAnswer_Refactored.py를 직접 python GetAnswer_Refactored.py 처럼
    # 실행했을 때만 동작하고, 다른 파일에서 import 할 때는 실행되지 않습니다.
    print("GetAnswer 모듈 직접 실행 모드 (테스트용)")

    # 시스템 초기화
    my_qa_chain = initialize_qa_system()

    if my_qa_chain:
        # 기존의 while 루프 (명령줄 인터페이스)를 여기에 넣어서 테스트 가능
        print("\n명령줄 테스트 인터페이스 시작 (종료: '종료')")
        while True:
            user_query = input("테스트 질문 입력 > ")
            if user_query.lower() == "종료":
                break
            response = get_answer(my_qa_chain, user_query)
            print(f"봇 응답: {response}")
            # 필요시 여기서 speak_text 테스트 호출 가능
    else:
        print("QA 시스템 초기화 실패로 테스트 인터페이스를 시작할 수 없습니다.")