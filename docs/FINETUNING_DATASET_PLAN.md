# 파인튜닝 학습 데이터 구축 계획

## 개요

이 문서는 `hdmf-ai-search` 시스템의 출력 생성 품질을 향상시키기 위한 파인튜닝 학습 데이터 구축 계획을 정의합니다.
파인튜닝 목표는 모델이 회사의 어투/문체로 일관된 답변을 생성하도록 하는 것입니다.

---

## 파인튜닝 대상 모델

> `model.py`에서 현재 모든 역할 모델이 동일 베이스 모델을 공유함.
> 파인튜닝 시 역할별로 별도 모델로 분리할지, 하나의 모델을 사용할지 추후 결정 예정.

```python
# model.py (현재 구조)
response_model = model      # 4. 답변 생성 모델
summary_model  = model      # 5. 요약 모델
translate_model = model     # 6. 번역 모델
```

| 모델 | 담당 케이스 | 프롬프트 구조 | 관련 코드 |
|---|---|---|---|
| `response_model` | RETRIEVE+answer, DIRECT+answer, 모든 report | system + (chat_history) + user | `rag/generator.py` |
| `summary_model`  | SUMMARIZE+answer (4 sub-types) | user 단독 (system 없음) | `tool.py` |
| `translate_model`| TRANSLATE+answer (4 sub-types) | user 단독 (system 없음) | `tool.py` |

> SUMMARIZE+report, TRANSLATE+report는 요약/번역 결과가 `final_context`에 채워진 후
> `response_model`의 report 모드로 처리됩니다. (`node.py` → `generate_report_node`)

---

## 케이스별 구조 요약

```
response_model:
  Case 1  RETRIEVE + answer  →  system(ANSWER_INSTRUCTIONS) + user(question+context) → 문서 기반 답변
  Case 2  RETRIEVE + report  →  system(REPORT_INSTRUCTIONS) + user(question+context) → 보고서
  Case 3  SUMMARIZE + answer →  요약 요청 구분에 따라 분기                              →  요약내용 = 답변
  Case 4  SUMMARIZE + report →  system(REPORT_INSTRUCTIONS) + user(question+요약문)  → 요약 기반 보고서
  Case 5  TRANSLATE + answer →  번역 요청 구분에 따라 분기                              →  번역내용 = 답변
  Case 6  TRANSLATE + report →  system(REPORT_INSTRUCTIONS) + user(question+번역문)  → 번역 기반 보고서
  Case 7  DIRECT + answer    →  system(DIRECT_INSTRUCTIONS) + user(question)         → 직접 답변
  Case 8  DIRECT + report    →  system(REPORT_INSTRUCTIONS) + user(question+"없음")  → 지식 기반 보고서

summary_model:
  Case 3A summarize_doc      →  user(SUMMARY_DOC_PROMPT  + 문서청크)    → 문서 요약
  Case 3B summarize_text     →  user(SUMMARY_TEXT_PROMPT + 붙여넣기)    → 텍스트 요약
  Case 3C summarize_page     →  user(SUMMARY_PAGE_PROMPT + 페이지청크)  → 페이지 요약
  Case 3D summarize_history  →  user(SUMMARY_HISTORY_PROMPT + AI응답)   → 히스토리 요약

translate_model:
  Case 5A translate_doc      →  user(TRANSLATE_DOC_PROMPT  + 문서청크)    → 문서 번역
  Case 5B translate_text     →  user(TRANSLATE_TEXT_PROMPT + 붙여넣기)    → 텍스트 번역
  Case 5C translate_page     →  user(TRANSLATE_PAGE_PROMPT + 페이지청크)  → 페이지 번역
  Case 5D translate_history  →  user(TRANSLATE_HISTORY_PROMPT + AI응답)   → 히스토리 번역
```

---

## 케이스별 수집 가이드 및 권장 비중

| Case | RAG 있음 | RAG 없음 | 싱글턴 | 멀티턴 | 권장 비중 |
|---|---|---|---|---|---|
| 1. RETRIEVE + answer  | ✅ 필수 | ❌ | ✅ | ✅ | ~25% |
| 2. RETRIEVE + report  | ✅ 필수 | ❌ | ✅ | ✅ | ~10% |
| 3. SUMMARIZE + answer | ✅ (doc/page) | ✅ (text/history) | ✅ | ✅ | ~15% |
| 4. SUMMARIZE + report | ✅ (소수) | ✅ (소수) | ✅ | ✅ | ~3% |
| 5. TRANSLATE + answer | ✅ (doc/page) | ✅ (text/history) | ✅ | ✅ | ~15% |
| 6. TRANSLATE + report | ✅ (소수) | ✅ (소수) | ✅ | ✅ | ~2% |
| 7. DIRECT + answer    | ✅ ⚠️ | ✅ | ✅ | ✅ | ~20% |
| 8. DIRECT + report    | ✅ ⚠️ | ✅ | ✅ | ✅ | ~10% |

---

## 공통 데이터 포맷

