from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.utils.language import detect_language, is_esg_related_multilingual
from app.config import SUPPORTED_LANGUAGES
from langchain.schema import Document
from typing import List, Tuple

# 创建分割器

def create_text_splitter(language: str) -> RecursiveCharacterTextSplitter:
    separators = {
        'en': ["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        'de': ["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        'it': ["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    }
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=separators.get(language, separators['en'])
    )

async def process_pdf_document_multilingual(file_path: str) -> Tuple[List[Document], str]:
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    sample_text = " ".join([doc.page_content for doc in documents[:3]])
    detected_language = detect_language(sample_text)
    esg_documents = []
    for doc in documents:
        if is_esg_related_multilingual(doc.page_content, detected_language):
            esg_documents.append(doc)
    if not esg_documents:
        esg_documents = documents
    text_splitter = create_text_splitter(detected_language)
    chunks = text_splitter.split_documents(esg_documents)
    return chunks, detected_language 