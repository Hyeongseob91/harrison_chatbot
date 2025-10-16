# 🎨 Streamlit 프론트엔드

> 사용자 친화적인 채팅 인터페이스 및 문서 업로드 UI

## 📋 개요

Streamlit을 기반으로 구축된 프로토타입 채팅 인터페이스입니다.
OpenAI API Key 설정, 문서 업로드, 실시간 채팅, 히스토리 조회 기능을 제공하며,
FastAPI (LangGraph API)와 Django 백엔드와 RESTful API로 통신합니다.

### 주요 기능

- **채팅 인터페이스**: 실시간 메시지 송수신 및 스트리밍 응답
- **문서 업로드**: PDF, TXT 파일 업로드 및 처리 상태 확인
- **API Key 관리**: OpenAI API Key 런타임 설정
- **히스토리 관리**: 이전 대화 세션 조회 및 불러오기
- **참고 문서 표시**: LLM 응답의 출처 문서 표시

## 📁 폴더 구조

```
frontend/
├── main.py                 # Streamlit 앱 진입점
├── components/
│   ├── __init__.py
│   ├── chat_ui.py          # 채팅 인터페이스 컴포넌트
│   ├── sidebar.py          # 사이드바 (설정, 문서 업로드)
│   └── history.py          # 히스토리 표시 컴포넌트
├── utils/
│   ├── __init__.py
│   └── api_client.py       # FastAPI, Django API 클라이언트
├── requirements.txt        # Python 의존성
└── .streamlit/
    └── config.toml         # Streamlit 설정 (테마, 포트 등)
```

## 🚀 로컬 실행

### 1. 의존성 설치

```bash
cd frontend
pip install -r requirements.txt
```

**requirements.txt**:
```
streamlit==1.29.0
requests==2.31.0
python-dotenv==1.0.0
```

### 2. 환경변수 설정

```bash
# .env 파일 생성
cat > .env << EOF
FASTAPI_URL=http://localhost:8000
DJANGO_URL=http://localhost:8001
EOF
```

### 3. Streamlit 실행

```bash
streamlit run main.py --server.port 8501
```

또는:

```bash
# 외부 접속 허용
streamlit run main.py --server.address 0.0.0.0 --server.port 8501
```

### 4. 브라우저 접속

```
http://localhost:8501
```

## 🎨 UI 구성

### 메인 화면 레이아웃

```
┌──────────────────────────────────────────────────────────┐
│ 🤖 LangGraph RAG Chatbot                                 │
├─────────────────┬────────────────────────────────────────┤
│ Sidebar (좁음)  │ Chat Area (넓음)                       │
│ ┌─────────────┐ │ ┌────────────────────────────────────┐│
│ │⚙️ 설정       │ │ │ 💬 User: RAG가 무엇인가요?         ││
│ │             │ │ ├────────────────────────────────────┤│
│ │ OpenAI Key: │ │ │ 🤖 Bot: RAG는 Retrieval-Augmented ││
│ │[**********] │ │ │         Generation의 약자로...     ││
│ │[설정 완료]   │ │ │                                    ││
│ │             │ │ │ 📚 참고 문서:                       ││
│ ├─────────────┤ │ │ - rag_intro.pdf (p.1)              ││
│ │📄 문서 업로드 │ │ └────────────────────────────────────┘│
│ │             │ │                                        │
│ │[파일 선택]   │ │ ┌────────────────────────────────────┐│
│ │[업로드]      │ │ │ 💬 질문을 입력하세요...             ││
│ │             │ │ │ [전송]                              ││
│ ├─────────────┤ │ └────────────────────────────────────┘│
│ │📜 히스토리    │ │                                        │
│ │             │ │                                        │
│ │- Session 1  │ │                                        │
│ │- Session 2  │ │                                        │
│ │- Session 3  │ │                                        │
│ └─────────────┘ │                                        │
└─────────────────┴────────────────────────────────────────┘
```

## 💻 주요 컴포넌트 구현

### 1. 메인 앱 (`main.py`)

```python
import streamlit as st
from components.chat_ui import render_chat
from components.sidebar import render_sidebar

# 페이지 설정
st.set_page_config(
    page_title="LangGraph RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key_set" not in st.session_state:
    st.session_state.api_key_set = False

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# 커스텀 CSS
st.markdown("""
<style>
.stChatMessage {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
}
.source-box {
    background-color: #f0f2f6;
    padding: 0.5rem;
    border-radius: 0.3rem;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# 레이아웃
render_sidebar()
render_chat()
```

### 2. 채팅 UI (`components/chat_ui.py`)

