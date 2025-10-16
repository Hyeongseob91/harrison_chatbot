# 🤖 LangGraph RAG Chatbot

> LangGraph 프레임워크 기반의 문서 검색형 AI 챗봇 시스템

## 📋 프로젝트 개요

이 프로젝트는 RAG(Retrieval-Augmented Generation) 기술을 활용한 문서 기반 질의응답 시스템입니다.
LangGraph를 사용하여 복잡한 워크플로우를 관리하고, 향후 Supervisor Agent 도입을 통해 멀티 에이전트 시스템으로 확장할 예정입니다.

### 주요 기능

- ✅ **문서 기반 RAG**: Vector DB를 활용한 정확한 문서 검색
- ✅ **비동기 처리**: FastAPI + LangGraph 비동기 노드로 동시 사용자 지원
- ✅ **Clean Architecture**: Domain-Application-Infrastructure 계층 분리
- ✅ **OpenAI 통합**: GPT-OSS-20B + text-embedding-3-large
- ✅ **사용자 관리**: Django 기반 인증 및 채팅 히스토리 저장
- ✅ **실시간 스트리밍**: SSE를 통한 실시간 응답
- 🔜 **Supervisor Agent**: 멀티 에이전트 의사결정 시스템
- 🔜 **MCP Server**: Claude Desktop 통합

## 🏗️ 아키텍처

### 전체 시스템 구조

```
┌─────────────┐
│  Streamlit  │ (Frontend)
│   UI/UX     │
└──────┬──────┘
       │ HTTP
┌──────▼──────────────────────┐
│   FastAPI (LangGraph API)   │
│  ┌────────────────────────┐ │
│  │   LangGraph Workflow   │ │
│  │  ┌──────────────────┐  │ │
│  │  │  user_input_node │  │ │
│  │  └────────┬─────────┘  │ │
│  │  ┌────────▼─────────┐  │ │
│  │  │ retrieval_node   │←─┼─┼─→ Qdrant (Vector DB)
│  │  └────────┬─────────┘  │ │
│  │  ┌────────▼─────────┐  │ │
│  │  │ reranking_node   │  │ │
│  │  └────────┬─────────┘  │ │
│  │  ┌────────▼─────────┐  │ │
│  │  │ synthesis_node   │  │ │
│  │  └────────┬─────────┘  │ │
│  │  ┌────────▼─────────┐  │ │
│  │  │ response_node    │←─┼─┼─→ OpenAI GPT
│  │  │  (LLM 답변 생성) │  │ │
│  │  └────────┬─────────┘  │ │
│  │  ┌────────▼─────────┐  │ │
│  │  │  history_node    │  │ │
│  │  └──────────────────┘  │ │
│  └────────────────────────┘ │
└──────┬──────────────────────┘
       │ HTTP
┌──────▼──────────┐
│  Django Backend │
│  (User, History)│
└──────┬──────────┘
       │
┌──────▼──────────┐
│   PostgreSQL    │
└─────────────────┘
```

### 기술 스택

**AI/ML**
- **LangGraph**: 워크플로우 오케스트레이션
- **LangChain**: LLM 추상화
- **OpenAI GPT-OSS-20B**: 답변 생성
- **OpenAI text-embedding-3-large**: 문서 임베딩

**Backend**
- **FastAPI**: LangGraph API 서버 (비동기)
- **Django + DRF**: 사용자 및 히스토리 관리
- **PostgreSQL**: 관계형 데이터베이스
- **Qdrant**: Vector 데이터베이스

**Frontend**
- **Streamlit**: 프로토타입 채팅 인터페이스

**Infrastructure**
- **Docker Compose**: 컨테이너 오케스트레이션
- **Uvicorn**: ASGI 서버 (workers=4)

## 📁 폴더 구조

```
langgraph_chatbot/
├── app/              # LangGraph 애플리케이션 (핵심 AI 엔진)
│   ├── main.py       # LangGraph 워크플로우 초기화
│   ├── domain/       # 도메인 계층 (엔티티, 값 객체)
│   ├── nodes/        # LangGraph 노드 (비동기)
│   ├── services/     # 서비스 계층 (Port-Adapter 패턴)
│   ├── utils/        # 유틸리티 (로깅, 파싱, 검증)
│   └── api/          # FastAPI 서버
│
├── backend/          # Django 백엔드
│   ├── users/        # 사용자 관리
│   ├── chat_history/ # 채팅 히스토리
│   └── documents/    # 문서 메타데이터
│
├── frontend/         # Streamlit UI
│   ├── main.py       # 채팅 인터페이스
│   ├── components/   # UI 컴포넌트
│   └── utils/        # API 클라이언트
│
├── config/           # 설정 파일
│   ├── settings.py   # 환경변수 관리
│   ├── llm_config.py # LLM 설정
│   └── database_config.py # DB 연결
│
├── docker/           # Docker 설정
│   ├── Dockerfile.api
│   ├── Dockerfile.django
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
├── mcp/              # MCP Server (향후)
├── tests/            # 테스트 코드
└── README.md         # 이 문서
```

