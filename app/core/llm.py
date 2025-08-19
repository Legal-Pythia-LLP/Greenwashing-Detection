from langchain_openai import AzureChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

from app.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# -------------------------------
# Initialize LLM
# -------------------------------

# Option 1: Azure OpenAI
# llm = AzureChatOpenAI(
#     azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     api_key=AZURE_OPENAI_API_KEY,
#     api_version="2023-07-01-preview",
#     azure_deployment="gpt-4o-mini",  # GPT-4o-mini deployment
#     temperature=0.1,
#     streaming=True,
#     callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
# )

# Option 2: Google Gemini LLM
llm = ChatGoogleGenerativeAI(
  model="gemini-2.0-flash",  # flash is faster
  temperature=0,  # Controls text generation "randomness" - 0 means completely deterministic, 0.7 slightly creative, 1.0 more random
  max_tokens=None,  # Maximum tokens to generate - None means use model default (can be omitted)
  timeout=None,  # Maximum wait time per request - None means default wait, can set to 60s etc
  max_retries=2,  # Max retries on error - recommended 2-3
    # other params...
)

# -------------------------------
# Initialize ClimateBERT for ESG classification
# -------------------------------
climatebert_model_name = "climatebert/distilroberta-base-climate-f"

try:
    climatebert_tokenizer = AutoTokenizer.from_pretrained(
        climatebert_model_name, local_files_only=False
    )
    climatebert_model = AutoModelForSequenceClassification.from_pretrained(
        climatebert_model_name, local_files_only=False
    )
except Exception as e:
    print(f"[Warning] Could not load ClimateBERT model: {e}")
    print("ESG classification will be disabled.")
    climatebert_tokenizer = None
    climatebert_model = None
