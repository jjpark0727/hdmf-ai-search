"""
main.py - 메인 실행 함수

그래프 실행 및 테스트를 위한 진입점
"""

from pprint import pprint
from langchain_core.runnables import RunnableConfig

from graph import graph, build_graph, visualize_graph
from config import ensure_directories


def run_chat(
    question: str,
    thread_id: str = "1",
    uploaded_files: list = None,
    recursion_limit: int = 10,
    verbose: bool = True
):
    """
    단일 질문 실행
    
    Args:
        question: 사용자 질문
        thread_id: 대화 스레드 ID
        uploaded_files: 업로드된 파일 ID 리스트
        recursion_limit: 최대 노드 방문 수
        verbose: 상세 출력 여부
    
    Returns:
        최종 응답 메시지
    """
    config = RunnableConfig(
        recursion_limit=recursion_limit,
        configurable={"thread_id": thread_id},
    )
    
    input_data = {
        "chat_history": [
            {
                "role": "user",
                "content": question
            }
        ]
    }
    
    if uploaded_files:
        input_data["uploaded_files"] = uploaded_files
    
    final_response = None
    
    for chunk in graph.stream(input_data, config=config):
        for node, update in chunk.items():
            if verbose:
                print(f"\n[Node: {node}]")
            
            if "messages" in update:
                for msg in update["messages"]:
                    # 도구 호출이 있으면 출력
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        if verbose:
                            print(f"🛠️ 도구 호출: {msg.tool_calls}")
                    
                    # 텍스트 답변이 있으면 출력
                    if node == "generate_answer_node":
                        if verbose:
                            print(f"💬 내용: {msg.content}")
                        final_response = msg.content
                    elif verbose and msg.content:
                        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                        print(f"💬 내용: {content_preview}")
            
            if "chat_history" in update and update["chat_history"]:
                last_msg = update["chat_history"][-1]
                if hasattr(last_msg, "content"):
                    final_response = last_msg.content
                    if verbose and node == "generate_answer_node":
                        print(f"💬 내용: {last_msg.content}")
            
            if verbose and "needed_search" in update:
                print(f"🔍 부족한 정보: {update['needed_search']}")
    
    return final_response


def run_interactive():
    """대화형 모드 실행"""
    print("=" * 50)
    print("LangGraph Agentic RAG 시스템")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요")
    print("=" * 50)
    
    thread_id = "interactive_1"
    uploaded_files = ["1", "2"]  # 기본 파일 설정
    
    while True:
        try:
            question = input("\n👤 질문: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ["quit", "exit", "q"]:
                print("프로그램을 종료합니다.")
                break
            
            if question.lower() == "clear":
                thread_id = f"interactive_{hash(question)}"
                print("대화 기록이 초기화되었습니다.")
                continue
            
            print("\n" + "-" * 40)
            response = run_chat(
                question=question,
                thread_id=thread_id,
                uploaded_files=uploaded_files,
                verbose=True
            )
            print("-" * 40)
            
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"오류 발생: {e}")


def get_state_snapshot(thread_id: str = "1", recursion_limit: int = 10):
    """
    현재 상태 스냅샷 조회
    
    Args:
        thread_id: 대화 스레드 ID
        recursion_limit: 재귀 제한
    
    Returns:
        상태 스냅샷
    """
    config = RunnableConfig(
        recursion_limit=recursion_limit,
        configurable={"thread_id": thread_id},
    )
    
    snapshot = graph.get_state(config)
    return snapshot


def print_state(thread_id: str = "1"):
    """상태 정보 출력"""
    snapshot = get_state_snapshot(thread_id)
    
    print("=" * 50)
    print("현재 상태 정보")
    print("=" * 50)
    print(f"Config: {snapshot.config}")
    print("-" * 30)
    print("Values:")
    pprint(snapshot.values)
    print("-" * 30)
    print(f"Next: {snapshot.next}")


# ============================================
# 테스트 함수들
# ============================================

def test_search_query():
    """검색 쿼리 테스트"""
    print("\n" + "=" * 50)
    print("테스트: 검색 쿼리")
    print("=" * 50)
    
    response = run_chat(
        question="미국과 일본의 6G 기술 개발 전략을 비교해줘",
        thread_id="test_search",
        uploaded_files=["1", "2"],
        verbose=True
    )
    
    return response


def test_summary_query():
    """요약 쿼리 테스트"""
    print("\n" + "=" * 50)
    print("테스트: 요약 쿼리")
    print("=" * 50)
    
    response = run_chat(
        question="1번 문서의 핵심 내용을 요약해줘",
        thread_id="test_summary",
        uploaded_files=["1", "2"],
        verbose=True
    )
    
    return response


def test_direct_answer():
    """직접 답변 테스트"""
    print("\n" + "=" * 50)
    print("테스트: 직접 답변")
    print("=" * 50)
    
    response = run_chat(
        question="안녕하세요!",
        thread_id="test_direct",
        uploaded_files=["1", "2"],
        verbose=True
    )
    
    return response


# ============================================
# 메인 실행
# ============================================

if __name__ == "__main__":
    import sys
    
    # 디렉토리 확인
    ensure_directories()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "interactive":
            run_interactive()
        elif command == "test":
            test_search_query()
            test_summary_query()
            test_direct_answer()
        elif command == "visualize":
            output_path = sys.argv[2] if len(sys.argv) > 2 else "graph.png"
            visualize_graph(graph, output_path)
        else:
            # 직접 질문 실행
            question = " ".join(sys.argv[1:])
            response = run_chat(question, verbose=True)
    else:
        # 기본: 대화형 모드
        run_interactive()
