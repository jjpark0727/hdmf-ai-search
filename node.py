"""
node.py - 모든 노드 정의

각 노드는 상태 관리만 담당하고, 실제 로직은 RAG 모듈에 위임
"""

from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

from state import GraphState
from model import decision_model, grader_model, rewrite_model, response_model
from prompt import (
    DECISION_INSTRUCTIONS,
    DECISION_TEMPLATE,
    RETRY_INSTRUCTIONS,
    RETRY_TEMPLATE,
)
from tool import (
    all_tools,
    retrieve_node_tools,
    summarize_node_tools,
)
from utils import get_combined_context
from rag.grader import DocumentGrader
from rag.query_transform import QueryTransformer
from rag.generator import RAGGenerator


# ============================================
# RAG 모듈 인스턴스 생성
# ============================================
document_grader = DocumentGrader(llm=grader_model)
query_transformer = QueryTransformer(llm=rewrite_model)
rag_generator = RAGGenerator(llm=response_model)


# ============================================
# 노드 1: 사용자 의도 분석
# ============================================
def analyze_user_intent(state: GraphState):
    """
    사용자 질문의 의도를 분석하여 도구 호출 또는 직접 응답 결정
    
    Returns:
        업데이트된 상태 (internal_history, original_query, retry_counts 등)
    """
    # 항상 매 대화턴마다 호출되고 초기화됨
    initial_retry_counts = {"usa": 0, "japan": 0}

    # 순수 대화 기록
    chat_history = state.get("chat_history", [])

    # 이번 턴의 진짜 원본 질문 (가장 최신 HumanMessage)
    current_real_question = chat_history[-1].content

    # 지시사항에 현재 세션의 실제 파일 정보 주입
    current_files = state.get("uploaded_files", [])
    DYNAMIC_INSTRUCTION = DECISION_INSTRUCTIONS + f"\n\n### 현재 세션 업로드 파일 목록: {current_files}"

    sys_msg = SystemMessage(content=DYNAMIC_INSTRUCTION)
    human_msg = HumanMessage(content=DECISION_TEMPLATE.format(question=current_real_question))

    # 최종 메시지 = [지시사항] + 대화 맥락 + [원본 질문]
    messages = [sys_msg] + chat_history[:-1] + [human_msg]

    # 모델 호출
    response = (
        decision_model
        .bind_tools(all_tools)
        .invoke(messages)
    )

    # 만약 아무 응답도 없는 경우
    if not response.tool_calls and not response.content:
        response.content = "[DIRECT_ANSWER]"

    return {
        "internal_history": [response],
        "original_query": current_real_question,
        "retry_counts": initial_retry_counts,
        "final_context": "",
        "needed_search": [],
        "from_summarize": False
    }


# ============================================
# 노드 2: 검색 노드 (Tool Node 래퍼)
# ============================================
standard_tool_node = ToolNode(retrieve_node_tools)


def retrieve_node(state: GraphState):
    """
    검색 도구 실행 노드
    
    ToolNode가 internal_history의 tool_calls를 실행
    """
    result = standard_tool_node.invoke({
        "messages": state["internal_history"]
    })

    return {"internal_history": result["messages"]}


# ============================================
# 노드 3: 요약 노드 (Tool Node 래퍼)
# ============================================
standard_summarize_tool_node = ToolNode(summarize_node_tools)


def summarize_node(state: GraphState):
    """
    요약 도구 실행 노드
    
    요약 결과를 chat_history에도 추가하여 대화 맥락 유지
    """
    result = standard_summarize_tool_node.invoke({
        "messages": state["internal_history"]
    })

    # 도구 결과(요약문) 추출
    summary_text = result["messages"][-1].content

    return {
        "internal_history": result["messages"],
        "chat_history": [AIMessage(content=summary_text)],
        "from_summarize": True
    }


