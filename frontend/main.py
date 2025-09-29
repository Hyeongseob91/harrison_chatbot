import streamlit as st
import requests
import json
from datetime import datetime
import os
from typing import List, Dict, Any
import uuid

# Page configuration
st.set_page_config(
    page_title="Document Analysis Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE = "http://localhost:8001/api"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []

def create_session():
    """Create a new chat session"""
    try:
        response = requests.post(
            f"{API_BASE}/sessions/",
            json={"session_name": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
        )
        if response.status_code == 200:
            session_data = response.json()
            st.session_state.session_id = session_data["session_id"]
            st.session_state.messages = []
            st.rerun()
        else:
            st.error(f"Failed to create session: {response.text}")
    except Exception as e:
        st.error(f"Error creating session: {e}")

def upload_document(file, domain):
    """Upload document to API"""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {
            "session_id": st.session_state.session_id,
            "domain": domain
        }

        with st.spinner("문서를 업로드하고 처리중입니다..."):
            response = requests.post(
                f"{API_BASE}/documents/upload",
                files=files,
                data=data,
                timeout=60
            )

        if response.status_code == 200:
            doc_data = response.json()
            st.success(f"문서가 성공적으로 업로드되었습니다! ({doc_data['vector_count']}개 청크)")
            load_documents()
            return True
        else:
            st.error(f"업로드 실패: {response.text}")
            return False
    except Exception as e:
        st.error(f"업로드 중 오류: {e}")
        return False

def load_documents():
    """Load documents for current session"""
    try:
        response = requests.get(
            f"{API_BASE}/documents/",
            params={"session_id": st.session_state.session_id}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.documents = data["documents"]
    except Exception as e:
        st.sidebar.error(f"문서 로드 오류: {e}")

def send_chat_message(message, domain="general"):
    """Send chat message to API"""
    try:
        with st.spinner("답변을 생성중입니다..."):
            response = requests.post(
                f"{API_BASE}/chat/",
                json={
                    "message": message,
                    "session_id": st.session_state.session_id,
                    "domain": domain
                },
                timeout=30
            )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Chat error: {response.text}")
            return None
    except Exception as e:
        st.error(f"채팅 중 오류: {e}")
        return None

def get_chat_suggestions(domain="general"):
    """Get chat suggestions from API"""
    try:
        response = requests.get(
            f"{API_BASE}/chat/suggestions",
            params={
                "session_id": st.session_state.session_id,
                "domain": domain
            }
        )
        if response.status_code == 200:
            return response.json()["suggestions"]
        return []
    except:
        return []

def main():
    # Header
    st.title("🤖 Document Analysis Chatbot")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("📁 문서 관리")

        # New session button
        if st.button("🆕 새 세션 시작", type="primary"):
            create_session()

        st.markdown(f"**현재 세션:** `{st.session_state.session_id[:8]}...`")

        # Document upload
        st.subheader("📤 문서 업로드")

        domain = st.selectbox(
            "분석 분야 선택",
            ["general", "legal", "medical", "financial", "technical"],
            format_func=lambda x: {
                "general": "일반",
                "legal": "법률",
                "medical": "의료",
                "financial": "금융",
                "technical": "기술"
            }.get(x, x)
        )

        uploaded_file = st.file_uploader(
            "파일 선택",
            type=["pdf", "txt", "docx", "doc", "xlsx", "xls"],
            help="지원 형식: PDF, TXT, DOCX, DOC, XLSX, XLS"
        )

        if uploaded_file and st.button("업로드"):
            if upload_document(uploaded_file, domain):
                st.rerun()

        # Document list
        st.subheader("📄 업로드된 문서")
        load_documents()

        if st.session_state.documents:
            for doc in st.session_state.documents:
                status_emoji = {
                    "completed": "✅",
                    "processing": "⏳",
                    "failed": "❌",
                    "pending": "📋"
                }.get(doc["upload_status"], "❓")

                st.markdown(f"""
                {status_emoji} **{doc['file_name']}**
                - 분야: {doc['domain']}
                - 청크: {doc.get('vector_count', 0)}개
                - 크기: {doc['file_size'] // 1024}KB
                """)
        else:
            st.info("업로드된 문서가 없습니다.")

    # Main chat interface
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("💬 채팅")

        # Chat history
        chat_container = st.container()

        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

                    # Show sources if available
                    if message["role"] == "assistant" and "sources" in message:
                        if message["sources"]:
                            with st.expander("📚 참고 문서"):
                                for i, source in enumerate(message["sources"][:3]):  # Limit to 3 sources
                                    st.markdown(f"""
                                    **{i+1}. {source['document_name']}** (유사도: {source['score']:.2f})

                                    {source['content_preview']}
                                    """)

        # Chat input
        if prompt := st.chat_input("질문을 입력하세요..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.write(prompt)

            # Get response
            response = send_chat_message(prompt, domain)

            if response:
                assistant_message = {
                    "role": "assistant",
                    "content": response["message"],
                    "sources": response.get("sources", [])
                }
                st.session_state.messages.append(assistant_message)

                with st.chat_message("assistant"):
                    st.write(response["message"])

                    # Show sources
                    if response.get("sources"):
                        with st.expander("📚 참고 문서"):
                            for i, source in enumerate(response["sources"][:3]):
                                st.markdown(f"""
                                **{i+1}. {source['document_name']}** (유사도: {source['score']:.2f})

                                {source['content_preview']}
                                """)

    with col2:
        st.subheader("💡 추천 질문")

        suggestions = get_chat_suggestions(domain)

        for suggestion in suggestions:
            if st.button(f"❓ {suggestion}", key=f"suggest_{hash(suggestion)}"):
                # Add to messages and get response
                st.session_state.messages.append({"role": "user", "content": suggestion})
                response = send_chat_message(suggestion, domain)

                if response:
                    assistant_message = {
                        "role": "assistant",
                        "content": response["message"],
                        "sources": response.get("sources", [])
                    }
                    st.session_state.messages.append(assistant_message)
                    st.rerun()

        # Clear chat
        if st.button("🗑️ 채팅 기록 삭제", type="secondary"):
            st.session_state.messages = []
            st.rerun()

        # Statistics
        st.subheader("📊 통계")
        st.metric("업로드된 문서", len(st.session_state.documents))
        st.metric("채팅 메시지", len(st.session_state.messages))

        total_chunks = sum(doc.get('vector_count', 0) for doc in st.session_state.documents)
        st.metric("총 문서 청크", total_chunks)

if __name__ == "__main__":
    main()