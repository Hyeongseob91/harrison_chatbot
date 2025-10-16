# 🧠 LangGraph 애플리케이션

> RAG Chatbot의 핵심 AI 엔진 - LangGraph 워크플로우 및 서비스 계층

## 📋 개요

이 폴더는 LangGraph 기반의 RAG 파이프라인을 구현한 핵심 애플리케이션입니다.
Clean Architecture 원칙을 따라 **Domain - Application - Infrastructure** 계층으로 분리되어 있으며,
모든 노드는 **비동기(async)** 로 구현되어 동시 사용자 처리가 가능합니다.

### 핵심 설계 원칙

- **Clean Architecture**: 계층 분리로 테스트 용이성 및 유지보수성 확보
- **Port-Adapter 패턴**: 외부 서비스 의존성을 인터페이스로 추상화
- **Dependency Injection**: Factory 패턴으로 서비스 생성 및 주입
- **비동기 처리**: 모든 노드와 서비스를 async로 구현

## 📁 폴더 구조

```
app/
├── main.py                   # LangGraph 워크플로우 초기화 및 실행
│
├── domain/                   # 도메인 계층 (순수 비즈니스 로직, 외부 의존성 없음)
│   ├── entities.py           # Document, Message, User 엔티티
│   ├── value_objects.py      # QueryType, RetrievalStrategy 값 객체
│   └── exceptions.py         # 도메인 예외 정의
│
├── nodes/                    # Application 계층 (LangGraph 노드 - Use Case 구현)
│   ├── graph_state/
│   │   ├── schemas.py        # ChatState TypedDict (LangGraph 상태 스키마)
│   │   └── reducers.py       # State 업데이트 로직 (상태 변환 함수)
│   │
│   ├── chat_process/         # 채팅 처리 관련 노드
│   │   ├── user_input_node.py    # 사용자 입력 검증 및 전처리
│   │   ├── response_node.py      # ⭐️ LLM 답변 생성 노드 (GPT 호출)
│   │   └── history_node.py       # 대화 히스토리 저장 노드
│   │
│   ├── source_process/       # 문서 검색 및 처리 관련 노드
│   │   ├── retrieval_node.py     # Vector DB에서 문서 검색
│   │   ├── reranking_node.py     # 검색 결과 재순위화
│   │   └── synthesis_node.py     # 컨텍스트 합성 및 프롬프트 구성
│   │
│   └── supervisor/           # Supervisor Agent (향후 확장)
│       └── supervisor_node.py    # 라우팅 및 의사결정 노드
│
├── services/                 # Infrastructure 계층 (외부 서비스 통신)
│   ├── interfaces/           # Port (추상 인터페이스)
│   │   ├── llm_interface.py        # ABC 기반 LLM 인터페이스
│   │   ├── embedding_interface.py  # ABC 기반 Embedding 인터페이스
│   │   ├── vector_store_interface.py # ABC 기반 Vector Store 인터페이스
│   │   └── document_interface.py   # ABC 기반 Document 처리 인터페이스
│   │
│   ├── implementations/      # Adapter (구체 구현체)
│   │   ├── openai_llm_service.py      # OpenAI GPT-OSS-20B 구현
│   │   ├── openai_embedding_service.py # OpenAI Embedding 구현
│   │   ├── qdrant_service.py          # Qdrant Vector DB CRUD 구현
│   │   └── document_service.py        # 문서 파싱 및 처리 구현
│   │
│   └── factory.py            # Factory Pattern으로 서비스 생성
│
├── utils/                    # 유틸리티 함수 및 도구
│   ├── logger.py             # structlog 기반 구조화 로깅
│   ├── parser.py             # 문서 파싱 유틸 (PDF, TXT, DOCX)
│   ├── decorators.py         # 재시도, 타이밍, 에러 핸들링 데코레이터
│   └── validators.py         # 입력 검증 유틸
│
└── api/                      # Presentation 계층 (FastAPI API 서버)
    ├── main.py               # FastAPI 애플리케이션 초기화
    ├── routes/
    │   ├── chat.py           # POST /chat/invoke, /chat/stream
    │   └── documents.py      # POST /documents/upload, GET /documents
    ├── schemas/
    │   ├── request.py        # Pydantic Request 모델
    │   └── response.py       # Pydantic Response 모델
    ├── middleware.py         # CORS, 에러 핸들링, 로깅 미들웨어
    └── docs/
        └── openapi.yaml      # OpenAPI 명세서
```

