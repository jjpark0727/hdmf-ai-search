"""
rag/vectorstore.py - 벡터스토어 관리

다양한 벡터 DB를 갈아끼울 수 있는 팩토리 패턴 구현
지원: Chroma, FAISS, Pinecone (확장 가능)

프로그램 시작 시 한번만 설졍 (글로벌): set_vector_store_type("chroma")

"""

from typing import List, Optional, Dict, Any, Literal
from pathlib import Path
from abc import ABC, abstractmethod
from langchain_core.documents import Document

from config import (
    VECTORSTORE_DIR,
    VECTORSTORE_COLLECTION_NAME,
)
from .embedder import get_default_embeddings


# ============================================
# 벡터스토어 타입 정의
# ============================================
VectorStoreType = Literal["chroma", "faiss", "pinecone"]


# ============================================
# 추상 베이스 클래스
# ============================================
class BaseVectorStore(ABC):
    """벡터스토어 추상 베이스 클래스"""
    
    @abstractmethod
    def add_documents(self, documents: List[Document]) -> List[str]:
        """문서 추가"""
        pass
    
    @abstractmethod
    def similarity_search(self, query: str, k: int = 5, filter: Dict = None) -> List[Document]:
        """유사도 검색"""
        pass
    
    @abstractmethod
    def max_marginal_relevance_search(
        self, query: str, k: int = 5, fetch_k: int = 20, filter: Dict = None
    ) -> List[Document]:
        """MMR 검색"""
        pass
    
    @abstractmethod
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None):
        """Retriever 반환"""
        pass
    
    @abstractmethod
    def get_all_by_filter(self, filter: Dict) -> List[Document]:
        """필터 조건에 맞는 모든 문서를 페이지/청크 순으로 반환"""
        pass

    @abstractmethod
    def delete(self, ids: List[str] = None, filter: Dict = None) -> bool:
        """문서 삭제"""
        pass


# ============================================
# Chroma 벡터스토어 
# ============================================
class ChromaVectorStore(BaseVectorStore):
    """Chroma 벡터스토어 구현"""
    
    def __init__(
        self,
        collection_name: str = VECTORSTORE_COLLECTION_NAME,
        persist_directory: Optional[str] = None,
        embeddings=None
    ):
        from langchain_chroma import Chroma
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory or str(VECTORSTORE_DIR)
        self.embeddings = embeddings or get_default_embeddings()
        
        self._store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )
    
    @property
    def store(self):
        """내부 Chroma 인스턴스 반환"""
        return self._store
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """문서 추가"""
        return self._store.add_documents(documents=documents)
    
    def similarity_search(
        self, query: str, k: int = 5, filter: Dict = None
    ) -> List[Document]:
        """유사도 검색"""
        kwargs = {"k": k}
        if filter:
            kwargs["filter"] = filter
        return self._store.similarity_search(query, **kwargs)
    
    def max_marginal_relevance_search(
        self, query: str, k: int = 5, fetch_k: int = 20, filter: Dict = None
    ) -> List[Document]:
        """MMR 검색"""
        return self._store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            filter=filter
        )
    
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None):
        """Retriever 반환"""
        return self._store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs or {}
        )
    
    def get_all_by_filter(self, filter: Dict) -> List[Document]:
        """필터 조건에 맞는 모든 문서를 페이지/청크 순으로 반환"""
        result = self._store._collection.get(
            where=filter,
            include=["documents", "metadatas"]
        )
        docs = []
        for text, meta in zip(result["documents"], result["metadatas"]):
            docs.append(Document(page_content=text, metadata=meta or {}))
        # page → chunk 순 정렬 (원문 순서 복원)
        docs.sort(key=lambda d: (
            int(d.metadata.get("page", 0)),
            int(d.metadata.get("chunk", 0))
        ))
        return docs

    def delete(self, ids: List[str] = None, filter: Dict = None) -> bool:
        """문서 삭제"""
        try:
            if ids:
                self._store.delete(ids=ids)
            # Chroma는 filter 기반 삭제를 직접 지원하지 않음
            return True
        except Exception as e:
            print(f"삭제 중 오류: {e}")
            return False

    def get_collection_count(self) -> int:
        """컬렉션 문서 수 반환"""
        return self._store._collection.count()


