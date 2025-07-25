from langchain_openai import AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import AZURE_OPENAI_ENDPOINT_2, AZURE_OPENAI_API_KEY_2

# Updated embedding model initialization
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_ENDPOINT_2,
    api_key=AZURE_OPENAI_API_KEY_2,
    api_version="2023-05-15",
    azure_deployment="text-embedding-3-large",  # Changed from deployment_name
    chunk_size=100
)

# Text splitter 文本切分器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
) 