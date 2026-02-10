"""
rag/embedder.py - (3) 임베딩 모델 관리

실험: 기본은 OpenAI, 비용 절감 시 Huggingface로 교체 
"""

from typing import Optional, Literal
from langchain_openai import OpenAIEmbeddings

from config import EMBEDDING_MODEL_NAME


EmbeddingProvider = Literal["openai", "huggingface"]


class EmbeddingManager:
    """임베딩 모델 팩토리 및 관리"""
    
    # 기본 모델 설정
    DEFAULT_MODELS = {
        "openai": "text-embedding-3-large",
        "huggingface": "BAAI/bge-m3",
    }
    # 기본 사용 (원본)
    @staticmethod
    def get_embeddings(
        provider: EmbeddingProvider = "openai",
        model_name: Optional[str] = None
    ):
        """
        임베딩 모델 인스턴스 반환
        
        Args:
            provider: 임베딩 제공자 ("openai", "huggingface", "cohere")
            model_name: 모델 이름 (None이면 기본값 사용)
        
        Returns:
            임베딩 모델 인스턴스
        """
        model = model_name or EmbeddingManager.DEFAULT_MODELS.get(provider)
        
        if provider == "openai":
            return EmbeddingManager._get_openai_embeddings(model)
        elif provider == "huggingface":
            return EmbeddingManager._get_huggingface_embeddings(model)
        else:
            raise ValueError(f"지원하지 않는 provider입니다: {provider}")
    
    @staticmethod
    def _get_openai_embeddings(model_name: str):
        """OpenAI 임베딩 모델 반환"""
        return OpenAIEmbeddings(model=model_name)
    
    @staticmethod
    def _get_huggingface_embeddings(model_name: str):
        """HuggingFace 임베딩 모델 반환"""
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=model_name)
        except ImportError:
            raise ImportError(
                "HuggingFace 임베딩을 사용하려면 langchain-huggingface 패키지가 필요합니다. "
                "pip install langchain-huggingface 로 설치하세요."
            )



# 기본 임베딩 인스턴스 (싱글톤 패턴)
_default_embeddings = None

# 사용 함수
def get_default_embeddings():
    """기본 임베딩 모델 인스턴스 반환 (싱글톤)"""
    global _default_embeddings
    if _default_embeddings is None:
        _default_embeddings = EmbeddingManager.get_embeddings(
            provider="openai",                       
            model_name=EMBEDDING_MODEL_NAME
        )
    return _default_embeddings
