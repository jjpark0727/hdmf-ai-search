# LangGraph Agentic RAG System

AI서치 시스템(1단계) 구현을 위한 LangGraph 기반 Agentic RAG 시스템 입니다. 


## 📁 프로젝트 구조

```
langgraph_rag_project/
├── config.py              # 환경변수, 경로, 상수 설정
├── model.py               # LLM, 임베딩 모델 설정
├── prompt.py              # 모든 프롬프트 템플릿
├── state.py               # GraphState 정의
├── tool.py                # 검색/요약 도구 정의
├── utils.py               # 유틸리티 함수
├── node.py                # 그래프 노드 정의
├── edge.py                # 그래프 엣지/라우팅
├── graph.py               # 그래프 빌더, 컴파일
├── main.py                # 메인 실행 함수
├── ingest.py              # 문서 임베딩 실행 함수
│
├── rag/                   # RAG 모듈 패키지
│   ├── __init__.py
│   ├── parser.py          # 문서 로딩, 메타데이터 주입
│   ├── chunker.py         # 청킹 전략
│   ├── embedder.py        # 임베딩 관리
│   ├── vectorstore.py     # 벡터스토어 관리
│   ├── retriever.py       # 검색기
│   ├── grader.py          # 문서 관련성 평가
│   ├── query_transform.py # 쿼리 변환/확장
│   └── generator.py       # RAG 답변 생성
│
├── RAGAS/                       # RAGAS 평가용 
│   ├── docs/                    # 평가에 사용할 문서 모음 
│   ├── generate_data.py         # RAGAS 평가 데이터셋 생성 
│   ├── ragas_dataset_v0.X.csv   # generate_data.py로 생성한 평가 데이터셋   
│   └── ragas_dataset.xlsx       # Gemini 로 생성한 평가 데이터셋
│
├── data/                  # 데이터 디렉토리
│   ├── pdfs/              # PDF 파일
│   └── vectorstore/       # 벡터스토어 저장
│
├── docs/                  # 문서 디렉토리
│   ├── architecture/      # 아키텍처 문서
│   ├── diagram/           # 다이어그램 문서
│   │
│   ├── PROJECT_OVERVIEW.md    
│   └── RAG_EXPERIMENT.md      
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
# 테스트용 샘플 파일: ict_japan_2024.pdf, ict_usa_2024.pdf 
```

### 4. 벡터스토어 초기화 (최초 1회)

```bash
# 테스트 문서 임베딩
python ingest.py

```

### 5. 실행

```bash
# 대화형 모드 (멀티턴)
python main.py interactive

# 단일 질문 실행
python main.py "미국과 일본의 6G 기술 개발 전략을 비교해줘"

# 테스트 실행
python main.py test

# 그래프 시각화
python main.py visualize graph.png
```

## 📊 그래프 워크플로우

자세한 워크플로우는 docs 폴더를 참고하세요. 
사용자 의도 (검색/요약/번역/기획안작성/직접답변 등) 별로 노드는 추가될 예정입니다.

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
- **chunker.py**: Recursive, Semantic, Token 기반 청킹 등 
- **retriever.py**: Similarity, MMR, Hybrid 검색 등
- **grader.py**: LLM 기반 문서 관련성 평가
- **query_transform.py**: Multi-Query, HyDE, Step-back 등 쿼리 변환
- **generator.py**: RAG/Direct 모드 답변 생성

### 노드/엣지 분리

- **node.py**: 상태 관리만 담당
    - analyze_user_intent_node : 사용자 의도 분석 노드
    - retrieve_node : 검색 노드 (retrieve_node_tools 사용)
    - summarize_node : 요약 노드 (summarize_node_tools 사용)
    - grade_documents_node : 문서 관련도 평가 노드 (실제 로직은 rag/DocumentGrader 담당)
    - rewrite_question_node : 쿼리 재작성 노드 (실제 로직은 rag/query_transform 담당)
    - retry_retrieve_node : 재검색 의도 파악 노드 
    - generate_answer_node : 답변 생성 노드 (실제 로직은 rag/generator 담당)
- **edge.py**: 조건부 엣지
    - route_tools: 사용자 의도 분석 결과에 따라 다음 노드 결정 (analyze_user_intent_node 이후)
    - route_after_grading: 문서 평가 결과에 따라 다음 노드 결정 (grade_documents_node 이후) 
- **rag/*.py**: 실제 비즈니스 로직 담당 (RAG 검색용)