## 🔄 LangGraph 워크플로우

### 전체 데이터 플로우

```
START
  ↓
┌─────────────────────────────────────────────┐
│ user_input_node                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ - 입력 검증 (빈 문자열, 길이 제한)            │
│ - SQL Injection, XSS 공격 방지               │
│ - 쿼리 타입 분석 (사실형/의견형)              │
│ - state["query"] 설정                       │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ retrieval_node                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 1. OpenAI Embedding API 호출                │
│    query → vector (1536 차원)               │
│ 2. Qdrant Vector 검색                       │
│    - HNSW 알고리즘 사용                      │
│    - top_k=10, similarity > 0.7            │
│ 3. state["retrieved_docs"] 설정            │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ reranking_node                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ - Cross-encoder로 재순위화 (선택적)          │
│ - 중복 문서 제거                             │
│ - Top-3 문서만 선택                          │
│ - state["retrieved_docs"] 업데이트         │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ synthesis_node                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ - 검색된 문서들을 하나의 컨텍스트로 합성       │
│ - 메타데이터 추출 (출처, 페이지 번호)          │
│ - 토큰 수 계산 (4096 토큰 제한)              │
│ - state["context"] 설정                    │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ response_node ⭐️ LLM 답변 생성              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ 1. System Prompt 구성                       │
│ 2. User Prompt: context + query            │
│ 3. OpenAI GPT-OSS-20B API 호출 (await)     │
│ 4. 응답 후처리 (출처 인용 추가)               │
│ 5. state["response"] 설정                  │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│ history_node                                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ - Django API로 채팅 히스토리 저장             │
│ - 토큰 사용량, 타이밍 정보 저장               │
│ - state["metadata"] 업데이트                │
└─────────────────┬───────────────────────────┘
                  ↓
                 END
```

### 워크플로우 코드 예시

```python
# app/main.py
from langgraph.graph import StateGraph
from app.nodes.graph_state.schemas import ChatState
from app.nodes.chat_process.user_input_node import user_input_node
from app.nodes.source_process.retrieval_node import retrieval_node
from app.nodes.source_process.reranking_node import reranking_node
from app.nodes.source_process.synthesis_node import synthesis_node
from app.nodes.chat_process.response_node import response_node
from app.nodes.chat_process.history_node import history_node

# LangGraph 워크플로우 정의
workflow = StateGraph(ChatState)

# 노드 추가
workflow.add_node("user_input", user_input_node)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("reranking", reranking_node)
workflow.add_node("synthesis", synthesis_node)
workflow.add_node("response", response_node)
workflow.add_node("history", history_node)

# 엣지 연결 (순서 정의)
workflow.set_entry_point("user_input")
workflow.add_edge("user_input", "retrieval")
workflow.add_edge("retrieval", "reranking")
workflow.add_edge("reranking", "synthesis")
workflow.add_edge("synthesis", "response")
workflow.add_edge("response", "history")
workflow.set_finish_point("history")

# 워크플로우 컴파일
app = workflow.compile()
```

## 📊 GraphState 스키마

### ChatState 정의

```python
# app/nodes/graph_state/schemas.py
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class ChatState(TypedDict):
    """
    LangGraph 워크플로우 전체에서 공유되는 상태 스키마

    각 노드는 이 상태의 일부를 읽고 업데이트합니다.
    TypedDict를 사용하여 타입 안정성을 보장합니다.
    """

    # 대화 메시지 리스트 (LangChain 메시지 형식)
    # add_messages 리듀서를 사용하여 메시지 자동 병합
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 사용자 쿼리 (원본 텍스트)
    query: str

    # Vector DB에서 검색된 문서 리스트
    # 각 문서는 {content, metadata, score} 구조
    retrieved_docs: list[dict]

    # 합성된 컨텍스트 (LLM에 전달할 문맥)
    context: str

    # LLM 생성 응답
    response: str

    # 메타데이터 (토큰 사용량, 타이밍, 모델 정보 등)
    metadata: dict
```

### State 업데이트 예시

```python
# 노드에서 상태 업데이트
async def my_node(state: ChatState) -> ChatState:
    # 일부 필드만 반환하면 자동으로 병합됨
    return {
        "retrieved_docs": [{"content": "...", "metadata": {...}}],
        "metadata": {"retrieval_time_ms": 150}
    }
```

