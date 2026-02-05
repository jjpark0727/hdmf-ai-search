"""
rag/retriever.py - 벡터스토어 및 검색기 관리
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
from langchain_core.documents import Document
from langchain_chroma import Chroma

from config import (
    VECTORSTORE_DIR,
    VECTORSTORE_COLLECTION_NAME,
    RETRIEVER_K,
)
from .embedder import get_default_embeddings


# 글로벌 벡터스토어 인스턴스
_vector_store = None


def get_vector_store(
    collection_name: str = VECTORSTORE_COLLECTION_NAME,
    persist_directory: Optional[str] = None,
    embeddings=None
) -> Chroma:
    """
    벡터스토어 인스턴스 반환 (싱글톤)
    
    Args:
        collection_name: 컬렉션 이름
        persist_directory: 저장 경로 (None이면 config에서 설정)
        embeddings: 임베딩 모델 (None이면 기본값 사용)
    
    Returns:
        Chroma 벡터스토어 인스턴스
    """
    global _vector_store
    
    if _vector_store is None:
        persist_dir = persist_directory or str(VECTORSTORE_DIR)
        emb = embeddings or get_default_embeddings()
        
        _vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=emb,
            persist_directory=persist_dir,
        )
    
    return _vector_store


class RetrieverFactory:
    """다양한 검색 전략 지원"""
    
    def __init__(self, vector_store: Optional[Chroma] = None):
        """
        Args:
            vector_store: 벡터스토어 인스턴스 (None이면 기본값 사용)
        """
        self.vector_store = vector_store or get_vector_store()
    
    def get_similarity_retriever(
        self,
        k: int = RETRIEVER_K,
        filter: Optional[Dict[str, Any]] = None
    ):
        """
        기본 유사도 검색 retriever
        
        Args:
            k: 반환할 문서 수
            filter: 메타데이터 필터 (예: {"country": "japan"})
        
        Returns:
            VectorStoreRetriever
        """
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        
        return self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs
        )
    
    def get_mmr_retriever(
        self,
        k: int = RETRIEVER_K,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Optional[Dict[str, Any]] = None
    ):
        """
        MMR (Maximal Marginal Relevance) retriever
        
        관련성과 다양성을 모두 고려하여 검색
        
        Args:
            k: 반환할 문서 수
            fetch_k: 초기 후보 문서 수
            lambda_mult: 다양성 가중치 (0: 다양성 우선, 1: 관련성 우선)
            filter: 메타데이터 필터
        
        Returns:
            VectorStoreRetriever
        """
        search_kwargs = {
            "k": k,
            "fetch_k": fetch_k,
            "lambda_mult": lambda_mult
        }
        if filter:
            search_kwargs["filter"] = filter
        
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs
        )
    
    def get_country_retriever(
        self,
        country: str,
        k: int = RETRIEVER_K,
        search_type: str = "similarity"
    ):
        """
        국가별 필터링된 retriever
        
        Args:
            country: 국가 코드 ("japan", "usa")
            k: 반환할 문서 수
            search_type: 검색 타입 ("similarity", "mmr")
        
        Returns:
            VectorStoreRetriever
        """
        filter = {"country": country}
        
        if search_type == "mmr":
            return self.get_mmr_retriever(k=k, filter=filter)
        return self.get_similarity_retriever(k=k, filter=filter)
    
    def search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        직접 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            filter: 메타데이터 필터
        
        Returns:
            Document 리스트
        """
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        
        return self.vector_store.similarity_search(query, **search_kwargs)
    
    def mmr_search(
        self,
        query: str,
        k: int = RETRIEVER_K,
        fetch_k: int = 20,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        MMR 검색 직접 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            fetch_k: 초기 후보 문서 수
            filter: 메타데이터 필터
        
        Returns:
            Document 리스트
        """
        return self.vector_store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            filter=filter
        )


# 편의 함수
def get_japan_retriever(k: int = RETRIEVER_K):
    """일본 문서 전용 retriever 반환"""
    factory = RetrieverFactory()
    return factory.get_country_retriever("japan", k=k)


def get_usa_retriever(k: int = RETRIEVER_K):
    """미국 문서 전용 retriever 반환"""
    factory = RetrieverFactory()
    return factory.get_country_retriever("usa", k=k)


def add_documents_to_vectorstore(
    documents: List[Document],
    vector_store: Optional[Chroma] = None
) -> List[str]:
    """
    벡터스토어에 문서 추가
    
    Args:
        documents: 추가할 문서 리스트
        vector_store: 벡터스토어 인스턴스 (None이면 기본값 사용)
    
    Returns:
        추가된 문서 ID 리스트
    """
    vs = vector_store or get_vector_store()
    return vs.add_documents(documents=documents)
