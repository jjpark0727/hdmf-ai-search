flowchart TB
    subgraph CLIENT["🖥️ Frontend (Client)"]
        subgraph WEB_APP["Web Application"]
            REACT["React / Next.js
            ━━━━━━━━━━━━━
            • 채팅 UI
            • 메시지 렌더링
            • 스트리밍 응답"]
            STATE_MGT["State Management
            (Redux / Zustand)"]
            WS_CLIENT["WebSocket Client
            (실시간 통신)"]
        end
    end

    subgraph GATEWAY["🚪 API Gateway"]
        NGINX["Nginx / Kong
        ━━━━━━━━━━━━
        • 로드밸런싱
        • Rate Limiting
        • SSL Termination"]
        AUTH["Authentication
        (JWT / OAuth2)"]
    end

    subgraph BACKEND["⚙️ Backend (Server)"]
        subgraph API_LAYER["API Layer"]
            FASTAPI["FastAPI
            ━━━━━━━━━━━━
            • REST Endpoints
            • WebSocket Handler
            • Streaming Response"]
            
            ENDPOINTS["Endpoints
            ─────────────────
            POST /chat
            GET /history
            POST /summarize
            WS /chat/stream"]
        end
        
        subgraph CORE_LAYER["Core Application Layer"]
            LANGGRAPH["LangGraph Engine
            ━━━━━━━━━━━━━━━
            • Graph State Machine
            • Node Execution
            • Conditional Routing"]
            
            LANGCHAIN["LangChain Components
            ━━━━━━━━━━━━━━━━━
            • ChatModels
            • Retrievers
            • Tools
            • Prompts"]
        end
        
        subgraph SERVICE_LAYER["Service Layer"]
            CHAT_SVC["ChatService"]
            RAG_SVC["RAGService"]
            GRADE_SVC["GradeService"]
        end
    end

    subgraph LLM_PROVIDERS["🤖 LLM Providers"]
        OPENAI["OpenAI API
        (GPT-4)"]
        ANTHROPIC["Anthropic API
        (Claude)"]
        AZURE["Azure OpenAI"]
    end

    subgraph DATA_LAYER["💾 Data Layer"]
        subgraph VECTOR_DB["Vector Database"]
            FAISS["FAISS
            (로컬/메모리)"]
            CHROMA["ChromaDB
            (영구 저장)"]
            PINECONE["Pinecone
            (클라우드)"]
        end
        
        subgraph RELATIONAL_DB["Relational Database"]
            POSTGRES["PostgreSQL
            ━━━━━━━━━━━
            • 대화 이력
            • 사용자 정보
            • 세션 관리"]
        end
        
        subgraph CACHE["Cache Layer"]
            REDIS["Redis
            ━━━━━━━━
            • 세션 캐시
            • 응답 캐시
            • Rate Limit"]
        end
    end

    subgraph INFRA["☁️ Infrastructure"]
        subgraph CONTAINER["Container Orchestration"]
            DOCKER["Docker"]
            K8S["Kubernetes"]
        end
        
        subgraph MONITORING["Monitoring & Logging"]
            PROMETHEUS["Prometheus
            + Grafana"]
            ELK["ELK Stack
            (로그 수집)"]
            LANGSMITH["LangSmith
            (LLM 모니터링)"]
        end
    end

    %% Connections
    REACT --> WS_CLIENT
    REACT --> STATE_MGT
    WS_CLIENT -->|"WSS"| NGINX
    REACT -->|"HTTPS"| NGINX
    
    NGINX --> AUTH
    AUTH --> FASTAPI
    
    FASTAPI --> ENDPOINTS
    ENDPOINTS --> LANGGRAPH
    LANGGRAPH --> LANGCHAIN
    LANGCHAIN --> CHAT_SVC & RAG_SVC & GRADE_SVC
    
    LANGCHAIN -->|"API Call"| OPENAI & ANTHROPIC & AZURE
    
    RAG_SVC --> FAISS & CHROMA & PINECONE
    CHAT_SVC --> POSTGRES
    CHAT_SVC --> REDIS
    
    FASTAPI --> PROMETHEUS
    LANGGRAPH --> LANGSMITH
    FASTAPI --> ELK
    
    DOCKER --> K8S

    %% Styling
    classDef frontend fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef gateway fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef backend fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef llm fill:#ffecb3,stroke:#ff8f00,stroke-width:2px
    classDef data fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef infra fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class REACT,STATE_MGT,WS_CLIENT frontend
    class NGINX,AUTH gateway
    class FASTAPI,ENDPOINTS,LANGGRAPH,LANGCHAIN,CHAT_SVC,RAG_SVC,GRADE_SVC backend
    class OPENAI,ANTHROPIC,AZURE llm
    class FAISS,CHROMA,PINECONE,POSTGRES,REDIS data
    class DOCKER,K8S,PROMETHEUS,ELK,LANGSMITH infra