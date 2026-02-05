flowchart TB
    subgraph USER["👤 사용자"]
        U[보험 담당자 / 분석가]
    end

    subgraph CHANNELS["📱 서비스 채널"]
        WEB[웹 채팅 인터페이스]
        API[API 엔드포인트]
        UPLOAD["📄 문서 업로드
        (최대 3개, 선택)"]
    end

    subgraph PREPROCESSING["⚙️ 전처리"]
        EMB[임베딩]
    end

    subgraph CORE_SERVICES["🎯 핵심 서비스"]
        subgraph CHAT_SERVICE["💬 대화 서비스"]
            CS1[질의 접수]
            CS2[대화 이력 관리]
            CS3[응답 전달]
        end
        
        subgraph INTENT_SERVICE["🧠 의도 분석 서비스"]
            IS1[질문 유형 분류]
            IS2[검색 필요 여부 판단]
            IS3[검색 필요 항목 식별 및 분리]
        end
        
        subgraph SEARCH_SERVICE["🔍 검색 서비스"]
            SS1[1번 문서 검색]
            SS2[2번 문서 검색]
            SS3[3번 문서 검색]
            SS4[문서 품질 검증]
        end
        
        subgraph ANSWER_SERVICE["📝 답변 서비스"]
            AS2[대화 요약]
            AS3[직접 답변]
            AS1[컨텍스트 기반 답변 생성]
        end
    end

    subgraph DATA_SOURCES["📚 데이터 소스"]
        DB1[(1번 문서 DB)]
        DB2[(2번 문서 DB)]
        DB3[(3번 문서 DB)]
        CHAT_DB[(대화 이력 DB)]
    end

    %% User Flow
    U --> WEB & API
    U -.->|"선택"| UPLOAD
    UPLOAD --> EMB
    
    WEB & API --> CS1
    CS1 --> IS1
    CS2 <--> CHAT_DB
    
    %% Intent Analysis Flow
    IS1 --> IS2
    IS2 -->|"검색 필요"| IS3
    
    %% Search Flow
    IS3 -->|"1번"| SS1
    IS3 -->|"2번"| SS2
    IS3 -->|"3번"| SS3
    
    SS1 & SS2 & SS3 --> SS4
    
    %% Grade & Retry Flow
    SS4 -->|"품질 통과"| AS1
    SS4 -->|"품질 미달
    & 재시도 가능"| IS1
    
    %% Response Flow
    AS1 --> CS3
    AS2 --> CS3
    AS3 --> CS3
    CS3 --> U

    %% Right-side connections (직접 답변, 요약)
    IS2 --->|"직접 답변 가능
    (검색 불필요)"| AS3
    IS2 --->|"요약 요청
    (검색 불필요)"| AS2

    %% DB connections at bottom
    EMB --> DB1 & DB2 & DB3
    DB1 <--> SS1
    DB2 <--> SS2
    DB3 <--> SS3

    %% Styling
    classDef user fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef channel fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef preprocess fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef service fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef data fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class U user
    class WEB,API,UPLOAD channel
    class EMB preprocess
    class CS1,CS2,CS3,IS1,IS2,IS3,SS1,SS2,SS3,SS4,AS1,AS2,AS3 service
    class DB1,DB2,DB3,CHAT_DB data