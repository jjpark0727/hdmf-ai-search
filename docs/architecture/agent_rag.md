```mermaid
flowchart TB
    subgraph ORCHESTRATION["🤖 LangGraph Orchestration"]
        direction TB
        STATE["GraphState
        ━━━━━━━━━━━━━━━
        • chat_history
        • internal_history
        • original_query
        • retry_counts
        • final_context
        • needed_search
        • from_summarize"]
        
        ROUTER{{"Conditional Router
        ─────────────────
        • summarize → SUM
        • retrieve → RAG
        • direct → GEN"}}
    end

    subgraph AGENT_LAYER["🧠 Agent Layer"]
        subgraph INTENT_AGENT["Intent Analysis Agent"]
            IA_PROMPT["Decision Prompt
            ━━━━━━━━━━━━━━
            • 사용자 의도 파악
            • 검색/요약/직접답변 분류
            • 적절한 도구 매핑"]
            IA_LLM["LLM (도구 선정)"]
            IA_TOOLS["Tool Selection
            ━━━━━━━━━━━━━
            • retriever_tool
            • summarize
            • DIRECT_ANSWER"]
        end
        
        subgraph RETRY_AGENT["Retry Retrieval Agent"]
            RT_LLM["LLM (검색 도구 선정)"]
            RT_TOOLS["Tool Selection
            ━━━━━━━━━━━━━
            • retriever_tool"]
        end
        
        subgraph GRADE_AGENT["Document Grader Agent"]
            GA_LLM["LLM (판단용)"]
            GA_PROMPT["Grade Prompt
            ━━━━━━━━━━━━━━
            • 질문-문서 관련성 평가
            • 답변 충분성 평가
            • 재검색 필요 여부 판단"]
        end
        
        subgraph REWRITE_AGENT["Query Rewriter Agent"]
            RW_LLM["LLM (재작성용)"]
            RW_PROMPT["Rewrite Prompt
            ━━━━━━━━━━━━━━
            • 원본 질문 의미 보존
            • 검색 키워드 확장
            • 구체적 표현으로 명확화"]
        end
    end

    subgraph RAG_PIPELINE["📚 RAG Pipeline"]
        subgraph RETRIEVAL["Retrieval Layer"]
            RET["Retriever"]
        end
        
        subgraph VECTORSTORES["Vector Store"]
            VS[("Vector DB")]
        end
        
        subgraph EMBEDDING["Embedding Layer"]
            EMB["Embedding Model
            ━━━━━━━━━━━━━━
            • OpenAI Ada
            • HuggingFace
            • Sentence-BERT"]
        end
    end

    subgraph GENERATION["✨ Generation Layer"]
        GEN_LLM["LLM (답변 생성)"]
        GEN_PROMPT["Generation Prompt
        ━━━━━━━━━━━━━━━
        • 컨텍스트 주입
        • 답변 형식 지정"]
        
        SUM_LLM["LLM (요약 생성)"]
        SUM_PROMPT["Summary Prompt
        ━━━━━━━━━━━━━
        • 대화 요약 지시"]
    end

    subgraph MEMORY["💾 Memory Management"]
        CHAT_MEM["Chat History
        (chat_history)"]
        INTERNAL_MEM["Internal History
        (internal_history)
        ━━━━━━━━━━━━━━
        • AIMessage
        • ToolMessage
        • HumanMessage"]
    end

    %% Orchestration Flow
    STATE --> ROUTER
    ROUTER -->|"tool_calls 분석"| IA_LLM
    IA_PROMPT --> IA_LLM
    IA_LLM --> IA_TOOLS
    
    %% Intent Agent Flow
    IA_TOOLS -->|"retriever_tool"| RET
    
    %% Retrieval Flow
    RET <--> VS
    EMB --> VS
    
    %% Grading Flow
    RET -->|"ToolMessage"| GA_LLM
    GA_PROMPT --> GA_LLM
    
    %% Rewrite Flow
    GA_LLM -->|"품질 미달"| RW_LLM
    RW_PROMPT --> RW_LLM
    RW_LLM -->|"재작성 쿼리"| RT_LLM
    
    %% Retry Agent Flow
    RT_LLM --> RT_TOOLS
    RT_TOOLS -->|"retriever_tool"| RET
    
    %% Generation Flow
    GA_LLM -->|"품질 통과"| GEN_LLM
    GEN_PROMPT --> GEN_LLM
    
    IA_TOOLS -->|"summarize"| SUM_LLM
    SUM_PROMPT --> SUM_LLM
    
    IA_TOOLS -->|"DIRECT_ANSWER"| GEN_LLM
    
    %% Memory Flow
    CHAT_MEM <--> STATE
    INTERNAL_MEM <--> STATE

    %% Styling
    classDef orchestration fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef agent fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef rag fill:#e0f2f1,stroke:#00796b,stroke-width:2px
    classDef generation fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef memory fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef llm fill:#ffecb3,stroke:#ffa000,stroke-width:2px
    
    class STATE,ROUTER orchestration
    class IA_PROMPT,IA_LLM,IA_TOOLS,RT_LLM,RT_TOOLS,GA_LLM,GA_PROMPT,RW_LLM,RW_PROMPT agent
    class RET,VS,EMB rag
    class GEN_LLM,GEN_PROMPT,SUM_LLM,SUM_PROMPT generation
    class CHAT_MEM,INTERNAL_MEM memory
    ```