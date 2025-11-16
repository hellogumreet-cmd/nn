import streamlit as st
import google.generativeai as genai
import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from operator import itemgetter
from PIL import Image # <--- NEW IMPORT FOR IMAGE HANDLING
from langchain_core.messages import HumanMessage # <--- NEW IMPORT FOR MULTIMODAL

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
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text-color); padding: 10px; transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--secondary-background-color); }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: var(--secondary-background-color); color: var(--primary-color); border-bottom: 3px solid var(--primary-color);
}
.stTextArea textarea {
    background-color: var(--secondary-background-color); color: var(--text-color);
    border: 1px solid var(--primary-color); border-radius: 8px;
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


# --- RAG PROMPT TEMPLATE (for Tab 2) ---
# This is NOT used for the image tab
rag_prompt_template = """
You are 'Nyay-Saathi,' a kind legal friend.
A common Indian citizen is asking for help.
Base your answer ONLY on the context provided below.
Do not use any legal jargon.
Give a simple, 3-step action plan in the following language: {language}.
If the context is not enough, just say "I'm sorry, I don't have enough information on that. Please contact NALSA."

CONTEXT:
{context}

QUESTION:
{question}

Your Simple, 3-Step Action Plan (in {language}):
"""

# --- LOAD THE MODEL & VECTOR STORE ---
@st.cache_resource
def load_models_and_db():
    try:
        embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2',
                                           model_kwargs={'device': 'cpu'})
        db = FAISS.load_local(DB_FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
        llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
        return db.as_retriever(), llm
    except Exception as e:
        st.error(f"Error loading models or vector store: {e}")
        st.error("Did you run 'ingest.py' and push the 'vectorstores' folder to GitHub?")
        st.stop()

retriever, llm = load_models_and_db()

# --- THE RAG CHAIN (for Tab 2) ---
rag_prompt = PromptTemplate.from_template(rag_prompt_template)
rag_chain = (
    {
        "context": itemgetter("question") | retriever,
        "question": itemgetter("question"),
        "language": itemgetter("language")
    }
    | rag_prompt
    | llm
    | StrOutputParser()
)

# --- THE APP UI ---
st.title("🤝 Nyay-Saathi (Justice Companion)")
st.markdown("Your legal friend, in your pocket. Built for India.")

# --- LANGUAGE SELECTOR ---
language = st.selectbox(
    "Choose your language:",
    ("Simple English", "Hindi (in Roman script)", "Kannada", "Tamil", "Telugu", "Marathi")
)

st.divider()

tab1, tab2 = st.tabs(["**Samjhao** (Explain this Document)", "**Kya Karoon?** (Ask a Question)"])

# --- TAB 1: SAMJHAO (EXPLAIN) - NOW WITH IMAGE UPLOAD ---
with tab1:
    st.header("Upload a Legal Document to Explain")
    st.write("Take a photo of your legal notice or agreement and upload it here.")
    
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Display the uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Your Uploaded Document", use_column_width=True)
        
        if st.button("Samjhao!", type="primary", key="samjhao_button"):
            with st.spinner("Your friend is reading the document..."):
                try:
                    # Get the image bytes
                    image_bytes = uploaded_file.getvalue()
                    
                    # Create the new multimodal prompt
                    prompt_text = f"""
                    You are 'Nyay-Saathi,' a kind legal friend.
                    The user has uploaded an image of a legal document.
                    First, extract all the text you can see from this image.
                    Then, explain that extracted text in simple, everyday {language}.
                    Do not use any legal jargon.
                    Identify the 3 most important parts for the user (like dates, names, or actions they must take).
                    The user is scared and confused. Be kind and reassuring.

                    Your Simple {language} Explanation:
                    """
                    
                    # Create the multimodal message
                    message = HumanMessage(
                        content=[
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": image_bytes}
                        ]
                    )
                    
                    # Invoke the LLM with the multimodal message
                    response = llm.invoke([message])
                    
                    if response.content:
                        st.subheader(f"Here's what it means in {language}:")
                        st.markdown(response.content)
                    else:
                        st.error("The AI could not read the document. Please try a clearer picture.")
                        
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# --- TAB 2: KYA KAROON? (WHAT TO DO?) ---
# This tab is 100% UNCHANGED and still works.
with tab2:
    st.header("Ask for a simple action plan")
    st.write("Scared? Confused? Ask a question and get a simple 3-step plan **based on real guides.**")
    user_question = st.text_input("Ask your question (e.g., 'My landlord is threatening to evict me')")
    
    if st.button("Get Plan", type="primary", key="kya_karoon_button"):
        if not user_question:
            st.warning("Please ask a question.")
        else:
            with st.spinner("Your friend is checking the guides..."):
                try:
                    docs = retriever.get_relevant_documents(user_question)
                    invoke_payload = {"question": user_question, "language": language}
                    response = rag_chain.invoke(invoke_payload)
                    
                    if response:
                        st.subheader(f"Here is a simple 3-step plan (in {language}):")
                        st.markdown(response)
                        st.divider()
                        st.subheader("Sources I used to answer you:")
                        if docs:
                            for doc in docs:
                                st.info(f"**From {doc.metadata.get('source', 'Unknown Guide')}:**\n\n...{doc.page_content}...")
                        else:
                            st.write("No specific sources were needed for this query.")
                except Exception as e:
                    st.error(f"An error occurred during RAG processing: {e}")

# --- DISCLAIMER ---
st.divider()
st.error("""
**Disclaimer:** I am an AI, not a lawyer. This is not legal advice.
Please consult a real lawyer or contact your local **NALSA (National Legal Services Authority)** for free legal aid.
""")