모든 케이스에서 아래 구조를 기본으로 합니다.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "(해당 케이스의 INSTRUCTIONS 전문)"
    },
    // chat_history[:-1]: 이전 대화 턴 (싱글턴이면 생략)
    { "role": "user",      "content": "이전 사용자 발화" },
    { "role": "assistant", "content": "이전 AI 응답" },
    {
      "role": "user",
      "content": "(해당 케이스의 TEMPLATE에 question/context를 채운 값)"
    },
    {
      "role": "assistant",
      "content": "(회사 어투로 작성된 이상적인 출력)"
    }
  ]
}
```

> `summary_model`, `translate_model`은 `system` 없이 `user` 단독 메시지만 사용합니다.
> (`tool.py`의 각 tool 함수 참고)

---

## Case 1 — RETRIEVE + answer

> **모델:** `response_model` | **호출 함수:** `generate_answer()` (`rag/generator.py`)
> **입력:** question + 검색 및 grade 통과한 문서 chunks (final_context)
> **출력:** 문서 기반 답변

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 단일 문서 지정 검색 | 있음 | "1번 문서에서 AI 위험관리 프레임워크 설명해줘" |
| 전체 문서 검색 | 있음 | "업로드 문서에서 핀테크 규제 현황 알려줘" |
| 복수 문서 비교 검색 | 있음 | "1번이랑 2번 문서에서 보험료 산정 방식 각각 찾아줘" |
| 멀티턴 — 문서 명시 연장 | 있음 | *(이전 대화 후)* "그럼 그 부분 문서에서 더 찾아봐줘" |
| RAG 없음 | ❌ | 업로드 파일 없으면 RETRIEVE 불성립 |

```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 질문-답변 업무를 수행하는 전문 어시스턴트야.\n제공된 검색 문맥(context)을 사용하여 사용자의 질문에 답변해줘.\n\n[답변 가이드라인]\n1. 반드시 제공된 문맥(context)에 근거하여 답변할 것.\n2. 문맥에 특정 주제에 대한 정보가 부족하거나 \"정보가 없다\"는 안내가 포함되어 있다면, 추측하지 말고 \"해당 정보는 문서에 포함되어 있지 않습니다\"라고 정중히 안내할 것.\n3. 답변은 논리적이고 친절하게 작성할 것.\n4. 만약 답변을 전혀 할 수 없는 경우에는 \"죄송합니다만, 요청하신 정보가 현재 문서에 없습니다\"라고 답변할 것."
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 제공된 문맥을 근거로 삼아 사용자의 질문에 대한 최종 답변을 작성하십시오.\n\n### [Data]\n- 원본 질문: AI 위험관리 프레임워크(AI RMF)의 핵심 구성요소가 뭐야?\n---\n- 문맥: AI 위험관리 프레임워크(AI RMF)는 크게 네 가지 핵심 기능으로 구성된다. 첫째, GOVERN(관리)은 AI 위험관리 문화와 관행을 조직 전반에 정착시키는 기반 기능이다. 둘째, MAP(식별)은 AI 시스템과 관련된 위험의 맥락을 설정하고 분류하는 기능이다. 셋째, MEASURE(측정)는 식별된 위험을 분석하고 평가하며 추적하는 기능이다. 넷째, MANAGE(관리)는 측정된 위험에 대한 우선순위를 설정하고 대응·복구 계획을 실행하는 기능이다.\n---"
    },
    {
      "role": "assistant",
      "content": "AI 위험관리 프레임워크(AI RMF)는 다음 네 가지 핵심 기능으로 구성됩니다.\n\n1. **GOVERN (관리):** AI 위험관리 문화와 관행을 조직 전반에 정착시키는 기반 기능입니다.\n2. **MAP (식별):** AI 시스템과 관련된 위험의 맥락을 설정하고 분류합니다.\n3. **MEASURE (측정):** 식별된 위험을 분석·평가하고 지속적으로 추적합니다.\n4. **MANAGE (관리):** 측정된 위험에 우선순위를 부여하고 대응·복구 계획을 실행합니다.\n\n이 네 기능은 순환적으로 운영되며, GOVERN이 나머지 세 기능의 토대를 이룹니다."
    }
  ]
}
```

---

## Case 2 — RETRIEVE + report

> **모델:** `response_model` | **호출 함수:** `generate_report()` (`rag/generator.py`)
> **입력:** question + 검색된 문서 chunks (final_context)
> **출력:** 기획안/보고서/제안서

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 문서 기반 기획안 | 있음 | "업로드 문서 참고해서 AI 도입 기획안 만들어줘" |
| 문서 기반 분석 보고서 | 있음 | "1번 문서에서 리스크 요인 찾아서 보고서 작성해줘" |
| 복수 문서 기반 제안서 | 있음 | "1번, 2번 문서 내용으로 금융 AI 도입 제안서 써줘" |
| 멀티턴 — 문서 참조 + 보고서 | 있음 | *(이전 대화 후)* "그 문서 내용 기반으로 제안서 작성해줘" |
| RAG 없음 | ❌ | 파일 없으면 RETRIEVE 불성립 |

> **경계 케이스 주의:** 이전 턴에서 검색이 완료된 후 "방금 내용으로 보고서 써줘"는
> `DIRECT_ANSWER + report` (Case 8)가 정답입니다.
> 현재 턴에서 **새 검색이 필요한지 여부**로 구분합니다.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 전문적인 기획안·보고서·제안서 작성 어시스턴트야.\n사용자의 요청에 따라 체계적이고 논리적인 문서를 작성해야 해.\n\n[작성 가이드라인]\n1. 제공된 참고 자료(context)가 있으면 이를 근거로 활용하되, 필요 시 사전 지식을 보충하라.\n2. 기획안/보고서의 구조는 사용자의 요청 의도에 맞게 자율적으로 구성하라.\n3. 각 섹션에는 구체적이고 실행 가능한 내용을 포함하라.\n4. 전문적이고 분석적인 톤을 유지하되, 읽기 쉬운 문체로 작성하라.\n5. 대화 기록(chat_history)이 있다면 이전 맥락을 반영하여 일관성을 유지하라."
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 정보를 바탕으로 사용자의 요청에 맞는 기획안/보고서를 작성하십시오.\n\n### [Data]\n- 사용자 요청: 업로드된 문서를 참고해서 금융권 AI 위험관리 도입 기획안을 작성해줘\n---\n- 참고 자료: 금융감독원은 2025년 AI 위험관리 프레임워크 도입 가이드라인을 발표하였다. 해당 가이드라인은 금융사가 AI 시스템 전 생애주기에 걸쳐 위험을 식별·평가·관리할 것을 권고하고 있다. 특히 AI 모델의 편향성, 불투명성, 사이버 보안 취약성을 3대 핵심 위험으로 규정하였으며, 각 위험에 대한 내부통제 체계 구축을 의무화할 예정이다. 또한 AI 레드팀 운영을 통한 사전 취약점 점검을 강력히 권고하고 있다.\n---"
    },
    {
      "role": "assistant",
      "content": "# 금융권 AI 위험관리 도입 기획안\n\n## 1. 추진 배경\n금융감독원의 AI 위험관리 프레임워크 도입 가이드라인(2025) 발표에 따라, 금융사는 AI 시스템 전 생애주기에 걸친 위험관리 체계 구축이 요구되고 있습니다. 규제 대응과 함께 AI 신뢰성 확보를 위한 선제적 체계 마련이 필요합니다.\n\n## 2. 현황 및 문제 진단\n- **3대 핵심 위험:** 모델 편향성, 불투명성(설명 불가), 사이버 보안 취약성\n- **현행 내부통제:** AI 전담 위험관리 프로세스 부재\n- **규제 동향:** AI 위험관리 내부통제 의무화 예정\n\n## 3. 추진 목표\n- AI 전 생애주기(개발→운영→폐기) 위험관리 프로세스 수립\n- AI 레드팀 운영을 통한 사전 취약점 점검 체계 구축\n- 금감원 가이드라인 100% 준수 및 감독 대응력 강화\n\n## 4. 세부 추진 과제\n\n### 4-1. AI 위험관리 거버넌스 구축\n- AI 위험관리 전담 조직(AI리스크팀) 신설\n- 이사회 수준의 AI 위험관리 보고 체계 마련\n\n### 4-2. 위험 평가 프레임워크 도입\n- GOVERN-MAP-MEASURE-MANAGE 4단계 프로세스 내재화\n- 모델별 위험 등급 분류 기준 마련\n\n### 4-3. AI 레드팀 운영\n- 분기 1회 이상 AI 모델 취약점 점검\n- 점검 결과 경영진 보고 및 개선 조치 이행\n\n## 5. 기대 효과\n- 규제 리스크 선제 대응으로 제재 리스크 최소화\n- AI 신뢰성 제고를 통한 고객 신뢰 확보\n- 내부 AI 거버넌스 수준 업계 선도"
    }
  ]
}
```

