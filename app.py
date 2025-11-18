import streamlit as st
from PIL import Image
import io

from config import LANGUAGES, DEFAULT_LANGUAGE, MAX_FILE_SIZE_MB
from session_manager import init_session_state, clear_session, get_chat_history_string, add_message, truncate_messages_if_needed
from models import get_generative_model
from rag_chain import invoke_rag
from document_processor import display_uploaded_document, extract_and_explain_document, check_if_response_from_document
from db import (
    get_or_create_user, create_session, add_message as db_add_message,
    get_session_messages, update_session_document, save_document_record,
    add_feedback, log_event
)
import uuid


st.set_page_config(
    page_title="Nyay-Saathi",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
:root {
    --primary-color: #00FFD1;
    --background-color: #08070C;
    --secondary-background-color: #1B1C2A;
    --text-color: #FAFAFA;
}
body { font-family: 'sans serif'; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stButton > button {
    border: 2px solid var(--primary-color); background: transparent; color: var(--primary-color);
    padding: 12px 24px; border-radius: 8px; font-weight: bold; transition: all 0.3s ease-in-out;
}
.stButton > button:hover {
    background: var(--primary-color); color: var(--background-color); box-shadow: 0 0 15px var(--primary-color);
}
.stTextArea textarea {
    background-color: var(--secondary-background-color); color: var(--text-color);
    border: 1px solid var(--primary-color); border-radius: 8px;
}
div[data-testid="chat-message-container"] {
    background-color: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text-color); padding: 10px; transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--secondary-background-color); }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--secondary-background-color); color: var(--primary-color); border-bottom: 3px solid var(--primary-color);
}
div[data-testid="stVerticalBlock"] {
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

init_session_state()


def landing_page():
    """Render the landing page."""
    st.title("Welcome to 🤝 Nyay-Saathi")
    st.subheader("Your AI legal friend, built for India.")
    st.markdown("This tool helps you understand complex legal documents and get clear, simple action plans.")
    st.markdown("---")

    if st.button("Click here to start", type="primary"):
        st.session_state.app_started = True
        st.rerun()


def render_tab_samjhao():
    """Render the document explanation tab."""
    st.header("Upload a Legal Document to Explain")
    st.write("Take a photo (or upload a PDF) of your legal notice or agreement.")

    uploaded_file = st.file_uploader(
        "Choose a file...",
        type=["jpg", "jpeg", "png", "pdf"],
        key=st.session_state.file_uploader_key
    )

    if uploaded_file is not None:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File too large! Maximum size is {MAX_FILE_SIZE_MB}MB. Your file is {file_size_mb:.2f}MB.")
            return

        new_file_bytes = uploaded_file.getvalue()
        if new_file_bytes != st.session_state.uploaded_file_bytes:
            st.session_state.uploaded_file_bytes = new_file_bytes
            st.session_state.uploaded_file_type = uploaded_file.type
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.samjhao_explanation = None
            st.session_state.document_context = "No document uploaded."
            st.session_state.document_extracted = False

    if st.session_state.uploaded_file_bytes is not None:
        display_uploaded_document(st.session_state.uploaded_file_bytes, st.session_state.uploaded_file_type)

        if st.button("Samjhao!", type="primary", key="samjhao_button"):
            spinner_text = "Your friend is reading and explaining..."
            if "image" in st.session_state.uploaded_file_type:
                spinner_text = "Reading your image... (this can take 15-30s)"

            with st.spinner(spinner_text):
                try:
                    result = extract_and_explain_document(
                        st.session_state.uploaded_file_bytes,
                        st.session_state.uploaded_file_type,
                        st.session_state.language
                    )

                    st.session_state.samjhao_explanation = result["explanation"]
                    st.session_state.document_context = result["extracted_text"]
                    st.session_state.document_extracted = True

                except Exception as e:
                    st.error(f"Error processing document: {e}")
                    st.warning("Please try again or contact support if the issue persists.")

    if st.session_state.samjhao_explanation:
        st.subheader(f"Here's what it means in {st.session_state.language}:")
        st.markdown(st.session_state.samjhao_explanation)

    if st.session_state.document_context != "No document uploaded." and st.session_state.samjhao_explanation:
        st.success("Context Saved! You can now ask questions about this document in the 'Kya Karoon?' tab.")


def render_tab_kya_karoon():
    """Render the Q&A tab."""
    st.header("Ask for a simple action plan")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Scared? Confused? Ask a question and get a simple 3-step plan **based on real guides.**")
    with col2:
        if st.button("Clear Chat ♻️"):
            clear_session()
            st.rerun()

    if st.session_state.document_context != "No document uploaded.":
        with st.container():
            st.info("**Context Loaded:** I have your uploaded document in memory. Feel free to ask questions about it!")

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            guides_sources = message.get("sources_from_guides")
            doc_context_used = message.get("source_from_document")

            if (guides_sources and len(guides_sources) > 0) or doc_context_used:
                st.subheader("Sources I used:")

                if doc_context_used:
                    st.warning(f"**From Your Uploaded Document:**\n\n...{st.session_state.document_context[:500]}...")

                if guides_sources:
                    for doc in guides_sources:
                        st.info(f"**From {doc.metadata.get('source', 'Unknown Guide')}:**\n\n...{doc.page_content}...")

            if message["role"] == "assistant" and message.get("id"):
                feedback_key = f"feedback_{i}"
                c1, c2, _ = st.columns([1, 1, 5])
                with c1:
                    if st.button("👍", key=f"{feedback_key}_up"):
                        try:
                            add_feedback(message["id"], st.session_state.user_id, 1)
                            log_event(st.session_state.user_id, "feedback_positive", {"message_id": message["id"]})
                            st.toast("Thanks for your feedback!")
                        except Exception as e:
                            st.warning("Could not save feedback")
                with c2:
                    if st.button("👎", key=f"{feedback_key}_down"):
                        try:
                            add_feedback(message["id"], st.session_state.user_id, -1)
                            log_event(st.session_state.user_id, "feedback_negative", {"message_id": message["id"]})
                            st.toast("Thanks for your feedback!")
                        except Exception as e:
                            st.warning("Could not save feedback")

    if prompt := st.chat_input(f"Ask your follow-up question in {st.session_state.language}..."):
        add_message("user", prompt)

        with st.spinner("Your friend is checking the guides..."):
            try:
                chat_history = get_chat_history_string(limit=6)
                current_doc_context = st.session_state.document_context

                response, docs = invoke_rag(
                    question=prompt,
                    language=st.session_state.language,
                    chat_history=chat_history,
                    document_context=current_doc_context
                )

                used_document = False

                if not docs and current_doc_context != "No document uploaded.":
                    with st.spinner("Auditing response source..."):
                        used_document = check_if_response_from_document(
                            prompt,
                            response,
                            current_doc_context
                        )

                message_id = str(uuid.uuid4())
                add_message("assistant", response, sources=docs, used_document=used_document, message_id=message_id)

                if st.session_state.current_session_id:
                    try:
                        db_add_message(
                            session_id=st.session_state.current_session_id,
                            role="user",
                            content=prompt,
                            sources=[],
                            used_document=False
                        )
                        db_add_message(
                            session_id=st.session_state.current_session_id,
                            role="assistant",
                            content=response,
                            sources=[doc.metadata.get("source", "") for doc in docs] if docs else [],
                            used_document=used_document
                        )
                    except Exception as e:
                        pass

                truncate_messages_if_needed(max_messages=20)
                log_event(st.session_state.user_id, "question_asked", {"question": prompt[:100]})

                st.rerun()

            except Exception as e:
                st.error(f"An error occurred: {e}")
                log_event(st.session_state.user_id, "error", {"error": str(e)[:100]})


def main():
    """Main app logic."""
    if not st.session_state.app_started:
        landing_page()
    else:
        st.title("🤝 Nyay-Saathi (Justice Companion)")
        st.markdown("Your legal friend, in your pocket. Built for India.")

        col1, col2 = st.columns([3, 1])
        with col1:
            language = st.selectbox(
                "Choose your language:",
                LANGUAGES,
                index=LANGUAGES.index(st.session_state.language) if st.session_state.language in LANGUAGES else 0
            )
            st.session_state.language = language
        with col2:
            st.write("")
            st.write("")
            if st.button("Start New Session ♻️", type="primary"):
                clear_session()
                st.rerun()

        st.divider()

        tab1, tab2 = st.tabs(["**Samjhao** (Explain this Document)", "**Kya Karoon?** (Ask a Question)"])

        with tab1:
            render_tab_samjhao()

        with tab2:
            render_tab_kya_karoon()

        st.divider()
        st.error("""
**Disclaimer:** I am an AI, not a lawyer. This is not legal advice.
Please consult a real lawyer or contact your local **NALSA (National Legal Services Authority)** for free legal aid.
""")


if __name__ == "__main__":
    try:
        if "user_id" not in st.session_state:
            st.session_state.user_id = "user_" + str(hash(st.session_id))[:16]

        get_or_create_user(st.session_state.user_id)
        log_event(st.session_state.user_id, "session_started", {})

        if "current_session_id" not in st.session_state or st.session_state.current_session_id is None:
            session = create_session(st.session_state.user_id, st.session_state.language)
            st.session_state.current_session_id = session["id"]

        main()

    except Exception as e:
        st.error(f"Application error: {e}")
        st.warning("Please refresh the page and try again.")
