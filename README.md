# Document Analysis Chatbot System

LangGraph와 ChromaDB를 활용한 전문 분야 문서 분석 RAG 챗봇 시스템입니다.

## 🏗️ 시스템 아키텍처

```
Frontend (Streamlit) ←→ Backend (FastAPI) ←→ Vector DB (ChromaDB)
                              ↓
                         PostgreSQL + Redis
                              ↓
                         LLM Service (GPT-OSS)
```

## 🎯 주요 기능

### 🔍 문서 분석
- **멀티 포맷 지원**: PDF, TXT, DOCX, XLSX 파일 처리
- **도메인별 분석**: 법률, 의료, 금융, 기술, 일반 분야
- **자동 청킹**: 문서를 의미 단위로 분할하여 벡터화

### 💬 RAG 기반 채팅
- **컨텍스트 기반 답변**: 업로드된 문서를 기반으로 정확한 답변 제공
- **소스 추적**: 답변의 근거가 된 문서 부분 표시
- **채팅 히스토리**: 이전 대화 내용을 고려한 연속적인 대화

### 🖥️ 직관적인 UI
- **실시간 채팅**: Streamlit 기반의 반응형 채팅 인터페이스
- **문서 관리**: 업로드, 삭제, 상태 확인
- **추천 질문**: 도메인별 맞춤 질문 제안

## 🛠️ 기술 스택

### Backend
- **FastAPI**: 고성능 API 서버
- **SQLAlchemy**: PostgreSQL ORM
- **ChromaDB**: 벡터 데이터베이스
- **LangGraph**: LLM 워크플로우 관리
- **Sentence Transformers**: 임베딩 모델

### Frontend
- **Streamlit**: 웹 UI 프레임워크
- **Requests**: HTTP 클라이언트

### Infrastructure
- **Docker Compose**: 컨테이너 오케스트레이션
- **PostgreSQL**: 메타데이터 저장
- **Redis**: 캐싱 및 세션 관리

## 🚀 설치 및 실행

### 1. 사전 요구사항
```bash
# Docker와 Docker Compose 설치 필요
docker --version
docker-compose --version

# Python 3.11+ 설치 필요
python --version
```

### 2. 프로젝트 설정
```bash
# 저장소 클론
git clone <repository-url>
cd langgraph_chatbot

# 환경변수 설정
cp .env.example .env
# .env 파일에서 GPT-OSS API 설정을 수정하세요
```

### 3. 의존성 설치
```bash
# Backend 의존성
cd backend
pip install -r requirements.txt
cd ..

# Frontend 의존성
cd frontend
pip install -r requirements.txt
cd ..
```

### 4. 시스템 시작
```bash
# 원클릭 실행
./start.sh

# 또는 수동 실행
docker-compose up -d
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8001 &
cd frontend && streamlit run main.py --server.port 8501 &
```

### 5. 접속
- **프론트엔드**: http://localhost:8501
- **API 문서**: http://localhost:8001/docs
- **헬스체크**: http://localhost:8001/health

## 📁 프로젝트 구조

```
langgraph_chatbot/
├── backend/                 # FastAPI 백엔드
│   ├── api/                # API 라우터
│   │   ├── chat.py        # 채팅 API
│   │   ├── documents.py   # 문서 관리 API
│   │   └── sessions.py    # 세션 관리 API
│   ├── services/          # 비즈니스 로직
│   │   ├── vector_service.py    # 벡터 DB 서비스
│   │   ├── document_service.py  # 문서 처리 서비스
│   │   └── llm_service.py       # LLM 서비스
│   ├── main.py           # FastAPI 앱
│   ├── database.py       # DB 모델 및 설정
│   ├── models.py         # Pydantic 모델
│   └── config.py         # 설정 관리
├── frontend/             # Streamlit 프론트엔드
│   └── main.py          # Streamlit 앱
├── docker-compose.yml   # Docker 구성
├── init.sql            # DB 초기화 스크립트
├── start.sh            # 실행 스크립트
└── .env               # 환경변수
```

## 🔧 설정 가이드

### GPT-OSS 모델 설정
`.env` 파일에서 다음 항목을 수정하세요:

```env
OPENAI_API_KEY=your-gpt-oss-api-key
OPENAI_API_BASE=http://your-gpt-oss-endpoint/v1
MODEL_NAME=your-model-name
```

### 도메인별 설정
```env
ANALYSIS_DOMAINS=["legal", "medical", "financial", "technical", "general"]
DEFAULT_DOMAIN=general
```

## 📊 API 엔드포인트

### 채팅 API
- `POST /api/chat/` - 메시지 전송
- `POST /api/chat/analyze` - 문서 분석
- `GET /api/chat/search` - 문서 검색
- `GET /api/chat/suggestions` - 추천 질문

### 문서 API
- `POST /api/documents/upload` - 문서 업로드
- `GET /api/documents/` - 문서 목록
- `DELETE /api/documents/{id}` - 문서 삭제

### 세션 API
- `POST /api/sessions/` - 세션 생성
- `GET /api/sessions/` - 세션 목록
- `GET /api/sessions/{id}/messages` - 메시지 히스토리

## 🎨 사용 예시

### 1. 문서 업로드
1. 사이드바에서 분석 분야 선택
2. 지원되는 파일 형식 업로드
3. 자동으로 처리 및 벡터화 완료

### 2. 질문하기
```
사용자: "이 계약서의 주요 리스크 요인은 무엇인가요?"
챗봇: "업로드하신 계약서를 분석한 결과, 다음과 같은 주요 리스크 요인들을 발견했습니다..."
```

### 3. 도메인별 활용
- **법률**: 계약서 검토, 법적 리스크 분석
- **의료**: 의료 기록 분석, 진단 보조
- **금융**: 재무제표 분석, 투자 보고서 검토
- **기술**: 기술 문서 분석, 코드 리뷰

## 🔍 트러블슈팅

### 일반적인 문제
1. **Docker 컨테이너 실행 실패**
   ```bash
   docker-compose logs
   ```

2. **API 연결 오류**
   ```bash
   curl http://localhost:8001/health
   ```

3. **문서 업로드 실패**
   - 파일 크기 확인 (최대 50MB)
   - 지원 파일 형식 확인

### 로그 확인
```bash
# Backend 로그
docker-compose logs backend

# 전체 시스템 로그
docker-compose logs
```

## 🚀 향후 개발 계획

### 2주차: 멀티모달 기능
- 이미지 처리 기능 추가
- LangGraph 복잡한 워크플로우 구현

### 3주차: 고도화
- 실시간 스트리밍 응답
- 성능 모니터링 대시보드
- 배포 최적화

## 📄 라이선스

MIT License

## 🤝 기여하기

1. Fork 프로젝트
2. Feature 브랜치 생성
3. 변경사항 커밋
4. 브랜치에 푸시
5. Pull Request 생성

---

**개발자**: Harrison
**연락처**: [your-email@example.com]
**프로젝트 타입**: Side Project / Portfolio