## 🎯 핵심 노드 상세 설명

### 1. user_input_node (입력 검증 및 전처리)

**위치**: `app/nodes/chat_process/user_input_node.py`

**역할**:
- 사용자 입력 검증 (빈 문자열, 길이 제한, 특수문자)
- SQL Injection, XSS 공격 패턴 탐지 및 차단
- 쿼리 타입 분석 (사실형 질문 vs 의견형 질문)
- 입력 정규화 (공백 제거, 소문자 변환 등)

**입력**:
- `state["messages"]`: 기존 대화 히스토리
- 사용자 최신 메시지

**출력**:
- `state["query"]`: 검증되고 정규화된 쿼리
- `state["metadata"]["query_type"]`: 쿼리 타입 (factual/opinion)

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.utils.validators import validate_input, detect_injection
from app.utils.logger import logger

async def user_input_node(state: ChatState) -> ChatState:
    """
    사용자 입력을 검증하고 전처리하는 노드

    Args:
        state: ChatState (messages 필드 필수)

    Returns:
        ChatState: query, metadata 업데이트

    Raises:
        ValueError: 입력이 유효하지 않을 경우
    """
    # 최신 사용자 메시지 추출
    user_message = state["messages"][-1].content

    logger.info("Processing user input", message_length=len(user_message))

    # 1. 기본 검증
    if not user_message or len(user_message.strip()) == 0:
        raise ValueError("쿼리가 비어있습니다")

    if len(user_message) > 1000:
        raise ValueError("쿼리가 너무 깁니다 (최대 1000자)")

    # 2. 보안 검증
    if detect_injection(user_message):
        raise ValueError("유효하지 않은 입력입니다")

    # 3. 정규화
    query = user_message.strip()

    # 4. 쿼리 타입 분석
    query_type = analyze_query_type(query)

    logger.info("Input validated", query_type=query_type)

    return {
        "query": query,
        "metadata": {
            "query_type": query_type,
            "original_length": len(user_message)
        }
    }

def analyze_query_type(query: str) -> str:
    """쿼리 타입 분석 (사실형/의견형)"""
    factual_keywords = ["무엇", "어떻게", "언제", "어디서", "누가"]
    opinion_keywords = ["생각", "의견", "추천", "어떤가"]

    query_lower = query.lower()

    if any(kw in query_lower for kw in factual_keywords):
        return "factual"
    elif any(kw in query_lower for kw in opinion_keywords):
        return "opinion"
    else:
        return "general"
```

### 2. retrieval_node (Vector 검색)

**위치**: `app/nodes/source_process/retrieval_node.py`

**역할**:
- 쿼리를 벡터로 변환 (OpenAI Embedding API)
- Qdrant에서 유사 문서 검색 (HNSW 알고리즘)
- Top-K 문서 반환 (기본 10개, similarity > 0.7)

**입력**:
- `state["query"]`: 사용자 쿼리

**출력**:
- `state["retrieved_docs"]`: 검색된 문서 리스트

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.services.factory import get_embedding_service, get_vector_store
from app.utils.logger import logger
import time

async def retrieval_node(state: ChatState) -> ChatState:
    """
    Vector DB에서 유사 문서를 검색하는 노드

    Args:
        state: ChatState (query 필드 필수)

    Returns:
        ChatState: retrieved_docs 업데이트
    """
    query = state["query"]
    logger.info("Starting retrieval", query=query)

    start_time = time.time()

    # 1. 임베딩 생성 (OpenAI text-embedding-3-large)
    embedding_service = get_embedding_service()
    query_vector = await embedding_service.embed(query)

    logger.debug("Embedding generated", vector_dim=len(query_vector))

    # 2. Vector 검색 (Qdrant)
    vector_store = get_vector_store()
    search_results = await vector_store.search(
        collection_name="documents",
        query_vector=query_vector,
        top_k=10,
        score_threshold=0.7  # 유사도 임계값
    )

    # 3. 결과 포맷팅
    retrieved_docs = []
    for result in search_results:
        retrieved_docs.append({
            "content": result.payload["text"],
            "metadata": {
                "filename": result.payload["filename"],
                "page": result.payload.get("page", 0),
                "chunk_id": result.id,
                "score": result.score
            }
        })

    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info("Retrieval completed",
                docs_found=len(retrieved_docs),
                elapsed_ms=elapsed_ms)

    return {
        "retrieved_docs": retrieved_docs,
        "metadata": {
            "retrieval_time_ms": elapsed_ms,
            "docs_retrieved": len(retrieved_docs)
        }
    }
```