---

## Case 3 — SUMMARIZE + answer

> **모델:** `summary_model` | **호출 위치:** `tool.py` 각 summarize_xxx_tool
> **프롬프트 구조:** `system` 없이 `user` 단독 메시지

### 3-A. summarize_doc — 문서 전체 요약

> **입력:** 벡터스토어에서 MMR 검색으로 추출한 문서 청크 (full_text) + format_instruction
> **출력:** 문서별 구조화 요약

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 단일 문서 요약 | 있음 | "1번 문서 요약해줘" |
| 복수 문서 요약 | 있음 | "1번이랑 2번 문서 요약해줘" |
| 형식 지정 요약 | 있음 | "1번 문서 3줄로 요약해줘" |
| RAG 없음 | ❌ | file_id 없으면 불성립 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 문서 요약 전문가입니다.\n제공된 문서에서 추출된 다양한 섹션의 핵심 내용을 간결하게 5줄의 불렛포인트로 요약해줘.\n\n지시사항:\n1. 각 문서별 주요 포인트를 포함할 것\n2. 간결하게 5줄의 불렛포인트로 정리할 것\n3. 전문적이고 분석적인 톤을 유지할 것\n\n출력 포맷:\n- 각 문서별로 구분하여 아래 형식으로 출력하라:\n  ## [N번 문서 요약]\n  (요약 내용)\n\n--- 요약 대상 본문 ---\n--- [문서 출처: 1번 문서] ---\n2025년 10월 New-Tech 트렌드 보고서에 따르면 보험업계의 AI 활용이 가속화되고 있다. 특히 언더라이팅 자동화 분야에서 AI 도입률이 전년 대비 34% 증가하였으며, 보험사기 탐지 정확도는 AI 도입 이후 평균 23%p 향상된 것으로 나타났다. 한편 임베디드 보험의 성장세가 두드러지는데, 플랫폼 기업과의 협업을 통해 보험료 수입이 15% 이상 증가한 사례가 보고되었다. 기후 리스크 관련 신상품 개발도 활발하여 파라메트릭 보험 출시 건수가 전년 대비 2배 증가하였다. 고령화 대응을 위한 헬스케어 연계 상품도 주목받고 있으며, 웨어러블 기기 데이터를 활용한 보험료 할인 상품이 시장에 출시되었다."
    },
    {
      "role": "assistant",
      "content": "## [1번 문서 요약]\n\n- **AI 언더라이팅 자동화 가속:** AI 도입률 전년 대비 34% 증가, 보험사기 탐지 정확도 23%p 향상\n- **임베디드 보험 성장:** 플랫폼 기업 협업을 통한 보험료 수입 15% 이상 증가\n- **파라메트릭 보험 확대:** 기후 리스크 대응 신상품 출시 건수 전년 대비 2배 증가\n- **헬스케어 연계 상품 부상:** 웨어러블 데이터 기반 보험료 할인 상품 시장 출시\n- **종합 평가:** 2025년 보험업계는 AI·디지털 전환과 기후·고령화 리스크 대응이 핵심 트렌드로 부상"
    }
  ]
}
```

### 3-B. summarize_text — 사용자 붙여넣기 텍스트 요약

> **입력:** 사용자가 메시지에 직접 붙여넣은 텍스트 (input_text) + format_instruction
> **출력:** 텍스트 요약

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 텍스트 붙여넣기 요약 | 없음 | "아래 내용 요약해줘: (본문)" |
| 형식 지정 | 없음 | "이 텍스트 3줄로 요약해줘: (본문)" |
| 파일 있어도 텍스트 직접 입력 | 있음/없음 | 질문에 본문이 포함된 경우 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 요약 전문가입니다. \n다음 제공된 텍스트의 핵심 내용을 3줄로 요약해줘.\n\n--- 요약 대상 텍스트 ---\n금융위원회는 2025년 2월, 금융권 클라우드 이용 활성화를 위해 망분리 규제를 대폭 완화하는 방안을 발표하였다. 기존에는 금융사가 인터넷 연결 환경과 업무망을 물리적으로 분리해야 했으나, 앞으로는 논리적 망분리 방식도 허용된다. 이번 규제 완화로 금융사는 퍼블릭 클라우드 서비스를 보다 자유롭게 활용할 수 있게 되었으며, AI·빅데이터 기반 금융 서비스 개발에 탄력을 받을 것으로 전망된다. 다만 금융보안원의 보안 인증 취득은 의무화되어, 보안 수준은 현행 수준을 유지할 예정이다.\n-----------------------"
    },
    {
      "role": "assistant",
      "content": "- 금융위원회가 망분리 규제를 완화하여 논리적 망분리 방식을 허용함으로써 퍼블릭 클라우드 활용이 가능해짐\n- 이에 따라 금융사의 AI·빅데이터 기반 서비스 개발 가속화 전망\n- 단, 금융보안원 보안 인증 의무화로 보안 수준은 현행 유지"
    }
  ]
}
```

### 3-C. summarize_page — 특정 페이지 요약

