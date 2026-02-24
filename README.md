# LangGraph Agentic RAG System

LangGraph 기반 Agentic RAG 시스템입니다.
사용자의 질문 의도를 분석하여 **검색 / 요약 / 번역 / 보고서 작성 / 직접 답변** 경로를 자동으로 선택하고, 멀티턴 대화를 지원합니다.

---

## 📁 프로젝트 구조

```
hdmf-ai-search/
├── config.py              # 환경변수, 경로, 상수 설정
├── model.py               # LLM · 임베딩 모델 설정
├── prompt.py              # 모든 프롬프트 템플릿
├── state.py               # GraphState 정의
├── tool.py                # 검색 · 요약 · 번역 도구 정의
├── node.py                # 그래프 노드 정의
├── edge.py                # 그래프 조건부 엣지 / 라우팅
├── graph.py               # 그래프 빌더 및 컴파일
├── main.py                # 메인 실행 진입점
├── ingest.py              # 문서 임베딩 실행
├── utils.py               # 유틸리티 함수
│
├── rag/                   # RAG 핵심 모듈 패키지
│   ├── __init__.py
│   ├── parser.py          # 문서 로딩 · 메타데이터 주입
│   ├── chunker.py         # 청킹 전략 (Recursive / Semantic / Token)
│   ├── embedder.py        # 임베딩 모델 관리
│   ├── vectorstore.py     # 벡터스토어 관리 (Chroma / FAISS / Pinecone)
│   ├── retriever.py       # 검색기 (Similarity / MMR / Hybrid)
│   ├── grader.py          # LLM 기반 문서 관련성 평가
│   ├── query_transform.py # 쿼리 재작성 / 확장
│   └── generator.py       # RAG · 직접 답변 · 보고서 생성
│
├── RAGAS/                          # RAGAS 평가 모듈
│   ├── docs/                       # 평가용 문서 모음 (DART, 보험개발원 등)
│   ├── generate_data.py            # RAGAS 평가 데이터셋 생성
│   ├── ragas_dataset_v0.1.csv      # RAGAS 평가 데이터셋 (1차시도)
│   ├── ragas_dataset_v0.2.csv      # RAGAS 평가 데이터셋 (2차시도)
│   └── ragas_dataset_gemini.xlsx   # 제미나이 활용한 평가 데이터셋
│
├── data/                  # 데이터 디렉토리
│   ├── pdfs/              # 입력 PDF 파일
│   └── vectorstore/       # 벡터스토어 저장 경로
│
├── docs/                     # 문서
│   ├── architecture/         # 아키텍처 문서
│   ├── diagram/              # 다이어그램
│   ├── PROJECT_OVERVIEW.md   # 프로젝트 개요
│   ├── RAG_EXPERIMENT.md     # RAG 모듈별 실험 
│   └── TEST_SCENARIO.md      # 테스트 시나리오 목록
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 OPENAI API 키 입력
OPENAI_API_KEY="your-api-key-here"

# .env 파일에 랭스미스 API 키 입력
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT= "AI Search_test"
LANGCHAIN_API_KEY="your-api-key-here"
```

### 3. PDF 파일 준비

```bash
mkdir -p data/pdfs
# data/pdfs 디렉토리에 PDF 파일 배치
```

### 4. 벡터스토어 초기화 (최초 1회)

```bash
python ingest.py
```

### 5. 실행

```bash
# 대화형 모드 (멀티턴) w/ 문서 참조 없음
python main.py interactive_chat

# 대화형 모드 (멀티턴) w/ 문서 참조
python main.py interactive_doc

# 직접 질문 실행 (단일턴)
python main.py "1번 문서의 핵심 내용을 요약해줘"

# 그래프 시각화
python main.py visualize graph.png
```

---

## 📊 그래프 워크플로우

```
START
  ↓
[analyze_user_intent_node]   ← 사용자 의도 분류 (RETRIEVE | SUMMARIZE | TRANSLATE | DIRECT_ANSWER) + 출력 형태 (answer | report) 결정
  ↓ [route_tools 조건부 엣지]
  │
  ├─[RETRIEVE]──────────────→ [decide_retriever_tool_node]
  │                                      ↓
  │                              [retrieve_node]
  │                                      ↓
  │                          [grade_documents_node]
  │                             [route_after_grading 조건부 엣지]
  │                               부족 ────┤├──────────────── OK 
  │                               ↓                            ↓
  │                          [rewrite_question_node]           │
  │                               ↓                            │
  │                          [retry_retrieve_node]             │
  │                              ↓                             │
  │                          [retrieve_node]                   │
  │                                                            │
  ├─[SUMMARIZE]─────────→ [decide_summary_tool_node]           │
  │                                ↓                           │
  │                        [summarize_node] ──────────────┐    │
  │                                                       │    │
  ├─[TRANSLATE]─────────→ [decide_translate_tool_node]    │    │
  │                                ↓                      │    │
  │                        [translate_node] ──────────────│    │
  │                                                       │    │
  └─[DIRECT_ANSWER]───────────────────────────────────────│    │
                                                          ↓    ↓  
                                              [route_to_generation_node]
                                               ↓ [route_to_generation 조건부 엣지]
                                        answer ┤├ report
                                           ↓        ↓
                          [generate_answer_node] [generate_report_node]
                                           ↓        ↓
                                          END      END
```

