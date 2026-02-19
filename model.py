"""
model.py - LLM 및 임베딩 모델 설정
"""

import os
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings

from config import (
    OPENAI_API_KEY,
    LLM_MODEL_NAME,
    EMBEDDING_MODEL_NAME,
)

# API 키 환경변수 설정
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# ============================================
# LLM 모델 초기화
# ============================================
# 기본 모델
model = init_chat_model(LLM_MODEL_NAME)

# 역할별 모델 (동일 모델 사용, 필요시 개별 설정 가능)
decision_model = model      # 1. 툴 사용/바로 답변 결정 모델
grader_model = model        # 2. 검색 결과 평가 모델
rewrite_model = model       # 3. 질문 재생성 모델
response_model = model      # 4. 답변 생성 모델
summary_model = model       # 5. 요약 모델
translate_model = model     # 6. 번역 모델

# ============================================
# 임베딩 모델 초기화
# ============================================
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME)


# ============================================
# 다른 모델로 교체 시 사용
# ============================================

def get_model(model_name: str = None):
    """모델 인스턴스 반환"""
    if model_name:
        return init_chat_model(model_name)
    return model


def get_embeddings(model_name: str = None):
    """임베딩 모델 인스턴스 반환"""
    if model_name:
        return OpenAIEmbeddings(model=model_name)
    return embeddings
