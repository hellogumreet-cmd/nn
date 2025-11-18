import streamlit as st
import json
from PIL import Image
import io
from config import EXTRACT_DOCUMENT_PROMPT_TEMPLATE
from models import get_generative_model


def display_uploaded_document(file_bytes: bytes, file_type: str):
    """Display the uploaded document based on type."""
    if "image" in file_type:
        image = Image.open(io.BytesIO(file_bytes))
        st.image(image, caption="Your Uploaded Document", use_column_width=True)
    elif "pdf" in file_type:
        st.info("PDF file uploaded. Click 'Samjhao!' to explain.")


def extract_and_explain_document(file_bytes: bytes, file_type: str, language: str):
    """Extract text and generate explanation from document."""
    try:
        model = get_generative_model()

        prompt_text = EXTRACT_DOCUMENT_PROMPT_TEMPLATE.format(
            file_type=file_type,
            language=language
        )

        data_part = {"mime_type": file_type, "data": file_bytes}
        response = model.generate_content([prompt_text, data_part])

        clean_response = response.text.strip().replace("```json", "").replace("```", "")
        response_json = json.loads(clean_response)

        return {
            "extracted_text": response_json.get("raw_text", ""),
            "explanation": response_json.get("explanation", "")
        }
    except json.JSONDecodeError:
        raise ValueError("AI response was not in valid JSON format")
    except Exception as e:
        raise Exception(f"Error processing document: {str(e)}")


def check_if_response_from_document(question: str, response: str, document_context: str) -> bool:
    """Audit whether response came primarily from the uploaded document."""
    if not document_context or document_context == "No document uploaded.":
        return False

    try:
        model = get_generative_model()

        audit_prompt = f"""
You are an auditor.
Question: "{question}"
Answer: "{response}"
Context: "{document_context[:1000]}"

Did the "Answer" come *primarily* from the "Context"?
Respond with ONLY the word 'YES' or 'NO'.
"""

        audit_response = model.generate_content(audit_prompt)

        return "YES" in audit_response.text.upper()
    except Exception as e:
        st.warning(f"Could not audit response source: {str(e)}")
        return False