### 의도 분류 태그

| 태그 | 설명 |
|---|---|
| `[RETRIEVE]` | 업로드된 문서에서 정보 검색 |
| `[SUMMARIZE]` | 문서 / 텍스트 / 페이지 / 이전 대화 요약 |
| `[TRANSLATE]` | 문서 / 텍스트 / 페이지 / 이전 대화 번역 |
| `[DIRECT_ANSWER]` | 도구 없이 직접 답변 (인사, 후속질문, 사전지식 활용한 질문 등) |
| `[INTENT:answer]` | 출력 형태: 단순 질의 응답 |
| `[INTENT:report]` | 출력 형태: 보고서 / 기획안 작성 |

---

## 🔧 주요 구성 요소

### 노드 (node.py)

| 노드 | 역할 | 진입 조건 | 입력 state | 업데이트 state |
|---|---|---|---|---|
| `analyze_user_intent_node` | 사용자 질문을 작업유형 (`[RETRIEVE/SUMMARIZE/TRANSLATE/DIRECT_ANSWER]`) 과 출력형태 (`[INTENT:answer/report]`) 로 분류 | START 직후 항상 실행 | `chat_history`, `uploaded_files` | `internal_history`, `original_query`, `intent_type`, `retry_count`=0, `final_context`="", `needed_search`=[], `from_summarize`=False |
| `decide_retriever_tool_node` | `search_doc_tool` 호출 인자 생성 (query, filter_metadata) | `[RETRIEVE]` 분류 시 | `chat_history`, `original_query`, `uploaded_files` | `internal_history` |
| `decide_summary_tool_node` | 4개 요약 도구 중 적절한 도구 및 인자 선택 | `[SUMMARIZE]` 분류 시 | `chat_history`, `original_query`, `uploaded_files` | `internal_history` |
| `decide_translate_tool_node` | 4개 번역 도구 중 적절한 도구 및 인자 선택 | `[TRANSLATE]` 분류 시 | `chat_history`, `original_query`, `uploaded_files` | `internal_history` |
| `retrieve_node` | 검색 도구 (`search_doc_tool`) 실행 | `decide_retriever_tool_node` 이후 / `retry_retrieve_node` 이후 | `internal_history` | `internal_history` |
| `summarize_node` | 요약 도구 실행 후 결과를 `chat_history` · `final_context`에 저장 | `decide_summary_tool_node` 이후 | `internal_history` | `internal_history`, `chat_history`, `final_context`, `from_summarize`=True |
| `translate_node` | 번역 도구 실행 후 결과를 `chat_history` · `final_context`에 저장 | `decide_translate_tool_node` 이후 | `internal_history` | `internal_history`, `chat_history`, `final_context`, `from_summarize`=True |
| `grade_documents_node` | 검색 결과의 관련도를 tool_call 단위로 개별 평가 | `retrieve_node` 이후 | `internal_history`, `original_query`, `retry_count`, `final_context` | `needed_search`, `final_context`, `retry_count` |
| `rewrite_question_node` | 관련도 부족 시 검색 쿼리 재작성 | `needed_search` 있고 `retry_count` < 2 | `original_query`, `needed_search` | `internal_history` |
| `retry_retrieve_node` | 재작성된 쿼리로 재검색 명령 생성 | `rewrite_question_node` 이후 | `internal_history`, `needed_search` | `internal_history` |
| `route_to_generation_node` | 생성 노드 분기 전 pass-through | 요약/번역 완료 후 / 검색 평가 통과 후 / `[DIRECT_ANSWER]` 분류 시 | `intent_type` | `intent_type` (변경 없음) |
| `generate_answer_node` | 최종 답변 생성. `from_summarize=True`이면 bypass (요약/번역 결과를 그대로 사용) | `intent_type`=`"answer"` | `chat_history`, `original_query`, `final_context`, `from_summarize` | bypass 시: `from_summarize`=False / 생성 시: `chat_history` |
| `generate_report_node` | 기획안 / 보고서 / 제안서 생성 (`final_context`를 context로 활용) | `intent_type`=`"report"` | `chat_history`, `original_query`, `final_context` | `chat_history` |

### 조건부 엣지 (edge.py)

| 엣지 | 분기 기준 |
|---|---|
| `route_tools` | `analyze_user_intent_node` 출력 태그 → `decide_retriever_tool_node` or `decide_summary_tool_node` or `decide_translate_tool_node` or `route_to_generation_node`로 분기 |
| `route_after_grading` | 관련도 평가 결과 + 재시도 횟수 → `route_to_generation_node`or `rewrite_Question_node` 분기 |
| `route_to_generation` | `intent_type` 결과 (`"answer"` or `"report"`) → `generate_answer_node` or `generate_report_node` 분기 |

### 도구 (tool.py)

**검색 도구**

