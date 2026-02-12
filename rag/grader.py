"""
rag/grader.py - 문서 관련성 평가 (순수 평가 로직)
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from prompt import DOC_GRADER_INSTRUCTIONS, DOC_GRADER_TEMPLATE


class GradeResult(BaseModel):
    """문서 평가 결과 스키마 (단일 검색 결과에 대한 평가)"""
    relevant: str = Field(description="'yes' if context is sufficient, 'no' if not")


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
        단일 검색 결과에 대한 관련성 평가

        Args:
            question: 사용자 질문
            context: 검색된 문서 컨텍스트
            instructions: 커스텀 지시사항 (None이면 기본값 사용)
            template: 커스텀 템플릿 (None이면 기본값 사용)

        Returns:
            GradeResult (relevant: "yes" 또는 "no")
        """
        instr = instructions or DOC_GRADER_INSTRUCTIONS
        tmpl = template or DOC_GRADER_TEMPLATE

        formatted_prompt = tmpl.format(
            question=question,
            context=context
        )

        result = self.structured_llm.invoke([
            SystemMessage(content=instr),
            HumanMessage(content=formatted_prompt)
        ])

        return result
