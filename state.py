"""
state.py - GraphState 정의
"""

from typing import TypedDict, List, Annotated, Dict
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """LangGraph 상태 정의"""
    
    # 사용자와의 순수 대화 리스트 (Human, AI 답변만 저장)
    chat_history: Annotated[list, add_messages]

    # 시스템 내부 작업용 메시지 리스트 (Tool calls, tool messages 등)
    # 도구호출, 결과, 재작성 질문
    internal_history: Annotated[list, add_messages]

    # grade document 노드로 검증된 양질의 문서
    final_context: str

    # 재검색이 필요한 메타데이터 필터 리스트 (예: [{"file_id": "1"}])
    needed_search: List[dict]

    # 재시도 횟수 추적 (단일 카운터, 최대 1회 재시도)
    retry_count: int

    # 업로드된 파일 메타데이터
    uploaded_files: List[dict]  # 예: [{"file_id": "1", "file_name": "report.pdf"}, ...]

    # 사용자의 원본 질문
    original_query: str

    # 요약 노드 경유 여부
    from_summarize: bool
