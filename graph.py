"""
graph.py - LangGraph 그래프 빌더 및 컴파일
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import GraphState
from node import (
    analyze_user_intent_node,
    decide_retriever_tool_node,
    decide_summary_tool_node,
    retrieve_node,
    summarize_node,
    grade_documents_node,
    rewrite_question_node,
    retry_retrieve_node,
    route_to_generation_node,
    generate_answer_node,
    generate_report_node,
)
from edge import route_tools, route_after_grading, route_to_generation


def build_graph(use_memory: bool = True) -> StateGraph:
    """
    LangGraph 워크플로우 그래프 생성
    
    Args:
        use_memory: 메모리 체크포인터 사용 여부
    
    Returns:
        컴파일된 그래프
    """
    # 그래프 구성 시작
    workflow = StateGraph(GraphState)

    # ============================================
    # 노드 정의
    # ============================================
    workflow.add_node("analyze_user_intent_node", analyze_user_intent_node)
    workflow.add_node("decide_retriever_tool_node", decide_retriever_tool_node)
    workflow.add_node("decide_summary_tool_node", decide_summary_tool_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("summarize_node", summarize_node)
    workflow.add_node("grade_documents_node", grade_documents_node)
    workflow.add_node("rewrite_question_node", rewrite_question_node)
    workflow.add_node("retry_retrieve_node", retry_retrieve_node)
    workflow.add_node("route_to_generation_node", route_to_generation_node)
    workflow.add_node("generate_answer_node", generate_answer_node)
    workflow.add_node("generate_report_node", generate_report_node)

    # ============================================
    # 엣지 연결 (흐름 정의)
    # ============================================

    # (1) 시작 지점
    workflow.add_edge(START, "analyze_user_intent_node")

    # (2) 고수준 의도 분석 후 라우팅 (텍스트 태그 기반)
    workflow.add_conditional_edges(
        "analyze_user_intent_node",
        route_tools,
        {
            "retrieve_decision": "decide_retriever_tool_node",
            "summarize_decision": "decide_summary_tool_node",
            "generate": "route_to_generation_node",
        },
    )

    # (3) 도구 결정 노드 → 실행 노드
    # (3)-1. 검색 도구 결정 → 검색 실행
    workflow.add_edge("decide_retriever_tool_node", "retrieve_node")

    # (3)-2. 요약 도구 결정 → 요약 실행
    workflow.add_edge("decide_summary_tool_node", "summarize_node")

    # (4) 실행 후 후속 처리
    # (4)-1. 요약 후 생성 라우팅으로 이동
    workflow.add_edge("summarize_node", "route_to_generation_node")

    # (4)-2. 검색 후 평가 노드로 이동
    workflow.add_edge("retrieve_node", "grade_documents_node")

    # (5) 평가 결과에 따라 라우팅 (관련도 판단)
    workflow.add_conditional_edges(
        "grade_documents_node",
        route_after_grading,
        {
            "generate": "route_to_generation_node",
            "rewrite_question": "rewrite_question_node",
        },
    )

    # (6) 질문 재작성 후 재검색 노드
    workflow.add_edge("rewrite_question_node", "retry_retrieve_node")

    # (7) 재검색 관제 이후 검색 툴 실행 노드로 이동
    workflow.add_edge("retry_retrieve_node", "retrieve_node")

    # (8) 생성 라우팅: intent_type에 따라 답변/기획안 분기
    workflow.add_conditional_edges(
        "route_to_generation_node",
        route_to_generation,
        {
            "answer": "generate_answer_node",
            "report": "generate_report_node",
        },
    )

    # (9) 최종 생성 후 종료
    workflow.add_edge("generate_answer_node", END)
    workflow.add_edge("generate_report_node", END)

    # ============================================
    # 그래프 컴파일
    # ============================================
    if use_memory:
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)
    else:
        graph = workflow.compile()

    return graph


def visualize_graph(graph, output_path: str = None):
    """
    그래프 시각화
    
    Args:
        graph: 컴파일된 그래프
        output_path: 이미지 저장 경로 (None이면 화면에 표시)
    """
    try:
        from IPython.display import display, Image
        
        png_data = graph.get_graph().draw_mermaid_png()
        
        if output_path:
            with open(output_path, "wb") as f:
                f.write(png_data)
            print(f"그래프 이미지가 저장되었습니다: {output_path}")
        else:
            display(Image(png_data))
    except ImportError:
        print("그래프 시각화를 위해 IPython이 필요합니다.")
    except Exception as e:
        print(f"그래프 시각화 중 오류 발생: {e}")


# 기본 그래프 인스턴스
graph = build_graph(use_memory=True)
