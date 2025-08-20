from langchain.text_splitter import RecursiveCharacterTextSplitter
from gw_api.config import (
    GOOGLE_API_KEY,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings


# Updated embedding model initialization
# embedding_model = AzureOpenAIEmbeddings(
#     azure_endpoint=AZURE_OPENAI_ENDPOINT_2,
#     api_key=AZURE_OPENAI_API_KEY_2,
#     api_version="2023-05-15",
#     azure_deployment="text-embedding-3-large",  # Changed from deployment_name
#     chunk_size=100
# )

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-exp-03-07", google_api_key=GOOGLE_API_KEY
)


# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
)


def load_vector_store(session_id: str):
    """Load persisted vector store from disk"""
    from pathlib import Path
    from gw_api.config import VECTOR_STORE_DIR

    persist_path = VECTOR_STORE_DIR / session_id
    if not persist_path.exists():
        return None
    from langchain_community.vectorstores import Chroma

    return Chroma(
        persist_directory=str(persist_path), embedding_function=embedding_model
    )