각 폴더의 상세 설명은 해당 폴더의 README.md를 참고하세요:
- [LangGraph 애플리케이션 가이드](./app/README.md)
- [Django 백엔드 가이드](./backend/README.md)
- [Streamlit 프론트엔드 가이드](./frontend/README.md)
- [Docker 배포 가이드](./docker/README.md)
- [환경 설정 가이드](./config/README.md)
- [테스트 가이드](./tests/README.md)

## 🚀 Quick Start

### 1. 사전 요구사항

- Python 3.11+
- Docker & Docker Compose
- OpenAI API Key

### 2. 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/langgraph_chatbot.git
cd langgraph_chatbot

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 입력

# 3. Docker 서비스 시작
cd docker
docker-compose up -d

# 4. 데이터베이스 마이그레이션
docker-compose exec django python manage.py migrate

# 5. 애플리케이션 접속
# - Streamlit UI: http://localhost:8501
# - FastAPI Docs: http://localhost:8000/docs
# - Django Admin: http://localhost:8001/admin
# - Qdrant Dashboard: http://localhost:6334
```

### 3. 문서 업로드 및 채팅

1. **Streamlit UI** (http://localhost:8501) 접속
2. 사이드바에서 **OpenAI API Key** 입력
3. **문서 업로드** (PDF, TXT 지원)
4. 채팅창에 **질문 입력**

## 📖 상세 문서

### 개발 가이드
- [LangGraph 워크플로우 가이드](./app/README.md) - 노드 추가, 서비스 확장
- [Django 백엔드 API](./backend/README.md) - 모델, API 엔드포인트
- [Streamlit 프론트엔드](./frontend/README.md) - UI 컴포넌트, API 연동
- [환경 설정](./config/README.md) - 환경변수, LLM 설정
- [테스트 가이드](./tests/README.md) - 단위/통합 테스트

### 배포 가이드
- [Docker 배포 가이드](./docker/README.md) - 컨테이너 오케스트레이션

## 🔧 개발 가이드

### 새 노드 추가

```python
# app/nodes/custom/my_node.py
from app.nodes.graph_state.schemas import ChatState

async def my_custom_node(state: ChatState) -> ChatState:
    """커스텀 노드 예시"""
    # 비즈니스 로직 구현
    result = await some_async_operation(state["query"])

    return {"custom_field": result}
```

워크플로우에 추가:
```python
# app/main.py
from app.nodes.custom.my_node import my_custom_node

workflow.add_node("my_node", my_custom_node)
workflow.add_edge("retrieval", "my_node")
workflow.add_edge("my_node", "synthesis")
```

### 새 서비스 추가

1. **인터페이스 정의**
```python
# app/services/interfaces/my_interface.py
from abc import ABC, abstractmethod

class MyServiceInterface(ABC):
    @abstractmethod
    async def do_something(self, input: str) -> str:
        pass
```

2. **구현체 작성**
```python
# app/services/implementations/my_service.py
class MyService(MyServiceInterface):
    async def do_something(self, input: str) -> str:
        # 실제 구현
        return f"Processed: {input}"
```

3. **Factory에 등록**
```python
# app/services/factory.py
def get_my_service() -> MyServiceInterface:
    return MyService()
```

## 🧪 테스트

```bash
# 모든 테스트 실행
pytest

# 단위 테스트만
pytest tests/unit

# 통합 테스트만
pytest tests/integration

# 커버리지 리포트
pytest --cov=app --cov-report=html tests/
```

## 📊 성능

- **동시 사용자**: FastAPI workers=4로 100+ 동시 요청 처리 가능
- **응답 시간**: 평균 2-3초 (문서 검색 + LLM 생성 포함)
- **Vector 검색**: Qdrant HNSW 알고리즘으로 밀리초 단위 검색
- **처리량**: 분당 200+ 쿼리 처리 (4 workers 기준)

## 🗺️ 로드맵

### Phase 1: 기본 RAG 파이프라인 ✅
- [x] LangGraph 워크플로우 구축
- [x] Qdrant Vector 검색
- [x] OpenAI LLM 통합
- [x] Streamlit UI

### Phase 2: 프로덕션 준비 ✅
- [x] 비동기 처리 및 동시 사용자 지원
- [x] Django 백엔드 (사용자, 히스토리)
- [x] Docker Compose 배포
- [x] Clean Architecture 적용

### Phase 3: 고급 기능 🔜
- [ ] Supervisor Agent (멀티 에이전트 라우팅)
- [ ] Reranking 모델 통합
- [ ] 대화 컨텍스트 관리
- [ ] 문서 청크 최적화

### Phase 4: 엔터프라이즈 기능 🔜
- [ ] MCP Server 구현 (Claude Desktop 통합)
- [ ] 프로덕션 배포 (AWS/GCP)
- [ ] 모니터링 및 로깅 (Prometheus, Grafana)
- [ ] A/B 테스팅 프레임워크

## 🤝 기여

이슈 및 PR 환영합니다!

### 기여 가이드

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### 코드 스타일

- Python: Black, isort, flake8
- Commit Message: Conventional Commits 형식

## 📄 라이선스

MIT License

## 📧 문의

프로젝트 관련 문의사항은 이슈를 등록해주세요.

---

**Built with ❤️ using LangGraph, FastAPI, and Django**