# 테스트 시나리오 목록

> 현재 graph 구조 기준 (단일 action per turn)
> 컬럼: 시나리오 | 분류 | 단일턴 여부 | 흐름 요약

---

## 1. 단일 턴 — RETRIEVE 경로

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| "문서에서 6G 기술에 대해 알려줘" | RETRIEVE + answer | ✅ | analyze → decide_R → retrieve → grade(OK) → route_gen → gen_answer → END |
| "1번 문서에서 핵심 기술 알려줘" | RETRIEVE + answer (필터) | ✅ | 위와 동일, `search_doc_tool(filter={"file_id":"1"})` |
| "1번과 2번 문서를 비교해서 알려줘" | RETRIEVE + answer (다중) | ✅ | `search_doc_tool` 2회 병렬 호출 → grade(각각) → route_gen → gen_answer |
| "문서 기반으로 6G 기술 보고서 작성해줘" | RETRIEVE + report | ✅ | analyze → decide_R → retrieve → grade(OK) → route_gen → gen_report → END |
| "1번 문서로 기획안 만들어줘" | RETRIEVE + report (필터) | ✅ | 위와 동일, `filter={"file_id":"1"}` |
| "문서에서 잘 없을 것 같은 정보 찾아줘" | RETRIEVE + 재검색 + answer | ✅ | analyze → retrieve → grade(FAIL) → rewrite → retry_retrieve → retrieve → grade(OK/FAIL) → gen_answer |
| "1번과 2번 문서에서 각각 찾아줘, 1번은 잘 안나올 수 있어" | RETRIEVE + 부분재검색 | ✅ | grade(1번:FAIL, 2번:OK) → 2번 final_context 보존 → rewrite(1번만) → retry → grade → gen_answer |

---

## 2. 단일 턴 — SUMMARIZE 경로

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| "1번 문서 요약해줘" | SUMMARIZE(doc) + answer | ✅ | analyze → decide_S → `summarize_doc_tool` → summarize_node → route_gen → gen_answer(bypass) |
| "1번, 2번 문서 함께 요약해줘" | SUMMARIZE(doc, 다중) + answer | ✅ | `summarize_doc_tool(file_ids=["1","2"])` → 각 문서 MMR → 합산 요약 |
| "1번 문서 5페이지 요약해줘" | SUMMARIZE(page) + answer | ✅ | `summarize_page_tool(file_ids=["1"], pages=[5])` → summarize_node → gen_answer(bypass) |
| "1번 문서 3~5페이지 요약해줘" | SUMMARIZE(multi-page) + answer | ✅ | `summarize_page_tool(file_ids=["1"], pages=[3,4,5])` |
| "1번 문서 5페이지, 2번 문서 3페이지 요약해줘" | SUMMARIZE(cross-doc page) + answer | ✅ | `summarize_page_tool` 문서별 분리 2회 호출 |
| "[텍스트 붙여넣기] 이거 요약해줘" | SUMMARIZE(text) + answer | ✅ | `summarize_text_tool(input_text=붙여넣은텍스트)` → summarize_node → gen_answer(bypass) |
| "[텍스트 붙여넣기] 3줄로 요약해줘" | SUMMARIZE(text) + format | ✅ | `summarize_text_tool(format_instruction="3줄로")` |
| "1번 문서 요약해서 보고서 만들어줘" | SUMMARIZE(doc) + report | ✅ | analyze → decide_S → `summarize_doc_tool` → summarize_node(chat_history에 요약 저장) → route_gen → gen_report(chat_history 기반) → END |

---

