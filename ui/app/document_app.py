import streamlit as st
import requests
import os
from config import API_URL

st.set_page_config(page_title="Document Understanding UI", layout="wide")
st.title("📄 Intelligent Document Understanding")

# Helper to get document types and fields
def get_document_types():
    try:
        resp = requests.get(f"{API_URL}/types")
        resp.raise_for_status()
        data = resp.json()
        return data.get("supported_types", []), data.get("document_types", {})
    except Exception as e:
        st.error(f"Failed to fetch document types: {e}")
        return [], {}

doc_types, doc_type_fields = get_document_types()

tabs = st.tabs(["Classify & Extract", "Batch Extract Entities"])

# --- Tab 1: Classify & Extract (single file) ---
with tabs[0]:
    st.header("Classify and Extract from a Document")
    uploaded_file = st.file_uploader("Upload a document (PDF, image)", type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"], key="single_upload")
    include_raw_text = st.checkbox("Include raw OCR text in response", value=False)
    if uploaded_file:
        if st.button("Process Document", key="process_single"):
            with st.spinner("Processing..."):
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                params = {"include_raw_text": str(include_raw_text).lower()}
                try:
                    resp = requests.post(f"{API_URL}/extract_entities", files=files, params=params)
                    resp.raise_for_status()
                    result = resp.json()
                    st.success(f"Document classified as: {result['document_type']} (confidence: {result['confidence']:.2f})")
                    st.json(result)
                    if "entities" in result:
                        st.subheader("Extracted Entities")
                        st.json(result["entities"])
                    if include_raw_text and "raw_text" in result:
                        st.subheader("Raw OCR Text")
                        st.code(result["raw_text"])
                except Exception as e:
                    st.error(f"Error: {e}")

# --- Tab 2: Batch Extract Entities ---
with tabs[1]:
    st.header("Batch Entity Extraction")
    st.write("Upload multiple files, select document type and fields, and extract entities from all.")
    batch_files = st.file_uploader("Upload multiple documents (PDF, image)", type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"], accept_multiple_files=True, key="multi_upload")
    if batch_files:
        if st.button("Extract Entities from All", key="batch_extract"):
            results = []
            for file in batch_files:
                with st.spinner(f"Processing {file.name}..."):
                    files = {"file": (file.name, file, file.type)}
                    try:
                        resp = requests.post(f"{API_URL}/extract_entities", files=files)
                        resp.raise_for_status()
                        data = resp.json()
                        results.append({
                            "filename": file.name,
                            "document_type": data.get("document_type"),
                            "confidence": data.get("confidence"),
                            "entities": data.get("entities", {})
                        })
                    except Exception as e:
                        st.error(f"Error processing {file.name}: {e}")
            if results:
                st.success(f"Processed {len(results)} files.")
                for res in results:
                    st.subheader(f"Results for {res['filename']}")
                    st.write(f"**Document Type:** {res['document_type']} (Confidence: {res.get('confidence', 0):.2f})")
                    st.json(res["entities"])
