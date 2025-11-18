from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter
from config import RAG_PROMPT_TEMPLATE
from models import get_retriever, get_llm


def format_docs(docs):
    """Format retrieved documents for RAG prompt."""
    return "\n\n".join(doc.page_content for doc in docs)


def build_rag_chain():
    """Build the RAG chain with document retrieval and LLM generation."""
    retriever = get_retriever()
    llm = get_llm()
    rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

    rag_chain = RunnableParallel(
        {
            "context": itemgetter("question") | retriever,
            "question": itemgetter("question"),
            "language": itemgetter("language"),
            "chat_history": itemgetter("chat_history"),
            "document_context": itemgetter("document_context")
        }
    ) | {
        "answer": (
            {
                "context": lambda x: format_docs(x["context"]),
                "question": itemgetter("question"),
                "language": itemgetter("language"),
                "chat_history": itemgetter("chat_history"),
                "document_context": itemgetter("document_context")
            }
            | rag_prompt
            | llm
            | StrOutputParser()
        ),
        "sources": itemgetter("context")
    }

    return rag_chain


def invoke_rag(question: str, language: str, chat_history: str, document_context: str):
    """Invoke RAG chain with error handling."""
    try:
        rag_chain = build_rag_chain()

        payload = {
            "question": question,
            "language": language,
            "chat_history": chat_history,
            "document_context": document_context
        }

        result = rag_chain.invoke(payload)
        return result["answer"], result["sources"]
    except Exception as e:
        raise Exception(f"RAG chain error: {str(e)}")