> **입력:** 벡터스토어에서 file_id + page 필터로 추출한 청크 (full_text) + 페이지 번호 + format_instruction
> **출력:** 페이지별 구조화 요약

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 단일 페이지 요약 | 있음 | "1번 문서 5페이지 요약해줘" |
| 복수 페이지 요약 | 있음 | "1번 문서 3, 5페이지 요약해줘" |
| 복수 문서 동일 페이지 | 있음 | "1번, 2번 문서 10페이지 요약해줘" |
| RAG 없음 | ❌ | file_id + page 없으면 불성립 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 문서 요약 전문가입니다. \n제공된 문서의 특정 페이지 내용을 바탕으로 핵심 정보를 간결하게 3~5줄의 불렛포인트로 요약해줘.\n\n출력 포맷:\n- 문서/페이지 별로 각각 구분하여 아래 형식으로 출력하라:\n  ## [N번 문서 - M페이지 요약]\n  (요약 내용)\n\n--- 요약 대상 본문 (요청 페이지: 5) ---\n--- [문서 ID: 1, 5페이지] ---\n제5장 AI 레드팀 운영 체계\n\n5.1 레드팀 구성 원칙\nAI 레드팀은 공격자 관점에서 AI 시스템의 취약점을 발굴하는 전문 조직이다. 레드팀은 내부 인력과 외부 전문가로 구성하는 것이 원칙이며, 최소 3인 이상으로 운영한다. 팀 구성 시 AI 개발자, 보안 전문가, 도메인 전문가가 포함되어야 한다.\n\n5.2 점검 주기 및 범위\n정기 점검은 연 2회 이상 실시하며, AI 모델 대규모 업데이트 시 수시 점검을 병행한다. 점검 범위는 모델 편향성, 적대적 공격 취약성, 개인정보 추론 가능성, 탈옥(jailbreak) 시도 저항성을 포함한다."
    },
    {
      "role": "assistant",
      "content": "## [1번 문서 - 5페이지 요약]\n\n- **레드팀 구성:** 내부+외부 전문가 혼합, 최소 3인 이상 (AI 개발자·보안·도메인 전문가 필수 포함)\n- **점검 주기:** 정기 연 2회 이상 + 모델 대규모 업데이트 시 수시 점검\n- **점검 4대 영역:** 모델 편향성 / 적대적 공격 취약성 / 개인정보 추론 가능성 / 탈옥 시도 저항성\n- **운영 원칙:** 공격자 관점의 취약점 발굴에 초점"
    }
  ]
}
```

### 3-D. summarize_history — 이전 AI 답변 요약

> **입력:** `decide_summary_tool_node`가 chat_history에서 추출한 AI 응답 원문 (input_text) + format_instruction
> **출력:** 이전 답변 요약
> **주의:** input_text는 원문을 한 글자도 빠짐없이 그대로 전달 (재구성 금지)

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 직전 AI 답변 요약 | 있음/없음 | "방금 답변 3줄로 요약해줘" |
| 이전 대화 지칭 | 있음/없음 | "위 내용 요약해줘", "그거 요약해줘" |
| 이전 보고서 요약 | 있음/없음 | "방금 쓴 기획안 요약해줘" |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 요약 전문가입니다. \n다음 제공된 대화 이력의 핵심 내용을 3줄로 요약해줘.\n\n--- 요약 대상 텍스트 ---\n금융권 AI 위험관리 도입 기획안\n\n1. 추진 배경\n금융감독원의 AI 위험관리 프레임워크 도입 가이드라인(2025) 발표에 따라, 금융사는 AI 시스템 전 생애주기에 걸친 위험관리 체계 구축이 요구되고 있습니다. 규제 대응과 함께 AI 신뢰성 확보를 위한 선제적 체계 마련이 필요합니다.\n\n2. 현황 및 문제 진단\n- 3대 핵심 위험: 모델 편향성, 불투명성, 사이버 보안 취약성\n- 현행 내부통제: AI 전담 위험관리 프로세스 부재\n- 규제 동향: AI 위험관리 내부통제 의무화 예정\n\n3. 추진 목표\n- AI 전 생애주기 위험관리 프로세스 수립\n- AI 레드팀 운영을 통한 사전 취약점 점검 체계 구축\n- 금감원 가이드라인 100% 준수 및 감독 대응력 강화\n-----------------------"
    },
    {
      "role": "assistant",
      "content": "- 금감원 AI RMF 가이드라인 대응을 위한 위험관리 체계 구축 기획안으로, 편향성·불투명성·보안 취약성을 3대 핵심 위험으로 규정\n- AI 전 생애주기 위험관리 프로세스 수립 및 AI 레드팀 운영이 핵심 추진 과제\n- 규제 준수 및 AI 신뢰성 제고를 통한 제재 리스크 최소화와 고객 신뢰 확보를 기대 효과로 제시"
    }
  ]
}
```

---

## Case 4 — SUMMARIZE + report

> **모델:** `response_model` | **호출 함수:** `generate_report()` (`rag/generator.py`)
> **입력:** question + summarize_node 결과가 final_context로 전달됨
> **출력:** 요약 결과 기반 보고서

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 문서 요약을 보고서 형식으로 | 있음 | "1번 문서 내용을 요약해서 임원 보고용 문서로 만들어줘" |
| 이전 답변을 요약 보고서로 | 있음/없음 | "방금 내용 요약해서 공식 보고서로 정리해줘" |
| 텍스트 요약 후 보고서 | 없음 | "*(본문 붙여넣기)* 요약해서 보고서로 만들어줘" |