## 3. 단일 턴 — TRANSLATE 경로

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| "1번 문서 영어로 번역해줘" | TRANSLATE(doc) + answer | ✅ | analyze → decide_T → `translate_doc_tool`(전체 청크 순서대로) → translate_node → route_gen → gen_answer(bypass) |
| "1번 문서 일본어로 번역해줘" | TRANSLATE(doc) + language | ✅ | `translate_doc_tool(language="일본어")` |
| "1번, 2번 문서 함께 번역해줘" | TRANSLATE(doc, 다중) + answer | ✅ | `translate_doc_tool(file_ids=["1","2"])` |
| "1번 문서 3페이지 번역해줘" | TRANSLATE(page) + answer | ✅ | `translate_page_tool(file_ids=["1"], pages=[3])` |
| "1번 문서 3~5페이지 번역해줘" | TRANSLATE(multi-page) + answer | ✅ | `translate_page_tool(file_ids=["1"], pages=[3,4,5])` |
| "[텍스트 붙여넣기] 이거 한국어로 번역해줘" | TRANSLATE(text) + answer | ✅ | `translate_text_tool(input_text=붙여넣은텍스트, language="한국어")` |

---

## 4. 단일 턴 — DIRECT_ANSWER 경로

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| "안녕하세요" / "고마워" | DIRECT_ANSWER + answer | ✅ | analyze → route_gen → gen_answer(chat_history 기반) → END |
| "6G 기술이 뭐야?" (사전지식 질문) | DIRECT_ANSWER + answer | ✅ | 위와 동일, 사전지식으로 답변 |
| "AI 트렌드 보고서 만들어줘" (사전지식) | DIRECT_ANSWER + report | ✅ | analyze → route_gen → gen_report(사전지식 활용) → END |

---

## 5. 멀티턴 시나리오 (2턴)

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| T1: "문서에서 6G 기술 알려줘" → T2: "방금 내용 요약해줘" | RETRIEVE → SUMMARIZE(history) | ❌ 2턴 | T1: retrieve → gen_answer / T2: `summarize_history_tool`(직전 AI 답변) → gen_answer(bypass) |
| T1: "문서에서 6G 기술 알려줘" → T2: "방금 내용 3줄로 요약해줘" | RETRIEVE → SUMMARIZE(history+format) | ❌ 2턴 | T2: `summarize_history_tool(format_instruction="3줄로")` |
| T1: "문서에서 6G 기술 알려줘" → T2: "방금 내용 영어로 번역해줘" | RETRIEVE → TRANSLATE(history) | ❌ 2턴 | T1: retrieve → gen_answer / T2: `translate_history_tool`(직전 AI 답변, language="영어") → gen_answer(bypass) |
| T1: "1번 문서 요약해줘" → T2: "방금 요약 내용 영어로 번역해줘" | SUMMARIZE → TRANSLATE(history) | ❌ 2턴 | T1: `summarize_doc` → gen_answer(bypass) / T2: `translate_history_tool`(요약 결과) → gen_answer(bypass) |
| T1: "1번 문서 번역해줘" → T2: "방금 번역 내용 3줄로 요약해줘" | TRANSLATE → SUMMARIZE(history) | ❌ 2턴 | T1: `translate_doc` → gen_answer(bypass) / T2: `summarize_history_tool`(번역 결과) → gen_answer(bypass) |
| T1: "문서에서 6G 기술 알려줘" → T2: "방금 내용으로 보고서 작성해줘" | RETRIEVE → DIRECT_ANSWER(report) | ❌ 2턴 | T1: retrieve → gen_answer / T2: DIRECT_ANSWER+report → gen_report(chat_history=T1 결과) → END |
| T1: "1번 문서 요약해줘" → T2: "방금 요약 내용으로 보고서 만들어줘" | SUMMARIZE → DIRECT_ANSWER(report) | ❌ 2턴 | T1: `summarize_doc` → gen_answer(bypass) / T2: DIRECT_ANSWER+report → gen_report(chat_history=요약 결과) |
| T1: "1번 문서 번역해줘" → T2: "방금 번역 내용으로 보고서 만들어줘" | TRANSLATE → DIRECT_ANSWER(report) | ❌ 2턴 | T1: `translate_doc` → gen_answer(bypass) / T2: DIRECT_ANSWER+report → gen_report(chat_history=번역 결과) |
| T1: "문서에서 6G 기술 알려줘" → T2: "좀 더 자세히 알려줘" | RETRIEVE → DIRECT_ANSWER(후속질문) | ❌ 2턴 | T1: retrieve → gen_answer / T2: DIRECT_ANSWER+answer → gen_answer(chat_history 기반 부연 설명) |
| T1: "1번 문서 요약해줘" → T2: "2번 문서도 요약해줘" | SUMMARIZE → SUMMARIZE | ❌ 2턴 | T1: `summarize_doc(["1"])` / T2: `summarize_doc(["2"])` (각각 독립 실행) |
| T1: "1번 문서 번역해줘" → T2: "2번 문서도 번역해줘" | TRANSLATE → TRANSLATE | ❌ 2턴 | T1: `translate_doc(["1"])` / T2: `translate_doc(["2"])` (각각 독립 실행) |

