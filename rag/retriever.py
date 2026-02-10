"""
rag/retriever.py - 검색기(Retriever) 관리

벡터스토어를 활용한 다양한 검색 전략 제공
벡터스토어는 vectorstore.py에서 관리
"""

from typing import List, Optional, Dict, Any
from langchain_core.documents import Document

from config import RETRIEVER_K
from .vectorstore import (
    get_vector_store,
    add_documents_to_vectorstore,
    BaseVectorStore,
    VectorStoreFactory,
    set_vector_store_type,
)


class RetrieverFactory:
    """다양한 검색 전략 지원"""
    
    def __init__(self, vector_store: Optional[BaseVectorStore] = None):
        """
        Args:
            vector_store: 벡터스토어 인스턴스 (None이면 기본값 사용)
        """
        self._vector_store = vector_store
    
    @property
    def vector_store(self) -> BaseVectorStore:
        """벡터스토어 인스턴스 (지연 로딩)"""
        if self._vector_store is None:
            self._vector_store = get_vector_store()
        return self._vector_store
    
    # 원본 (검색용)
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
    
    # 원본 (요약)
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
    
    # 국가별 필터
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
    
    # 의미 + 키워드 결합 하이브리드 검색 (실험용)
    def get_hybrid_retriever(
        self,
        documents: List[Document],
        k: int = RETRIEVER_K,
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6
    ):
        """
        하이브리드 검색 retriever (Dense + Sparse)
        
        BM25 (키워드 기반) + Dense (의미 기반) 검색 결합
        
        Args:
            documents: BM25 인덱싱용 문서 리스트
            k: 반환할 문서 수
            bm25_weight: BM25 가중치
            dense_weight: Dense 검색 가중치
        
        Returns:
            EnsembleRetriever
        """
        try:
            from langchain.retrievers import EnsembleRetriever
            from langchain_community.retrievers import BM25Retriever
        except ImportError:
            raise ImportError(
                "하이브리드 검색을 사용하려면 rank_bm25 패키지가 필요합니다. "
                "pip install rank_bm25 로 설치하세요."
            )
        
        # BM25 Retriever
        bm25_retriever = BM25Retriever.from_documents(documents, k=k)
        
        # Dense Retriever
        dense_retriever = self.get_similarity_retriever(k=k)
        
        # Ensemble
        return EnsembleRetriever(
            retrievers=[bm25_retriever, dense_retriever],
            weights=[bm25_weight, dense_weight]
        )
    

    # 유사한 문서 리스트 
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
        return self.vector_store.similarity_search(query, k=k, filter=filter)
    
    # 요약용 문서 검색
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


# ============================================
# 편의 함수 (하위 호환성 유지)
# ============================================

def get_japan_retriever(k: int = RETRIEVER_K):
    """일본 문서 전용 retriever 반환"""
    factory = RetrieverFactory()
    return factory.get_country_retriever("japan", k=k)


def get_usa_retriever(k: int = RETRIEVER_K):
    """미국 문서 전용 retriever 반환"""
    factory = RetrieverFactory()
    return factory.get_country_retriever("usa", k=k)


# ============================================
# Re-export (하위 호환성)
# ============================================
# vectorstore.py의 함수들을 retriever.py에서도 접근 가능하도록 re-export
__all__ = [
    # Retriever 관련
    "RetrieverFactory",
    "get_japan_retriever",
    "get_usa_retriever",
    # Vectorstore 관련 (re-export)
    "get_vector_store",
    "add_documents_to_vectorstore",
    "set_vector_store_type",
    "VectorStoreFactory",
]
