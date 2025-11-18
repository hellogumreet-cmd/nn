import streamlit as st
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from config import DB_FAISS_PATH, MODEL_NAME, EMBEDDING_MODEL


@st.cache_resource
def get_embeddings():
    """Get cached embeddings model."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}
    )


@st.cache_resource
def get_vector_store():
    """Get cached FAISS vector store."""
    try:
        embeddings = get_embeddings()
        db = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        return db
    except Exception as e:
        st.error(f"Error loading vector store: {e}")
        st.error("Did you run 'ingest.py' and push the 'vectorstores' folder to GitHub?")
        st.stop()


@st.cache_resource
def get_retriever():
    """Get cached retriever from vector store."""
    db = get_vector_store()
    return db.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": 3,
            "score_threshold": 0.3
        }
    )


@st.cache_resource
def get_llm():
    """Get cached LLM instance."""
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
    except Exception as e:
        st.error(f"Error configuring LLM: {e}")
        st.error("Please check your API key in Streamlit Secrets.")
        st.stop()


@st.cache_resource
def get_generative_model():
    """Get cached generative model for document analysis."""
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        st.error(f"Error configuring generative model: {e}")
        st.error("Please check your API key in Streamlit Secrets.")
        st.stop()