> **권장 수량:** 전체의 3% 이하. 과다 수집 시 일반 요약도 report로 분류하는 편향 발생.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 전문적인 기획안·보고서·제안서 작성 어시스턴트야.\n사용자의 요청에 따라 체계적이고 논리적인 문서를 작성해야 해.\n\n[작성 가이드라인]\n1. 제공된 참고 자료(context)가 있으면 이를 근거로 활용하되, 필요 시 사전 지식을 보충하라.\n2. 기획안/보고서의 구조는 사용자의 요청 의도에 맞게 자율적으로 구성하라.\n3. 각 섹션에는 구체적이고 실행 가능한 내용을 포함하라.\n4. 전문적이고 분석적인 톤을 유지하되, 읽기 쉬운 문체로 작성하라.\n5. 대화 기록(chat_history)이 있다면 이전 맥락을 반영하여 일관성을 유지하라."
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 정보를 바탕으로 사용자의 요청에 맞는 기획안/보고서를 작성하십시오.\n\n### [Data]\n- 사용자 요청: 1번 문서 내용을 요약해서 임원 보고용 문서로 만들어줘\n---\n- 참고 자료: ## [1번 문서 요약]\n\n- AI 언더라이팅 자동화 가속: AI 도입률 전년 대비 34% 증가, 보험사기 탐지 정확도 23%p 향상\n- 임베디드 보험 성장: 플랫폼 기업 협업을 통한 보험료 수입 15% 이상 증가\n- 파라메트릭 보험 확대: 기후 리스크 대응 신상품 출시 건수 전년 대비 2배 증가\n- 헬스케어 연계 상품 부상: 웨어러블 데이터 기반 보험료 할인 상품 시장 출시\n- 종합 평가: 2025년 보험업계는 AI·디지털 전환과 기후·고령화 리스크 대응이 핵심 트렌드\n---"
    },
    {
      "role": "assistant",
      "content": "# 2025년 보험업계 핵심 트렌드 요약 보고서\n\n**보고 일자:** 2026년 3월\n**보고 목적:** 보험개발원 New-Tech 트렌드 보고서(2025.10) 핵심 내용 임원 보고\n\n---\n\n## 핵심 요약 (Executive Summary)\n2025년 보험업계는 **AI 기반 자동화**, **임베디드 보험 성장**, **기후·헬스케어 신상품 확대**를 3대 핵심 축으로 급격한 변화를 겪고 있습니다.\n\n---\n\n## 1. AI 활용 현황\n| 항목 | 수치 |\n|---|---|\n| AI 언더라이팅 도입률 증가 | 전년 대비 +34% |\n| 보험사기 탐지 정확도 향상 | +23%p |\n\n→ **시사점:** 언더라이팅 효율화 및 손해율 개선 기회 확대\n\n## 2. 신사업 모델 동향\n- **임베디드 보험:** 플랫폼 협업 보험료 수입 +15% 이상\n- **파라메트릭 보험:** 기후 리스크 대응 신상품 출시 2배 증가\n- **헬스케어 연계:** 웨어러블 기기 활용 보험료 할인 상품 본격화\n\n## 3. 대응 방향 제언\n1. AI 언더라이팅 시스템 자체 구축 또는 전문 솔루션 도입 검토\n2. 플랫폼 기업 대상 임베디드 보험 파트너십 확대\n3. ESG 연계 파라메트릭 상품 개발 TF 구성"
    }
  ]
}
```

---

## Case 5 — TRANSLATE + answer

> **모델:** `translate_model` | **호출 위치:** `tool.py` 각 translate_xxx_tool
> **프롬프트 구조:** `system` 없이 `user` 단독 메시지

### 5-A. translate_doc — 문서 전체 번역

> **입력:** `get_all_by_filter`로 순서대로 가져온 전체 청크 (full_text) + language + format_instruction

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 단일 문서 번역 | 있음 | "1번 문서 영어로 번역해줘" |
| 복수 문서 번역 | 있음 | "1번, 2번 문서 번역해줘" |
| 언어 지정 | 있음 | "1번 문서 일본어로 번역해줘" |
| RAG 없음 | ❌ | file_id 없으면 불성립 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 전문 번역가입니다.\n제공된 문서 내용을 영어로 번역하세요.\n\n번역 원칙:\n1. 원문의 모든 내용을 빠짐없이 번역할 것 (요약하거나 생략하지 말 것)\n2. 원문의 구조와 형식(제목, 소제목, 단락, 목록, 표 등)을 그대로 유지할 것\n3. 사용자가 별도 출력 형식을 지정한 경우(원문 형식 그대로)에만 해당 형식을 따를 것\n4. 번역 결과는 영어로만 출력할 것\n\n출력 포맷:\n- 각 문서별로 구분하여 아래 형식으로 출력하라:\n  ## [N번 문서 번역]\n  (번역 내용)\n\n--- 번역 대상 본문 ---\n--- [문서 출처: 1번 문서] ---\n제1조(목적) 이 지침은 금융회사가 인공지능(AI) 시스템을 도입·운영함에 있어 발생할 수 있는 위험을 체계적으로 식별·평가·관리하기 위한 기준을 제시함을 목적으로 한다.\n\n제2조(적용범위) 이 지침은 은행, 보험사, 금융투자업자 등 「금융회사의 지배구조에 관한 법률」 제2조에 따른 금융회사에 적용한다."
    },
    {
      "role": "assistant",
      "content": "## [Document 1 Translation]\n\n**Article 1 (Purpose)** The purpose of these guidelines is to provide standards for financial institutions to systematically identify, assess, and manage risks that may arise in the introduction and operation of artificial intelligence (AI) systems.\n\n**Article 2 (Scope of Application)** These guidelines apply to financial companies as defined under Article 2 of the \"Act on Corporate Governance of Financial Companies,\" including banks, insurance companies, and financial investment business entities."
    }
  ]
}
```

### 5-B. translate_text — 사용자 붙여넣기 텍스트 번역

