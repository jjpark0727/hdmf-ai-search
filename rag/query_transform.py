"""
rag/query_transform.py - 쿼리 변환 및 확장 전략
"""

from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from prompt import REWRITE_INSTRUCTIONS, REWRITE_TEMPLATE


class QueryTransformer:
    """
    쿼리 변환 및 확장 전략
    
    검색 품질 향상을 위한 다양한 쿼리 변환 기법 제공
    """
    
    def __init__(self, llm):
        """
        Args:
            llm: LangChain LLM 인스턴스
        """
        self.llm = llm
    
    def rewrite_for_missing_info(
        self,
        question: str,
        target_countries: List[str],
        instructions: Optional[str] = None,
        template: Optional[str] = None
    ) -> str:
        """
        부족한 국가 정보 보완을 위한 쿼리 재작성
        
        Args:
            question: 원본 질문
            target_countries: 재검색이 필요한 국가 리스트 (예: ["usa", "japan"])
            instructions: 커스텀 지시사항 (None이면 기본값 사용)
            template: 커스텀 템플릿 (None이면 기본값 사용)
        
        Returns:
            재작성된 검색 쿼리
        """
        instr = instructions or REWRITE_INSTRUCTIONS
        tmpl = template or REWRITE_TEMPLATE
        
        # 국가 리스트를 문자열로 변환
        countries_str = ", ".join(target_countries)
        
        # 템플릿에 데이터 주입
        formatted_content = tmpl.format(
            target_countries=countries_str,
            question=question
        )
        
        # 모델 호출
        response = self.llm.invoke([
            SystemMessage(content=instr),
            HumanMessage(content=formatted_content)
        ])
        
        return response.content
    
    def multi_query(
        self,
        question: str,
        num_queries: int = 3
    ) -> List[str]:
        """
        하나의 질문을 여러 관점의 쿼리로 변환 (Multi-Query)
        
        Args:
            question: 원본 질문
            num_queries: 생성할 쿼리 수
        
        Returns:
            변환된 쿼리 리스트
        """
        prompt = f"""당신은 검색 쿼리 전문가입니다.
다음 질문을 {num_queries}개의 서로 다른 관점에서 재작성해주세요.
각 쿼리는 원본 질문의 의도를 유지하면서 다른 키워드나 표현을 사용해야 합니다.

원본 질문: {question}

각 쿼리를 줄바꿈으로 구분하여 출력하세요. 번호나 부연설명 없이 쿼리만 출력하세요.
"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        queries = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
        
        return queries[:num_queries]
    
    def hyde(
        self,
        question: str
    ) -> str:
        """
        HyDE (Hypothetical Document Embedding)
        
        질문에 대한 가상의 답변을 생성하여 검색에 활용
        
        Args:
            question: 원본 질문
        
        Returns:
            가상의 답변 문서
        """
        prompt = f"""다음 질문에 대한 상세하고 전문적인 답변을 작성해주세요.
실제 데이터가 아니어도 괜찮으니, 해당 주제에 대해 있을 법한 내용으로 작성해주세요.

질문: {question}

답변:"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def step_back(
        self,
        question: str
    ) -> str:
        """
        Step-back Prompting
        
        구체적인 질문을 더 일반적인 질문으로 변환
        
        Args:
            question: 원본 질문
        
        Returns:
            더 일반적인 형태의 질문
        """
        prompt = f"""다음 질문을 한 단계 뒤로 물러나서 더 일반적이고 근본적인 질문으로 변환해주세요.
구체적인 사례나 특정 상황 대신, 해당 주제의 핵심 개념이나 원리를 묻는 질문으로 바꿔주세요.

원본 질문: {question}

변환된 질문 (부연설명 없이 질문만):"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    
    def decompose(
        self,
        question: str,
        max_subquestions: int = 3
    ) -> List[str]:
        """
        질문 분해 (Question Decomposition)
        
        복잡한 질문을 여러 개의 하위 질문으로 분해
        
        Args:
            question: 원본 질문
            max_subquestions: 최대 하위 질문 수
        
        Returns:
            하위 질문 리스트
        """
        prompt = f"""다음 질문을 답변하기 위해 필요한 하위 질문들로 분해해주세요.
각 하위 질문은 독립적으로 검색하여 답을 찾을 수 있어야 합니다.
최대 {max_subquestions}개의 하위 질문만 생성하세요.

원본 질문: {question}

하위 질문들 (각 질문을 줄바꿈으로 구분, 번호 없이):"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        subquestions = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
        
        return subquestions[:max_subquestions]
    
    def expand_with_synonyms(
        self,
        question: str
    ) -> str:
        """
        동의어 확장
        
        질문에 동의어나 관련 키워드를 추가하여 검색 범위 확장
        
        Args:
            question: 원본 질문
        
        Returns:
            확장된 검색 쿼리
        """
        prompt = f"""다음 질문의 핵심 키워드에 대한 동의어나 관련 용어를 추가하여 
검색에 더 효과적인 쿼리로 확장해주세요.

원본 질문: {question}

확장된 쿼리 (부연설명 없이 쿼리만):"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
