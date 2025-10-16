# 🧪 테스트

> 단위 테스트 및 통합 테스트 가이드

## 📋 개요

pytest를 사용한 포괄적인 테스트 스위트입니다.
단위 테스트(Unit Tests), 통합 테스트(Integration Tests), E2E 테스트를 포함하며,
Mock 객체를 사용하여 외부 의존성을 격리합니다.

## 📁 폴더 구조

```
tests/
├── __init__.py
├── conftest.py             # pytest fixtures 및 설정
│
├── unit/                   # 단위 테스트 (빠름, 격리)
│   ├── __init__.py
│   ├── test_nodes/         # 노드 테스트
│   │   ├── test_user_input_node.py
│   │   ├── test_retrieval_node.py
│   │   ├── test_response_node.py
│   │   └── test_synthesis_node.py
│   ├── test_services/      # 서비스 테스트
│   │   ├── test_llm_service.py
│   │   ├── test_embedding_service.py
│   │   └── test_qdrant_service.py
│   └── test_utils/         # 유틸리티 테스트
│       ├── test_logger.py
│       └── test_validators.py
│
├── integration/            # 통합 테스트 (느림, 실제 서비스 사용)
│   ├── __init__.py
│   ├── test_workflow.py    # 전체 LangGraph 워크플로우
│   ├── test_api.py         # FastAPI 엔드포인트
│   └── test_django_api.py  # Django API
│
└── e2e/                    # End-to-End 테스트
    ├── __init__.py
    └── test_full_flow.py   # 전체 시스템 플로우
```

## 🚀 테스트 실행

### 의존성 설치

```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 전체 테스트 실행

```bash
# 모든 테스트
pytest

# verbose 모드
pytest -v

# 실패 시 즉시 중단
pytest -x
```

### 특정 테스트만 실행

```bash
# 단위 테스트만
pytest tests/unit

# 통합 테스트만
pytest tests/integration

# 특정 파일
pytest tests/unit/test_nodes/test_response_node.py

# 특정 테스트 함수
pytest tests/unit/test_nodes/test_response_node.py::test_response_node_success
```

### 커버리지 리포트

```bash
# 커버리지와 함께 테스트
pytest --cov=app tests/

# HTML 리포트 생성
pytest --cov=app --cov-report=html tests/

# htmlcov/index.html 열기
open htmlcov/index.html
```

### 마커 사용

```bash
# 느린 테스트 제외
pytest -m "not slow"

# 비동기 테스트만
pytest -m "asyncio"
```

## 🛠️ conftest.py (Fixtures)

```python
# tests/conftest.py
import pytest
import asyncio
from typing import Generator
from app.services.interfaces.llm_interface import LLMInterface
from app.services.interfaces.embedding_interface import EmbeddingInterface
from app.services.interfaces.vector_store_interface import VectorStoreInterface

# ==== Event Loop Fixture (비동기 테스트용) ====

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 생성"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==== Mock Services ====

class MockLLMService(LLMInterface):
    """테스트용 Mock LLM 서비스"""

    async def generate(self, **kwargs) -> str:
        return "모의 LLM 응답입니다"

    async def stream(self, **kwargs):
        for chunk in ["모의 ", "스트리밍 ", "응답"]:
            yield chunk

    @property
    def last_token_count(self) -> int:
        return 100


class MockEmbeddingService(EmbeddingInterface):
    """테스트용 Mock Embedding 서비스"""

    async def embed(self, text: str) -> list[float]:
        # 고정된 벡터 반환
        return [0.1] * 1536


class MockVectorStore(VectorStoreInterface):
    """테스트용 Mock Vector Store"""

    async def search(self, **kwargs) -> list[dict]:
        return [
            {
                "content": "테스트 문서 내용",
                "metadata": {
                    "filename": "test.pdf",
                    "page": 1,
                    "score": 0.9
                }
            }
        ]


# ==== Fixtures ====

@pytest.fixture
def mock_llm_service(monkeypatch):
    """LLM 서비스를 Mock으로 교체"""
    monkeypatch.setattr(
        "app.services.factory.get_llm_service",
        lambda: MockLLMService()
    )


@pytest.fixture
def mock_embedding_service(monkeypatch):
    """Embedding 서비스를 Mock으로 교체"""
    monkeypatch.setattr(
        "app.services.factory.get_embedding_service",
        lambda: MockEmbeddingService()
    )


