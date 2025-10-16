# 🗄️ Django 백엔드

> 사용자 관리, 채팅 히스토리, 문서 메타데이터 저장을 담당하는 Django + DRF 백엔드 서버

## 📋 개요

Django와 Django REST Framework(DRF)를 사용하여 구축된 백엔드 서버입니다.
사용자 인증, 채팅 세션 관리, 문서 메타데이터를 PostgreSQL에 저장하고,
RESTful API를 제공하여 Frontend 및 LangGraph API와 통신합니다.

### 주요 역할

- **사용자 관리**: 회원가입, 로그인, 프로필 관리
- **채팅 히스토리**: 대화 세션 및 메시지 저장/조회
- **문서 메타데이터**: 업로드된 문서 정보 관리
- **JWT 인증**: 토큰 기반 인증 시스템
- **OpenAI API Key 관리**: 사용자별 API Key 암호화 저장

## 📁 폴더 구조

```
backend/
├── manage.py                # Django 관리 명령어 실행
│
├── config/                  # Django 프로젝트 전역 설정
│   ├── __init__.py
│   ├── settings.py          # Django 설정 (DB, MIDDLEWARE, APPS 등)
│   ├── urls.py              # URL 라우팅 (앱별 URL 포함)
│   ├── wsgi.py              # WSGI 설정 (프로덕션)
│   └── asgi.py              # ASGI 설정 (WebSocket 지원)
│
├── users/                   # 사용자 관리 앱
│   ├── __init__.py
│   ├── models.py            # User, Profile 모델
│   ├── serializers.py       # DRF Serializer (회원가입, 로그인)
│   ├── views.py             # ViewSet (회원가입, 로그인, 프로필)
│   ├── urls.py              # URL 패턴
│   ├── admin.py             # Django Admin 설정
│   └── tests.py             # 테스트 코드
│
├── chat_history/            # 채팅 히스토리 앱
│   ├── __init__.py
│   ├── models.py            # ChatSession, ChatMessage 모델
│   ├── serializers.py       # Serializer
│   ├── views.py             # ViewSet (세션 생성, 메시지 저장/조회)
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
│
├── documents/               # 문서 메타데이터 관리 앱
│   ├── __init__.py
│   ├── models.py            # DocumentMetadata 모델
│   ├── serializers.py
│   ├── views.py             # ViewSet (문서 목록, 업로드, 삭제)
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
│
├── requirements.txt         # Python 의존성 패키지
└── pytest.ini              # pytest 설정
```

## 🗃️ 데이터베이스 모델

### 1. User & Profile (사용자)

