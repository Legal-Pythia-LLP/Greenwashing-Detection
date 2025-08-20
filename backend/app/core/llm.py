from langchain_openai import AzureChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

from app.config import GOOGLE_API_KEY

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


llm = ChatGoogleGenerativeAI(
  model="gemini-2.0-flash",  # flash is faster
  temperature=0,  # Controls text generation "randomness" - 0 means completely deterministic, 0.7 slightly creative, 1.0 more random
  max_tokens=None,  # Maximum tokens to generate - None means use model default (can be omitted)
  timeout=None,  # Maximum wait time per request - None means default wait, can set to 60s etc
  max_retries=2,  # Max retries on error - recommended 2-3
  google_api_key=GOOGLE_API_KEY
    # other params...
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
