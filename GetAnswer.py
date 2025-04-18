# GetAnswer.py (CSV 로딩 로그 노란색으로 출력)
import os
import shutil
import glob
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
import traceback

# --- 설정 ---
_CSV_DIRECTORY_PATH = r"C:\Users\skku07\Documents\GitHub\OneDayAI\BaseballCSVs" # 실제 경로로 수정 필요
_FAISS_INDEX_DIR = "faiss_indices"

# ANSI 색상 코드 정의 (가독성을 위해)
YELLOW = "\033[33m"
RESET = "\033[0m" # 색상 리셋

# --- 내부 헬퍼 함수 (수정) ---
def _create_or_load_vectorstore(directory_path, chunk_size, chunk_overlap):
    """
    지정된 디렉토리의 모든 CSV 파일에서 데이터를 로드하여
    FAISS 인덱스를 생성하거나 로드합니다. 인덱스 경로는 설정값에 따라 동적으로 결정됩니다.
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

    index_subdir = f"c{chunk_size}_o{chunk_overlap}"
    index_path = os.path.join(_FAISS_INDEX_DIR, index_subdir)
    os.makedirs(_FAISS_INDEX_DIR, exist_ok=True)

    if os.path.exists(index_path):
        print(f"'{index_subdir}' 설정에 맞는 기존 인덱스 로드: {index_path}")
        try:
            return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"인덱스 로드 실패 ({e}), 새 인덱스 생성 시도...")
            shutil.rmtree(index_path, ignore_errors=True)
            print(f"기존 인덱스 폴더 삭제: {index_path}")

    print(f"'{directory_path}' 폴더 내 CSV 파일에서 새 인덱스 생성 중 (chunk_size={chunk_size}, chunk_overlap={chunk_overlap})...")

    csv_files = glob.glob(os.path.join(directory_path, '*.csv'))
    if not csv_files:
        raise ValueError(f"지정된 디렉토리 '{directory_path}'에서 CSV 파일을 찾을 수 없습니다.")

    print(f"발견된 CSV 파일: {len(csv_files)}개")
    all_documents = []
    for csv_file in csv_files:
        # --- 이 부분을 수정하여 노란색으로 출력 ---
        print(f"{YELLOW} - 로딩 중: {os.path.basename(csv_file)}{RESET}")
        # ----------------------------------------
        try:
            loader = CSVLoader(file_path=csv_file, encoding='utf-8-sig')
            documents = loader.load()
            if documents:
                all_documents.extend(documents)
            else:
                print(f"   경고: '{os.path.basename(csv_file)}' 파일에서 문서를 로드하지 못했습니다 (파일이 비어있거나 형식이 다를 수 있음).")
        except Exception as load_e:
             print(f"   오류: '{os.path.basename(csv_file)}' 파일 로딩 중 오류 발생: {load_e}")
             # raise load_e

    if not all_documents:
        raise ValueError(f"'{directory_path}' 내의 CSV 파일들에서 유효한 문서를 로드하지 못했습니다.")

    print(f"총 {len(all_documents)}개 문서 로드 완료. 텍스트 분할 중...")

    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    texts = text_splitter.split_documents(all_documents)
    if not texts:
         raise ValueError("문서를 청크로 분할하지 못했습니다.")

    print(f"문서 분할 완료 ({len(texts)}개 청크 생성). FAISS 인덱스 생성 중...")
    vectorstore = FAISS.from_documents(texts, embeddings)
    vectorstore.save_local(index_path)
    print(f"새 인덱스 저장 완료: {index_path}")
    print(f"{YELLOW}주의: '{directory_path}' 내의 CSV 파일 내용이 변경되면, '{_FAISS_INDEX_DIR}' 폴더를 직접 삭제해야 변경 사항이 반영된 새 인덱스가 생성됩니다.{RESET}")
    return vectorstore


# --- 공개 인터페이스 함수 (수정) ---
def initialize_qa_system(character_system_prompt="You are a helpful assistant.",
                         temperature=0.7, chunk_size=1000, chunk_overlap=100):
    """
    지정된 폴더의 CSV 데이터와 캐릭터 페르소나, 설정값들을 기반으로 QA 시스템을 초기화합니다.
    """
    print(f"QA 시스템 초기화 시작 (T={temperature}, C={chunk_size}, O={chunk_overlap})")
    print(f"페르소나: {character_system_prompt[:100]}...")

    try:
        if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "YOUR_API_KEY_HERE":
             raise ValueError("OpenAI API 키가 설정되지 않았거나 유효하지 않습니다.")

        vectorstore = _create_or_load_vectorstore(_CSV_DIRECTORY_PATH, chunk_size, chunk_overlap)

        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')

        llm = ChatOpenAI(temperature=temperature, model_name='gpt-4o-mini')

        _template = f"""
{character_system_prompt}
Use the following pieces of context from CSV data and the chat history to answer the question at the end. If you don't know the answer from the context, just say that you don't have information about that in the provided data, don't try to make up an answer. If the question is conversational and not directly answerable from the context, answer it naturally based on your persona and the chat history.
Context: {{context}}
Chat History: {{chat_history}}
Question: {{question}}
Answer:"""
        QA_PROMPT = PromptTemplate(
            template=_template, input_variables=["context", "chat_history", "question"]
        )

        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(),
            memory=memory,
            return_source_documents=False,
            combine_docs_chain_kwargs={"prompt": QA_PROMPT},
            verbose=False
        )
        print("페르소나 및 설정 적용 QA 시스템 초기화 성공")
        return qa_chain

    except Exception as e:
        print(f"QA 시스템 초기화 중 오류 발생: {e}")
        traceback.print_exc()
        return None

# get_answer 함수는 변경 없음
def get_answer(chain, query):
    if not chain:
        return "오류: QA 시스템이 준비되지 않았습니다."
    try:
        print(f"QA Chain 호출: Query='{query}'")
        result = chain.invoke({"question": query})
        print(f"QA Chain 결과: {result}")
        answer = result.get("answer", "답변을 찾을 수 없습니다.")
        if isinstance(answer, dict):
            answer = answer.get("answer", "답변 형식 오류")
        return answer.strip() if answer else "빈 답변이 반환되었습니다."
    except Exception as e:
        print(f"답변 생성 중 오류 발생 (get_answer): {e}")
        traceback.print_exc()
        return f"답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

# get_data_source_description 함수 수정
def get_data_source_description():
    """데이터 소스 디렉토리에 대한 설명을 반환합니다."""
    if os.path.isdir(_CSV_DIRECTORY_PATH):
        try:
            csv_count = len(glob.glob(os.path.join(_CSV_DIRECTORY_PATH, '*.csv')))
            return f"'{os.path.basename(_CSV_DIRECTORY_PATH)}' 폴더 내 {csv_count}개 CSV 데이터 기반"
        except Exception:
             return f"'{os.path.basename(_CSV_DIRECTORY_PATH)}' 폴더 데이터 기반"
    else:
        return "CSV 데이터 폴더 기반 (경로 확인 필요)"