---

## 6. 멀티턴 시나리오 (3턴 이상)

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| T1: "문서에서 6G 찾아줘" → T2: "방금 내용 요약해줘" → T3: "방금 요약 영어로 번역해줘" | RETRIEVE → SUMMARIZE → TRANSLATE | ❌ 3턴 | T1: retrieve → gen_answer / T2: `summarize_history` → gen_answer(bypass) / T3: `translate_history`(요약 결과) → gen_answer(bypass) |
| T1: "문서에서 6G 찾아줘" → T2: "방금 내용 요약해줘" → T3: "방금 요약 내용으로 보고서 만들어줘" | RETRIEVE → SUMMARIZE → REPORT | ❌ 3턴 | T1: retrieve → gen_answer / T2: `summarize_history` → gen_answer(bypass) / T3: DIRECT_ANSWER+report → gen_report |
| T1: "1번 문서 요약해줘" → T2: "방금 요약 영어로 번역해줘" → T3: "방금 번역 내용으로 보고서 만들어줘" | SUMMARIZE → TRANSLATE → REPORT | ❌ 3턴 | T1: `summarize_doc` / T2: `translate_history` / T3: DIRECT_ANSWER+report → gen_report |
| T1: "1번 문서 요약해줘" → T2: "2번 문서도 요약해줘" → T3: "두 요약 내용 합쳐서 비교 보고서 만들어줘" | SUMMARIZE×2 → REPORT | ❌ 3턴 | T1,T2: 각각 `summarize_doc` / T3: DIRECT_ANSWER+report → gen_report(chat_history에 두 요약 모두 존재) |

---

## 7. 경계 / 예외 케이스

| 시나리오 | 분류 | 단일턴 | 흐름 요약 |
|---|---|:---:|---|
| "문서에 없는 내용 찾아줘" (재검색 2회 모두 실패) | RETRIEVE + 재검색 실패 | ✅ | grade(FAIL) → rewrite → retry → grade(FAIL, retry_count≥MAX) → gen_answer("정보 없음" 답변) |
| "안녕" (대화 기록 없음, 첫 턴) | DIRECT_ANSWER + answer (cold start) | ✅ | chat_history 없이 gen_answer |
| T1: "문서 검색해줘" → T2: "1번 문서에서 찾아줘" (문서 범위 좁히기) | RETRIEVE → RETRIEVE(필터 추가) | ❌ 2턴 | T2: RETRIEVE, `filter={"file_id":"1"}` (chat_history 맥락 반영) |
| "이전 대화 전체 요약해줘" (여러 AI 답변 합산) | SUMMARIZE(history, 복수) | ✅ (멀티턴 이후) | `summarize_history_tool(input_text=여러 AI 답변 합산)` → gen_answer(bypass) |

---

## 참고: 노드 약어 정의

| 약어 | 노드명 |
|---|---|
| analyze | `analyze_user_intent_node` |
| decide_R | `decide_retriever_tool_node` |
| retrieve | `retrieve_node` |
| grade | `grade_documents_node` |
| rewrite | `rewrite_question_node` |
| retry_retrieve | `retry_retrieve_node` |
| decide_S | `decide_summary_tool_node` |
| summarize_node | `summarize_node` |
| decide_T | `decide_translate_tool_node` |
| translate_node | `translate_node` |
| route_gen | `route_to_generation_node` |
| gen_answer | `generate_answer_node` |
| gen_report | `generate_report_node` |
| bypass | `from_summarize=True`이므로 gen_answer 내부 로직 스킵, chat_history의 결과가 그대로 응답 |
