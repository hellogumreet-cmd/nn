import os

DB_FAISS_PATH = "vectorstores/db_faiss"
MODEL_NAME = "gemini-2.5-flash"
MAX_MESSAGE_HISTORY = 8
MAX_FILE_SIZE_MB = 20
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

LANGUAGES = [
    "Simple English",
    "Hindi (in Roman script)",
    "Kannada",
    "Tamil",
    "Telugu",
    "Marathi"
]

DEFAULT_LANGUAGE = "Simple English"

RAG_PROMPT_TEMPLATE = """
You are 'Nyay-Saathi,' a kind legal friend.
A common Indian citizen is asking for help.
You have two sources of information. Prioritize the MOST relevant one.
1. CONTEXT_FROM_GUIDES: (General guides from a database)
{context}

2. DOCUMENT_CONTEXT: (Specific text from a document the user uploaded)
{document_context}

Answer the user's 'new question' based on the most relevant context.
If the 'new question' is a follow-up, use the 'chat history' to understand it.
Do not use any legal jargon.
Give a simple, step-by-step action plan in the following language: {language}.
If no context is relevant, just say "I'm sorry, I don't have enough information on that. Please contact NALSA."

CHAT HISTORY:
{chat_history}

NEW QUESTION:
{question}

Your Simple, Step-by-Step Action Plan (in {language}):
"""

AUDIT_PROMPT_TEMPLATE = """
You are an auditor.
Question: "{question}"
Answer: "{response}"
Context: "{context}"

Did the "Answer" come *primarily* from the "Context"?
Respond with ONLY the word 'YES' or 'NO'.
"""

EXTRACT_DOCUMENT_PROMPT_TEMPLATE = """
You are an AI assistant. The user has uploaded a document (MIME type: {file_type}).
Perform two tasks:
1. Extract all raw text from the document.
2. Explain the document in simple, everyday {language}.

Respond with ONLY a JSON object in this format:
{{
  "raw_text": "The raw extracted text...",
  "explanation": "Your simple {language} explanation..."
}}
"""

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")
