"""
rag/chunker.py - 텍스트 청킹 전략
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)

from config import CHUNK_SIZE, CHUNK_OVERLAP


class ChunkingStrategy:
    """다양한 청킹 전략 지원"""
    
    def __init__(
        self, 
        chunk_size: int = CHUNK_SIZE, 
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def recursive_chunk(
        self, 
        documents: List[Document],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        add_start_index: bool = True
    ) -> List[Document]:
        """
        기본 재귀 청킹 (Recursive Character Text Splitter)
        
        문단, 문장, 단어 순으로 재귀적으로 분할하여 의미 단위 유지
        
        Args:
            documents: 분할할 문서 리스트
            chunk_size: 청크 크기 (기본값: config에서 설정)
            chunk_overlap: 청크 오버랩 (기본값: config에서 설정)
            add_start_index: 시작 인덱스 메타데이터 추가 여부
        
        Returns:
            분할된 Document 리스트
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or self.chunk_size,
            chunk_overlap=chunk_overlap or self.chunk_overlap,
            add_start_index=add_start_index,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return splitter.split_documents(documents)
    
    def token_chunk(
        self, 
        documents: List[Document],
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Document]:
        """
        토큰 기반 청킹 (Token Text Splitter)
        
        LLM 토큰 수 기준으로 분할
        
        Args:
            documents: 분할할 문서 리스트
            chunk_size: 토큰 수 기준 청크 크기
            chunk_overlap: 토큰 수 기준 오버랩
        
        Returns:
            분할된 Document 리스트
        """
        splitter = TokenTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        return splitter.split_documents(documents)
    
    def semantic_chunk(
        self, 
        documents: List[Document],
        embeddings,
        breakpoint_threshold_type: str = "percentile"
    ) -> List[Document]:
        """
        의미 기반 청킹 (Semantic Chunker)
        
        임베딩 유사도 기반으로 의미적으로 연관된 문장들을 그룹화
        
        Args:
            documents: 분할할 문서 리스트
            embeddings: 임베딩 모델
            breakpoint_threshold_type: 분할 기준 ("percentile", "standard_deviation", "interquartile")
        
        Returns:
            분할된 Document 리스트
        """
        try:
            from langchain_experimental.text_splitter import SemanticChunker
            
            splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type=breakpoint_threshold_type
            )
            return splitter.split_documents(documents)
        except ImportError:
            raise ImportError(
                "SemanticChunker를 사용하려면 langchain-experimental 패키지가 필요합니다. "
                "pip install langchain-experimental 로 설치하세요."
            )
    
    def chunk_by_strategy(
        self, 
        documents: List[Document],
        strategy: str = "recursive",
        **kwargs
    ) -> List[Document]:
        """
        전략 이름으로 청킹 실행
        
        Args:
            documents: 분할할 문서 리스트
            strategy: 청킹 전략 ("recursive", "token", "semantic")
            **kwargs: 각 전략별 추가 파라미터
        
        Returns:
            분할된 Document 리스트
        """
        strategies = {
            "recursive": self.recursive_chunk,
            "token": self.token_chunk,
            "semantic": self.semantic_chunk,
        }
        
        if strategy not in strategies:
            raise ValueError(f"지원하지 않는 전략입니다: {strategy}. 가능한 값: {list(strategies.keys())}")
        
        return strategies[strategy](documents, **kwargs)


# 편의 함수
def chunk_documents(
    documents: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Document]:
    """
    문서를 기본 설정으로 청킹
    
    Args:
        documents: 분할할 문서 리스트
        chunk_size: 청크 크기
        chunk_overlap: 청크 오버랩
    
    Returns:
        분할된 Document 리스트
    """
    chunker = ChunkingStrategy(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return chunker.recursive_chunk(documents)
