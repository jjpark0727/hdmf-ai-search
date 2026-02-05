"""
rag/grader.py - 문서 관련성 평가 (순수 평가 로직)
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from prompt import DOC_GRADER_INSTRUCTIONS, DOC_GRADER_TEMPLATE


class GradeResult(BaseModel):
    """문서 평가 결과 스키마"""
    usa: str = Field(description="'yes' if sufficient, 'no' if not")
    japan: str = Field(description="'yes' if sufficient, 'no' if not")


class DocumentGrader:
    """
    LLM 기반 문서 관련성 평가
    
    검색된 문서가 사용자 질문에 답변하기에 충분한지 평가
    """
    
    def __init__(self, llm):
        """
        Args:
            llm: LangChain LLM 인스턴스
        """
        self.llm = llm
        self.structured_llm = llm.with_structured_output(GradeResult)
    
    def grade(
        self,
        question: str,
        context: str,
        instructions: Optional[str] = None,
        template: Optional[str] = None
    ) -> GradeResult:
        """
        문서 관련성 평가 수행
        
        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            instructions: 커스텀 지시사항 (None이면 기본값 사용)
            template: 커스텀 템플릿 (None이면 기본값 사용)
        
        Returns:
            GradeResult (usa, japan 각각 "yes" 또는 "no")
        """
        instr = instructions or DOC_GRADER_INSTRUCTIONS
        tmpl = template or DOC_GRADER_TEMPLATE
        
        # 템플릿에 질문과 컨텍스트 주입
        formatted_prompt = tmpl.format(
            question=question,
            context=context
        )
        
        # 모델 호출
        result = self.structured_llm.invoke([
            SystemMessage(content=instr),
            HumanMessage(content=formatted_prompt)
        ])
        
        return result
    
    def grade_single_country(
        self,
        question: str,
        context: str,
        country: str
    ) -> bool:
        """
        단일 국가에 대한 문서 관련성 평가
        
        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            country: 평가할 국가 ("usa" 또는 "japan")
        
        Returns:
            bool - True이면 충분, False이면 부족
        """
        result = self.grade(question, context)
        
        if country == "usa":
            return result.usa == "yes"
        elif country == "japan":
            return result.japan == "yes"
        else:
            raise ValueError(f"지원하지 않는 국가입니다: {country}")
    
    def get_needed_countries(
        self,
        question: str,
        context: str
    ) -> list:
        """
        추가 검색이 필요한 국가 리스트 반환
        
        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
        
        Returns:
            재검색이 필요한 국가 리스트 (예: ["usa"], ["japan"], ["usa", "japan"], [])
        """
        result = self.grade(question, context)
        
        needed = []
        if result.usa == "no":
            needed.append("usa")
        if result.japan == "no":
            needed.append("japan")
        
        return needed
