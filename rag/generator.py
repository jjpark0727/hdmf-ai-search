"""
rag/generator.py - RAG 전용 답변 생성 (순수 생성 로직)
"""

from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from prompt import (
    ANSWER_GENERATION_INSTRUCTIONS,
    ANSWER_GENERATION_TEMPLATE,
    DIRECT_ANSWER_GENERATION_INSTRUCTIONS,
    DIRECT_ANSWER_GENERATION_TEMPLATE,
    REPORT_GENERATION_INSTRUCTIONS,
    REPORT_GENERATION_TEMPLATE,
)


class RAGGenerator:
    """
    RAG 전용 답변 생성

    검색된 컨텍스트를 기반으로 최종 답변 생성
    """

    def __init__(self, llm):
        """
        Args:
            llm: LangChain LLM 인스턴스
        """
        self.llm = llm

    def generate_answer(
        self,
        question: str,
        context: str,
        chat_history: Optional[List] = None,
    ) -> AIMessage:
        """
        컨텍스트 기반 RAG 답변 생성

        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            chat_history: 이전 대화 기록 (선택)

        Returns:
            AIMessage - 생성된 답변
        """
        instr = ANSWER_GENERATION_INSTRUCTIONS
        tmpl = ANSWER_GENERATION_TEMPLATE

        # 프롬프트 구성
        formatted_prompt = tmpl.format(
            question=question,
            context=context
        )

        # 메시지 구성
        messages = [SystemMessage(content=instr)]

        # 대화 기록 추가 (있는 경우)
        if chat_history:
            messages.extend(chat_history[:-1])  # 마지막 질문 제외


        # 최종 메시지 구성 = 시스템프롬프트 + chat_history + 템플릿 (질문 + 검색 문맥)
        messages.append(HumanMessage(content=formatted_prompt))

        # 모델 호출
        response = self.llm.invoke(messages)

        return response

    def generate_direct_answer(
        self,
        question: str,
        chat_history: Optional[List] = None,
    ) -> AIMessage:
        """
        직접 답변 생성 (RAG 컨텍스트 없이)

        일상 대화, 후속 질문, 내부 지식 질문 등 도구 호출 없이 직접 답변하는 경우에 사용

        Args:
            question: 사용자 질문
            chat_history: 이전 대화 기록 (선택)

        Returns:
            AIMessage - 생성된 답변
        """
        # 프롬프트 구성
        formatted_prompt = DIRECT_ANSWER_GENERATION_TEMPLATE.format(question=question)

        # 메시지 구성
        messages = [SystemMessage(content=DIRECT_ANSWER_GENERATION_INSTRUCTIONS)]

        # 대화 기록 추가 (있는 경우)
        if chat_history:
            messages.extend(chat_history[:-1])

        # 최종 메시지 구성 = 시스템프롬프트 + chat_history + 템플릿 (질문)
        messages.append(HumanMessage(content=formatted_prompt))

        # 모델 호출
        response = self.llm.invoke(messages)

        return response

    def generate_with_mode(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List] = None,
    ) -> AIMessage:
        """
        모드 자동 선택하여 답변 생성

        컨텍스트가 있으면 RAG 모드, 없으면 직접 답변 모드

        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트 
            chat_history: 이전 대화 기록 

        Returns:
            AIMessage - 생성된 답변
        """

        # 검색 context가 있는 경우
        if context and context.strip():
            return self.generate_answer(
                question=question,
                context=context,
                chat_history=chat_history
            )
        else:
            # 직접 답변하는 경우
            return self.generate_direct_answer(
                question=question,
                chat_history=chat_history
            )


    def generate_report(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List] = None,
    ) -> AIMessage:
        """
        기획안/보고서/제안서 생성

        검색 결과(final_context)나 요약 결과(chat_history)를 참고하여
        체계적인 문서를 작성

        Args:
            question: 사용자 요청 (원본 질문)
            context: 검색된 문서 컨텍스트 (없으면 "없음")
            chat_history: 이전 대화 기록 (요약 결과 포함)

        Returns:
            AIMessage - 생성된 기획안/보고서
        """
        # 프롬프트 구성
        formatted_prompt = REPORT_GENERATION_TEMPLATE.format(
            question=question,
            context=context if context and context.strip() else "없음"
        )

        # 메시지 구성
        messages = [SystemMessage(content=REPORT_GENERATION_INSTRUCTIONS)]

        # 대화 기록 추가 (있는 경우)
        if chat_history:
            messages.extend(chat_history[:-1])

        messages.append(HumanMessage(content=formatted_prompt))

        # 모델 호출
        response = self.llm.invoke(messages)

        return response

    # 인용 포함 답변 (실험용)
    def generate_with_citations(
        self,
        question: str,
        documents: List,
        chat_history: Optional[List] = None
    ) -> AIMessage:
        """
        인용 포함 답변 생성

        Args:
            question: 사용자 질문
            documents: Document 객체 리스트 (메타데이터 포함)
            chat_history: 이전 대화 기록 (선택)

        Returns:
            AIMessage - 인용이 포함된 답변
        """
        # 문서별 인용 번호 부여
        context_with_citations = []
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            context_with_citations.append(
                f"[{i}] (출처: {source}, 페이지: {page})\n{doc.page_content}"
            )

        full_context = "\n\n".join(context_with_citations)

        # 인용 지시사항 추가
        citation_instructions = ANSWER_GENERATION_INSTRUCTIONS + """

            [인용 규칙]
            - 답변에서 특정 정보를 언급할 때 해당 출처 번호를 [1], [2] 형식으로 표기하세요.
            - 여러 출처의 정보를 종합할 경우 [1,2] 형식으로 표기하세요.
            """

        return self.generate(
            question=question,
            context=full_context,
            chat_history=chat_history,
            instructions=citation_instructions
        )