# ============================================
# FAISS 벡터스토어
# ============================================
class FAISSVectorStore(BaseVectorStore):
    """FAISS 벡터스토어 구현"""
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        index_name: str = "index",
        embeddings=None
    ):
        self.persist_directory = persist_directory or str(VECTORSTORE_DIR / "faiss")
        self.index_name = index_name
        self.embeddings = embeddings or get_default_embeddings()
        self._store = None
        
        # 기존 인덱스 로드 시도
        self._try_load()
    
    def _try_load(self):
        """기존 인덱스 로드 시도"""
        try:
            from langchain_community.vectorstores import FAISS
            
            index_path = Path(self.persist_directory)
            if index_path.exists():
                self._store = FAISS.load_local(
                    self.persist_directory,
                    self.embeddings,
                    index_name=self.index_name,
                    allow_dangerous_deserialization=True
                )
        except Exception:
            self._store = None
    
    @property
    def store(self):
        """내부 FAISS 인스턴스 반환"""
        return self._store
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """문서 추가"""
        from langchain_community.vectorstores import FAISS
        
        if self._store is None:
            # 새 인덱스 생성
            self._store = FAISS.from_documents(documents, self.embeddings)
        else:
            # 기존 인덱스에 추가
            self._store.add_documents(documents)
        
        # 저장
        self._save()
        
        # FAISS는 ID를 반환하지 않으므로 임시 ID 생성
        return [f"doc_{i}" for i in range(len(documents))]
    
    def _save(self):
        """인덱스 저장"""
        if self._store:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            self._store.save_local(self.persist_directory, index_name=self.index_name)
    
    def similarity_search(
        self, query: str, k: int = 5, filter: Dict = None
    ) -> List[Document]:
        """유사도 검색"""
        if self._store is None:
            return []
        
        # FAISS는 기본적으로 메타데이터 필터를 지원하지 않음
        # 필터가 필요하면 검색 후 후처리
        results = self._store.similarity_search(query, k=k * 2 if filter else k)
        
        if filter:
            results = self._apply_filter(results, filter, k)
        
        return results[:k]
    
    def _apply_filter(
        self, documents: List[Document], filter: Dict, k: int
    ) -> List[Document]:
        """메타데이터 필터 적용 (후처리)"""
        filtered = []
        for doc in documents:
            match = True
            for key, value in filter.items():
                if doc.metadata.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(doc)
            if len(filtered) >= k:
                break
        return filtered
    
    def max_marginal_relevance_search(
        self, query: str, k: int = 5, fetch_k: int = 20, filter: Dict = None
    ) -> List[Document]:
        """MMR 검색"""
        if self._store is None:
            return []
        
        results = self._store.max_marginal_relevance_search(
            query=query,
            k=k * 2 if filter else k,
            fetch_k=fetch_k
        )
        
        if filter:
            results = self._apply_filter(results, filter, k)
        
        return results[:k]
    
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None):
        """Retriever 반환"""
        if self._store is None:
            raise ValueError("FAISS 인덱스가 초기화되지 않았습니다. 먼저 문서를 추가하세요.")
        
        return self._store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs or {}
        )
    
    def get_all_by_filter(self, filter: Dict) -> List[Document]:
        """필터 조건에 맞는 모든 문서를 페이지/청크 순으로 반환 (FAISS 폴백)"""
        if self._store is None:
            return []
        # FAISS는 get() 미지원 → 충분히 큰 k로 전체 검색 후 필터링
        results = self._store.similarity_search("", k=10000)
        filtered = self._apply_filter(results, filter, k=len(results))
        filtered.sort(key=lambda d: (
            int(d.metadata.get("page", 0)),
            int(d.metadata.get("chunk", 0))
        ))
        return filtered

    def delete(self, ids: List[str] = None, filter: Dict = None) -> bool:
        """문서 삭제 (FAISS는 삭제를 잘 지원하지 않음)"""
        print("경고: FAISS는 개별 문서 삭제를 효율적으로 지원하지 않습니다.")
        return False


# ============================================
# Pinecone 벡터스토어 (Optional)
# ============================================
class PineconeVectorStore(BaseVectorStore):
    """Pinecone 벡터스토어 구현 (클라우드 기반)"""
    
    def __init__(
        self,
        index_name: str,
        namespace: str = "",
        embeddings=None
    ):
        try:
            from langchain_pinecone import PineconeVectorStore as LCPinecone
        except ImportError:
            raise ImportError(
                "Pinecone을 사용하려면 langchain-pinecone 패키지가 필요합니다. "
                "pip install langchain-pinecone pinecone-client 로 설치하세요."
            )
        
        self.index_name = index_name
        self.namespace = namespace
        self.embeddings = embeddings or get_default_embeddings()
        
        self._store = LCPinecone.from_existing_index(
            index_name=self.index_name,
            embedding=self.embeddings,
            namespace=self.namespace
        )
    
    @property
    def store(self):
        return self._store
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        return self._store.add_documents(documents=documents)
    
    def similarity_search(
        self, query: str, k: int = 5, filter: Dict = None
    ) -> List[Document]:
        kwargs = {"k": k}
        if filter:
            kwargs["filter"] = filter
        return self._store.similarity_search(query, **kwargs)
    
    def max_marginal_relevance_search(
        self, query: str, k: int = 5, fetch_k: int = 20, filter: Dict = None
    ) -> List[Document]:
        return self._store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            filter=filter
        )
    
    def as_retriever(self, search_type: str = "similarity", search_kwargs: Dict = None):
        return self._store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs or {}
        )
    
    def get_all_by_filter(self, filter: Dict) -> List[Document]:
        """필터 조건에 맞는 모든 문서를 페이지/청크 순으로 반환 (Pinecone 폴백)"""
        results = self._store.similarity_search("", k=10000, filter=filter)
        results.sort(key=lambda d: (
            int(d.metadata.get("page", 0)),
            int(d.metadata.get("chunk", 0))
        ))
        return results

    def delete(self, ids: List[str] = None, filter: Dict = None) -> bool:
        try:
            if ids:
                self._store.delete(ids=ids)
            return True
        except Exception as e:
            print(f"삭제 중 오류: {e}")
            return False