**User 모델** (`users/models.py`):
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    커스텀 사용자 모델

    Django 기본 User를 확장하여 이메일 필수화
    """
    email = models.EmailField(
        unique=True,
        verbose_name="이메일",
        help_text="로그인 시 사용되는 이메일 주소"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="가입일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="정보 수정일")

    USERNAME_FIELD = "email"  # 이메일로 로그인
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"

    def __str__(self):
        return self.email
```

**Profile 모델** (`users/models.py`):
```python
from cryptography.fernet import Fernet
from django.conf import settings

class Profile(models.Model):
    """
    사용자 프로필 (1:1 관계)

    OpenAI API Key 암호화 저장
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # 암호화된 OpenAI API Key 저장
    _encrypted_api_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="암호화된 API Key"
    )

    preferred_language = models.CharField(
        max_length=10,
        default="ko",
        choices=[("ko", "한국어"), ("en", "English")],
        verbose_name="선호 언어"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profiles"

    def set_api_key(self, plain_key: str):
        """
        OpenAI API Key를 암호화하여 저장

        Args:
            plain_key: 평문 API Key (sk-로 시작)
        """
        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        encrypted = cipher.encrypt(plain_key.encode())
        self._encrypted_api_key = encrypted.decode()
        self.save()

    def get_api_key(self) -> str:
        """
        암호화된 API Key를 복호화하여 반환

        Returns:
            평문 API Key
        """
        if not self._encrypted_api_key:
            return ""

        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted = cipher.decrypt(self._encrypted_api_key.encode())
        return decrypted.decode()

    def __str__(self):
        return f"{self.user.email}의 프로필"
```

**Signal (자동 Profile 생성)**:
```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """User 생성 시 자동으로 Profile 생성"""
    if created:
        Profile.objects.create(user=instance)
```

### 2. ChatSession & ChatMessage (채팅 히스토리)

**ChatSession 모델** (`chat_history/models.py`):
```python
import uuid
from django.db import models
from users.models import User

class ChatSession(models.Model):
    """
    채팅 세션

    사용자별로 여러 대화 세션을 가질 수 있음
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        verbose_name="사용자"
    )

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="세션 ID"
    )

    title = models.CharField(
        max_length=255,
        verbose_name="세션 제목",
        help_text="첫 번째 질문으로 자동 생성"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="마지막 업데이트")

    class Meta:
        db_table = "chat_sessions"
        ordering = ["-updated_at"]  # 최신순 정렬
        verbose_name = "채팅 세션"
        verbose_name_plural = "채팅 세션 목록"

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    @property
    def message_count(self) -> int:
        """이 세션의 총 메시지 수"""
        return self.messages.count()
```

**ChatMessage 모델** (`chat_history/models.py`):
```python
class ChatMessage(models.Model):
    """
    채팅 메시지

    user 또는 assistant 역할의 메시지 저장
    """
    ROLE_CHOICES = [
        ("user", "사용자"),
        ("assistant", "AI 어시스턴트")
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="세션"
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="역할"
    )

    content = models.TextField(verbose_name="메시지 내용")

    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="메타데이터",
        help_text="토큰 사용량, 출처, 타이밍 정보 등"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]  # 시간순 정렬
        verbose_name = "채팅 메시지"
        verbose_name_plural = "채팅 메시지 목록"

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."

    @property
    def token_usage(self) -> int:
        """메타데이터에서 토큰 사용량 추출"""
        return self.metadata.get("tokens_used", 0)
```

### 3. DocumentMetadata (문서 메타데이터)

**DocumentMetadata 모델** (`documents/models.py`):
```python
from django.db import models
from users.models import User

class DocumentMetadata(models.Model):
    """
    업로드된 문서의 메타데이터

    실제 문서 내용은 Qdrant에 저장되고,
    여기서는 문서 정보만 관리
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="사용자"
    )

    filename = models.CharField(max_length=255, verbose_name="파일명")

    file_path = models.CharField(
        max_length=500,
        verbose_name="파일 경로",
        help_text="서버 또는 S3 경로"
    )

    file_size = models.IntegerField(verbose_name="파일 크기 (bytes)")

    file_type = models.CharField(
        max_length=50,
        verbose_name="파일 타입",
        help_text="PDF, TXT, DOCX 등"
    )

    page_count = models.IntegerField(
        default=0,
        verbose_name="페이지 수"
    )

    chunk_count = models.IntegerField(
        default=0,
        verbose_name="청크 수",
        help_text="Vector DB에 저장된 청크 개수"
    )

    qdrant_collection = models.CharField(
        max_length=100,
        verbose_name="Qdrant 컬렉션 이름"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="업로드일")

    processed = models.BooleanField(
        default=False,
        verbose_name="처리 완료 여부",
        help_text="임베딩 및 Vector DB 저장 완료"
    )

    processing_error = models.TextField(
        blank=True,
        verbose_name="처리 오류",
        help_text="오류 발생 시 오류 메시지"
    )

    class Meta:
        db_table = "document_metadata"
        ordering = ["-uploaded_at"]
        verbose_name = "문서 메타데이터"
        verbose_name_plural = "문서 메타데이터 목록"

    def __str__(self):
        return f"{self.filename} ({self.user.email})"

    @property
    def is_processed(self) -> bool:
        """처리 완료 여부"""
        return self.processed

    def mark_as_processed(self, chunk_count: int):
        """문서 처리 완료 표시"""
        self.processed = True
        self.chunk_count = chunk_count
        self.save()

    def mark_as_failed(self, error_message: str):
        """문서 처리 실패 표시"""
        self.processed = False
        self.processing_error = error_message
        self.save()
```

## 🔌 API 엔드포인트

### 인증 API (users/)

#### 1. 회원가입

```http
POST /api/users/register/
Content-Type: application/json

