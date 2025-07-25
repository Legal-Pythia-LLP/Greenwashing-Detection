from langchain_openai import AzureChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

from app.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT

# Initialize LangChain components with updated parameters
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2023-07-01-preview",
    azure_deployment="gpt-4o-mini",  # Changed from deployment_name
    temperature=0.1,
    streaming=True,
    callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
)

# Initialize ClimateBERT
climatebert_model_name = "climatebert/distilroberta-base-climate-f"
try:
    climatebert_tokenizer = AutoTokenizer.from_pretrained(
        climatebert_model_name, local_files_only=False
    )
    climatebert_model = AutoModelForSequenceClassification.from_pretrained(
        climatebert_model_name, local_files_only=False
    )
except Exception as e:
    print(f"Warning: Could not load ClimateBERT model: {e}")
    print("ESG classification will be disabled.")
    climatebert_tokenizer = None
    climatebert_model = None 