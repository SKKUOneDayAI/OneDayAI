# GetAnswer.py (RAG + 페르소나 적용)
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate # 프롬프트 템플릿 추가

# --- 설정 ---
_CSV_FILE_PATH = r"C:\Users\skku07\Documents\GitHub\OneDayAI\dummy_basketball.csv" # 내부 관리
_FAISS_INDEX_PATH = "faiss_index_baseball_persona" # 인덱스 경로 (필요시 재생성)

# --- 내부 헬퍼 함수 (변경 없음) ---
def _create_or_load_vectorstore(file_path, index_path):
    # ... (이전과 동일한 코드) ...
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    if os.path.exists(index_path):
        print(f"기존 인덱스 로드: {index_path}")
        try:
             # allow_dangerous_deserialization=True 추가 (FAISS 최신 버전 호환성)
             return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
             print(f"인덱스 로드 실패 ({e}), 새 인덱스 생성 시도...")
             # 실패 시 인덱스 삭제하고 재생성 (선택적)
             # import shutil
             # shutil.rmtree(index_path, ignore_errors=True)
             # return _create_or_load_vectorstore(file_path, index_path) # 재귀 호출보다는 아래 로직으로 진행

    print(f"'{file_path}'에서 새 인덱스 생성 중...")
    loader = CSVLoader(file_path=file_path, encoding='utf-8-sig') # UTF-8-SIG 시도
    documents = loader.load()
    if not documents:
        raise ValueError(f"CSV 파일 '{file_path}'에서 문서를 로드하지 못했습니다.")
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    texts = text_splitter.split_documents(documents)
    if not texts:
         raise ValueError("문서를 청크로 분할하지 못했습니다.")
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local(index_path)
    print(f"새 인덱스 저장 완료: {index_path}")
    return vectorstore


# --- 공개 인터페이스 함수 ---
def initialize_qa_system(character_system_prompt="You are a helpful assistant."):
    """
    CSV 데이터와 캐릭터 페르소나를 기반으로 QA 시스템을 초기화합니다.
    character_system_prompt 인자를 받아 페르소나를 적용합니다.
    """
    print(f"QA 시스템 초기화 시작 (데이터 경로: {_CSV_FILE_PATH})")
    print(f"적용될 페르소나: {character_system_prompt[:100]}...") # 페르소나 확인용 로그

    try:
        if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "YOUR_API_KEY_HERE":
             raise ValueError("OpenAI API 키가 설정되지 않았거나 유효하지 않습니다.")

        vectorstore = _create_or_load_vectorstore(_CSV_FILE_PATH, _FAISS_INDEX_PATH)
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer') # output_key 명시

        llm = ChatOpenAI(temperature=0.7, model_name='gpt-3.5-turbo') # 온도는 여기서 조절하거나 app.py에서 전달

        # --- 페르소나 적용을 위한 프롬프트 템플릿 수정 ---
        # CONDENSE_QUESTION_PROMPT는 기본값을 사용하거나 필요시 수정
        # QA_PROMPT를 수정하여 시스템 프롬프트를 주입
        _template = f"""
{character_system_prompt}

Use the following pieces of context from CSV data and the chat history to answer the question at the end.
If you don't know the answer from the context, just say that you don't have information about that in the provided data, don't try to make up an answer.
If the question is conversational and not directly answerable from the context, answer it naturally based on your persona and the chat history.

Context:
{{context}}

Chat History:
{{chat_history}}

Question: {{question}}
Answer:"""

        QA_PROMPT = PromptTemplate(
            template=_template, input_variables=["context", "chat_history", "question"]
        )
        # -------------------------------------------------

        # combine_docs_chain_kwargs를 사용하여 사용자 정의 프롬프트 전달
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory,
            return_source_documents=False, # 필요시 True로 변경
            combine_docs_chain_kwargs={"prompt": QA_PROMPT}, # 수정된 QA 프롬프트 적용!
            verbose=False # 디버깅 시 True로 변경
        )
        print("페르소나 적용 QA 시스템 초기화 성공")
        return qa_chain

    except Exception as e:
        print(f"QA 시스템 초기화 중 오류 발생: {e}")
        # raise # 필요시 오류를 다시 발생시켜 app.py에서 처리
        return None # 실패 시 None 반환

def get_answer(chain, query):
    """주어진 QA 체인(페르소나 적용됨)과 질문을 사용하여 답변을 생성합니다."""
    if not chain:
        return "오류: QA 시스템이 준비되지 않았습니다."
    try:
        print(f"QA Chain 호출: Query='{query}'")
        result = chain.invoke({"question": query}) # invoke 사용 (권장)
        print(f"QA Chain 결과: {result}")
        # result 딕셔너리 구조 확인 필요 (Langchain 버전에 따라 다를 수 있음)
        answer = result.get("answer", "답변을 찾을 수 없습니다.")
        # 가끔 결과가 이중 딕셔너리일 수 있음
        if isinstance(answer, dict):
             answer = answer.get("answer", "답변 형식 오류")

        # 답변 앞뒤 공백 제거
        return answer.strip() if answer else "빈 답변이 반환되었습니다."

    except Exception as e:
        print(f"답변 생성 중 오류 발생 (get_answer): {e}")
        import traceback
        traceback.print_exc() # 상세 오류 출력
        # 사용자에겐 간단한 메시지 전달
        return f"답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

def get_data_source_description():
    """데이터 소스 설명을 반환합니다 (변경 없음)."""
    if os.path.exists(_CSV_FILE_PATH):
        return f"'{os.path.basename(_CSV_FILE_PATH)}' 데이터 기반"
    else:
        return "CSV 데이터 기반 (파일 경로 확인 필요)"