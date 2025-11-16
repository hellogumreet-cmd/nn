import streamlit as st
import google.generativeai as genai
import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from operator import itemgetter
from PIL import Image 
from langchain_core.messages import HumanMessage 
import base64

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(page_title="Nyay-Saathi", page_icon="🤝", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
/* ... (Your custom CSS is here, hidden for brevity) ... */
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
/* Style the chat messages */
div[data-testid="chat-message-container"] {
    background-color: var(--secondary-background-color);
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
}
/* This is the tab styling from before */
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text-color); padding: 10px; transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--secondary-background-color); }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--secondary-background-color); color: var(--primary-color); border-bottom: 3px solid var(--primary-color);
}
</style>
""", unsafe_allow_html=True)


# --- API KEY CONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception as e:
    st.error(f"Error configuring: {e}. Please check your API key in Streamlit Secrets.")
    st.stop()

DB_FAISS_PATH = "vectorstores/db_faiss"
MODEL_NAME = "gemini-2.5-flash-lite"


# --- RAG PROMPT TEMPLATE ---
# --- NEW: Updated prompt to accept document_context ---
rag_prompt_template = """
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

# --- LOAD THE MODEL & VECTOR STORE ---
@st.cache_resource
def get_models_and_db():
    try:
        embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2',
                                           model_kwargs={'device': 'cpu'})
        db = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
        
        retriever = db.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": 3,
                "score_threshold": 0.3
            }
        )
        
        return retriever, llm
    except Exception as e:
        st.error(f"Error loading models or vector store: {e}")
        st.error("Did you run 'ingest.py' and push the 'vectorstores' folder to GitHub?")
        st.stop()

retriever, llm = get_models_and_db()

# --- NEW HELPER FUNCTION ---
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# --- THE RAG CHAIN ---
# --- NEW: Updated RAG chain to accept document_context ---
rag_prompt = PromptTemplate.from_template(rag_prompt_template)

rag_chain_with_sources = RunnableParallel(
    {
        "context": itemgetter("question") | retriever,
        "question": itemgetter("question"),
        "language": itemgetter("language"),
        "chat_history": itemgetter("chat_history"),
        "document_context": itemgetter("document_context") # Pass through
    }
) | {
    "answer": (
        {
            "context": (lambda x: format_docs(x["context"])),
            "question": itemgetter("question"),
            "language": itemgetter("language"),
            "chat_history": itemgetter("chat_history"),
            "document_context": itemgetter("document_context") # Pass to prompt
        }
        | rag_prompt
        | llm
        | StrOutputParser()
    ),
    "sources": itemgetter("context") # Sources still come from the retriever
}

# --- THE APP UI ---
st.title("🤝 Nyay-Saathi (Justice Companion)")
st.markdown("Your legal friend, in your pocket. Built for India.")

# --- LANGUAGE SELECTOR ---
language = st.selectbox(
    "Choose your language:",
    ("Simple English", "Hindi (in Roman script)", "Kannada", "Tamil", "Telugu", "Marathi")
)

st.divider()

# --- THE TAB-BASED LAYOUT ---
tab1, tab2 = st.tabs(["**Samjhao** (Explain this Document)", "**Kya Karoon?** (Ask a Question)"])