### 3. reranking_node (재순위화)

**위치**: `app/nodes/source_process/reranking_node.py`

**역할**:
- Cross-encoder 모델로 쿼리-문서 관련성 재평가
- 중복 문서 제거 (같은 파일의 인접 청크)
- Top-3 문서만 선택하여 컨텍스트 크기 최적화

**입력**:
- `state["query"]`: 사용자 쿼리
- `state["retrieved_docs"]`: 검색된 문서 (Top-10)

**출력**:
- `state["retrieved_docs"]`: 재순위화된 문서 (Top-3)

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.utils.logger import logger

async def reranking_node(state: ChatState) -> ChatState:
    """
    검색 결과를 재순위화하고 필터링하는 노드

    Args:
        state: ChatState (query, retrieved_docs 필수)

    Returns:
        ChatState: retrieved_docs 업데이트 (Top-3)
    """
    query = state["query"]
    docs = state["retrieved_docs"]

    logger.info("Starting reranking", initial_docs=len(docs))

    if len(docs) == 0:
        logger.warning("No documents to rerank")
        return {"retrieved_docs": []}

    # 1. 중복 제거 (같은 파일의 인접 청크)
    deduplicated_docs = remove_duplicates(docs)

    # 2. Cross-encoder 재순위화 (향후 구현)
    # reranked_docs = await cross_encoder_rerank(query, deduplicated_docs)

    # 현재는 스코어 기준 정렬
    sorted_docs = sorted(
        deduplicated_docs,
        key=lambda x: x["metadata"]["score"],
        reverse=True
    )

    # 3. Top-3 선택
    top_docs = sorted_docs[:3]

    logger.info("Reranking completed", final_docs=len(top_docs))

    return {"retrieved_docs": top_docs}


def remove_duplicates(docs: list[dict]) -> list[dict]:
    """인접 청크 중복 제거"""
    seen_files = set()
    unique_docs = []

    for doc in docs:
        file_key = doc["metadata"]["filename"]
        if file_key not in seen_files:
            unique_docs.append(doc)
            seen_files.add(file_key)

    return unique_docs
```

### 4. synthesis_node (컨텍스트 합성)

**위치**: `app/nodes/source_process/synthesis_node.py`

**역할**:
- 여러 문서를 하나의 컨텍스트로 합성
- 메타데이터 추출 및 포맷팅 (출처, 페이지)
- 토큰 수 계산 및 제한 (최대 4096 토큰)

**입력**:
- `state["retrieved_docs"]`: 재순위화된 문서

**출력**:
- `state["context"]`: 합성된 컨텍스트 문자열

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.utils.logger import logger
import tiktoken

async def synthesis_node(state: ChatState) -> ChatState:
    """
    검색된 문서들을 하나의 컨텍스트로 합성하는 노드

    Args:
        state: ChatState (retrieved_docs 필수)

    Returns:
        ChatState: context 업데이트
    """
    docs = state["retrieved_docs"]

    logger.info("Starting context synthesis", docs_count=len(docs))

    if len(docs) == 0:
        return {
            "context": "검색된 문서가 없습니다.",
            "metadata": {"context_tokens": 0}
        }

    # 1. 컨텍스트 구성
    context_parts = []
    for i, doc in enumerate(docs, 1):
        filename = doc["metadata"]["filename"]
        page = doc["metadata"]["page"]
        content = doc["content"]

        context_parts.append(
            f"[문서 {i}: {filename}, p.{page}]\n{content}\n"
        )

    context = "\n---\n".join(context_parts)

    # 2. 토큰 수 계산
    token_count = count_tokens(context)

    # 3. 토큰 제한 (4096 토큰)
    if token_count > 4096:
        logger.warning("Context too long, truncating",
                      original_tokens=token_count)
        context = truncate_context(context, max_tokens=4096)
        token_count = 4096

    logger.info("Context synthesized", tokens=token_count)

    return {
        "context": context,
        "metadata": {"context_tokens": token_count}
    }


def count_tokens(text: str) -> int:
    """텍스트의 토큰 수 계산 (tiktoken)"""
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))


def truncate_context(text: str, max_tokens: int) -> str:
    """토큰 수 제한에 맞게 텍스트 잘라내기"""
    encoding = tiktoken.encoding_for_model("gpt-4")
    tokens = encoding.encode(text)
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)
```

