"""
ingest.py - data/pdfs 폴더에 있는 문서 임베딩
main.py 실행 전 선행되어야 함
"""

import json
from pathlib import Path
from rag.parser import load_pdf_with_metadata
from rag.chunker import ChunkingStrategy
from rag.vectorstore import get_vector_store
from config import PDF_DIR, DATA_DIR

# 임베딩된 파일 메타데이터 저장 경로
UPLOADED_FILES_PATH = DATA_DIR / "uploaded_files.json"

from rag.vectorstore import get_vector_store, VectorStoreFactory

def ingest_documents():
    """PDF_DIR 내 모든 PDF를 벡터스토어에 임베딩"""
    
    # ✅ 싱글톤 캐시 초기화 (이전 인스턴스 제거)
    VectorStoreFactory.clear_instances()
    
    # 1. PDF 파일 목록 수집
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"PDF 파일이 없습니다: {PDF_DIR}")
        return

def ingest_documents():
    """PDF_DIR 내 모든 PDF를 벡터스토어에 임베딩"""

    # 1. PDF 파일 목록 수집
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"PDF 파일이 없습니다: {PDF_DIR}")
        return

    # 2. PDF 로드 + 메타데이터 주입
    all_docs = []
    uploaded_files = []

    for idx, pdf_path in enumerate(pdf_files, start=1):
        file_id = str(idx)
        print(f"[{file_id}] {pdf_path.name} 로딩 중...")
        docs = load_pdf_with_metadata(
            file_path=str(pdf_path),
            file_id=file_id
        )
        all_docs.extend(docs)
        uploaded_files.append({"file_id": file_id, "file_name": pdf_path.name})

    # 3. 청킹
    print("문서 청킹 중...")
    chunker = ChunkingStrategy()
    all_chunks = chunker.recursive_chunk(all_docs)

    # 4. 벡터스토어에 저장
    print(f"벡터스토어에 {len(all_chunks)}개 청크 저장 중...")
    vector_store = get_vector_store()
    vector_store.add_documents(all_chunks)

    # 5. 파일 메타데이터 저장
    UPLOADED_FILES_PATH.write_text(
        json.dumps(uploaded_files, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"파일 메타데이터 저장: {UPLOADED_FILES_PATH}")

    print("완료!")


def load_uploaded_files() -> list[dict]:
    """저장된 파일 메타데이터 로드"""
    if UPLOADED_FILES_PATH.exists():
        return json.loads(UPLOADED_FILES_PATH.read_text(encoding="utf-8"))
    return []


if __name__ == "__main__":
    ingest_documents()
