"""
edge.py - 모든 엣지 및 조건부 엣지 정의

그래프의 흐름을 제어하는 라우팅 함수들
"""

from state import GraphState
from config import MAX_RETRY_COUNT


# ============================================
# 조건부 엣지 1: 툴 라우팅
# ============================================
def route_tools(state: GraphState) -> str:
    """
    사용자 의도 분석 결과의 텍스트 태그에 따라 다음 노드 결정

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름 ("retrieve_decision", "summarize_decision", "generate")
    """
    last_message = state["internal_history"][-1]
    content = last_message.content if hasattr(last_message, "content") else ""
    print(f"\n🟡[Edge: route_tools]")
    print(f"[DEBUG] route_tools: content = {content}")

    if "[RETRIEVE]" in content:
        print(f"[DEBUG] route_tools: [RETRIEVE] → retrieve_decision")
        return "retrieve_decision"

    if "[SUMMARIZE]" in content:
        print(f"[DEBUG] route_tools: [SUMMARIZE] → summarize_decision")
        return "summarize_decision"

    # [DIRECT_ANSWER] 또는 기타
    print(f"[DEBUG] route_tools: [DIRECT_ANSWER] → generate")
    return "generate"


# ============================================
# 조건부 엣지 2: 평가 결과 기반 라우팅
# ============================================
def route_after_grading(state: GraphState) -> str:
    """
    문서 평가 결과에 따라 다음 노드 결정

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름 ("generate", "rewrite_question")
    """
    needed = state.get("needed_search", [])
    retry_count = state.get("retry_count", 0)

    # 부족한 정보가 없으면 생성 라우팅으로
    if not needed:
        return "generate"

    # 재시도 횟수가 MAX_RETRY_COUNT 이상이면 생성 라우팅으로
    if retry_count >= MAX_RETRY_COUNT:
        return "generate"

    # 아직 재시도 가능하면 질문 재작성
    return "rewrite_question"


# ============================================
# 조건부 엣지 3: 생성 라우팅 (답변 vs 기획안)
# ============================================
def route_to_generation(state: GraphState) -> str:
    """
    intent_type에 따라 답변 생성 또는 기획안 생성 노드 결정

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름 ("answer", "report")
    """
    intent_type = state.get("intent_type", "answer")
    print(f"\n🟡[Edge: route_to_generation]")
    print(f"[DEBUG] route_to_generation: intent_type = {intent_type}")

    if intent_type == "report":
        return "report"

    return "answer"


# ============================================
# 보조 함수: 도구 호출 여부 확인
# ============================================
def has_tool_calls(state: GraphState) -> bool:
    """
    현재 상태에 도구 호출이 있는지 확인

    Args:
        state: 현재 그래프 상태

    Returns:
        도구 호출 여부
    """
    if "internal_history" not in state or not state["internal_history"]:
        return False

    last_message = state["internal_history"][-1]
    return hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)


def get_tool_type(state: GraphState) -> str:
    """
    호출된 도구의 타입 반환

    Args:
        state: 현재 그래프 상태

    Returns:
        도구 타입 ("retrieve", "summarize", "none")
    """
    if not has_tool_calls(state):
        return "none"

    last_message = state["internal_history"][-1]
    tool_name = last_message.tool_calls[0]["name"]

    if "summarize" in tool_name:
        return "summarize"
    if "search_doc" in tool_name:
        return "retrieve"

    return "none"


def should_continue_search(state: GraphState) -> bool:
    """
    검색을 계속해야 하는지 확인

    Args:
        state: 현재 그래프 상태

    Returns:
        계속 검색 여부
    """
    needed = state.get("needed_search", [])
    retry_count = state.get("retry_count", 0)

    if not needed:
        return False

    return retry_count < MAX_RETRY_COUNT