> **입력:** 사용자가 메시지에 직접 붙여넣은 텍스트 (input_text) + language + format_instruction

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 텍스트 붙여넣기 번역 | 없음 | "이거 영어로 번역해줘: (텍스트)" |
| 언어 지정 번역 | 없음 | "아래 내용 일본어로 번역해줘: (텍스트)" |
| 파일 있어도 텍스트 직접 입력 | 있음/없음 | 질문에 본문이 포함된 경우 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 전문 번역가입니다.\n다음 제공된 텍스트를 영어로 번역하세요.\n\n번역 원칙:\n1. 원문의 모든 내용을 빠짐없이 번역할 것 (요약하거나 생략하지 말 것)\n2. 원문의 구조와 형식(단락, 목록, 강조 등)을 그대로 유지할 것\n3. 사용자가 별도 출력 형식을 지정한 경우(원문 형식 그대로)에만 해당 형식을 따를 것\n4. 번역 결과는 영어로만 출력할 것\n\n--- 번역 대상 텍스트 ---\n안녕하십니까. 당사는 AI 기반 보험 상품 개발 분야에서 10년간의 전문성을 보유한 핀테크 기업입니다. 귀사와의 전략적 파트너십 체결을 통해 상호 성장을 도모하고자 제안서를 제출합니다.\n-----------------------"
    },
    {
      "role": "assistant",
      "content": "Good day. Our company is a fintech firm with 10 years of expertise in AI-based insurance product development. We hereby submit this proposal with the aim of fostering mutual growth through the establishment of a strategic partnership with your organization."
    }
  ]
}
```

### 5-C. translate_page — 특정 페이지 번역

> **입력:** file_id + page 필터로 가져온 청크 전체 (full_text) + language + format_instruction

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 단일 페이지 번역 | 있음 | "1번 문서 3페이지 영어로 번역해줘" |
| 복수 페이지 번역 | 있음 | "1번 문서 3, 5페이지 번역해줘" |
| 복수 문서 동일 페이지 | 있음 | "1번, 2번 문서 10페이지 번역해줘" |
| RAG 없음 | ❌ | file_id + page 없으면 불성립 |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 전문 번역가입니다.\n제공된 문서의 특정 페이지 내용을 영어로 번역하세요.\n\n번역 원칙:\n1. 원문의 모든 내용을 빠짐없이 번역할 것 (요약하거나 생략하지 말 것)\n2. 원문의 구조와 형식(제목, 소제목, 단락, 목록, 표 등)을 그대로 유지할 것\n3. 사용자가 별도 출력 형식을 지정한 경우(원문 형식 그대로)에만 해당 형식을 따를 것\n4. 번역 결과는 영어로만 출력할 것\n\n출력 포맷:\n- 문서/페이지 별로 각각 구분하여 아래 형식으로 출력하라:\n  ## [N번 문서 - M페이지 번역]\n  (번역 내용)\n\n--- 번역 대상 본문 (요청 페이지: 3) ---\n--- [문서 ID: 2, 3페이지] ---\n3. 자동차보험 대인사고 현황 분석\n\n2023년 자동차보험 대인사고 건수는 총 124,582건으로 전년 대비 3.2% 감소하였다. 그러나 건당 평균 보험금 지급액은 245만원으로 전년 대비 7.8% 증가하여 손해율 개선에 부정적 영향을 미쳤다. 연령대별로는 65세 이상 고령 운전자의 사고 비율이 18.3%로 전년(16.1%) 대비 2.2%p 증가하였다."
    },
    {
      "role": "assistant",
      "content": "## [Document 2 - Page 3 Translation]\n\n**3. Analysis of Personal Injury Accidents in Auto Insurance**\n\nThe total number of personal injury accidents in auto insurance for 2023 was 124,582 cases, a 3.2% decrease compared to the previous year. However, the average insurance payment per case increased by 7.8% to KRW 2.45 million compared to the previous year, negatively impacting the improvement of the loss ratio. By age group, the proportion of accidents involving elderly drivers aged 65 and over increased by 2.2 percentage points to 18.3%, up from 16.1% in the previous year."
    }
  ]
}
```

### 5-D. translate_history — 이전 AI 답변 번역

> **입력:** chat_history에서 추출한 AI 응답 원문 (input_text) + language + format_instruction
> **주의:** input_text는 원문을 한 글자도 빠짐없이 그대로 전달 (재구성 금지)

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 직전 AI 답변 번역 | 있음/없음 | "방금 답변 영어로 번역해줘" |
| 이전 보고서 번역 | 있음/없음 | "방금 쓴 기획안 영어로 번역해줘" |
| 이전 대화 지칭 | 있음/없음 | "위 내용 일본어로 번역해줘" |

```json
{
  "messages": [
    {
      "role": "user",
      "content": "당신은 전문 번역가입니다.\n다음 제공된 텍스트를 영어로 번역하세요.\n\n번역 원칙:\n1. 원문의 모든 내용을 빠짐없이 번역할 것 (요약하거나 생략하지 말 것)\n2. 원문의 구조와 형식(단락, 목록, 강조 등)을 그대로 유지할 것\n3. 사용자가 별도 출력 형식을 지정한 경우(원문 형식 그대로)에만 해당 형식을 따를 것\n4. 번역 결과는 영어로만 출력할 것\n\n--- 번역 대상 텍스트 ---\nAI 위험관리의 3대 핵심은 다음과 같습니다.\n\n**1. 투명성 (Transparency):** AI 모델의 의사결정 과정을 이해관계자가 이해할 수 있도록 설명 가능성을 확보해야 합니다.\n**2. 책임성 (Accountability):** AI 시스템의 결과에 대한 명확한 책임 소재를 규정하고 거버넌스 체계를 구축해야 합니다.\n**3. 견고성 (Robustness):** 적대적 공격, 분포 이동 등 다양한 환경 변화에도 안정적으로 작동하는 시스템을 구축해야 합니다.\n-----------------------"
    },
    {
      "role": "assistant",
      "content": "The three core principles of AI risk management are as follows.\n\n**1. Transparency:** It is necessary to ensure explainability so that stakeholders can understand the decision-making process of AI models.\n**2. Accountability:** Clear lines of accountability for the outcomes of AI systems must be established, along with a governance framework.\n**3. Robustness:** Systems must be built to operate reliably under various environmental changes, including adversarial attacks and distribution shifts."
    }
  ]
}
```

---

## Case 6 — TRANSLATE + report

> **모델:** `response_model` | **호출 함수:** `generate_report()` (`rag/generator.py`)
> **입력:** question + translate_node 결과가 final_context로 전달됨
> **출력:** 번역 결과 기반 공식 보고서

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 번역 결과를 공식 제안서로 | 있음 | "1번 문서 번역해서 해외 투자자 제출용 공식 보고서로 만들어줘" |
| 이전 번역 기반 보고서 | 있음/없음 | "방금 번역 결과를 보고서로 정리해줘" |
| 텍스트 번역 후 보고서 | 없음 | "*(텍스트)* 영어로 번역해서 공식 보고서 형식으로 출력해줘" |

