# 🐳 Docker 설정

> 전체 시스템 컨테이너화 및 오케스트레이션

## 📋 개요

Docker Compose를 사용하여 모든 서비스(PostgreSQL, Qdrant, FastAPI, Django, Streamlit)를
컨테이너로 실행하고 통합 관리합니다. 개발 환경과 프로덕션 환경 모두 지원합니다.

## 📁 파일 구조

```
docker/
├── Dockerfile.api          # FastAPI (LangGraph API) 이미지
├── Dockerfile.django       # Django 백엔드 이미지
├── Dockerfile.frontend     # Streamlit 프론트엔드 이미지
├── docker-compose.yml      # 통합 오케스트레이션 설정
└── docker-compose.prod.yml # 프로덕션 설정 (선택)
```

## 🗂️ 서비스 구성

### 서비스 목록

| 서비스명 | 이미지 | 포트 | 역할 |
|----------|--------|------|------|
| **postgres** | postgres:15 | 5432 | PostgreSQL (사용자, 히스토리) |
| **qdrant** | qdrant/qdrant:latest | 6333, 6334 | Vector DB (문서 임베딩) |
| **api** | custom (Dockerfile.api) | 8000 | FastAPI (LangGraph 엔진) |
| **django** | custom (Dockerfile.django) | 8001 | Django 백엔드 |
| **frontend** | custom (Dockerfile.frontend) | 8501 | Streamlit UI |

### 네트워크 구성

```
┌────────────────────────────────────────┐
│  Docker Network: langgraph_network     │
│                                        │
│  ┌──────────┐  ┌──────────┐           │
│  │PostgreSQL│  │  Qdrant  │           │
│  │  :5432   │  │:6333/6334│           │
│  └────┬─────┘  └────┬─────┘           │
│       │             │                  │
│  ┌────▼─────────────▼─────┐           │
│  │      FastAPI (API)      │           │
│  │         :8000           │           │
│  └────┬────────────────────┘           │
│       │                                │
│  ┌────▼──────────┐  ┌────────────┐    │
│  │    Django     │  │ Streamlit  │    │
│  │     :8001     │  │   :8501    │    │
│  └───────────────┘  └────────────┘    │
└────────────────────────────────────────┘
```

## 🚀 실행 방법

### 1. 환경변수 설정

```bash
# 루트 디렉토리에서
cp .env.example .env

# .env 파일 편집
nano .env
```

**.env 파일**:
```bash
# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-oss-20b
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=chatbot
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_secure_password_here

# Django
DJANGO_SECRET_KEY=your-django-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Encryption
ENCRYPTION_KEY=your-fernet-key-here
```

### 2. Docker Compose 실행

```bash
cd docker

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만
docker-compose logs -f api
```

### 3. 데이터베이스 마이그레이션

```bash
# Django 마이그레이션
docker-compose exec django python manage.py migrate

# 슈퍼유저 생성
docker-compose exec django python manage.py createsuperuser
```

### 4. 서비스 접속

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **Django Admin**: http://localhost:8001/admin
- **Qdrant Dashboard**: http://localhost:6334

### 5. 중지 및 삭제

```bash
# 중지
docker-compose stop

# 중지 및 컨테이너 삭제
docker-compose down

# 볼륨까지 완전 삭제
docker-compose down -v
```

## 📦 docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15
    container_name: langgraph_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - langgraph_network

  # Qdrant Vector DB
  qdrant:
    image: qdrant/qdrant:latest
    container_name: langgraph_qdrant
    ports:
      - "6333:6333"  # API
      - "6334:6334"  # Dashboard
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - langgraph_network

  # FastAPI (LangGraph API)
  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    container_name: langgraph_api
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL}
      - OPENAI_EMBEDDING_MODEL=${OPENAI_EMBEDDING_MODEL}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_started
    command: uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    networks:
      - langgraph_network
    restart: unless-stopped

  # Django Backend
  django:
    build:
      context: ..
      dockerfile: docker/Dockerfile.django
    container_name: langgraph_django
    ports:
      - "8001:8001"
    environment:
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS}
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 4"
    networks:
      - langgraph_network
    restart: unless-stopped

  # Streamlit Frontend
  frontend:
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
    container_name: langgraph_frontend
    ports:
      - "8501:8501"
    environment:
      - FASTAPI_URL=http://api:8000
      - DJANGO_URL=http://django:8001
    depends_on:
      - api
      - django
    command: streamlit run main.py --server.port 8501 --server.address 0.0.0.0
    networks:
      - langgraph_network
    restart: unless-stopped

