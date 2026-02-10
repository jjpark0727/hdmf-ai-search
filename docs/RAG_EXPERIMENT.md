# RAG 실험 가이드

각 모듈별 현재 사용 중인 함수와 교체 가능한 대안을 정리합니다.

---

## python ingest.py (선행 1회 실행)

| 모듈 | 사용 함수 | 현재 설정 | 대안 |
|------|-----------|-----------|------|
| **parser** | `load_pdf_with_metadata()` → `DocumentParser.load(mode="page")` | `PyMuPDFLoader` (페이지 단위) | `mode="single"` (전체를 하나로) |
| **chunker** | `ChunkingStrategy.recursive_chunk()` | `RecursiveCharacterTextSplitter` (size=1000, overlap=200) | `token_chunk()`, `semantic_chunk()` |
| **embedder** | `get_default_embeddings()` → `EmbeddingManager.get_embeddings("openai")` | `OpenAIEmbeddings("text-embedding-3-large")` | `get_embeddings("huggingface")` → `BAAI/bge-m3` |
| **vectorstore** | `ChromaVectorStore.add_documents()` | Chroma (persist: `data/vectorstore/`) | `FAISSVectorStore`, `PineconeVectorStore` |

---

## python main.py (각 노드별)

| 노드 | 모듈 | 사용 함수 | 현재 설정 | 대안 |
|------|------|-----------|-----------|------|
| **tool.py 초기화** | **retriever** | `get_japan_retriever()` / `get_usa_retriever()` → `get_country_retriever()` → `get_similarity_retriever()` | `search_type="similarity"`, k=6, filter=`{"country": "..."}` | `get_mmr_retriever()`, `get_hybrid_retriever()` |
| **retrieve_node** | **vectorstore** | `ChromaVectorStore.similarity_search()` (retriever 내부) | Chroma similarity | FAISS로 교체 시 후처리 필터 |
| **summarize_node** (doc/page tool) | **vectorstore** | `ChromaVectorStore.max_marginal_relevance_search()` | doc: k=15, fetch_k=40 / page: k=10, fetch_k=30 | k/fetch_k 파라미터 조정 |
| **grade_documents_node** | **grader** | `DocumentGrader.grade()` | structured output (`GradeResult`) + `DOC_GRADER_INSTRUCTIONS` | `grade_single_country()`, 커스텀 instructions 주입 |
| **rewrite_question_node** | **query_transform** | `QueryTransformer.rewrite_for_missing_info()` | `REWRITE_INSTRUCTIONS` + `REWRITE_TEMPLATE` | `multi_query()`, `hyde()`, `step_back()`, `decompose()` |
| **generate_answer_node** | **generator** | `RAGGenerator.generate_with_mode()` | context 있으면 `generate()` / 없으면 `generate_direct()` | `generate_with_citations()` (인용 포함 답변) |

---

## 실험 시 교체 포인트

### ingest.py

```python
# chunker 교체 예시
all_chunks = chunker.token_chunk(japan_docs + usa_docs)
all_chunks = chunker.semantic_chunk(japan_docs + usa_docs, embeddings=get_default_embeddings())

# embedder 교체 예시 (get_default_embeddings 수정)
_default_embeddings = EmbeddingManager.get_embeddings(provider="huggingface")  # BAAI/bge-m3

# vectorstore 교체 예시 (ingest.py 상단에 추가)
from rag.vectorstore import set_vector_store_type
set_vector_store_type("faiss")  # "chroma" | "faiss" | "pinecone"
```

### main.py

```python
# retriever 교체 예시 (retriever.py 수정)
def get_japan_retriever(k=RETRIEVER_K):
    factory = RetrieverFactory()
    return factory.get_mmr_retriever(k=k, filter={"country": "japan"})

# query_transform 교체 예시 (rewrite_question_node 수정)
rewritten_query = query_transformer.multi_query(question=original_question)
rewritten_query = query_transformer.hyde(question=original_question)

# generator 교체 예시 (generate_answer_node 수정)
response = rag_generator.generate_with_citations(question=question, documents=docs)
```