> **권장 수량:** 전체의 2% 이하. 현실에서 매우 드문 케이스입니다.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 전문적인 기획안·보고서·제안서 작성 어시스턴트야.\n사용자의 요청에 따라 체계적이고 논리적인 문서를 작성해야 해.\n\n[작성 가이드라인]\n1. 제공된 참고 자료(context)가 있으면 이를 근거로 활용하되, 필요 시 사전 지식을 보충하라.\n2. 기획안/보고서의 구조는 사용자의 요청 의도에 맞게 자율적으로 구성하라.\n3. 각 섹션에는 구체적이고 실행 가능한 내용을 포함하라.\n4. 전문적이고 분석적인 톤을 유지하되, 읽기 쉬운 문체로 작성하라.\n5. 대화 기록(chat_history)이 있다면 이전 맥락을 반영하여 일관성을 유지하라."
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 정보를 바탕으로 사용자의 요청에 맞는 기획안/보고서를 작성하십시오.\n\n### [Data]\n- 사용자 요청: 1번 문서 영어로 번역해서 해외 투자자 제출용 공식 보고서 형식으로 만들어줘\n---\n- 참고 자료: ## [Document 1 Translation]\n\n**Article 1 (Purpose)** The purpose of these guidelines is to provide standards for financial institutions to systematically identify, assess, and manage risks that may arise in the introduction and operation of artificial intelligence (AI) systems.\n\n**Article 2 (Scope of Application)** These guidelines apply to financial companies as defined under Article 2 of the \"Act on Corporate Governance of Financial Companies,\" including banks, insurance companies, and financial investment business entities.\n---"
    },
    {
      "role": "assistant",
      "content": "# AI Risk Management Framework Guidelines\n## Official Report for International Investor Submission\n\n**Date:** March 2026\n**Issuing Organization:** [Company Name]\n**Purpose:** Translation and formatting of Korean FSC AI Risk Management Guidelines for international stakeholder communication\n\n---\n\n## Executive Summary\nThis document presents the official English translation of the Korean Financial Services Commission's AI Risk Management Framework Guidelines, prepared for submission to international investors and partners.\n\n## Article 1: Purpose\nThese guidelines establish standards for financial institutions to systematically identify, assess, and manage risks arising from the introduction and operation of artificial intelligence (AI) systems.\n\n## Article 2: Scope of Application\nThese guidelines apply to financial companies — including banks, insurance companies, and financial investment business entities — as defined under Article 2 of the Act on Corporate Governance of Financial Companies.\n\n---\n*This document is an official translation prepared for external distribution.*"
    }
  ]
}
```

---

## Case 7 — DIRECT_ANSWER + answer

> **모델:** `response_model` | **호출 함수:** `generate_direct_answer()` (`rag/generator.py`)
> **입력:** question + chat_history (컨텍스트 없음)
> **출력:** 직접 답변

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 인사/일상 대화 | 없음 | "안녕하세요", "고마워요" |
| 일반 지식 질문 | 없음 | "보험료 산정 방식이 일반적으로 어떻게 돼?" |
| **파일 있어도 문서 미참조** ⚠️ | **있음** | **"AI 모델이 뭐야?", "임베디드 보험 설명해줘"** |
| 멀티턴 후속 — 문서 참조 없음 | 있음/없음 | *(이전 답변 후)* "더 자세히 설명해줘" |
| 멀티턴 후속 — 이전 주제 연장 | 있음/없음 | *(이전 답변 후)* "그럼 단점은 뭐야?" |

> **중요:** 파일이 업로드된 상태에서도 질문에 문서 참조 표현이 없으면 DIRECT_ANSWER가 정답.
> 이 케이스를 충분히 포함해야 `RETRIEVE` 과다 판정을 방지할 수 있습니다.

**예시 A — RAG 없음, 일반 지식**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 이전 대화 맥락과 사전 지식을 두루 활용하는 친근한 AI 어시스턴트야.\n\n[답변 가이드라인]\n- 대화 기록(chat_history)이 있다면 적극 활용하여 맥락에 맞게 답변하라.\n- 사전 지식으로 답변하되, 불확실한 내용이 있다면 그 사실을 명시하라.\n- 이전 답변에서 다룬 내용을 반복하지 말고, 추가적인 설명이나 보충 정보를 제공하라."
    },
    {
      "role": "user",
      "content": "### [Data]\n- 질문: 임베디드 보험이 뭐야?"
    },
    {
      "role": "assistant",
      "content": "임베디드 보험(Embedded Insurance)은 비보험 상품이나 서비스를 구매하는 시점에 보험이 함께 제공되는 형태를 말합니다.\n\n예를 들어 항공권 구매 시 여행자 보험이 자동으로 포함되거나, 스마트폰 구매 시 파손 보험이 함께 제공되는 방식입니다.\n\n**핵심 특징:**\n- **구매 편의성:** 별도 가입 절차 없이 주요 구매 여정에서 자연스럽게 제공\n- **맞춤형 커버리지:** 구매 상품·서비스에 최적화된 보장 설계\n- **플랫폼 협업:** 이커머스, 핀테크, 모빌리티 플랫폼과의 제휴를 통해 확산\n\n전통적 보험 판매 채널 대비 고객 접점이 넓고 가입 마찰이 낮아 최근 보험업계의 성장 동력으로 주목받고 있습니다."
    }
  ]
}
```