# ============================================
# 노드 4: 문서 관련도 평가 (상태 관리만)
# ============================================
def grade_documents_node(state: GraphState):
    """
    검색된 문서의 관련성 평가 노드
    
    실제 평가 로직은 DocumentGrader에 위임하고,
    이 노드는 상태 업데이트만 담당
    """
    internal_history = state.get("internal_history", [])
    
    # 모든 도구 결과 호출해서 합침
    current_full_context = get_combined_context(internal_history)
    
    # 원본 질문
    original_question = state["original_query"]
    
    # DocumentGrader에 평가 위임
    grade_result = document_grader.grade(
        question=original_question,
        context=current_full_context
    )
    
    # 결과 채점
    needed = []
    validated_blocks = []
    
    # 기존 retry_count 가져오기 (없으면 초기화)
    retry_counts = state.get("retry_counts", {"usa": 0, "japan": 0})
    
    # USA 평가
    if grade_result.usa == "no":
        needed.append("usa")
        retry_counts["usa"] += 1
    else:
        # 성공시 해당 툴의 내용만 추출해서 보관
        for msg in reversed(internal_history):
            if isinstance(msg, HumanMessage):
                break
            if isinstance(msg, ToolMessage) and "usa" in msg.name:
                validated_blocks.append(msg.content)
                break
    
    # JAPAN 평가
    if grade_result.japan == "no":
        needed.append("japan")
        retry_counts["japan"] += 1
    else:
        # 성공시 해당 툴의 내용만 추출해서 보관
        for msg in reversed(internal_history):
            if isinstance(msg, HumanMessage):
                break
            if isinstance(msg, ToolMessage) and "japan" in msg.name:
                validated_blocks.append(msg.content)
                break
    
    new_final_context = state.get("final_context", "") + "\n\n" + "\n\n".join(validated_blocks)
    
    # 어떤 국가라도 2번 이상 실패할 경우 로그
    for country in needed:
        if retry_counts.get(country, 0) >= 2:
            num = retry_counts.get(country, 0)
            print(f"---[LOG] {country} 정보 검색 {num}회 실패. 답변 생성으로 이동합니다")
    
    return {
        "needed_search": needed,
        "final_context": new_final_context.strip(),
        "retry_counts": retry_counts
    }


# ============================================
# 노드 5: 쿼리 재작성 (상태 관리만)
# ============================================
def rewrite_question_node(state: GraphState):
    """
    부족한 국가 정보를 위한 쿼리 재작성 노드
    
    실제 재작성 로직은 QueryTransformer에 위임하고,
    이 노드는 상태 업데이트만 담당
    """
    # 원본 질문
    original_question = state["original_query"]
    
    # 재검색이 필요한 국가 리스트
    needed_countries = state["needed_search"]
    
    # QueryTransformer에 재작성 위임
    rewritten_query = query_transformer.rewrite_for_missing_info(
        question=original_question,
        target_countries=needed_countries
    )
    
    # 새로운 HumanMessage (재작성된 질문) 반환
    return {"internal_history": [HumanMessage(content=rewritten_query)]}


# ============================================
# 노드 6: 재검색 의도 파악
# ============================================
def retry_retrieve_node(state: GraphState):
    """
    재작성된 질문으로 재검색 도구 호출 생성
    """
    internal_history = state.get("internal_history", [])
    
    # 재작성된 질문
    rewritten_question = internal_history[-1].content
    
    # 재검색이 필요한 리스트
    needed = state.get("needed_search", [])
    
    # 재검색 지시사항
    sys_msg = SystemMessage(content=RETRY_INSTRUCTIONS)
    
    # 히스토리 (재작성 질문 제외)
    history = internal_history[:-1]
    
    # 재검색 타겟
    human_msg = HumanMessage(content=RETRY_TEMPLATE.format(
        needed=needed,
        question=rewritten_question
    ))
    
    # 최종 메시지 = [지시사항] + [대화맥락] + [needed 정보 + 재작성 질문]
    messages = [sys_msg] + history + [human_msg]
    
    # 모델 호출
    response = (
        decision_model
        .bind_tools(retrieve_node_tools)
        .invoke(messages)
    )
    
    return {"internal_history": [response]}


# ============================================
# 노드 7: 답변 생성 (상태 관리만)
# ============================================
def generate_answer_node(state: GraphState):
    """
    최종 답변 생성 노드
    
    실제 생성 로직은 RAGGenerator에 위임하고,
    이 노드는 상태 업데이트만 담당
    """
    chat_history = state.get("chat_history", [])
    
    # 요약 노드에서 온 경우, 바로 종료
    # summarize_node에서 이미 chat_history에 요약 결과를 추가했으므로
    # 여기서는 from_summarize 플래그만 리셋 (chat_history는 유지)
    if state.get("from_summarize", False):
        return {"from_summarize": False}
    
    # 질문과 컨텍스트 가져오기
    question = state["original_query"]
    context = state.get("final_context", "")
    needed = state.get("needed_search", [])
    retry_counts = state.get("retry_counts", {})
    
    # 정보가 부족한 국가 리스트 (2회 이상 실패한 국가)
    missing_countries = [
        country for country in needed
        if retry_counts.get(country, 0) >= 2
    ]
    
    # RAGGenerator에 답변 생성 위임
    response = rag_generator.generate_with_mode(
        question=question,
        context=context if context else None,
        chat_history=chat_history,
        missing_countries=missing_countries if missing_countries else None
    )
    
    return {"chat_history": [response]}
