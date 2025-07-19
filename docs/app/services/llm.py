from app.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY_2, AZURE_OPENAI_ENDPOINT_2
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager

# LLM 实例
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-07-01-preview",
    azure_deployment="gpt-4o-mini",
    temperature=0.1,
    streaming=True,
    callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
)

# Embedding Model 实例
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_ENDPOINT_2,
    api_key=AZURE_OPENAI_API_KEY_2,
    api_version="2023-05-15",
    azure_deployment="text-embedding-3-large",
    chunk_size=100
) 