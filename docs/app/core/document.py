from typing import List
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from app.core.utils import is_esg_related
from app.core.vector_store import text_splitter

# 解析pdf并切块
async def process_pdf_document(file_path: str) -> List[Document]:
    """Process PDF document and return chunks"""
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    # Filter ESG-related content   add to list
    esg_documents = []
    for doc in documents:
        if is_esg_related(doc.page_content):
            esg_documents.append(doc)
    # 检查是否为空
    if not esg_documents:
        esg_documents = documents  # Fallback to all documents
    # Split documents
    chunks = text_splitter.split_documents(esg_documents)
    return chunks 