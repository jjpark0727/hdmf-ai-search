"""
utils.py - 유틸리티 함수
"""

from typing import List
from langchain_core.messages import ToolMessage, HumanMessage

# 원본
def get_combined_context(messages: List) -> str:
    """
    메시지 히스토리에서 Tool 결과를 결합하여 컨텍스트 생성
    
    가장 최근의 HumanMessage를 만나기 전까지 역순으로 ToolMessage 수집
    
    Args:
        messages: 메시지 리스트 (internal_history)
    
    Returns:
        결합된 컨텍스트 문자열
    """
    context_blocks = []
    seen_tool_ids = set()  # 중복 체크용

    # 뒤에서부터 전체 히스토리를 훑음
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            # 중복 제거
            if msg.tool_call_id not in seen_tool_ids:
                seen_tool_ids.add(msg.tool_call_id)
                context_blocks.append(f"## 출처: {msg.name}\n{msg.content}")

        # 가장 최근 질문 (원본 혹은 재작성된 질문) 만나면 멈춤
        if isinstance(msg, HumanMessage):
            break

    return "\n\n".join(reversed(context_blocks))


# ============================================
# 보조 함수: optional
# ============================================

# 국가별 결과 추출 
def extract_tool_results_by_country(
    messages: List,
    country: str
) -> str:
    """
    특정 국가의 Tool 결과만 추출
    
    Args:
        messages: 메시지 리스트
        country: 국가 코드 ("japan" 또는 "usa")
    
    Returns:
        해당 국가의 Tool 결과 문자열
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, ToolMessage) and country in msg.name:
            return msg.content
    
    return ""

# 최신 툴 결과 
def get_latest_tool_result(messages: List, tool_name_contains: str) -> str:
    """
    특정 이름을 포함하는 가장 최근 Tool 결과 반환
    
    Args:
        messages: 메시지 리스트
        tool_name_contains: Tool 이름에 포함된 문자열
    
    Returns:
        Tool 결과 문자열 (없으면 빈 문자열)
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, ToolMessage) and tool_name_contains in msg.name:
            return msg.content
    
    return ""

# 디버깅용
def format_chat_history_for_display(messages: List, max_messages: int = 10) -> str:
    """
    대화 기록을 읽기 쉬운 형식으로 포맷팅
    
    Args:
        messages: 메시지 리스트
        max_messages: 최대 표시할 메시지 수
    
    Returns:
        포맷팅된 대화 기록 문자열
    """
    formatted = []
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    for msg in recent_messages:
        role = type(msg).__name__.replace("Message", "")
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        formatted.append(f"[{role}]: {content}")
    
    return "\n".join(formatted)


def count_tokens_estimate(text: str) -> int:
    """
    텍스트의 토큰 수 추정 (대략적)
    
    한글: 약 2-3자당 1토큰
    영어: 약 4자당 1토큰
    
    Args:
        text: 텍스트
    
    Returns:
        추정 토큰 수
    """
    # 간단한 추정: 평균적으로 3자당 1토큰
    return len(text) // 3

# 컨텍스트 길이제한 
def truncate_context(context: str, max_tokens: int = 4000) -> str:
    """
    컨텍스트를 최대 토큰 수에 맞게 자르기
    
    Args:
        context: 원본 컨텍스트
        max_tokens: 최대 토큰 수
    
    Returns:
        잘린 컨텍스트
    """
    estimated_tokens = count_tokens_estimate(context)
    
    if estimated_tokens <= max_tokens:
        return context
    
    # 비율에 맞게 자르기
    ratio = max_tokens / estimated_tokens
    max_chars = int(len(context) * ratio)
    
    truncated = context[:max_chars]
    
    # 문장 단위로 자르기 (가능한 경우)
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.8:  # 80% 이상 유지되면 문장 단위로 자름
        truncated = truncated[:last_period + 1]
    
    return truncated + "\n\n[... 이하 생략 ...]"