| 도구 | 설명 |
|---|---|
| `search_doc_tool` | 벡터스토어 유사도 검색. `filter_metadata`로 특정 문서 필터링 가능 |

> 검색 도구는 추후 기능에 따라 추가 확장될 수 있습니다. 

**요약 도구**

| 도구 | 설명 |
|---|---|
| `summarize_doc_tool` | 사용자가 지정한 특정 문서 전체 요약 (MMR 검색 후 요약) |
| `summarize_page_tool` | 사용자가 지정한 특정 문서의 특정 페이지 요약 |
| `summarize_text_tool` | 사용자가 직접 입력한 텍스트 요약 |
| `summarize_history_tool` | 이전 대화(AI 답변)를 대상으로 요약 |

**번역 도구**

| 도구 | 설명 |
|---|---|
| `translate_doc_tool` | 사용자가 지정한 특정 문서 전체 번역 (전체 청크를 페이지/청크 순으로 가져와 번역) |
| `translate_page_tool` | 사용자가 지정한 특정 페이지 번역 |
| `translate_text_tool` | 사용자가 직접 입력한 텍스트 번역 |
| `translate_history_tool` | 이전 대화(AI 답변)를 대상으로 번역 |

> 번역 도구는 원문을 요약하지 않고 **원문 형식 그대로** 번역합니다.

### LLM 모델 역할 분리 (model.py)

| 역할 | 변수명 | 설명 |
|---|---|---|
| 의도 분석 / 도구 결정 | `decision_model` | 사용자 의도 분류 및 tool_calls 생성 |
| 문서 관련도 평가 | `grader_model` | 검색 결과 관련도 JSON 평가 |
| 쿼리 재작성 | `rewrite_model` | 부족한 검색어 재생성 |
| 답변 생성 | `response_model` | RAG / Direct / Report 답변 생성 |
| 요약 | `summary_model` | 문서 · 텍스트 · 히스토리 요약 |
| 번역 | `translate_model` | 문서 · 텍스트 · 히스토리 번역 |

> 연재는 변수명만 구분하고 동일한 LLM 모델 사용 (GPT-4.1-mini)

### RAG 모듈 (rag/)

| 모듈 | 설명 |
|---|---|
| `parser.py` | PDF / DOCX 로딩, 파일 메타데이터(`file_id`, `file_name`, `page`) 주입 |
| `chunker.py` | Recursive (default) / Semantic / Token 기반 청킹 전략 |
| `embedder.py` | 임베딩 모델 관리 |
| `vectorstore.py` | Chroma (default) / FAISS / Pinecone 벡터스토어 팩토리 패턴. `get_all_by_filter()`로 전체 청크 순서대로 조회 가능 |
| `retriever.py` | Similarity (default) / MMR / Hybrid 검색기 |
| `grader.py` | LLM 기반 문서 관련도 평가 (`DocumentGrader`) |
| `query_transform.py` | 재검색을 위한 쿼리 변환 (`QueryTransformer`) |
| `generator.py` | RAG 답변 / 직접 답변 / 보고서 생성 (`RAGGenerator`) |

### 상태 (state.py)

| 필드 | 타입 | 설명 |
|---|---|---|
| `chat_history` | `list` | 사용자-AI 순수 대화 이력 (Human / AI message) |
| `internal_history` | `list` | 시스템 내부 작업 이력 (tool_calls, tool messages 등) |
| `final_context` | `str` | 생성 노드에 전달되는 컨텍스트. RETRIEVE 경로: 관련도 평가를 통과한 검색 결과 누적 / SUMMARIZE·TRANSLATE 경로: 요약·번역 결과 |
| `needed_search` | `List[dict]` | 재검색이 필요한 메타데이터 필터 목록 (태그가 [RETRIEVER] 일 때만 사용) |
| `retry_count` | `int` | 재검색 시도 횟수 (태그가 [RETRIEVER] 일 때만 사용) |
| `uploaded_files` | `List[dict]` | 현재 세션 업로드 파일 메타데이터 |
| `original_query` | `str` | 현재 턴 사용자 최초 원본 질문 |
| `from_summarize` | `bool` | 요약/번역 노드 경유 여부 (generate_answer bypass 플래그) |
| `intent_type` | `str` | 출력 형태 (`"answer"` or `"report"`) |

---

## 📋 테스트 시나리오

지원 시나리오 목록은 [docs/TEST_SCENARIO.md](docs/TEST_SCENARIO.md)를 참고하세요.

**단일 턴으로 처리 가능한 주요 케이스:**
- 문서 검색 및 질의 응답
- 단일/다중 문서 요약 · 페이지 요약 · 텍스트 요약
- 단일/다중 문서 번역 · 페이지 번역 · 텍스트 번역
- 검색 결과 기반 보고서 / 기획안 작성
- 요약 결과 기반 보고서 / 기획안 작성

**멀티턴으로 처리하는 케이스:**
- 검색 → 요약 / 번역 / 보고서
- 요약 → 번역 / 보고서
- 번역 → 요약 / 보고서
- 검색 → 요약 → 번역
