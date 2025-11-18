import streamlit as st
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY
from datetime import datetime
import uuid


@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def get_or_create_user(user_id: str) -> dict:
    """Get or create a user record."""
    supabase = get_supabase_client()

    response = supabase.table("users").select("*").eq("auth_id", user_id).maybeSingle().execute()
    user = response.data

    if user:
        supabase.table("users").update({"last_active": datetime.utcnow().isoformat()}).eq("auth_id", user_id).execute()
        return user

    new_user = {
        "auth_id": user_id,
        "language": "Simple English",
        "created_at": datetime.utcnow().isoformat(),
        "last_active": datetime.utcnow().isoformat()
    }

    result = supabase.table("users").insert(new_user).execute()
    return result.data[0] if result.data else new_user


def create_session(user_id: str, language: str = "Simple English") -> dict:
    """Create a new chat session."""
    supabase = get_supabase_client()

    user_response = supabase.table("users").select("id").eq("auth_id", user_id).maybeSingle().execute()
    internal_user_id = user_response.data["id"] if user_response.data else None

    if not internal_user_id:
        raise ValueError("User not found")

    session = {
        "user_id": internal_user_id,
        "session_name": f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "language": language,
        "document_context": "No document uploaded.",
        "created_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("chat_sessions").insert(session).execute()
    return result.data[0] if result.data else session


def add_message(session_id: str, role: str, content: str, sources: list = None, used_document: bool = False) -> dict:
    """Add a message to a session."""
    supabase = get_supabase_client()

    message = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources or [],
        "used_document": used_document,
        "created_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("chat_messages").insert(message).execute()
    return result.data[0] if result.data else message


def get_session_messages(session_id: str) -> list:
    """Get all messages from a session."""
    supabase = get_supabase_client()

    result = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at").execute()
    return result.data if result.data else []


def update_session_document(session_id: str, document_context: str, metadata: dict = None) -> dict:
    """Update a session with document context."""
    supabase = get_supabase_client()

    update_data = {
        "document_context": document_context,
        "document_metadata": metadata or {},
        "updated_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("chat_sessions").update(update_data).eq("id", session_id).execute()
    return result.data[0] if result.data else update_data


def save_document_record(user_id: str, session_id: str, filename: str, file_size: int,
                         file_type: str, extracted_text: str, explanation: str, language: str) -> dict:
    """Save document metadata and extraction to database."""
    supabase = get_supabase_client()

    user_response = supabase.table("users").select("id").eq("auth_id", user_id).maybeSingle().execute()
    internal_user_id = user_response.data["id"] if user_response.data else None

    if not internal_user_id:
        raise ValueError("User not found")

    doc_record = {
        "user_id": internal_user_id,
        "session_id": session_id,
        "original_filename": filename,
        "file_size": file_size,
        "file_type": file_type,
        "extracted_text": extracted_text,
        "explanation": explanation,
        "language": language,
        "created_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("user_documents").insert(doc_record).execute()
    return result.data[0] if result.data else doc_record


def add_feedback(message_id: str, user_id: str, rating: int, comment: str = None) -> dict:
    """Add user feedback to a message."""
    supabase = get_supabase_client()

    user_response = supabase.table("users").select("id").eq("auth_id", user_id).maybeSingle().execute()
    internal_user_id = user_response.data["id"] if user_response.data else None

    if not internal_user_id:
        raise ValueError("User not found")

    feedback = {
        "message_id": message_id,
        "user_id": internal_user_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("feedback").insert(feedback).execute()
    return result.data[0] if result.data else feedback


def log_event(user_id: str, event_type: str, event_data: dict = None) -> dict:
    """Log an analytics event."""
    supabase = get_supabase_client()

    user_response = supabase.table("users").select("id").eq("auth_id", user_id).maybeSingle().execute()
    internal_user_id = user_response.data["id"] if user_response.data else None

    event = {
        "user_id": internal_user_id,
        "event_type": event_type,
        "event_data": event_data or {},
        "created_at": datetime.utcnow().isoformat()
    }

    result = supabase.table("analytics").insert(event).execute()
    return result.data[0] if result.data else event


def get_user_sessions(user_id: str) -> list:
    """Get all sessions for a user."""
    supabase = get_supabase_client()

    user_response = supabase.table("users").select("id").eq("auth_id", user_id).maybeSingle().execute()
    internal_user_id = user_response.data["id"] if user_response.data else None

    if not internal_user_id:
        return []

    result = supabase.table("chat_sessions").select("*").eq("user_id", internal_user_id).eq("is_deleted", False).order("created_at", desc=True).execute()
    return result.data if result.data else []
