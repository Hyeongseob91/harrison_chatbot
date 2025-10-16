# ⚙️ 환경 설정

> 애플리케이션 전역 설정 및 환경변수 관리

## 📋 개요

이 폴더는 LangGraph RAG Chatbot의 모든 설정을 중앙에서 관리합니다.
Pydantic Settings를 사용하여 환경변수를 타입 안전하게 로드하고,
LLM, Embedding, 데이터베이스 연결 설정을 제공합니다.

## 📁 파일 구조

```
config/
├── __init__.py
├── settings.py         # Pydantic Settings (환경변수 통합 관리)
├── llm_config.py       # LLM 설정 (OpenAI GPT-OSS-20B)
├── embedding_config.py # Embedding 설정 (text-embedding-3-large)
└── database_config.py  # DB 연결 설정 (PostgreSQL, Qdrant)
```

## 🔧 주요 설정 파일

### 1. settings.py (환경변수 통합 관리)

**역할**: `.env` 파일에서 환경변수를 로드하고 검증

```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    애플리케이션 전역 설정

    .env 파일에서 환경변수를 자동으로 로드
    """

    # OpenAI 설정
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-oss-20b"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Qdrant 설정
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "documents"

    # PostgreSQL 설정
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "chatbot"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str

    # Django 설정
    DJANGO_SECRET_KEY: str
    DJANGO_DEBUG: bool = False
    DJANGO_ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    # 암호화 키 (Fernet)
    ENCRYPTION_KEY: str

    # FastAPI 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = False


# 싱글톤 인스턴스
settings = Settings()
```

**사용 예시**:
```python
from config.settings import settings

print(settings.OPENAI_API_KEY)
print(settings.QDRANT_HOST)
```

### 2. llm_config.py (LLM 설정)

**역할**: OpenAI GPT 모델 설정 및 프롬프트 템플릿

```python
# config/llm_config.py
from config.settings import settings

class LLMConfig:
    """LLM (OpenAI GPT-OSS-20B) 설정"""

    MODEL_NAME = settings.OPENAI_MODEL
    API_KEY = settings.OPENAI_API_KEY

    # 생성 파라미터
    TEMPERATURE = 0.7
    MAX_TOKENS = 1000
    TOP_P = 0.9
    FREQUENCY_PENALTY = 0.0
    PRESENCE_PENALTY = 0.0

    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 문서 기반 질의응답 AI 어시스턴트입니다.

주어진 Context를 참고하여 사용자의 질문에 정확하고 상세하게 답변하세요.

규칙:
1. Context에 있는 정보만을 기반으로 답변하세요
2. Context에 없는 내용은 추측하지 말고 "제공된 문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요
3. 답변은 명확하고 이해하기 쉽게 작성하세요
4. 가능한 경우 구체적인 예시나 수치를 포함하세요
5. 답변은 한국어로 작성하세요
"""

    @classmethod
    def get_user_prompt_template(cls) -> str:
        """사용자 프롬프트 템플릿"""
        return """Context:
{context}

Question: {query}

Answer:"""


llm_config = LLMConfig()
```

**사용 예시**:
```python
from config.llm_config import llm_config

print(llm_config.MODEL_NAME)
print(llm_config.SYSTEM_PROMPT)
```

### 3. embedding_config.py (Embedding 설정)

**역할**: OpenAI Embedding 모델 설정

```python
# config/embedding_config.py
from config.settings import settings

class EmbeddingConfig:
    """Embedding (OpenAI text-embedding-3-large) 설정"""

    MODEL_NAME = settings.OPENAI_EMBEDDING_MODEL
    API_KEY = settings.OPENAI_API_KEY

    # 임베딩 차원 (text-embedding-3-large)
    EMBEDDING_DIM = 3072

    # 배치 크기
    BATCH_SIZE = 100

    # 청크 설정
    CHUNK_SIZE = 500  # 문자 수
    CHUNK_OVERLAP = 50  # 오버랩


embedding_config = EmbeddingConfig()
```

### 4. database_config.py (데이터베이스 연결)

**역할**: PostgreSQL 및 Qdrant 연결 설정

```python
# config/database_config.py
from config.settings import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from qdrant_client import AsyncQdrantClient

# PostgreSQL 비동기 엔진
postgres_url = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

async_engine = create_async_engine(
    postgres_url,
    echo=False,
    pool_size=20,           # 커넥션 풀 크기
    max_overflow=10,        # 초과 연결 허용
    pool_pre_ping=True,     # 연결 상태 체크
    pool_recycle=3600       # 1시간마다 연결 재생성
)

# 비동기 세션 팩토리
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Qdrant 비동기 클라이언트
qdrant_client = AsyncQdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
    timeout=60,
    prefer_grpc=True  # gRPC 사용 (더 빠름)
)


# 의존성 주입용 함수
async def get_db_session():
    """PostgreSQL 세션 가져오기"""
    async with AsyncSessionLocal() as session:
        yield session


def get_qdrant_client():
    """Qdrant 클라이언트 가져오기"""
    return qdrant_client
```

**사용 예시**:
```python
from config.database_config import get_qdrant_client, get_db_session

# Qdrant 사용
qdrant = get_qdrant_client()
results = await qdrant.search(...)

# PostgreSQL 사용 (FastAPI dependency)
async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
    ...
```

## 🔐 환경변수 설정

### .env 파일 구조

프로젝트 루트에 `.env` 파일을 생성:

```bash
# .env

# ============================================
# OpenAI 설정
# ============================================
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-oss-20b
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# ============================================
# Qdrant 설정
# ============================================
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

# ============================================
# PostgreSQL 설정
# ============================================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_secure_password_here

# ============================================
# Django 설정
# ============================================
DJANGO_SECRET_KEY=your-django-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# ============================================
# 암호화 키 (Fernet)
# ============================================
ENCRYPTION_KEY=your-fernet-key-here

# ============================================
# FastAPI 설정
# ============================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
```

### 환경별 설정 파일

**개발 환경**: `.env.development`
```bash
DJANGO_DEBUG=True
QDRANT_HOST=localhost
POSTGRES_HOST=localhost
```

**프로덕션 환경**: `.env.production`
```bash
DJANGO_DEBUG=False
QDRANT_HOST=qdrant
POSTGRES_HOST=postgres
```

**사용법**:
```python
# config/settings.py
class Settings(BaseSettings):
    class Config:
        env_file = ".env.production"  # 환경별로 변경
```

## 🔑 비밀 키 생성

### Django Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Fernet Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## ✅ 설정 검증

### 설정 값 확인 스크립트

```python
# scripts/check_config.py
from config.settings import settings

def check_config():
    """설정 값 검증"""
    print("=== Configuration Check ===")

    # OpenAI
    assert settings.OPENAI_API_KEY.startswith("sk-"), "Invalid OpenAI API Key"
    print(f"✅ OpenAI Model: {settings.OPENAI_MODEL}")

    # Qdrant
    print(f"✅ Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

    # PostgreSQL
    print(f"✅ PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    # Encryption
    from cryptography.fernet import Fernet
    try:
        Fernet(settings.ENCRYPTION_KEY.encode())
        print("✅ Encryption Key: Valid")
    except Exception:
        print("❌ Encryption Key: Invalid")

    print("\n=== All checks passed ===")


if __name__ == "__main__":
    check_config()
```

**실행**:
```bash
python scripts/check_config.py
```

## 📖 참고 자료

- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/)
- [Python Dotenv](https://github.com/theskumar/python-dotenv)
- [12 Factor App](https://12factor.net/config)

---

**설정을 중앙에서 관리하여 유지보수성과 보안성을 높이세요.**
