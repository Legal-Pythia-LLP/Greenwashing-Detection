from langchain_openai import AzureChatOpenAI
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

from app.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings



# Initialize LangChain components with updated parameters
# llm = AzureChatOpenAI(
#     azure_endpoint=AZURE_OPENAI_ENDPOINT,
#     api_key=AZURE_OPENAI_API_KEY,
#     api_version="2023-07-01-preview",
#     azure_deployment="gpt-4o-mini",  # Changed from deployment_name
#     temperature=0.1,
#     streaming=True,
#     callback_manager=CallbackManager([StreamingStdOutCallbackHandler()])
# )

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",  # flash比较快
    temperature=0,  # 控制生成文本的“随机性” 0 表示完全确定，0.7 稍微有创造性，1.0 比较随机
    max_tokens=None,  # 最多生成多少 token（字词） None 表示使用模型默认（可不写）
    timeout=None,  # 单次请求最长等待时间 None 表示默认等待，可设置为 60 秒等
    max_retries=2,  # max_retries出错时重试次数 推荐设置为 2~3
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