"""
config.py - 환경변수 및 경로 설정
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ============================================
# API Keys
# ============================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# LangSmith (선택적)
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "LangGraph RAG Project")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

# ============================================
# 경로 설정
# ============================================
# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent

# 데이터 경로
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
VECTORSTORE_DIR = DATA_DIR / "vectorstore"

# PDF 파일 경로
PDF_FILES = {
    "japan": PDF_DIR / "ict_japan_2024.pdf",
    "usa": PDF_DIR / "ict_usa_2024.pdf",
}

# ============================================
# 벡터스토어 설정
# ============================================
VECTORSTORE_COLLECTION_NAME = "example_collection_meta"

# ============================================
# 모델 설정
# ============================================
# LLM 모델
LLM_MODEL_NAME = "gpt-4.1-mini"

# 임베딩 모델
EMBEDDING_MODEL_NAME = "text-embedding-3-large"

# ============================================
# RAG 설정
# ============================================
# 청킹 설정
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# 검색 설정
RETRIEVER_K = 6  # 검색 결과 개수

# 재시도 설정
MAX_RETRY_COUNT = 2

# ============================================
# 디렉토리 생성
# ============================================

def ensure_directories():
    """필요한 디렉토리가 없으면 생성"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

# 모듈 로드 시 디렉토리 생성
ensure_directories()
