"""
rag/parser.py - (1) 문서 로딩 및 메타데이터 주입

실험: 기본 load() 또는 load_pdf_with_metadata() 사용

"""

from typing import List, Dict, Optional
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_core.documents import Document


class DocumentParser:
    """다양한 형식의 문서 로딩 및 메타데이터 주입"""
    
    SUPPORTED_LOADERS = {
        ".pdf": PyMuPDFLoader,             
        ".docx": Docx2txtLoader,        
    }
    
    def __init__(self):
        pass
    
    # 원본 
    def load(
        self, 
        file_path: str, 
        metadata: Optional[Dict] = None,
        mode: str = "page"
    ) -> List[Document]:
        """
        파일을 로드하고 메타데이터를 주입
        
        Args:
            file_path: 파일 경로
            metadata: 추가할 메타데이터 (예: {"country": "japan", "file_id": "1"})
            mode: 로딩 모드 ("page" - 페이지별, "single" - 전체를 하나로)
        
        Returns:
            Document 리스트
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension not in self.SUPPORTED_LOADERS:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {extension}")
        
        loader_class = self.SUPPORTED_LOADERS[extension]
        
        # PDF의 경우 mode 파라미터 지원
        if extension == ".pdf":
            loader = loader_class(str(file_path), mode=mode)
        else:
            loader = loader_class(str(file_path))
        
        documents = loader.load()
        
        # 메타데이터 주입
        if metadata:
            documents = self._inject_metadata(documents, metadata)
        
        return documents
    

    # 여러 파일을 한번에 로딩 (실험용)
    def load_multiple(
        self, 
        file_configs: List[Dict],
        mode: str = "page"
    ) -> List[Document]:
        """
        여러 파일을 로드하고 각각에 메타데이터 주입
        
        Args:
            file_configs: 파일 설정 리스트
                예: [
                    {"path": "japan.pdf", "metadata": {"country": "japan", "file_id": "1"}},
                    {"path": "usa.pdf", "metadata": {"country": "usa", "file_id": "2"}}
                ]
            mode: 로딩 모드
        
        Returns:
            모든 Document 리스트
        """
        all_documents = []
        
        for config in file_configs:
            file_path = config["path"]
            metadata = config.get("metadata", {})
            
            docs = self.load(file_path, metadata=metadata, mode=mode)
            all_documents.extend(docs)
        
        return all_documents
    

    # 메타데이터 주입
    def _inject_metadata(
        self, 
        documents: List[Document], 
        metadata: Dict
    ) -> List[Document]:
        """문서 리스트에 메타데이터 주입"""
        for doc in documents:
            doc.metadata.update(metadata)
        return documents


# 사용 함수
def load_pdf_with_metadata(
    file_path: str,
    country: str,
    file_id: str,
    mode: str = "page"
) -> List[Document]:
    """
    PDF 파일을 로드하고 country, file_id 메타데이터 주입
    
    Args:
        file_path: PDF 파일 경로
        country: 국가 코드 (예: "japan", "usa")
        file_id: 파일 ID (예: "1", "2")
        mode: 로딩 모드
    
    Returns:
        Document 리스트
    """
    parser = DocumentParser()
    metadata = {
        "country": country,
        "file_id": file_id
    }
    return parser.load(file_path, metadata=metadata, mode=mode)