```python
import streamlit as st
from utils.api_client import send_message, stream_message

def render_chat():
    """채팅 인터페이스 렌더링"""

    st.title("🤖 LangGraph RAG Chatbot")

    # API Key 설정 확인
    if not st.session_state.get("api_key_set", False):
        st.warning("⚠️ 사이드바에서 OpenAI API Key를 먼저 설정해주세요.")
        return

    # 기존 메시지 표시
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

            # Assistant 메시지인 경우 출처 표시
            if msg["role"] == "assistant" and "sources" in msg:
                render_sources(msg["sources"])

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요"):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 사용자 메시지 표시
        with st.chat_message("user"):
            st.write(prompt)

        # API 호출 (스트리밍)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            with st.spinner("답변 생성 중..."):
                try:
                    # 스트리밍 응답
                    for chunk in stream_message(prompt):
                        full_response += chunk
                        message_placeholder.write(full_response + "▌")

                    message_placeholder.write(full_response)

                    # 메타데이터 및 출처 가져오기 (별도 API 호출)
                    # 실제로는 스트리밍 마지막에 포함되어야 함
                    sources = []  # TODO: 구현

                    # Assistant 메시지 저장
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "sources": sources
                    })

                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")


def render_sources(sources: list):
    """참고 문서 출처 렌더링"""
    if not sources:
        return

    with st.expander("📚 참고 문서", expanded=False):
        for i, source in enumerate(sources, 1):
            filename = source.get("filename", "Unknown")
            page = source.get("page", 0)
            score = source.get("score", 0.0)

            st.markdown(
                f"**{i}.** `{filename}` (p.{page}, 유사도: {score:.2f})"
            )
```

### 3. 사이드바 (`components/sidebar.py`)

```python
import streamlit as st
import requests
from utils.api_client import upload_document, get_documents, set_api_key

def render_sidebar():
    """사이드바 렌더링 (설정, 문서 업로드, 히스토리)"""

    with st.sidebar:
        # 1. OpenAI API Key 설정
        render_api_key_section()

        st.divider()

        # 2. 문서 업로드
        render_document_upload_section()

        st.divider()

        # 3. 히스토리
        render_history_section()


def render_api_key_section():
    """API Key 설정 섹션"""
    st.header("⚙️ 설정")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="sk-로 시작하는 OpenAI API 키를 입력하세요",
        placeholder="sk-..."
    )

    if st.button("설정 완료", use_container_width=True):
        if not api_key:
            st.error("API Key를 입력해주세요")
        elif not api_key.startswith("sk-"):
            st.error("유효하지 않은 API Key 형식입니다")
        else:
            # API Key 설정
            success = set_api_key(api_key)

            if success:
                st.session_state["api_key_set"] = True
                st.success("✅ API Key가 설정되었습니다")
                st.rerun()
            else:
                st.error("API Key 설정에 실패했습니다")


def render_document_upload_section():
    """문서 업로드 섹션"""
    st.header("📄 문서 업로드")

    uploaded_file = st.file_uploader(
        "PDF 또는 TXT 파일을 선택하세요",
        type=["pdf", "txt"],
        help="최대 50MB까지 업로드 가능합니다"
    )

    if uploaded_file and st.button("업로드", use_container_width=True):
        with st.spinner(f"'{uploaded_file.name}' 업로드 중..."):
            result = upload_document(uploaded_file)

            if result["success"]:
                st.success(f"✅ {uploaded_file.name} 업로드 완료")
                st.info(f"페이지 수: {result['page_count']}")
            else:
                st.error(f"업로드 실패: {result['error']}")

    # 업로드된 문서 목록
    st.subheader("📚 업로드된 문서")

    documents = get_documents()
    if documents:
        for doc in documents:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📄 {doc['filename']}")
            with col2:
                if st.button("🗑️", key=f"delete_{doc['id']}"):
                    # 삭제 로직
                    pass
    else:
        st.info("업로드된 문서가 없습니다")


def render_history_section():
    """히스토리 섹션"""
    st.header("📜 대화 히스토리")

    # 히스토리 목록 가져오기
    sessions = []  # TODO: Django API 호출

    if sessions:
        for session in sessions:
            if st.button(
                session["title"],
                key=f"session_{session['session_id']}",
                use_container_width=True
            ):
                # 세션 불러오기
                load_session(session["session_id"])
    else:
        st.info("대화 히스토리가 없습니다")

    # 새 세션 시작
    if st.button("➕ 새 대화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.rerun()


def load_session(session_id: str):
    """이전 세션 불러오기"""
    # Django API에서 메시지 가져오기
    messages = []  # TODO: API 호출

    st.session_state.messages = messages
    st.session_state.current_session_id = session_id
    st.rerun()
```