# ============================================
# 벡터스토어 팩토리
# ============================================
class VectorStoreFactory:
    """벡터스토어 팩토리 클래스"""
    
    _instances: Dict[str, BaseVectorStore] = {}
    
    @classmethod
    def create(
        cls,
        store_type: VectorStoreType = "chroma",
        **kwargs
    ) -> BaseVectorStore:
        """
        벡터스토어 인스턴스 생성
        
        Args:
            store_type: 벡터스토어 타입 ("chroma", "faiss", "pinecone")
            **kwargs: 각 벡터스토어별 추가 인자
        
        Returns:
            BaseVectorStore 인스턴스
        """
        if store_type == "chroma":
            return ChromaVectorStore(**kwargs)
        elif store_type == "faiss":
            return FAISSVectorStore(**kwargs)
        elif store_type == "pinecone":
            return PineconeVectorStore(**kwargs)
        else:
            raise ValueError(f"지원하지 않는 벡터스토어 타입: {store_type}")
    
    @classmethod
    def get_or_create(
        cls,
        store_type: VectorStoreType = "chroma",
        instance_key: str = "default",
        **kwargs
    ) -> BaseVectorStore:
        """
        싱글톤 패턴으로 벡터스토어 인스턴스 반환
        
        Args:
            store_type: 벡터스토어 타입
            instance_key: 인스턴스 식별 키
            **kwargs: 추가 인자
        
        Returns:
            BaseVectorStore 인스턴스
        """
        key = f"{store_type}_{instance_key}"
        
        if key not in cls._instances:
            cls._instances[key] = cls.create(store_type, **kwargs)
        
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """모든 캐시된 인스턴스 제거"""
        cls._instances.clear()


# ============================================
# 글로벌 벡터스토어 인스턴스 (하위 호환성)
# ============================================
_vector_store: Optional[BaseVectorStore] = None
_vector_store_type: VectorStoreType = "chroma"


def set_vector_store_type(store_type: VectorStoreType):
    """글로벌 벡터스토어 타입 설정"""
    global _vector_store_type, _vector_store
    _vector_store_type = store_type
    _vector_store = None  # 기존 인스턴스 초기화


def get_vector_store(
    collection_name: str = VECTORSTORE_COLLECTION_NAME,
    persist_directory: Optional[str] = None,
    embeddings=None,
    store_type: Optional[VectorStoreType] = None
) -> BaseVectorStore:
    """
    벡터스토어 인스턴스 반환 (싱글톤)
    
    기존 코드와 호환성 유지
    
    Args:
        collection_name: 컬렉션 이름 (Chroma용)
        persist_directory: 저장 경로
        embeddings: 임베딩 모델
        store_type: 벡터스토어 타입 (None이면 글로벌 설정 사용)
    
    Returns:
        BaseVectorStore 인스턴스
    """
    global _vector_store
    
    use_type = store_type or _vector_store_type
    
    if _vector_store is None:
        if use_type == "chroma":
            _vector_store = VectorStoreFactory.create(
                "chroma",
                collection_name=collection_name,
                persist_directory=persist_directory,
                embeddings=embeddings
            )
        elif use_type == "faiss":
            _vector_store = VectorStoreFactory.create(
                "faiss",
                persist_directory=persist_directory,
                embeddings=embeddings
            )
        else:
            _vector_store = VectorStoreFactory.create(use_type)
    
    return _vector_store


# 원본 코드 
def add_documents_to_vectorstore(
    documents: List[Document],
    vector_store: Optional[BaseVectorStore] = None
) -> List[str]:
    """
    벡터스토어에 문서 추가 (하위 호환성)
    
    Args:
        documents: 추가할 문서 리스트
        vector_store: 벡터스토어 인스턴스 (None이면 기본값 사용)
    
    Returns:
        추가된 문서 ID 리스트
    """
    vs = vector_store or get_vector_store()
    return vs.add_documents(documents=documents)
