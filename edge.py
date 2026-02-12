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
    사용자 의도 분석 결과에 따라 다음 노드 결정

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름 ("retrieve", "summarize", "generate_answer")
    """
    last_message = state["internal_history"][-1]
    print(f"[DEBUG] route_tools: last_message type = {type(last_message)}")
    print(f"[DEBUG] route_tools: hasattr tool_calls = {hasattr(last_message, 'tool_calls')}")
    if hasattr(last_message, "tool_calls"):
        print(f"[DEBUG] route_tools: last_message.tool_calls = {last_message.tool_calls}")

    # 도구 호출이 있는 경우
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        print(f"[DEBUG] route_tools: tool_name = {tool_name}")

        # 요약 도구인 경우
        if "summarize" in tool_name:
            print(f"[DEBUG] route_tools: 요약 도구 → summarize")
            return "summarize"

        # 검색 도구인 경우
        print(f"[DEBUG] route_tools: 검색 도구 → retrieve")
        return "retrieve"

    # 도구 호출이 없으면 직접 답변
    print("[DEBUG] route_tools: tool_calls 없음 → generate_answer")
    return "generate_answer"


# ============================================
# 조건부 엣지 2: 평가 결과 기반 라우팅
# ============================================
def route_after_grading(state: GraphState) -> str:
    """
    문서 평가 결과에 따라 다음 노드 결정

    Args:
        state: 현재 그래프 상태

    Returns:
        다음 노드 이름 ("generate_answer", "rewrite_question")
    """
    needed = state.get("needed_search", [])
    retry_count = state.get("retry_count", 0)

    # 부족한 정보가 없으면 답변 생성
    if not needed:
        return "generate_answer"

    # 재시도 횟수가 MAX_RETRY_COUNT 이상이면 답변 생성
    if retry_count >= MAX_RETRY_COUNT:
        return "generate_answer"

    # 아직 재시도 가능하면 질문 재작성
    return "rewrite_question"


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