{
  "username": "user123",
  "email": "user@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123"
}
```

**응답 (201 Created)**:
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com",
  "created_at": "2025-01-15T10:00:00Z",
  "token": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Serializer 코드** (`users/serializers.py`):
```python
from rest_framework import serializers
from users.models import User
from django.contrib.auth.password_validation import validate_password

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "비밀번호가 일치하지 않습니다"}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user
```

#### 2. 로그인 (JWT)

```http
POST /api/users/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**응답 (200 OK)**:
```json
{
  "user": {
    "id": 1,
    "username": "user123",
    "email": "user@example.com"
  },
  "token": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

#### 3. 토큰 갱신

```http
POST /api/users/token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**응답**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### 4. 프로필 조회/수정

```http
GET /api/users/profile/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답**:
```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com",
  "profile": {
    "preferred_language": "ko",
    "has_api_key": true
  }
}
```

```http
PATCH /api/users/profile/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "preferred_language": "en"
}
```

#### 5. OpenAI API Key 설정

```http
POST /api/users/profile/set-api-key/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "api_key": "sk-1234567890abcdef..."
}
```

**응답**:
```json
{
  "status": "success",
  "message": "API Key가 안전하게 저장되었습니다"
}
```

### 채팅 히스토리 API (chat_history/)

#### 1. 세션 생성

```http
POST /api/chat-history/sessions/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "title": "RAG 시스템 질문"
}
```

**응답 (201 Created)**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "RAG 시스템 질문",
  "created_at": "2025-01-15T10:30:00Z",
  "message_count": 0
}
```

#### 2. 세션 목록 조회

```http
GET /api/chat-history/sessions/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답**:
```json
{
  "count": 5,
  "results": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "RAG 시스템 질문",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:35:00Z",
      "message_count": 6
    },
    ...
  ]
}
```

#### 3. 메시지 저장

```http
POST /api/chat-history/messages/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "user",
  "content": "RAG가 무엇인가요?",
  "metadata": {}
}
```

**응답 (201 Created)**:
```json
{
  "id": 123,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "role": "user",
  "content": "RAG가 무엇인가요?",
  "metadata": {},
  "created_at": "2025-01-15T10:31:00Z"
}
```

#### 4. 세션별 메시지 히스토리 조회

```http
GET /api/chat-history/sessions/{session_id}/messages/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "RAG 시스템 질문",
  "messages": [
    {
      "role": "user",
      "content": "RAG가 무엇인가요?",
      "created_at": "2025-01-15T10:31:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "RAG는 Retrieval-Augmented Generation의 약자로...",
      "created_at": "2025-01-15T10:31:02Z",
      "metadata": {
        "tokens_used": 450,
        "model": "gpt-oss-20b"
      }
    },
    ...
  ]
}
```

### 문서 관리 API (documents/)

#### 1. 문서 목록 조회

```http
GET /api/documents/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답**:
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "filename": "rag_introduction.pdf",
      "file_type": "PDF",
      "file_size": 2048576,
      "page_count": 10,
      "chunk_count": 45,
      "uploaded_at": "2025-01-15T09:00:00Z",
      "processed": true
    },
    ...
  ]
}
```

#### 2. 문서 상세 조회

```http
GET /api/documents/{id}/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답**:
```json
{
  "id": 1,
  "filename": "rag_introduction.pdf",
  "file_type": "PDF",
  "file_size": 2048576,
  "page_count": 10,
  "chunk_count": 45,
  "qdrant_collection": "documents",
  "uploaded_at": "2025-01-15T09:00:00Z",
  "processed": true,
  "processing_error": ""
}
```

#### 3. 문서 삭제

```http
DELETE /api/documents/{id}/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**응답 (204 No Content)**

#### 4. 문서 업로드 (메타데이터 생성)

```http
POST /api/documents/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
Content-Type: multipart/form-data

file: (binary data)
```

**응답 (201 Created)**:
```json
{
  "id": 2,
  "filename": "new_document.pdf",
  "file_type": "PDF",
  "file_size": 1024000,
  "uploaded_at": "2025-01-15T11:00:00Z",
  "processed": false,
  "message": "문서가 업로드되었습니다. 처리 중입니다."
}
```

## 🚀 로컬 실행

### 1. 가상환경 생성 및 활성화

```bash
cd backend
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
Django==4.2.0
djangorestframework==3.14.0
djangorestframework-simplejwt==5.2.2
django-cors-headers==4.0.0
psycopg2-binary==2.9.6
cryptography==41.0.0
python-dotenv==1.0.0
```

### 3. 환경변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chatbot
POSTGRES_USER=admin
POSTGRES_PASSWORD=password

# 암호화 키 (Fernet)
ENCRYPTION_KEY=your-fernet-key-here
EOF
```