### 4. API 클라이언트 (`utils/api_client.py`)

```python
import requests
from typing import Dict, List, Generator
import os
from dotenv import load_dotenv

load_dotenv()

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")
DJANGO_URL = os.getenv("DJANGO_URL", "http://localhost:8001")


def set_api_key(api_key: str) -> bool:
    """
    OpenAI API Key 설정

    Args:
        api_key: OpenAI API Key

    Returns:
        성공 여부
    """
    try:
        response = requests.post(
            f"{FASTAPI_URL}/api/set-key",
            json={"api_key": api_key},
            timeout=5
        )
        return response.status_code == 200
    except Exception:
        return False


def send_message(query: str, session_id: str = None) -> Dict:
    """
    동기 메시지 전송

    Args:
        query: 사용자 질문
        session_id: 세션 ID (선택)

    Returns:
        응답 데이터 (response, sources, metadata)
    """
    try:
        response = requests.post(
            f"{FASTAPI_URL}/chat/invoke",
            json={"query": query, "session_id": session_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"API 호출 실패: {str(e)}")


def stream_message(query: str, session_id: str = None) -> Generator[str, None, None]:
    """
    스트리밍 메시지 전송

    Args:
        query: 사용자 질문
        session_id: 세션 ID (선택)

    Yields:
        응답 청크
    """
    try:
        with requests.post(
            f"{FASTAPI_URL}/chat/stream",
            json={"query": query, "session_id": session_id},
            stream=True,
            timeout=30
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    # SSE 형식: "data: {...}"
                    data_str = line.decode().replace("data: ", "")

                    if data_str:
                        import json
                        data = json.loads(data_str)

                        if "chunk" in data:
                            yield data["chunk"]
                        elif "done" in data and data["done"]:
                            break

    except Exception as e:
        raise Exception(f"스트리밍 실패: {str(e)}")


def upload_document(file) -> Dict:
    """
    문서 업로드

    Args:
        file: 업로드할 파일 객체

    Returns:
        업로드 결과 (success, page_count, error)
    """
    try:
        files = {"file": file}
        response = requests.post(
            f"{FASTAPI_URL}/documents/upload",
            files=files,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()
        return {
            "success": True,
            "page_count": data.get("page_count", 0),
            "document_id": data.get("document_id")
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_documents() -> List[Dict]:
    """
    업로드된 문서 목록 조회

    Returns:
        문서 목록
    """
    try:
        response = requests.get(
            f"{DJANGO_URL}/api/documents/",
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", [])

    except Exception:
        return []
```

## 🎨 Streamlit 설정

### `.streamlit/config.toml`

```toml
[theme]
primaryColor = "#4CAF50"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

## 📱 반응형 레이아웃

```python
# main.py에서 사용
st.markdown("""
<style>
/* 모바일 대응 */
@media (max-width: 768px) {
    .stChatMessage {
        font-size: 0.9rem;
    }
}

/* 채팅 메시지 스타일 */
.stChatMessage[data-testid="user-message"] {
    background-color: #e3f2fd;
}

.stChatMessage[data-testid="assistant-message"] {
    background-color: #f1f8e9;
}

/* 사이드바 */
.css-1d391kg {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)
```

## 🧪 테스트

### 컴포넌트 테스트

```python
# tests/test_api_client.py
import pytest
from utils.api_client import send_message, stream_message

def test_send_message():
    """동기 메시지 전송 테스트"""
    response = send_message("테스트 질문")

    assert "response" in response
    assert len(response["response"]) > 0


def test_stream_message():
    """스트리밍 메시지 테스트"""
    chunks = list(stream_message("테스트 질문"))

    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)
```

## 📊 성능 최적화

### 1. 세션 상태 캐싱

```python
@st.cache_data(ttl=3600)
def get_documents_cached():
    """문서 목록 캐싱 (1시간)"""
    return get_documents()
```

### 2. 이미지 최적화

```python
# 로고 등 정적 이미지 캐싱
@st.cache_resource
def load_logo():
    return Image.open("assets/logo.png")
```

## 📖 참고 자료

- [Streamlit 공식 문서](https://docs.streamlit.io/)
- [Streamlit Chat Elements](https://docs.streamlit.io/library/api-reference/chat)
- [Streamlit 테마 커스터마이징](https://docs.streamlit.io/library/advanced-features/theming)

---

**Streamlit 프론트엔드는 사용자와 RAG 시스템 간의 직관적인 인터페이스를 제공합니다.**
