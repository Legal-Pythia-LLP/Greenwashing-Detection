from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from app.core.utils import is_esg_related
from app.core.vector_store import text_splitter

# Parse PDF and split into chunks
async def process_pdf_document(file_path: str) -> List[Document]:
    """Process PDF document and return chunks"""
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    # Filter ESG-related content and add to list
    esg_documents = []
    for doc in documents:
        if is_esg_related(doc.page_content):
            esg_documents.append(doc)
    # Check if empty
    if not esg_documents:
        esg_documents = documents  # Fallback to all documents
    # Split documents
    chunks = text_splitter.split_documents(esg_documents)
    return chunks
