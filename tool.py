"""
tool.py - 모든 도구(Tool) 정의

검색 도구 및 요약 도구 정의
"""

from typing import Optional
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from model import summary_model
from rag.retriever import RetrieverFactory
from rag.vectorstore import get_vector_store
from prompt import SUMMARY_DOC_PROMPT, SUMMARY_TEXT_PROMPT, SUMMARY_PAGE_PROMPT, SUMMARY_HISTORY_PROMPT


# ============================================
# 검색 도구 (Retrieval Tools)
# ============================================

# Retriever 팩토리 인스턴스
retriever_factory = RetrieverFactory()


@tool("search_doc_tool")
def search_doc(query: str, filter_metadata: Optional[dict] = None) -> str:
    """
    업로드된 문서에서 정보를 검색합니다.
    질문에서 특정 문서를 지정한 경우 'filter_metadata'에 해당 메타데이터 필터를 전달하세요.
    반드시 '현재 세션 업로드 파일 메타데이터'에 존재하는 key/value만 사용하세요.

    Args:
        query: 검색 쿼리
        filter_metadata: 메타데이터 필터 (예: {"file_id": "1"}, {"file_name": "보고서.pdf"})
                         None이면 전체 문서 대상 검색

    Returns:
        검색된 문서 내용
    """
    retriever = retriever_factory.get_similarity_retriever(filter=filter_metadata)
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])


# ============================================
# 요약 도구 (Summarization Tools)
# ============================================

@tool("summarize_doc_tool")
def summarize_doc(file_ids: list[str],
                  format_instruction: str = "간결하게 5줄의 불렛포인트") -> str:
    """
    업로드된 특정 문서(들)의 전체 내용을 요약하거나 핵심 정보를 추출할 때 사용합니다.
    유저의 질문에서 요약할 문서의 ID를 추출하여, 'file_ids (List[str])'으로 전달하세요.
    사용자가 출력 양식을 지정한 경우 'format_instruction' 인자로 전달하세요.
    반드시 '제공된 문서'의 내용에 기반하여 요약을 수행해야 할 때만 이 도구를 호출하세요.
    """
    vector_store = get_vector_store()
    all_docs_content = []

    for fid in file_ids:
        # MMR 검색: 문서 전체를 골고루 대변하는 다양한 정보 추출
        docs = vector_store.max_marginal_relevance_search(
            query="이 문서의 핵심 주제",
            k=15,
            fetch_k=40,
            filter={"file_id": fid}
        )

        content = "\n".join([doc.page_content for doc in docs])
        if content:
            all_docs_content.append(f"--- [문서 출처: {fid}번 문서] ---\n{content}")

    full_text = "\n\n".join(all_docs_content)

    if not full_text:
        return "요약할 수 있는 문서 내용을 찾지 못했습니다. 파일 ID를 확인해주세요."

    # 요약 프롬프트 구성
    summary_prompt = SUMMARY_DOC_PROMPT.format(full_text=full_text, format_instruction=format_instruction)

    # 요약 모델 호출
    response = summary_model.invoke([HumanMessage(content=summary_prompt)])

    return response.content


@tool("summarize_text_tool", description="사용자가 직접 입력한 텍스트 본문을 요약합니다.")
def summarize_text(input_text: str,
                   format_instruction: str = "간결하게 3줄의 불렛포인트") -> str:
    """
    사용자가 직접 입력하거나 복사하여 붙여넣은 텍스트 본문을 요약합니다.
    유저의 질문에서 요약 대상이 되는 본문 내용을 추출하여 'input_text' 인자로 전달하세요.
    사용자가 출력 양식을 지정한 경우 'format_instruction' 인자로 전달하세요.
    """
    # 요약 프롬프트 구성
    summary_prompt = SUMMARY_TEXT_PROMPT.format(input_text=input_text, format_instruction=format_instruction)

    # 요약 모델 호출
    response = summary_model.invoke([HumanMessage(content=summary_prompt)])

    return response.content


@tool("summarize_history_tool", description="이전 대화 내용을 요약합니다. 사용자의 요청에 따라 직전 답변 하나 또는 여러 답변을 합쳐서 요약할 수 있습니다.")
def summarize_history(input_text: str, format_instruction: str = "간결하게 3줄의 불렛포인트") -> str:
    """
    이전 대화 내용을 요약합니다.
    사용자의 요청 의도에 따라, 단일 또는 복수의 AI 답변을 추출하여 'input_text' 인자로 전달하세요.
    사용자가 출력 양식을 지정한 경우 'format_instruction' 인자로 전달하세요.
    """
    # 요약 프롬프트 구성
    summary_prompt = SUMMARY_HISTORY_PROMPT.format(input_text=input_text, format_instruction=format_instruction)

    # 요약 모델 호출
    response = summary_model.invoke([HumanMessage(content=summary_prompt)])

    return response.content


@tool("summarize_page_tool")
def summarize_page(file_ids: list[str], pages: list[int], format_instruction: str = "간결하게 3~5줄의 불렛포인트") -> str:
    """
    업로드된 문서들 중 특정 페이지의 핵심 내용을 요약합니다.
    사용자의 마지막 질문에서 언급된 'file_ids'와 'pages'(페이지 번호 정수 리스트)를 인자로 전달하세요.
    사용자가 출력 양식을 지정한 경우 'format_instruction' 인자로 전달하세요.
    """
    vector_store = get_vector_store()
    all_docs_content = []

    for fid in file_ids:
        for pg in pages:
            # 특정 문서 특정 페이지만 타겟팅
            docs = vector_store.max_marginal_relevance_search(
                query="해당 페이지의 핵심 주제",
                k=10,
                fetch_k=30,
                filter={
                    "$and": [
                        {"file_id": {"$eq": fid}},
                        {"page": {"$eq": pg}}
                    ]
                }
            )

            content = "\n".join([doc.page_content for doc in docs])
            if content:
                all_docs_content.append(f"--- [문서 ID: {fid}, {pg}페이지] ---\n{content}")

    full_text = "\n\n".join(all_docs_content)

    if not full_text:
        return "요약할 수 있는 문서 내용을 찾지 못했습니다."

    # 요약 프롬프트 구성
    pages_str = ", ".join(map(str, pages))
    summary_prompt = SUMMARY_PAGE_PROMPT.format(pages=pages_str, full_text=full_text, format_instruction=format_instruction)

    # 요약 모델 호출
    response = summary_model.invoke([HumanMessage(content=summary_prompt)])

    return response.content


# ============================================
# 도구 리스트 정의
# ============================================

# 검색 전용 툴
retrieve_node_tools = [search_doc]

# 요약 전용 툴
summarize_node_tools = [summarize_text, summarize_doc, summarize_page, summarize_history]

# 모든 도구
all_tools = retrieve_node_tools + summarize_node_tools