**Fernet Key 생성**:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# 출력된 키를 ENCRYPTION_KEY에 설정
```

### 4. 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 5. 서버 실행

```bash
# 개발 서버 실행
python manage.py runserver 0.0.0.0:8001

# 프로덕션 (Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8001 --workers 4
```

### 6. Django Admin 접속

```
http://localhost:8001/admin
```

## 🔐 보안 고려사항

### 1. OpenAI API Key 암호화

```python
# users/models.py
from cryptography.fernet import Fernet
from django.conf import settings

class Profile(models.Model):
    _encrypted_api_key = models.CharField(max_length=500, blank=True)

    def set_api_key(self, plain_key: str):
        """암호화하여 저장"""
        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        encrypted = cipher.encrypt(plain_key.encode())
        self._encrypted_api_key = encrypted.decode()
        self.save()

    def get_api_key(self) -> str:
        """복호화하여 반환"""
        if not self._encrypted_api_key:
            return ""
        cipher = Fernet(settings.ENCRYPTION_KEY.encode())
        decrypted = cipher.decrypt(self._encrypted_api_key.encode())
        return decrypted.decode()
```

### 2. JWT 인증 설정

```python
# config/settings.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

### 3. CORS 설정

```python
# config/settings.py
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

# 개발 환경
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8501",  # Streamlit
    "http://localhost:8000",  # FastAPI
]

# 프로덕션 환경
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.yourdomain\.com$",
]
```

## 📊 데이터베이스 마이그레이션 가이드

### 모델 변경 시 워크플로우

1. **모델 수정** (`models.py`)
```python
class DocumentMetadata(models.Model):
    # 새 필드 추가
    language = models.CharField(max_length=10, default="ko")
```

2. **마이그레이션 생성**
```bash
python manage.py makemigrations documents
```

3. **마이그레이션 확인**
```bash
python manage.py showmigrations documents
```

4. **마이그레이션 적용**
```bash
python manage.py migrate documents
```

5. **롤백 (필요 시)**
```bash
# 이전 마이그레이션으로
python manage.py migrate documents 0001_initial
```

### 데이터 마이그레이션 (Data Migration)

```bash
# 빈 마이그레이션 생성
python manage.py makemigrations --empty documents
```

```python
# documents/migrations/0002_populate_language.py
from django.db import migrations

def populate_language(apps, schema_editor):
    DocumentMetadata = apps.get_model('documents', 'DocumentMetadata')
    for doc in DocumentMetadata.objects.all():
        doc.language = "ko"
        doc.save()

class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_language),
    ]
```

## 🧪 테스트

### 단위 테스트

```python
# users/tests.py
from django.test import TestCase
from users.models import User, Profile

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_user_creation(self):
        """사용자 생성 테스트"""
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.check_password("testpass123"))

    def test_profile_auto_creation(self):
        """Profile이 자동으로 생성되는지 테스트"""
        self.assertIsNotNone(self.user.profile)

    def test_api_key_encryption(self):
        """API Key 암호화/복호화 테스트"""
        test_key = "sk-test1234567890"
        self.user.profile.set_api_key(test_key)

        # 암호화된 값 확인
        self.assertNotEqual(
            self.user.profile._encrypted_api_key,
            test_key
        )

        # 복호화 확인
        self.assertEqual(
            self.user.profile.get_api_key(),
            test_key
        )
```

### API 테스트

```python
# users/tests.py
from rest_framework.test import APITestCase
from rest_framework import status

class UserAPITest(APITestCase):
    def test_user_registration(self):
        """회원가입 API 테스트"""
        url = "/api/users/register/"
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123"
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("access", response.data["token"])

    def test_user_login(self):
        """로그인 API 테스트"""
        # 사용자 생성
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        url = "/api/users/login/"
        data = {
            "email": "test@example.com",
            "password": "testpass123"
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
```

### 테스트 실행

```bash
# 모든 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test users

# Coverage 리포트
coverage run --source='.' manage.py test
coverage report
coverage html  # htmlcov/index.html
```

## 📖 참고 자료

### Django
- [Django 공식 문서](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)

### 보안
- [Django Security Best Practices](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Django 백엔드는 사용자 데이터와 채팅 히스토리를 안전하게 관리하는 핵심 서버입니다.**