# --- TAB 1: SAMJHAO (EXPLAIN) ---
with tab1:
    st.header("Upload a Legal Document to Explain")
    st.write("Take a photo (or upload a PDF) of your legal notice or agreement.")
    
    uploaded_file = st.file_uploader("Choose a file...", type=["jpg", "jpeg", "png", "pdf"])
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_type = uploaded_file.type
        
        if "image" in file_type:
            image = Image.open(uploaded_file)
            st.image(image, caption="Your Uploaded Document", use_column_width=True)
        elif "pdf" in file_type:
            st.info("PDF file uploaded. Click 'Samjhao!' to explain.")
        
        if st.button("Samjhao!", type="primary", key="samjhao_button"):
            
            # --- NEW: We will run two AI calls ---
            
            # 1. The original "Explain" call
            with st.spinner("Your friend is reading and explaining..."):
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    
                    prompt_text_explain = f"""
                    You are 'Nyay-Saathi,' a kind legal friend.
                    The user has uploaded a document (MIME type: {file_type}).
                    First, extract all the text you can see from this document.
                    Then, explain that extracted text in simple, everyday {language}.
                    Do not use any legal jargon.
                    Identify the 3 most important parts for the user (like dates, names, or actions they must take).
                    The user is scared and confused. Be kind and reassuring.

                    Your Simple {language} Explanation:
                    """
                    
                    data_part = {'mime_type': file_type, 'data': file_bytes}
                    response_explain = model.generate_content([prompt_text_explain, data_part])
                    
                    if response_explain.text:
                        st.subheader(f"Here's what it means in {language}:")
                        st.markdown(response_explain.text)
                    else:
                        st.error("The AI could not read the document. Please try a clearer file.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            
            # 2. The new "Extract and Save" call
            with st.spinner("Saving document context for chat..."):
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    prompt_text_extract = "Extract all text from this document. Respond with ONLY the raw text, no other conversation or pleasantries."
                    
                    data_part = {'mime_type': file_type, 'data': file_bytes}
                    response_extract = model.generate_content([prompt_text_extract, data_part])
                    
                    if response_extract.text:
                        # Save the raw text to the session state
                        st.session_state.document_context = response_extract.text
                        st.success("Context Saved! You can now ask questions about this document in the 'Kya Karoon?' tab.")
                    else:
                        st.warning("Could not extract text to save for chat.")
                        
                except Exception as e:
                    st.warning(f"Could not save context: {e}")

# --- TAB 2: KYA KAROON? (WHAT TO DO?) ---
with tab2:
    st.header("Ask for a simple action plan")
    st.write("Scared? Confused? Ask a question and get a simple 3-step plan **based on real guides.**")

    # 1. Initialize all session state variables
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "document_context" not in st.session_state:
        st.session_state.document_context = "No document uploaded." # Set a default

    # 2. Display a message if context is loaded
    if st.session_state.document_context != "No document uploaded.":
        with st.container():
            st.info(f"**Context Loaded:** I have your uploaded document in memory. Feel free to ask questions about it!")

    # 3. Display all past messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # --- THIS IS THE FIX ---
            # 3a. Get all possible sources from the message
            guides_sources = message.get("sources_from_guides") # This is a list
            doc_context_used = message.get("source_from_document")   # This is a boolean

            # 3b. Only show the header if *any* source exists
            if (guides_sources and len(guides_sources) > 0) or doc_context_used:
                st.subheader("Sources I used:")
                
                # 3c. Display the document context if it was used
                if doc_context_used:
                    st.warning(f"**From Your Uploaded Document:**\n\n...{st.session_state.document_context[:500]}...") # Show a 500-char snippet
                
                # 3d. Display the guide sources if they were found
                if guides_sources:
                    for doc in guides_sources:
                        st.info(f"**From {doc.metadata.get('source', 'Unknown Guide')}:**\n\n...{doc.page_content}...")
            # --- END OF FIX ---

    # 4. Define the chat input box
    if prompt := st.chat_input(f"Ask your follow-up question in {language}..."):
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Your friend is checking the guides..."):
            try:
                chat_history_str = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:-1]])
                
                # 4a. Get the context that will be used for *this* specific turn
                current_doc_context = st.session_state.document_context
                
                invoke_payload = {
                    "question": prompt,
                    "language": language,
                    "chat_history": chat_history_str,
                    "document_context": current_doc_context # Pass the saved context
                }
                
                response_dict = rag_chain_with_sources.invoke(invoke_payload) 
                response = response_dict["answer"]
                docs = response_dict["sources"]
                
                # --- THIS IS THE FIX ---
                # 4b. Check if the AI *likely* used the document.
                # A simple check: if no guides were found, the AI *must* have used the document.
                # A smarter check would be to ask the AI, but this is faster.
                used_document = False
                if not docs and current_doc_context != "No document uploaded.":
                    used_document = True

                # 4c. Save ALL sources to the session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "sources_from_guides": docs,
                    "source_from_document": used_document # Save True/False
                })
                # --- END OF FIX ---
                
                st.rerun()
            
            except Exception as e:
                st.error(f"An error occurred during RAG processing: {e}")

# --- DISCLAIMER (At the bottom, full width) ---
st.divider()
st.error("""
**Disclaimer:** I am an AI, not a lawyer. This is not legal advice.
Please consult a real lawyer or contact your local **NALSA (National Legal Services Authority)** for free legal aid.
""")