@pytest.fixture
def mock_vector_store(monkeypatch):
    """Vector Store를 Mock으로 교체"""
    monkeypatch.setattr(
        "app.services.factory.get_vector_store",
        lambda: MockVectorStore()
    )


@pytest.fixture
def sample_chat_state():
    """샘플 ChatState"""
    return {
        "messages": [],
        "query": "테스트 질문",
        "retrieved_docs": [],
        "context": "",
        "response": "",
        "metadata": {}
    }
```

## 🔬 단위 테스트 예시

### 노드 테스트

```python
# tests/unit/test_nodes/test_response_node.py
import pytest
from app.nodes.chat_process.response_node import response_node
from app.nodes.graph_state.schemas import ChatState

@pytest.mark.asyncio
async def test_response_node_success(mock_llm_service, sample_chat_state):
    """response_node가 정상적으로 응답을 생성하는지 테스트"""

    # Given: 테스트 상태
    state = ChatState(
        **sample_chat_state,
        context="테스트 컨텍스트",
        retrieved_docs=[
            {
                "content": "문서 내용",
                "metadata": {"filename": "test.pdf", "page": 1, "score": 0.9}
            }
        ]
    )

    # When: 노드 실행
    result = await response_node(state)

    # Then: 검증
    assert "response" in result
    assert len(result["response"]) > 0
    assert "metadata" in result
    assert "tokens_used" in result["metadata"]


@pytest.mark.asyncio
async def test_response_node_empty_context(mock_llm_service, sample_chat_state):
    """빈 컨텍스트 처리 테스트"""

    state = ChatState(**sample_chat_state, context="", retrieved_docs=[])

    result = await response_node(state)

    # 빈 컨텍스트여도 응답 생성
    assert "response" in result
```

### 서비스 테스트

```python
# tests/unit/test_services/test_llm_service.py
import pytest
from app.services.implementations.openai_llm_service import OpenAILLMService

@pytest.mark.asyncio
async def test_llm_service_generate():
    """LLM 서비스 generate 메서드 테스트"""

    # Mock API Key로 초기화
    service = OpenAILLMService(api_key="test-key")

    # API 호출 Mock (실제 호출 방지)
    # pytest-mock 사용
    ...


@pytest.mark.asyncio
async def test_llm_service_stream():
    """LLM 서비스 stream 메서드 테스트"""
    ...
```

## 🔗 통합 테스트 예시

### 워크플로우 테스트

```python
# tests/integration/test_workflow.py
import pytest
from app.main import app as langgraph_app
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_workflow():
    """전체 LangGraph 워크플로우 통합 테스트"""

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
    assert "tokens_used" in result["metadata"]
```

### API 테스트

```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_chat_invoke_endpoint():
    """채팅 invoke 엔드포인트 테스트"""

    response = client.post(
        "/chat/invoke",
        json={"query": "테스트 질문", "session_id": "test123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "metadata" in data


def test_document_upload_endpoint():
    """문서 업로드 엔드포인트 테스트"""

    with open("tests/fixtures/sample.pdf", "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("sample.pdf", f, "application/pdf")}
        )

    assert response.status_code == 201
    data = response.json()
    assert "document_id" in data
```

## 🎭 Mock 패턴

### 외부 API Mock

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mocked_openai():
    """OpenAI API를 Mock으로 테스트"""

    with patch("openai.AsyncOpenAI") as MockOpenAI:
        # Mock 설정
        mock_instance = MockOpenAI.return_value
        mock_instance.chat.completions.create = AsyncMock(
            return_value={
                "choices": [{"message": {"content": "모의 응답"}}],
                "usage": {"total_tokens": 100}
            }
        )

        # 테스트 실행
        ...
```

### 데이터베이스 Mock

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

@pytest.fixture
def test_db():
    """테스트용 인메모리 DB"""
    engine = create_engine("sqlite:///:memory:")
    # 테이블 생성
    Base.metadata.create_all(engine)

    session = Session(engine)
    yield session

    session.close()
```

## 📊 테스트 커버리지 목표

| 레이어 | 커버리지 목표 |
|--------|--------------|
| Domain | 100% |
| Nodes | 90%+ |
| Services | 85%+ |
| API | 80%+ |
| Utils | 95%+ |

## 📖 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

---

**철저한 테스트로 안정적인 시스템을 구축하세요.**
