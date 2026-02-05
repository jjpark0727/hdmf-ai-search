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
    
    def generate(
        self,
        question: str,
        context: str,
        chat_history: Optional[List] = None,
        missing_countries: Optional[List[str]] = None,
        instructions: Optional[str] = None,
        template: Optional[str] = None
    ) -> AIMessage:
        """
        컨텍스트 기반 RAG 답변 생성
        
        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            chat_history: 이전 대화 기록 (선택)
            missing_countries: 정보가 부족한 국가 리스트 (선택)
            instructions: 커스텀 지시사항 (None이면 기본값 사용)
            template: 커스텀 템플릿 (None이면 기본값 사용)
        
        Returns:
            AIMessage - 생성된 답변
        """
        instr = instructions or ANSWER_GENERATION_INSTRUCTIONS
        tmpl = template or ANSWER_GENERATION_TEMPLATE
        
        # 부족한 국가 정보 안내 메시지 추가
        full_context = context
        if missing_countries:
            missing_info_notice = self._build_missing_info_notice(missing_countries)
            full_context = f"{context}\n{missing_info_notice}"
        
        # 프롬프트 구성
        formatted_prompt = tmpl.format(
            question=question,
            context=full_context
        )
        
        # 메시지 구성
        messages = [SystemMessage(content=instr)]
        
        # 대화 기록 추가 (있는 경우)
        if chat_history:
            messages.extend(chat_history[:-1])  # 마지막 질문 제외
        
        messages.append(HumanMessage(content=formatted_prompt))
        
        # 모델 호출
        response = self.llm.invoke(messages)
        
        return response
    
    def generate_direct(
        self,
        question: str,
        chat_history: Optional[List] = None,
        instructions: Optional[str] = None,
        template: Optional[str] = None
    ) -> AIMessage:
        """
        직접 답변 생성 (RAG 컨텍스트 없이)
        
        인사, 일상 대화, 이전 맥락 기반 추가 질문 등에 사용
        
        Args:
            question: 사용자 질문
            chat_history: 이전 대화 기록 (선택)
            instructions: 커스텀 지시사항 (None이면 기본값 사용)
            template: 커스텀 템플릿 (None이면 기본값 사용)
        
        Returns:
            AIMessage - 생성된 답변
        """
        instr = instructions or DIRECT_ANSWER_GENERATION_INSTRUCTIONS
        tmpl = template or DIRECT_ANSWER_GENERATION_TEMPLATE
        
        # 프롬프트 구성
        formatted_prompt = tmpl.format(question=question)
        
        # 메시지 구성
        messages = [SystemMessage(content=instr)]
        
        # 대화 기록 추가 (있는 경우)
        if chat_history:
            messages.extend(chat_history[:-1])  # 마지막 질문 제외
        
        messages.append(HumanMessage(content=formatted_prompt))
        
        # 모델 호출
        response = self.llm.invoke(messages)
        
        return response
    
    def generate_with_mode(
        self,
        question: str,
        context: Optional[str] = None,
        chat_history: Optional[List] = None,
        missing_countries: Optional[List[str]] = None
    ) -> AIMessage:
        """
        모드 자동 선택하여 답변 생성
        
        컨텍스트가 있으면 RAG 모드, 없으면 직접 답변 모드
        
        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트 (없으면 직접 답변)
            chat_history: 이전 대화 기록 (선택)
            missing_countries: 정보가 부족한 국가 리스트 (선택)
        
        Returns:
            AIMessage - 생성된 답변
        """
        if context and context.strip():
            # RAG 모드
            return self.generate(
                question=question,
                context=context,
                chat_history=chat_history,
                missing_countries=missing_countries
            )
        else:
            # 직접 답변 모드
            return self.generate_direct(
                question=question,
                chat_history=chat_history
            )
    
    def _build_missing_info_notice(self, countries: List[str]) -> str:
        """부족한 국가 정보 안내 메시지 생성"""
        notices = []
        for country in countries:
            notices.append(f"(참고: {country.upper()}에 대한 정보는 제공된 문서에 없습니다.)")
        return "\n".join(notices)
    
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