volumes:
  postgres_data:
  qdrant_data:

networks:
  langgraph_network:
    driver: bridge
```

## 🏗️ Dockerfile 예시

### Dockerfile.api (FastAPI)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY app/ ./app/
COPY config/ ./config/

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Dockerfile.django (Django)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY backend/ .

# 정적 파일 디렉토리 생성
RUN mkdir -p staticfiles

# 포트 노출
EXPOSE 8001

# 실행 (docker-compose에서 command로 override)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "4"]
```

### Dockerfile.frontend (Streamlit)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 복사
COPY frontend/ .

# Streamlit 설정 복사
COPY frontend/.streamlit /app/.streamlit

# 포트 노출
EXPOSE 8501

# 실행
CMD ["streamlit", "run", "main.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

## 🔧 트러블슈팅

### 1. Qdrant 연결 실패

**문제**: `Connection refused to qdrant:6333`

**해결책**:
```bash
# Qdrant 상태 확인
docker-compose logs qdrant

# Qdrant 재시작
docker-compose restart qdrant

# 헬스체크 확인
curl http://localhost:6333/healthz
```

### 2. PostgreSQL 마이그레이션 실패

**문제**: `django.db.utils.OperationalError: FATAL: database "chatbot" does not exist`

**해결책**:
```bash
# PostgreSQL 컨테이너 접속
docker-compose exec postgres psql -U admin

# 데이터베이스 생성
CREATE DATABASE chatbot;
\q

# 마이그레이션 재실행
docker-compose exec django python manage.py migrate
```

### 3. API 서버 느림

**문제**: 응답 시간이 너무 오래 걸림

**해결책**:
```yaml
# docker-compose.yml에서 workers 수 증가
api:
  command: uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 8

django:
  command: gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 8
```

### 4. 볼륨 데이터 초기화

**문제**: 데이터베이스를 완전히 초기화하고 싶음

**해결책**:
```bash
# 모든 컨테이너 및 볼륨 삭제
docker-compose down -v

# 이미지 재빌드
docker-compose build --no-cache

# 다시 시작
docker-compose up -d
```

## 📊 리소스 모니터링

### 컨테이너 리소스 사용량

```bash
# 실시간 모니터링
docker stats

# 특정 컨테이너만
docker stats langgraph_api langgraph_django
```

### 로그 관리

```bash
# 최근 100줄
docker-compose logs --tail=100

# 실시간 로그 (모든 서비스)
docker-compose logs -f

# 특정 서비스만
docker-compose logs -f api

# 타임스탬프 포함
docker-compose logs -f -t api
```

### 디스크 사용량

```bash
# 볼륨 사용량 확인
docker volume ls
docker volume inspect langgraph_postgres_data

# 사용하지 않는 리소스 정리
docker system prune -a --volumes
```

## 🔐 보안 설정

### 1. Secrets 관리 (프로덕션)

```yaml
# docker-compose.prod.yml
version: '3.8'

secrets:
  openai_key:
    file: ./secrets/openai_key.txt
  postgres_password:
    file: ./secrets/postgres_password.txt
  django_secret:
    file: ./secrets/django_secret.txt

services:
  api:
    secrets:
      - openai_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_key
```

### 2. 네트워크 격리

```yaml
networks:
  frontend:  # Streamlit만 외부 접근 가능
    driver: bridge
  backend:   # API, Django, DB는 내부 네트워크
    driver: bridge
    internal: true
```

### 3. 읽기 전용 컨테이너

```yaml
api:
  read_only: true
  tmpfs:
    - /tmp
    - /var/cache
```

## 📖 참고 자료

- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Qdrant Docker](https://qdrant.tech/documentation/quick-start/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)

---

**Docker Compose로 전체 시스템을 간편하게 배포하고 관리하세요.**
