# LangGraph Agentic RAG Project

LangGraph를 활용한 Agentic RAG (Retrieval-Augmented Generation) 시스템입니다.

## 📁 프로젝트 구조

```
langgraph_rag_project/
├── config.py              # 환경변수, 경로, 상수 설정
├── model.py               # LLM, 임베딩 모델 설정
├── prompt.py              # 모든 프롬프트 템플릿
├── state.py               # GraphState 정의
│
├── rag/                   # RAG 모듈 패키지
│   ├── __init__.py
│   ├── parser.py          # 문서 로딩, 메타데이터 주입
│   ├── chunker.py         # 청킹 전략
│   ├── embedder.py        # 임베딩 관리
│   ├── retriever.py       # 벡터스토어, 검색기
│   ├── grader.py          # 문서 관련성 평가
│   ├── query_transform.py # 쿼리 변환/확장
│   └── generator.py       # RAG 답변 생성
│
├── tool.py                # 검색/요약 도구 정의
├── utils.py               # 유틸리티 함수
├── node.py                # 그래프 노드 정의
├── edge.py                # 그래프 엣지/라우팅
├── graph.py               # 그래프 빌더, 컴파일
├── main.py                # 메인 실행 함수
│
├── data/                  # 데이터 디렉토리
│   ├── pdfs/              # PDF 파일
│   └── vectorstore/       # 벡터스토어 저장
│
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 입력
OPENAI_API_KEY=your-api-key-here
```

### 3. PDF 파일 준비

```bash
# data/pdfs 디렉토리에 PDF 파일 배치
mkdir -p data/pdfs
# ict_japan_2024.pdf, ict_usa_2024.pdf 파일 복사
```

### 4. 벡터스토어 초기화 (최초 1회)

```python
from rag.parser import load_pdf_with_metadata
from rag.chunker import chunk_documents
from rag.retriever import add_documents_to_vectorstore

# 문서 로딩
japan_docs = load_pdf_with_metadata("data/pdfs/ict_japan_2024.pdf", "japan", "1")
usa_docs = load_pdf_with_metadata("data/pdfs/ict_usa_2024.pdf", "usa", "2")

# 청킹
japan_chunks = chunk_documents(japan_docs)
usa_chunks = chunk_documents(usa_docs)

# 벡터스토어에 추가
add_documents_to_vectorstore(japan_chunks + usa_chunks)
```

### 5. 실행

```bash
# 대화형 모드
python main.py interactive

# 단일 질문 실행
python main.py "미국과 일본의 6G 기술 개발 전략을 비교해줘"

# 테스트 실행
python main.py test

# 그래프 시각화
python main.py visualize graph.png
```

## 📊 그래프 워크플로우

자세한 워크플로우는 docs 폴더를 참고하세요 

```
START
  │
  ▼
[analyze_user_intent_node] ──┬── retrieve ──► [retrieve_node]
  │                          │                      │
  │                          │                      ▼
  │                          │              [grade_documents_node]
  │                          │                      │
  │                          │         ┌────────────┴────────────┐
  │                          │         │                         │
  │                          │    (충분)│                    (부족)│
  │                          │         ▼                         ▼
  │                          │         │            [rewrite_question_node]
  │                          │         │                         │
  │                          │         │                         ▼
  │                          │         │            [retry_retrieve_node]
  │                          │         │                         │
  │                          │         │                         ▼
  │                          │         │            [retrieve_node] (재검색)
  │                          │         │
  │                          └── summarize ──► [summarize_node]
  │                          │                      │
  │                          │                      │
  └── generate_answer ───────┴──────────────────────┘
                                        │
                                        ▼
                            [generate_answer_node]
                                        │
                                        ▼
                                       END
```

## 🔧 주요 기능

### RAG 모듈

- **parser.py**: PDF, DOCX 등 다양한 문서 형식 지원
- **chunker.py**: Recursive, Semantic, Token 기반 청킹
- **retriever.py**: Similarity, MMR, Hybrid 검색
- **grader.py**: LLM 기반 문서 관련성 평가
- **query_transform.py**: Multi-Query, HyDE, Step-back 등 쿼리 변환
- **generator.py**: RAG/Direct 모드 답변 생성

### 노드/엣지 분리

- **node.py**: 상태 관리만 담당
- **rag/*.py**: 실제 비즈니스 로직 담당 (RAG 검색)
- 테스트 용이, 재사용 가능

## 📝 사용 예시

```python
from main import run_chat

# 검색 쿼리
response = run_chat(
    question="미국과 일본의 6G 기술 개발 전략을 비교해줘",
    thread_id="session_1",
    uploaded_files=["1", "2"]
)

# 요약 쿼리
response = run_chat(
    question="1번 문서의 핵심 내용을 요약해줘",
    thread_id="session_1",
    uploaded_files=["1", "2"]
)
```