### 5. response_node ⭐️ (LLM 답변 생성)

**위치**: `app/nodes/chat_process/response_node.py`

**역할**:
- **최종 답변 생성** (OpenAI GPT-OSS-20B 호출)
- 시스템 프롬프트 및 사용자 프롬프트 구성
- 응답 후처리 (출처 인용 추가, 포맷팅)

**입력**:
- `state["context"]`: 합성된 컨텍스트
- `state["query"]`: 사용자 쿼리

**출력**:
- `state["response"]`: LLM 생성 응답

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.services.factory import get_llm_service
from app.utils.logger import logger
import time

async def response_node(state: ChatState) -> ChatState:
    """
    ⭐️ LLM을 사용하여 최종 답변을 생성하는 노드

    이 노드에서 OpenAI GPT-OSS-20B API를 호출하여
    사용자 질문에 대한 답변을 생성합니다.

    Args:
        state: ChatState (context, query 필수)

    Returns:
        ChatState: response, metadata 업데이트
    """
    context = state["context"]
    query = state["query"]

    logger.info("Starting response generation", query=query)

    start_time = time.time()

    # 1. LLM 서비스 가져오기 (Dependency Injection)
    llm_service = get_llm_service()

    # 2. 시스템 프롬프트 구성
    system_prompt = """당신은 문서 기반 질의응답 AI 어시스턴트입니다.

주어진 Context를 참고하여 사용자의 질문에 정확하고 상세하게 답변하세요.

규칙:
1. Context에 있는 정보만을 기반으로 답변하세요
2. Context에 없는 내용은 추측하지 말고 "제공된 문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요
3. 답변은 명확하고 이해하기 쉽게 작성하세요
4. 가능한 경우 구체적인 예시나 수치를 포함하세요
5. 답변은 한국어로 작성하세요
"""

    # 3. 사용자 프롬프트 구성
    user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""

    # 4. LLM API 호출 ⭐️ 실제 LLM 호출 지점
    try:
        response = await llm_service.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info("Response generated successfully",
                   response_length=len(response),
                   elapsed_ms=elapsed_ms,
                   tokens_used=llm_service.last_token_count)

        # 5. 응답 후처리 (출처 인용 추가)
        processed_response = add_citations(
            response=response,
            sources=state["retrieved_docs"]
        )

        return {
            "response": processed_response,
            "metadata": {
                "model": "gpt-oss-20b",
                "tokens_used": llm_service.last_token_count,
                "generation_time_ms": elapsed_ms,
                "temperature": 0.7
            }
        }

    except Exception as e:
        logger.error("LLM generation failed", error=str(e))
        return {
            "response": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
            "metadata": {"error": str(e)}
        }


def add_citations(response: str, sources: list[dict]) -> str:
    """
    응답에 출처 인용 추가

    Args:
        response: LLM 생성 응답
        sources: 참고한 문서 리스트

    Returns:
        출처가 포함된 응답
    """
    if not sources:
        return response

    citations = "\n\n**📚 참고 문서:**\n"
    for i, doc in enumerate(sources, 1):
        filename = doc["metadata"]["filename"]
        page = doc["metadata"]["page"]
        score = doc["metadata"]["score"]
        citations += f"{i}. {filename} (p.{page}, 유사도: {score:.2f})\n"

    return response + citations
```

### 6. history_node (히스토리 저장)

**위치**: `app/nodes/chat_process/history_node.py`

**역할**:
- Django API를 호출하여 채팅 히스토리 저장
- 토큰 사용량, 타이밍 정보 기록
- 사용자별 세션 관리

**입력**:
- `state["query"]`: 사용자 질문
- `state["response"]`: LLM 응답
- `state["metadata"]`: 메타데이터

**출력**:
- 상태 업데이트 없음 (side effect만 수행)

**코드 스켈레톤**:
```python
from app.nodes.graph_state.schemas import ChatState
from app.utils.logger import logger
import httpx

