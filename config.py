"""
config.py - 환경변수 및 경로 설정
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def _get_secret(key: str):
    """환경변수(.env) → Streamlit Secrets 순서로 값을 읽음"""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


# ============================================
# API Keys
# ============================================
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

# LangSmith
LANGCHAIN_TRACING_V2 = _get_secret("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = _get_secret("LANGCHAIN_ENDPOINT")
LANGCHAIN_PROJECT = _get_secret("LANGCHAIN_PROJECT")
LANGCHAIN_API_KEY = _get_secret("LANGCHAIN_API_KEY")

# ============================================
# 경로 설정
# ============================================
# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent

# Streamlit Cloud 환경 감지
IS_CLOUD = Path("/mount/src").exists()

if IS_CLOUD:
    # Streamlit Cloud: /tmp 사용 (휘발성이지만 GitHub repo와 분리)
    BASE_DIR = Path("/tmp/hdmf-ai-search")
else:
    # 로컬: 프로젝트 루트 사용
    BASE_DIR = PROJECT_ROOT

# 데이터 경로
DATA_DIR        = BASE_DIR / "data"
PDF_DIR         = BASE_DIR / "data" / "pdfs"
VECTORSTORE_DIR = BASE_DIR / "data" / "vectorstore"


# # 데이터 경로
# DATA_DIR = PROJECT_ROOT / "data"
# PDF_DIR = DATA_DIR / "pdfs"
# VECTORSTORE_DIR = DATA_DIR / "vectorstore"

# PDF 파일 경로 (업로드된 파일 리스트로 동적 관리)
PDF_FILES = []

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

# 검색 재시도 설정
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
