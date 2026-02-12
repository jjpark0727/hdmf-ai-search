"""
graph.py - LangGraph 그래프 빌더 및 컴파일
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import GraphState
from node import (
    analyze_user_intent_node,
    retrieve_node,
    summarize_node,
    grade_documents_node,
    rewrite_question_node,
    retry_retrieve_node,
    generate_answer_node,
)
from edge import route_tools, route_after_grading


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
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("summarize_node", summarize_node)
    workflow.add_node("grade_documents_node", grade_documents_node)
    workflow.add_node("rewrite_question_node", rewrite_question_node)
    workflow.add_node("retry_retrieve_node", retry_retrieve_node)
    workflow.add_node("generate_answer_node", generate_answer_node)

    # ============================================
    # 엣지 연결 (흐름 정의)
    # ============================================

    # (1) 시작 지점
    workflow.add_edge(START, "analyze_user_intent_node")

    # (2) 초기 의도 분석 후 라우팅
    workflow.add_conditional_edges(
        "analyze_user_intent_node",
        route_tools,
        {
            "retrieve": "retrieve_node",
            "summarize": "summarize_node",
            "generate_answer": "generate_answer_node"
        },
    )

    # (3) 의도에 따른 분기
    # (3)-1. 요약 후에도 답변 생성 노드로 이동
    workflow.add_edge("summarize_node", "generate_answer_node")

    # (3)-2. 검색 후 평가 노드로 이동
    workflow.add_edge("retrieve_node", "grade_documents_node")

    # (4) 평가 결과에 따라 라우팅
    workflow.add_conditional_edges(
        "grade_documents_node",
        route_after_grading,
        {
            "generate_answer": "generate_answer_node",
            "rewrite_question": "rewrite_question_node",
        },
    )

    # (5) 질문 재작성 후 재검색 노드
    workflow.add_edge("rewrite_question_node", "retry_retrieve_node")

    # (6) 재검색 관제 이후 검색 툴 실행 노드로 이동
    workflow.add_edge("retry_retrieve_node", "retrieve_node")

    # (7) 최종 답변 생성 후 종료
    workflow.add_edge("generate_answer_node", END)

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
