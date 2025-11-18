import streamlit as st
from datetime import datetime
import hashlib


def get_session_id():
    """Get a unique session ID for the user."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(datetime.now().timestamp()).split(".")[0]
    return st.session_state.session_id


def init_session_state():
    """Initialize all session state variables."""
    if "app_started" not in st.session_state:
        st.session_state.app_started = False

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "document_context" not in st.session_state:
        st.session_state.document_context = "No document uploaded."

    if "uploaded_file_bytes" not in st.session_state:
        st.session_state.uploaded_file_bytes = None

    if "uploaded_file_type" not in st.session_state:
        st.session_state.uploaded_file_type = None

    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None

    if "samjhao_explanation" not in st.session_state:
        st.session_state.samjhao_explanation = None

    if "file_uploader_key" not in st.session_state:
        st.session_state.file_uploader_key = 0

    if "language" not in st.session_state:
        st.session_state.language = "Simple English"

    if "document_extracted" not in st.session_state:
        st.session_state.document_extracted = False

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None

    if "message_ids" not in st.session_state:
        st.session_state.message_ids = {}


def clear_session():
    """Clear session data for a fresh start."""
    st.session_state.messages = []
    st.session_state.document_context = "No document uploaded."
    st.session_state.uploaded_file_bytes = None
    st.session_state.uploaded_file_type = None
    st.session_state.uploaded_filename = None
    st.session_state.samjhao_explanation = None
    st.session_state.file_uploader_key += 1
    st.session_state.document_extracted = False
    st.session_state.message_ids = {}


def get_chat_history_string(limit: int = 6) -> str:
    """Get formatted chat history for RAG context."""
    if not st.session_state.messages:
        return ""

    recent_messages = st.session_state.messages[-limit:]
    return "\n".join([f"{m['role']}: {m['content']}" for m in recent_messages])


def add_message(role: str, content: str, sources: list = None, used_document: bool = False, message_id: str = None):
    """Add a message to the conversation."""
    message = {
        "role": role,
        "content": content,
        "sources_from_guides": sources or [],
        "source_from_document": used_document,
        "id": message_id
    }
    st.session_state.messages.append(message)

    if message_id:
        st.session_state.message_ids[len(st.session_state.messages) - 1] = message_id


def truncate_messages_if_needed(max_messages: int = 20):
    """Remove oldest messages if conversation exceeds limit."""
    if len(st.session_state.messages) > max_messages:
        st.session_state.messages = st.session_state.messages[-max_messages:]