async def history_node(state: ChatState) -> ChatState:
    """
    채팅 히스토리를 Django API에 저장하는 노드

    Args:
        state: ChatState (전체 상태 필요)

    Returns:
        ChatState: 상태 변경 없음
    """
    logger.info("Saving chat history")

    # Django API 엔드포인트
    django_url = "http://django:8001/api/chat-history/messages/"

    # 저장할 데이터 구성
    history_data = {
        "session_id": state.get("session_id", "default"),
        "messages": [
            {
                "role": "user",
                "content": state["query"]
            },
            {
                "role": "assistant",
                "content": state["response"],
                "metadata": state["metadata"]
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(django_url, json=history_data)
            response.raise_for_status()

        logger.info("History saved successfully")

    except Exception as e:
        logger.error("Failed to save history", error=str(e))
        # 히스토리 저장 실패는 워크플로우를 중단하지 않음

    return {}  # 상태 변경 없음
```

## 🔌 서비스 계층 (Port-Adapter 패턴)

### Port (인터페이스)

**위치**: `app/services/interfaces/llm_interface.py`

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator

class LLMInterface(ABC):
    """
    LLM 서비스 추상 인터페이스 (Port)

    구현체는 OpenAI, Anthropic, 로컬 모델 등 다양할 수 있음
    """

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0
    ) -> str:
        """
        답변 생성 (동기)

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            temperature: 생성 다양성 (0.0-2.0)
            max_tokens: 최대 토큰 수
            top_p: Nucleus sampling

        Returns:
            생성된 답변
        """
        pass

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 답변 생성

        Yields:
            생성된 답변 청크
        """
        pass

    @property
    @abstractmethod
    def last_token_count(self) -> int:
        """마지막 호출의 토큰 사용량"""
        pass
```

### Adapter (구현체)

**위치**: `app/services/implementations/openai_llm_service.py`

```python
from openai import AsyncOpenAI
from app.services.interfaces.llm_interface import LLMInterface
from config.settings import settings
from app.utils.logger import logger
from typing import AsyncGenerator

class OpenAILLMService(LLMInterface):
    """
    OpenAI API를 사용한 LLM 서비스 구현체 (Adapter)
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: OpenAI API Key (없으면 설정에서 가져옴)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = settings.OPENAI_MODEL  # "gpt-oss-20b"
        self._last_token_count = 0

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 1.0
    ) -> str:
        """OpenAI Chat Completion API 호출"""

        logger.debug("Calling OpenAI API", model=self.model)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )

            # 토큰 사용량 저장
            self._last_token_count = response.usage.total_tokens

            # 응답 추출
            content = response.choices[0].message.content

            logger.debug("OpenAI API call succeeded",
                        tokens=self._last_token_count)

            return content

        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e))
            raise

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> AsyncGenerator[str, None]:
        """OpenAI 스트리밍 API 호출"""

        logger.debug("Starting OpenAI stream", model=self.model)

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("OpenAI stream failed", error=str(e))
            raise

    @property
    def last_token_count(self) -> int:
        return self._last_token_count
```

### Dependency Injection (Factory)

**위치**: `app/services/factory.py`

```python
from app.services.interfaces.llm_interface import LLMInterface
from app.services.interfaces.embedding_interface import EmbeddingInterface
from app.services.interfaces.vector_store_interface import VectorStoreInterface
from app.services.implementations.openai_llm_service import OpenAILLMService
from app.services.implementations.openai_embedding_service import OpenAIEmbeddingService
from app.services.implementations.qdrant_service import QdrantService
from config.settings import settings

# 싱글톤 인스턴스 (선택적)
_llm_service = None
_embedding_service = None
_vector_store = None


def get_llm_service() -> LLMInterface:
    """
    LLM 서비스 인스턴스를 반환하는 팩토리 함수

    환경에 따라 다른 구현체를 반환할 수 있음:
    - 프로덕션: OpenAI
    - 테스트: Mock
    """
    global _llm_service

    if _llm_service is None:
        _llm_service = OpenAILLMService(
            api_key=settings.OPENAI_API_KEY
        )

    return _llm_service


def get_embedding_service() -> EmbeddingInterface:
    """Embedding 서비스 팩토리"""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = OpenAIEmbeddingService(
            api_key=settings.OPENAI_API_KEY
        )

    return _embedding_service


def get_vector_store() -> VectorStoreInterface:
    """Vector Store 서비스 팩토리"""
    global _vector_store

    if _vector_store is None:
        _vector_store = QdrantService(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )

    return _vector_store
```

## 🚀 API 사용법

### FastAPI 엔드포인트

**1. 채팅 (동기)**

```bash
curl -X POST http://localhost:8000/chat/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "query": "RAG가 무엇인가요?",
    "session_id": "user123"
  }'
```

**응답**:
```json
{
  "response": "RAG는 Retrieval-Augmented Generation의 약자로...\n\n**📚 참고 문서:**\n1. rag_intro.pdf (p.1, 유사도: 0.92)",
  "metadata": {
    "model": "gpt-oss-20b",
    "tokens_used": 450,
    "generation_time_ms": 2300,
    "retrieval_time_ms": 150
  }
}
```

**2. 채팅 (스트리밍)**

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "RAG가 무엇인가요?"
  }'
```

**응답 (SSE)**:
```
data: {"chunk": "RAG는 "}
data: {"chunk": "Retrieval-"}
data: {"chunk": "Augmented "}
data: {"chunk": "Generation"}
data: {"done": true, "metadata": {...}}
```

**3. 문서 업로드**

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@document.pdf"
```

**응답**:
```json
{
  "document_id": "doc_12345",
  "filename": "document.pdf",
  "page_count": 10,
  "chunks_created": 45,
  "status": "processed"
}
```

## 🧪 테스트

### 단위 테스트 (Node)

```python
# tests/unit/nodes/test_response_node.py
import pytest
from app.nodes.chat_process.response_node import response_node
from app.nodes.graph_state.schemas import ChatState

@pytest.mark.asyncio
async def test_response_node_success():
    """response_node가 정상적으로 응답을 생성하는지 테스트"""

    # Given: 테스트 상태
    state = ChatState(
        query="테스트 질문입니다",
        context="테스트 컨텍스트입니다",
        retrieved_docs=[
            {
                "content": "문서 내용",
                "metadata": {"filename": "test.pdf", "page": 1, "score": 0.9}
            }
        ],
        messages=[],
        response="",
        metadata={}
    )

    # When: 노드 실행
    result = await response_node(state)

    # Then: 검증
    assert "response" in result
    assert len(result["response"]) > 0
    assert "metadata" in result
    assert result["metadata"]["model"] == "gpt-oss-20b"
    assert result["metadata"]["tokens_used"] > 0
```

### Mock 서비스 사용

```python
# tests/conftest.py
import pytest
from app.services.interfaces.llm_interface import LLMInterface

class MockLLMService(LLMInterface):
    """테스트용 Mock LLM 서비스"""

    async def generate(self, **kwargs) -> str:
        return "모의 응답입니다"

    async def stream(self, **kwargs):
        yield "모의 "
        yield "스트리밍 "
        yield "응답"

    @property
    def last_token_count(self) -> int:
        return 100

@pytest.fixture
def mock_llm_service(monkeypatch):
    """LLM 서비스를 Mock으로 교체"""
    monkeypatch.setattr(
        "app.services.factory.get_llm_service",
        lambda: MockLLMService()
    )
```

### 통합 테스트 (Workflow)

```python
# tests/integration/test_workflow.py
import pytest
from app.main import app as langgraph_app
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
async def test_full_workflow():
    """전체 워크플로우 통합 테스트"""

    # Given: 초기 상태
    initial_state = {
        "messages": [HumanMessage(content="RAG란 무엇인가요?")],
        "query": "",
        "retrieved_docs": [],
        "context": "",
        "response": "",
        "metadata": {}
    }

    # When: 워크플로우 실행
    result = await langgraph_app.ainvoke(initial_state)

    # Then: 검증
    assert result["response"] != ""
    assert len(result["retrieved_docs"]) > 0
    assert result["context"] != ""
    assert result["metadata"]["tokens_used"] > 0
```

## 📊 성능 최적화

### 1. 비동기 처리

모든 I/O 작업을 비동기로 처리하여 동시성 확보:

```python
# ❌ 동기 방식 (블로킹)
def slow_node(state):
    result = requests.get("http://api.com")  # 블로킹
    return {"data": result.json()}

# ✅ 비동기 방식 (논블로킹)
async def fast_node(state):
    async with httpx.AsyncClient() as client:
        result = await client.get("http://api.com")  # 논블로킹
    return {"data": result.json()}
```

### 2. Connection Pooling

```python
# config/database_config.py
from qdrant_client import AsyncQdrantClient

# Qdrant 클라이언트 재사용
qdrant_client = AsyncQdrantClient(
    host="localhost",
    port=6333,
    timeout=60,  # 연결 타임아웃
    prefer_grpc=True  # gRPC 사용 (더 빠름)
)
```

### 3. 캐싱

```python
from functools import lru_cache
import hashlib

# 임베딩 캐싱 (같은 쿼리 반복 시 재사용)
_embedding_cache = {}

async def get_embedding_cached(text: str):
    cache_key = hashlib.md5(text.encode()).hexdigest()

    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]

    embedding = await embedding_service.embed(text)
    _embedding_cache[cache_key] = embedding

    return embedding
```

## 🔧 확장 가이드

### 새 노드 추가 (3단계)

**1단계: 노드 파일 생성**

```python
# app/nodes/custom/my_custom_node.py
from app.nodes.graph_state.schemas import ChatState
from app.utils.logger import logger

async def my_custom_node(state: ChatState) -> ChatState:
    """
    커스텀 비즈니스 로직을 수행하는 노드

    예: 쿼리 확장, 번역, 감정 분석 등
    """
    logger.info("Running custom node")

    query = state["query"]

    # 비즈니스 로직 구현
    expanded_query = await expand_query(query)

    return {
        "query": expanded_query,
        "metadata": {"query_expanded": True}
    }

async def expand_query(query: str) -> str:
    """쿼리 확장 로직"""
    # 예: 동의어 추가, 관련 키워드 추가
    return query + " (관련 키워드 포함)"
```

**2단계: 워크플로우에 노드 추가**

```python
# app/main.py
from app.nodes.custom.my_custom_node import my_custom_node

# 노드 추가
workflow.add_node("custom", my_custom_node)

# 엣지 연결 (user_input → custom → retrieval)
workflow.add_edge("user_input", "custom")
workflow.add_edge("custom", "retrieval")
```

**3단계: 테스트 작성**

```python
# tests/unit/nodes/test_my_custom_node.py
import pytest
from app.nodes.custom.my_custom_node import my_custom_node

@pytest.mark.asyncio
async def test_my_custom_node():
    state = {"query": "테스트"}
    result = await my_custom_node(state)
    assert result["metadata"]["query_expanded"] is True
```

### 새 서비스 추가 (4단계)

**1단계: 인터페이스 정의**

```python
# app/services/interfaces/translator_interface.py
from abc import ABC, abstractmethod

class TranslatorInterface(ABC):
    @abstractmethod
    async def translate(self, text: str, target_lang: str) -> str:
        pass
```

**2단계: 구현체 작성**

```python
# app/services/implementations/google_translator.py
from app.services.interfaces.translator_interface import TranslatorInterface

class GoogleTranslator(TranslatorInterface):
    async def translate(self, text: str, target_lang: str) -> str:
        # Google Translate API 호출
        return f"Translated: {text}"
```

**3단계: Factory에 등록**

```python
# app/services/factory.py
def get_translator_service() -> TranslatorInterface:
    return GoogleTranslator()
```

**4단계: 노드에서 사용**

```python
from app.services.factory import get_translator_service

async def translation_node(state: ChatState) -> ChatState:
    translator = get_translator_service()
    translated = await translator.translate(state["query"], "en")
    return {"query": translated}
```

## 📖 참고 자료

### LangGraph
- [LangGraph 공식 문서](https://python.langchain.com/docs/langgraph)
- [LangGraph 튜토리얼](https://langchain-ai.github.io/langgraph/tutorials/)
- [StateGraph API 레퍼런스](https://langchain-ai.github.io/langgraph/reference/graphs/)

### Clean Architecture
- [Clean Architecture (Uncle Bob)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Port-Adapter 패턴 (Hexagonal Architecture)](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/)

### 비동기 프로그래밍
- [Python asyncio 공식 문서](https://docs.python.org/3/library/asyncio.html)
- [Real Python - Async IO in Python](https://realpython.com/async-io-python/)

---

**이 문서는 `app/` 폴더의 LangGraph 애플리케이션을 이해하고 확장하는 데 필요한 모든 정보를 담고 있습니다.**
