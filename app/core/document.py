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
    # Filter ESG-related content   add to list
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


# Process OCR text and split into chunks
async def process_ocr_text(ocr_text: str, metadata: dict = None) -> List[Document]:
    """Process OCR text and return chunks"""
    # Create a Document object from OCR text
    if metadata is None:
        metadata = {}
    
    document = Document(page_content=ocr_text, metadata=metadata)
    
    # Filter ESG-related content
    esg_documents = []
    if is_esg_related(document.page_content):
        esg_documents.append(document)
    
    # Check if empty - fallback to all content if no ESG content found
    if not esg_documents:
        esg_documents = [document]
    
    # Split documents
    chunks = text_splitter.split_documents(esg_documents)
    return chunks