**예시 B — RAG 있음, 멀티턴 후속 (문서 참조 없음)**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 이전 대화 맥락과 사전 지식을 두루 활용하는 친근한 AI 어시스턴트야.\n(DIRECT_ANSWER_GENERATION_INSTRUCTIONS 전문)"
    },
    {
      "role": "user",
      "content": "임베디드 보험이 뭐야?"
    },
    {
      "role": "assistant",
      "content": "임베디드 보험은 비보험 상품 구매 시점에 보험이 함께 제공되는 형태입니다..."
    },
    {
      "role": "user",
      "content": "### [Data]\n- 질문: 그럼 임베디드 보험의 단점은 뭐야?"
    },
    {
      "role": "assistant",
      "content": "임베디드 보험의 주요 단점은 다음과 같습니다.\n\n1. **보장 범위 제한:** 주 상품에 최적화되다 보니 개인 상황에 맞는 맞춤 보장이 어렵습니다.\n2. **인지율 저하:** 구매 과정에서 자동 포함되어 가입 사실을 인지하지 못하거나 보장 내용을 확인하지 않는 경우가 많습니다.\n3. **보험료 불투명성:** 전체 상품 가격에 포함되어 실질 보험료를 파악하기 어렵습니다.\n4. **플랫폼 의존성:** 제휴 플랫폼의 정책 변경에 따라 상품 지속성이 불안정할 수 있습니다.\n\n소비자 관점에서는 편리하지만 보장 내용을 꼼꼼히 확인하는 것이 중요합니다."
    }
  ]
}
```

---

## Case 8 — DIRECT_ANSWER + report

> **모델:** `response_model` | **호출 함수:** `generate_report()` (`rag/generator.py`)
> **입력:** question + context="없음" (또는 chat_history가 맥락 역할)
> **출력:** 기획안/보고서 (문서 없이 지식 기반)

| 상황 | RAG 여부 | 예시 질문 |
|---|---|---|
| 순수 지식 기반 기획안 | 없음 | "반려동물 보험 신상품 개발 기획안 작성해줘" |
| 순수 지식 기반 보고서 | 없음 | "AI 보험상품 트렌드 분석 보고서 써줘" |
| **이전 검색 후 보고서** ⚠️ | **있음** | *(검색 완료 후)* **"방금 내용으로 기획안 작성해줘"** |
| 이전 AI 답변 기반 보고서 | 있음/없음 | "방금 설명한 내용으로 보고서 만들어줘" |
| 멀티턴 누적 대화 기반 | 있음/없음 | "지금까지 논의한 내용으로 제안서 써줘" |

> **경계 케이스 구분 핵심:**
> - 현재 질문에서 **새 검색이 필요** → `RETRIEVE + report` (Case 2)
> - 이전 턴에서 이미 검색 완료, **지금은 작성만 필요** → `DIRECT_ANSWER + report` (Case 8)

**예시 A — RAG 없음, 순수 지식 기반 보고서**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 전문적인 기획안·보고서·제안서 작성 어시스턴트야.\n(REPORT_GENERATION_INSTRUCTIONS 전문)"
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 정보를 바탕으로 사용자의 요청에 맞는 기획안/보고서를 작성하십시오.\n\n### [Data]\n- 사용자 요청: 반려동물 보험 신상품 개발 기획안 작성해줘\n---\n- 참고 자료: 없음\n---"
    },
    {
      "role": "assistant",
      "content": "# 반려동물 보험 신상품 개발 기획안\n\n## 1. 시장 현황\n- 국내 반려동물 양육 가구 약 602만 가구(2024년 기준), 전체의 25% 수준\n- 반려동물 관련 시장 규모 약 4조원, 연평균 12% 성장\n- 반려동물 보험 가입률 약 1% — 영국(25%), 스웨덴(40%) 대비 매우 저조\n\n## 2. 기회 요인\n- 고령화·1인 가구 증가로 반려동물 '가족화' 트렌드 심화\n- 동물병원비 급증에 따른 보험 수요 증가\n- 마이데이터 기반 반려동물 건강 데이터 활용 가능성\n\n## 3. 상품 콘셉트\n\n### 3-1. 기본 보장\n- 질병·상해 치료비 (연간 최대 300만원)\n- 입원·수술비 (1회당 최대 150만원)\n- 슬개골 탈구·백내장 등 견종 특이 질환 포함\n\n### 3-2. 선택 특약\n- **헬스케어 특약:** 건강검진비 연 1회 지원\n- **장묘 특약:** 반려동물 사망 시 장례비 지원\n- **배상책임 특약:** 반려동물 기인 제3자 피해 보상\n\n## 4. 차별화 전략\n- 웨어러블 기기(펫 GPS·활동량 측정기) 연동 할인\n- 비대면 수의사 상담 서비스 번들 제공\n- 월 1만원대 소액 단순 상품으로 가입 장벽 최소화\n\n## 5. 추진 일정\n| 단계 | 기간 | 주요 과제 |\n|---|---|---|\n| 사전 기획 | 2026년 2Q | 시장 조사, 손해율 분석 |\n| 상품 개발 | 2026년 3Q | 보장 설계, 보험료 산출 |\n| 심사·출시 | 2026년 4Q | 금감원 심사, 채널 구축 |"
    }
  ]
}
```

**예시 B — RAG 있음, 이전 검색 후 보고서 (멀티턴)**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "너는 전문적인 기획안·보고서·제안서 작성 어시스턴트야.\n(REPORT_GENERATION_INSTRUCTIONS 전문)"
    },
    {
      "role": "user",
      "content": "1번 문서에서 AI 레드팀 핵심 내용 찾아줘"
    },
    {
      "role": "assistant",
      "content": "AI 레드팀의 핵심은 공격자 관점에서 AI 시스템 취약점을 사전 발굴하는 것입니다. 레드팀은 최소 3인으로 구성하며, 분기 1회 이상 정기 점검을 실시합니다. 주요 점검 항목은 모델 편향성, 적대적 공격 취약성, 개인정보 추론 가능성, 탈옥(jailbreak) 저항성입니다."
    },
    {
      "role": "user",
      "content": "### [Instruction]\n아래 정보를 바탕으로 사용자의 요청에 맞는 기획안/보고서를 작성하십시오.\n\n### [Data]\n- 사용자 요청: 방금 내용으로 AI 레드팀 도입 제안서 작성해줘\n---\n- 참고 자료: 없음\n---"
    },
    {
      "role": "assistant",
      "content": "# AI 레드팀 도입 제안서\n\n## 1. 제안 배경\n금융감독원 AI 위험관리 가이드라인에 따라 AI 시스템의 사전 취약점 점검 체계 구축이 권고되고 있습니다. AI 레드팀은 공격자 관점에서 취약점을 선제적으로 발굴하여 AI 시스템 신뢰성을 확보하는 핵심 수단입니다.\n\n## 2. 레드팀 구성 방안\n\n| 구분 | 내용 |\n|---|---|\n| 팀 규모 | 최소 3인 이상 |\n| 구성 원칙 | 내부 인력 + 외부 전문가 혼합 |\n| 필수 역할 | AI 개발자, 보안 전문가, 도메인 전문가 |\n\n## 3. 운영 계획\n\n### 정기 점검\n- **주기:** 분기 1회 이상 (연 4회)\n- **대규모 모델 업데이트 시:** 수시 추가 점검\n\n### 4대 점검 항목\n1. **모델 편향성:** 특정 집단에 대한 차별적 결과 발생 여부\n2. **적대적 공격 취약성:** 입력 조작을 통한 오분류 유도 가능성\n3. **개인정보 추론 가능성:** 모델 출력을 통한 개인정보 역추론 가능성\n4. **탈옥(Jailbreak) 저항성:** 안전장치 우회 시도에 대한 저항 수준\n\n## 4. 기대 효과\n- **규제 대응:** 금감원 AI 위험관리 가이드라인 준수\n- **사고 예방:** 사전 취약점 발굴로 AI 사고 가능성 최소화\n- **신뢰 제고:** AI 시스템 신뢰성 입증을 통한 고객·감독 신뢰 확보"
    }
  ]
}
```
