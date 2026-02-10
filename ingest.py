"""
ingest.py - data/pdfs 폴더에 있는 문서 임베딩
main.py 실행 전 선행되어야 함
"""


from pathlib import Path
from rag.parser import load_pdf_with_metadata
from rag.chunker import ChunkingStrategy
from rag.vectorstore import get_vector_store
from config import PDF_FILES

def ingest_documents():
    """PDF를 벡터스토어에 임베딩"""
    
    # 1. PDF 파일 존재 확인
    if not PDF_FILES["japan"].exists():
        print(f"일본 PDF가 없습니다: {PDF_FILES['japan']}")
        return
    if not PDF_FILES["usa"].exists():
        print(f"미국 PDF가 없습니다: {PDF_FILES['usa']}")
        return
    
    # 2. PDF 로드 + 메타데이터 주입
    print("일본 문서 로딩 중...")
    japan_docs = load_pdf_with_metadata(
        file_path=str(PDF_FILES["japan"]),
        country="japan",
        file_id="1"
    )
    
    print("미국 문서 로딩 중...")
    usa_docs = load_pdf_with_metadata(
        file_path=str(PDF_FILES["usa"]),
        country="usa",
        file_id="2"
    )
    
    # 3. 청킹
    print("문서 청킹 중...")
    chunker = ChunkingStrategy()
    all_chunks = chunker.recursive_chunk(japan_docs + usa_docs) # 청킹 방법 변경 가능
    
    # 4. 벡터스토어에 저장
    print(f"벡터스토어에 {len(all_chunks)}개 청크 저장 중...")
    vector_store = get_vector_store()
    vector_store.add_documents(all_chunks)
    
    print("✅ 완료!")

if __name__ == "__main__":
    ingest_documents()